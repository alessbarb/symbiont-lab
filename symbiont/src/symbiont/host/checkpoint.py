from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..core.foundation.limits import OrganismLimits
from .acclimation import CapabilityBaseline, HostAcclimation
from .consolidated_baseline import (
    ConsolidatedBaselineSeed,
    consolidate_baseline,
    seed_capability_baseline,
)
from .continuity import APPARATUS_FIELDS, required_checkpoint_fields
from .drift import DriftAwareBaseline
from .durable import durable_atomic_write
from .rhythms import CyclePhase, RhythmModel

CHECKPOINT_SCHEMA_VERSION = 12
# v10 -> v11 (Longitudinal Integrity v1 §4-§5) introduced organism-state
# identity. v12 adds an independent hash of continuation conditions because
# runtime controls affect future learning but are apparatus configuration, not
# organism state. No migration is retained: v11 checkpoints lack this contract.
IDENTITY_VERIFIED_SINCE_SCHEMA = 11
IDENTITY_SCOPE = "organism-state-v1"
UNVERIFIED_LEGACY_ORIGIN = "unverified_legacy_origin"
# Owner policy of 2026-10-02 (issue #276): checkpoints saved before schema 11
# stay admissible, marked, with no retirement date. The admission is not open
# ended by default: when the checkpoint schema reaches this version the policy
# must be decided again, and a test fails until this constant is moved or the
# legacy path is removed.
LEGACY_ADMISSION_REVIEW_AT_SCHEMA = 13
# Save-event metadata and embodiment history written around the organism
# checkpoint by the embodiment apparatus are not organism state identity.
_IDENTITY_EXCLUDED_FIELDS = frozenset(
    {"checkpoint_lineage", "runtime_provenance"}
    | {field.checkpoint_field for field in APPARATUS_FIELDS}
)
MAX_HOST_CHECKPOINT_BYTES = OrganismLimits().max_host_checkpoint_bytes


class CheckpointError(ValueError):
    """Raised for a malformed checkpoint payload or an unsupported schema version."""


def _capability_fingerprint(capability_id: str) -> str:
    return sha256(f"symbiont-seen:{capability_id}".encode("utf-8")).hexdigest()


def _seed_payload(seed: ConsolidatedBaselineSeed) -> dict[str, int]:
    return {
        "center_class": seed.center_class,
        "scale_class": seed.scale_class,
        "maturity_class": seed.maturity_class,
    }


def _seed_from_payload(entry: dict[str, Any]) -> ConsolidatedBaselineSeed:
    return ConsolidatedBaselineSeed(
        center_class=int(entry["center_class"]),
        scale_class=int(entry["scale_class"]),
        maturity_class=int(entry["maturity_class"]),
    )


def _baseline_from_stats_entry(entry: dict[str, Any]) -> CapabilityBaseline:
    """Only the consolidated {center_class, scale_class, maturity_class} shape reaches here."""
    return seed_capability_baseline(_seed_from_payload(entry))


def export_checkpoint(
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
    drift_baselines: dict[str, DriftAwareBaseline] | None = None,
    saved_at_tick: int | None = None,
    include_replay: bool = False,
) -> dict[str, Any]:
    """Serialize public descriptive projections and, on request, replay state.

    Public projections remain coarse and omit raw telemetry. Replay blocks
    (``include_replay``) are a separate causal contract for deterministic
    hosts only: they retain bounded accumulators and raw-derived buffers
    required to continue exactly after restore, so the real host never
    requests them and restarts from the coarse projection instead.

    ``saved_at_tick`` is an organism-relative tick counter, not a timestamp or
    calendar date. Exact replay state is intentionally explicit so callers can
    distinguish deterministic continuation from the privacy-reducing public
    snapshot.
    """
    payload: dict[str, Any] = {"schema_version": CHECKPOINT_SCHEMA_VERSION}

    if saved_at_tick is not None:
        payload["saved_at_tick"] = saved_at_tick

    if acclimation is not None:
        payload["acclimation"] = {
            capability_id: _seed_payload(consolidate_baseline(baseline))
            for capability_id in acclimation.acclimated_capabilities
            if (baseline := acclimation.baseline(capability_id)) is not None
        }
        if include_replay:
            payload["acclimation_replay"] = acclimation.replay_state()

    if rhythm_model is not None:
        payload["rhythms"] = [
            {
                "percept_name": percept_name,
                "phase": phase.value,
                **_seed_payload(consolidate_baseline(baseline)),
            }
            for percept_name, phase in rhythm_model.learned_contexts
            if (baseline := rhythm_model.baseline(percept_name, phase)) is not None
        ]
        if include_replay:
            payload["rhythms_replay"] = rhythm_model.replay_state()

    if drift_baselines is not None:
        payload["drift"] = {
            name: _seed_payload(consolidate_baseline(baseline))
            for name, baseline in drift_baselines.items()
            if baseline.is_established
        }
        # The public projection above is intentionally coarse.  Preserve the
        # bounded state that can affect the very next observation separately;
        # otherwise restoring during a pending drift streak changes novelty,
        # regulation, and therefore the future trajectory.
        if include_replay:
            payload["drift_replay"] = {
                name: baseline.replay_state() for name, baseline in drift_baselines.items()
            }

    return payload


