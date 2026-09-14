from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from .acclimation import CapabilityBaseline, HostAcclimation
from .drift import DriftAwareBaseline
from .rhythms import RhythmModel, TimeBucket

CHECKPOINT_SCHEMA_VERSION = 3


class CheckpointError(ValueError):
    """Raised for a malformed checkpoint payload or an unsupported schema version."""


def export_checkpoint(
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
    drift_baselines: dict[str, DriftAwareBaseline] | None = None,
    saved_at_tick: int | None = None,
) -> dict[str, Any]:
    """Serialize only safe, abstract descriptive state — never raw readings,
    timestamps or capability details (roadmap v0.37, extended v0.46).

    Every field written here is already part of what v0.33/v0.35/v0.36
    commit to exposing publicly: count/mean/variance. A single checkpoint
    on its own cannot reconstruct a specific past reading, so exporting and
    later importing one is explicit, user-triggered model persistence, not
    a telemetry log. This is *not* an unconditional non-reconstruction
    guarantee, though: two checkpoints of an already-established aggregate
    taken one sample apart can still be differenced to solve algebraically
    for that one new reading (see
    :meth:`~symbiont.host.adaptive.AdaptiveSenseModel.export`'s docstring,
    roadmap safety finding B01) — no mechanism here defends against that
    yet. ``saved_at_tick`` (v0.46) is an organism-relative tick counter,
    not a timestamp or calendar date — the same privacy discipline v0.35's
    ``TimeBucket`` already holds to.
    """
    payload: dict[str, Any] = {"schema_version": CHECKPOINT_SCHEMA_VERSION}

    if saved_at_tick is not None:
        payload["saved_at_tick"] = saved_at_tick

    if acclimation is not None:
        payload["acclimation"] = {
            capability_id: {"count": baseline.count, "mean": baseline.mean, "variance": baseline.variance}
            for capability_id in acclimation.acclimated_capabilities
            if (baseline := acclimation.baseline(capability_id)) is not None
        }

    if rhythm_model is not None:
        payload["rhythms"] = [
            {
                "percept_name": percept_name,
                "time_bucket": time_bucket.value,
                "count": baseline.count,
                "mean": baseline.mean,
                "variance": baseline.variance,
            }
            for percept_name, time_bucket in rhythm_model.learned_contexts
            if (baseline := rhythm_model.baseline(percept_name, time_bucket)) is not None
        ]

    if drift_baselines is not None:
        payload["drift"] = {
            name: {"count": baseline.count, "mean": baseline.mean, "variance": baseline.variance}
            for name, baseline in drift_baselines.items()
            if baseline.is_established
        }

    return payload


def _migrate_v1_to_v2(payload: dict[str, Any]) -> dict[str, Any]:
    """v1 checkpoints predate ``saved_at_tick`` — v2 makes it explicit but
    optional, defaulting to ``None`` (unknown) for anything migrated from
    v1 rather than guessing a tick count that was never recorded."""
    migrated = dict(payload)
    migrated["schema_version"] = 2
    migrated.setdefault("saved_at_tick", None)
    return migrated


def _migrate_v2_to_v3(payload: dict[str, Any]) -> dict[str, Any]:
    """v2 checkpoints predate the organism self-model (roadmap v0.53) — v3
    adds it as an empty, additive top-level key so a checkpoint saved before
    this milestone restores with a cold-start self-model rather than
    failing to load."""
    migrated = dict(payload)
    migrated["schema_version"] = 3
    migrated.setdefault("self_model", {})
    return migrated


_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
}


def _migrate_to_current(payload: dict[str, Any]) -> dict[str, Any]:
    version = payload.get("schema_version")
    seen: set[Any] = set()
    while version != CHECKPOINT_SCHEMA_VERSION:
        if version in seen:
            raise CheckpointError(f"migration loop detected at schema_version {version!r}")
        migration = _MIGRATIONS.get(version)
        if migration is None:
            raise CheckpointError(
                f"unsupported checkpoint schema_version {version!r}; expected "
                f"{CHECKPOINT_SCHEMA_VERSION} and no migration path is registered for it"
            )
        seen.add(version)
        payload = migration(payload)
        version = payload.get("schema_version")
    return payload


def import_checkpoint(
    payload: dict[str, Any],
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
) -> tuple[HostAcclimation, RhythmModel, dict[str, DriftAwareBaseline]]:
    """Reconstruct model instances from a checkpoint payload.

    A payload from an older schema version is migrated forward through the
    registered migration chain (roadmap v0.46) before being read; anything
    newer than this code understands, or older with no registered
    migration path, is refused outright rather than guessed at.

    Pass an existing ``acclimation``/``rhythm_model`` (matching the
    ``min_samples``/bound config the checkpoint was exported with) to
    restore into it rather than a freshly-defaulted one — a baseline
    exported once it passed a lower ``min_samples`` may otherwise not read
    back as "already learned" against a differently-configured instance.
    """
    if not isinstance(payload, dict):
        raise CheckpointError("checkpoint payload must be a JSON object")

    schema_version = payload.get("schema_version")
    if schema_version is None:
        raise CheckpointError("checkpoint payload is missing schema_version")
    if schema_version > CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(
            f"checkpoint schema_version {schema_version!r} is newer than this code supports "
            f"({CHECKPOINT_SCHEMA_VERSION})"
        )
    if schema_version != CHECKPOINT_SCHEMA_VERSION:
        payload = _migrate_to_current(payload)

    try:
        acclimation = acclimation if acclimation is not None else HostAcclimation()
        for capability_id, stats in payload.get("acclimation", {}).items():
            acclimation.restore(
                capability_id,
                CapabilityBaseline(count=stats["count"], mean=stats["mean"], variance=stats["variance"]),
            )

        rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel()
        for entry in payload.get("rhythms", []):
            rhythm_model.restore(
                entry["percept_name"],
                TimeBucket(entry["time_bucket"]),
                CapabilityBaseline(count=entry["count"], mean=entry["mean"], variance=entry["variance"]),
            )

        drift_baselines: dict[str, DriftAwareBaseline] = {}
        for name, stats in payload.get("drift", {}).items():
            baseline = DriftAwareBaseline()
            baseline.restore(count=stats["count"], mean=stats["mean"], variance=stats["variance"])
            drift_baselines[name] = baseline
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointError(f"malformed checkpoint payload: {exc}") from exc

    return acclimation, rhythm_model, drift_baselines


def save_checkpoint_atomic(payload: dict[str, Any], path: str | Path) -> None:
    """Write a checkpoint to disk atomically (roadmap v0.46).

    Writes to a temporary file in the same directory, flushes and fsyncs
    it, then renames it into place — ``os.replace`` is atomic on the same
    filesystem on every platform Python supports. A crash or power loss
    mid-write can only ever leave the temporary file behind; the path
    callers actually read is either the previous complete checkpoint or the
    new complete one, never a half-written one.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_checkpoint_file(path: str | Path) -> dict[str, Any] | None:
    """Read a checkpoint previously written by :func:`save_checkpoint_atomic`
    (roadmap v0.46 — crash/restart recovery).

    Returns ``None`` if the file does not exist, so a caller can treat "no
    prior state" and "state that failed to parse" differently: the former
    is a normal first run, the latter (a malformed or truncated file, which
    the atomic write above should make unreachable in practice) raises
    :class:`CheckpointError` rather than silently starting fresh over
    corrupted data.
    """
    target = Path(path)
    if not target.is_file():
        return None
    try:
        with target.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise CheckpointError(f"checkpoint file {target} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CheckpointError(f"checkpoint file {target} does not contain a JSON object")
    return payload