def checkpoint_state_hash(payload: dict[str, Any]) -> str:
    """Content hash of organism state, key order independent.

    Excludes ``checkpoint_lineage`` (save events), ``runtime_provenance`` (what
    produced the save) and apparatus-owned embodiment history. Two checkpoints
    of the same organism state hash identically whenever they were taken.
    """
    state = {key: value for key, value in payload.items() if key not in _IDENTITY_EXCLUDED_FIELDS}
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def continuation_condition_hash(controls: dict[str, Any]) -> str:
    """Hash apparatus controls that govern how a saved organism continues."""
    encoded = json.dumps(controls, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def lineage_history(payload: dict[str, Any]) -> dict[str, Any]:
    """The part of a checkpoint's lineage that every later save must carry.

    ``transforms`` lists the authorized transforms the organism has been
    through. ``unverified_legacy_origin`` records that some ancestor checkpoint
    was accepted without a verifiable identity (schema 10 and earlier). Both are
    facts about the organism's history, not about one save, so they outlive the
    checkpoint that first recorded them instead of vanishing at the next save.
    """
    lineage = payload.get("checkpoint_lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    history: dict[str, Any] = {}
    transforms = lineage.get("transforms")
    if isinstance(transforms, list) and transforms:
        history["transforms"] = [str(item) for item in transforms]
    if lineage.get(UNVERIFIED_LEGACY_ORIGIN) is True or "identity_scope" not in lineage:
        history[UNVERIFIED_LEGACY_ORIGIN] = True
    return history


def has_unverified_legacy_origin(payload: dict[str, Any]) -> bool:
    """Whether this state, or an ancestor of it, was accepted without identity."""
    return lineage_history(payload).get(UNVERIFIED_LEGACY_ORIGIN) is True


def require_verified_origin(payload: dict[str, Any]) -> None:
    """Fail closed for uses that need a subject of verifiable origin.

    Confirmatory and held-out experiments must not start from a state whose
    history includes a checkpoint that was never identity-checked
    (research programme A2, subject provenance).
    """
    if has_unverified_legacy_origin(payload):
        raise CheckpointError(
            "checkpoint has an unverified legacy origin: an ancestor was saved "
            "before state identity was verifiable, so it cannot be used where a "
            "verified origin is required"
        )


def stamp_checkpoint_identity(payload: dict[str, Any], *, transform: str) -> dict[str, Any]:
    """Re-identify a checkpoint that an authorized transform has changed.

    A transform such as re-embodiment produces a different organism state, so
    the stored identifier no longer describes it. The new identifier chains
    from the one it replaced and names the transform, so the change is recorded
    instead of being indistinguishable from corruption. Returns a new payload.
    """
    if not transform:
        raise ValueError("transform must name the authorized change")
    stamped = dict(payload)
    previous = stamped.get("checkpoint_lineage")
    previous = previous if isinstance(previous, dict) else {}
    history = lineage_history(stamped)
    lineage: dict[str, Any] = {
        "checkpoint_id": checkpoint_state_hash(stamped),
        "parent_checkpoint_hash": previous.get("checkpoint_id"),
        "identity_scope": IDENTITY_SCOPE,
        **history,
        "transforms": [*history.get("transforms", []), transform],
    }
    if _saved_by_current_schema(stamped):
        provenance = stamped.get("runtime_provenance")
        controls = provenance.get("session_controls") if isinstance(provenance, dict) else None
        if isinstance(controls, dict):
            lineage["continuation_condition_hash"] = continuation_condition_hash(controls)
    # The schema the saving runtime declared travels with the state; a
    # transform never upgrades a legacy checkpoint to a current one.
    if "schema_version" in previous:
        lineage["schema_version"] = previous["schema_version"]
    stamped["checkpoint_lineage"] = lineage
    return stamped


def verify_checkpoint_identity(payload: dict[str, Any]) -> None:
    """Fail closed unless a checkpoint matches the identity it recorded.

    Call it on the payload as loaded. A lineage block that declares an
    ``identity_scope`` is verifiable and must match. One without it is a legacy
    identifier (schema 10 and earlier) that covered only base runtime fields
    and was never checked; it is accepted only from a legacy save.
    """
    lineage = payload.get("checkpoint_lineage")
    if isinstance(lineage, dict) and "identity_scope" in lineage:
        if lineage["identity_scope"] != IDENTITY_SCOPE:
            raise CheckpointError("checkpoint_lineage has an unsupported identity_scope")
        try:
            recomputed = checkpoint_state_hash(payload)
        except (TypeError, ValueError) as exc:
            raise CheckpointError(f"checkpoint state is not canonical JSON: {exc}") from exc
        if lineage.get("checkpoint_id") != recomputed:
            raise CheckpointError(
                "checkpoint state does not match its recorded checkpoint_id; "
                "the checkpoint was modified after it was saved"
            )
        if _saved_by_current_schema(payload):
            provenance = payload.get("runtime_provenance")
            if not isinstance(provenance, dict):
                raise CheckpointError(
                    "current-schema checkpoint is missing required field 'runtime_provenance'"
                )
            controls = provenance.get("session_controls")
            if not isinstance(controls, dict):
                raise CheckpointError(
                    "current-schema checkpoint is missing required field 'session_controls'"
                )
            try:
                expected = continuation_condition_hash(controls)
            except (TypeError, ValueError) as exc:
                raise CheckpointError(
                    f"checkpoint continuation conditions are not canonical JSON: {exc}"
                ) from exc
            if lineage.get("continuation_condition_hash") != expected:
                raise CheckpointError(
                    "checkpoint continuation conditions do not match their recorded hash"
                )
        return
    if _saved_by_current_schema(payload):
        raise CheckpointError(
            "checkpoint saved by a current runtime carries no verifiable checkpoint_lineage"
        )


def _declared_schema(block: Any, key: str) -> int | None:
    value = block.get(key) if isinstance(block, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _saved_by_current_schema(payload: dict[str, Any]) -> bool:
    """Whether the runtime that saved this state declared a verifying schema.

    Decided from what the saving runtime recorded — in the lineage block and in
    runtime_provenance — which transforms and migrations carry over unchanged.
    A verifiable ``identity_scope`` alone is not evidence of it: an authorized
    transform gives a legacy checkpoint a verifiable identity without giving it
    the fields that only a later schema writes.
    """
    declared = (
        _declared_schema(payload.get("checkpoint_lineage"), "schema_version"),
        _declared_schema(payload.get("runtime_provenance"), "checkpoint_schema_version"),
    )
    return any(
        version is not None and version >= IDENTITY_VERIFIED_SINCE_SCHEMA for version in declared
    )


def require_current_schema_fields(payload: dict[str, Any], *, layer: str) -> None:
    """Reject a current-schema checkpoint that lost acquired state.

    Restore paths may default an absent field to a fresh subsystem when loading
    partial or explicitly transformed payloads. This is not a schema migration:
    this runtime accepts only its exact checkpoint schema. For a checkpoint
    saved by the current runtime, absence is loss and must not become a healthy
    empty subsystem.
    """
    if not _saved_by_current_schema(payload):
        return
    for field in sorted(required_checkpoint_fields(layer)):
        if field not in payload:
            raise CheckpointError(f"current-schema checkpoint is missing required field {field!r}")


def normalize_checkpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate that a checkpoint is at the current schema and return a copy.

    Every restore consumer reads the object returned here, so they all see the
    same payload. Older schemas are rejected: no migration path is kept. The
    input object is never mutated.
    """
    if not isinstance(payload, dict):
        raise CheckpointError("checkpoint payload must be a JSON object")

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        if schema_version is None:
            raise CheckpointError("checkpoint payload is missing schema_version")
        raise CheckpointError("checkpoint schema_version must be an integer")
    if schema_version > CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(
            f"checkpoint schema_version {schema_version!r} is newer than this code supports "
            f"({CHECKPOINT_SCHEMA_VERSION})"
        )

    if schema_version != CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(
            f"unsupported checkpoint schema_version {schema_version!r}; this code loads only "
            f"schema {CHECKPOINT_SCHEMA_VERSION} and carries no migrations from older schemas"
        )
    return dict(payload)


def import_checkpoint(
    payload: dict[str, Any],
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
) -> tuple[HostAcclimation, RhythmModel, dict[str, DriftAwareBaseline]]:
    """Reconstruct model instances from a checkpoint payload.

    Only the exact current checkpoint schema is accepted. Historical payloads
    remain archival evidence but require a separately governed conversion
    process before they can become live runtime state.

    Pass an existing ``acclimation``/``rhythm_model`` (matching the
    ``min_samples``/bound config the checkpoint was exported with) to
    restore into it rather than a freshly-defaulted one — a baseline
    exported once it passed a lower ``min_samples`` may otherwise not read
    back as "already learned" against a differently-configured instance.
    """
    payload = normalize_checkpoint(payload)

    try:
        acclimation = acclimation if acclimation is not None else HostAcclimation()
        for capability_id, stats in payload.get("acclimation", {}).items():
            acclimation.restore(capability_id, _baseline_from_stats_entry(stats))
        raw_acclimation_replay = payload.get("acclimation_replay")
        if raw_acclimation_replay is not None:
            if not isinstance(raw_acclimation_replay, dict):
                raise CheckpointError("acclimation_replay must be an object")
            acclimation.restore_replay_state(raw_acclimation_replay)

        rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel()
        for entry in payload.get("rhythms", []):
            rhythm_model.restore(
                entry["percept_name"],
                CyclePhase(entry["phase"]),
                _baseline_from_stats_entry(entry),
            )
        raw_rhythms_replay = payload.get("rhythms_replay")
        if raw_rhythms_replay is not None:
            if not isinstance(raw_rhythms_replay, dict):
                raise CheckpointError("rhythms_replay must be an object")
            rhythm_model.restore_replay_state(raw_rhythms_replay)

        drift_baselines: dict[str, DriftAwareBaseline] = {}
        for name, stats in payload.get("drift", {}).items():
            seeded = _baseline_from_stats_entry(stats)
            baseline = DriftAwareBaseline()
            baseline.restore(count=seeded.count, mean=seeded.mean, variance=seeded.variance)
            drift_baselines[name] = baseline
        raw_replay = payload.get("drift_replay", {})
        if raw_replay is not None:
            if not isinstance(raw_replay, dict):
                raise CheckpointError("drift_replay must be an object")
            for name, replay_state in raw_replay.items():
                if not isinstance(name, str) or not isinstance(replay_state, dict):
                    raise CheckpointError("malformed drift replay state")
                baseline = drift_baselines.get(name)
                if baseline is None:
                    baseline = DriftAwareBaseline()
                    drift_baselines[name] = baseline
                baseline.restore_replay_state(replay_state)
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointError(f"malformed checkpoint payload: {exc}") from exc

    return acclimation, rhythm_model, drift_baselines


def save_checkpoint_atomic(payload: dict[str, Any], path: str | Path) -> None:
    """Write a checkpoint to disk atomically and durably (roadmap v0.46).

    Writes to a temporary file in the same directory, flushes and fsyncs
    it, renames it into place with ``os.replace``, and fsyncs the parent
    directory so directory entries reach persistent storage on POSIX.
    """
    target = Path(path)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    if len(encoded) > MAX_HOST_CHECKPOINT_BYTES:
        raise CheckpointError("checkpoint exceeds host size limit")
    durable_atomic_write(target, encoded, sync_dir=True)


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
