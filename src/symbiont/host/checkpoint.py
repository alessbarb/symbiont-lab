from __future__ import annotations

from typing import Any

from .acclimation import CapabilityBaseline, HostAcclimation
from .drift import DriftAwareBaseline
from .rhythms import RhythmModel, TimeBucket

CHECKPOINT_SCHEMA_VERSION = 1


class CheckpointError(ValueError):
    """Raised for a malformed checkpoint payload or an unsupported schema version."""


def export_checkpoint(
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
    drift_baselines: dict[str, DriftAwareBaseline] | None = None,
) -> dict[str, Any]:
    """Serialize only safe, abstract descriptive state — never raw readings,
    timestamps or capability details (roadmap v0.37).

    Every field written here is already part of what v0.33/v0.35/v0.36
    commit to exposing publicly: count/mean/variance. Nothing in a
    checkpoint can reconstruct a specific past reading, so exporting and
    later importing one is explicit, user-triggered model persistence, not
    a telemetry log.
    """
    payload: dict[str, Any] = {"schema_version": CHECKPOINT_SCHEMA_VERSION}

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


def import_checkpoint(
    payload: dict[str, Any],
    *,
    acclimation: HostAcclimation | None = None,
    rhythm_model: RhythmModel | None = None,
) -> tuple[HostAcclimation, RhythmModel, dict[str, DriftAwareBaseline]]:
    """Reconstruct model instances from a checkpoint payload.

    Rejects anything not written by the current schema version outright,
    rather than guessing at a migration — a checkpoint is either read
    exactly as it was written, or refused.

    Pass an existing ``acclimation``/``rhythm_model`` (matching the
    ``min_samples``/bound config the checkpoint was exported with) to
    restore into it rather than a freshly-defaulted one — a baseline
    exported once it passed a lower ``min_samples`` may otherwise not read
    back as "already learned" against a differently-configured instance.
    """
    if not isinstance(payload, dict):
        raise CheckpointError("checkpoint payload must be a JSON object")

    schema_version = payload.get("schema_version")
    if schema_version != CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(
            f"unsupported checkpoint schema_version {schema_version!r}; "
            f"expected {CHECKPOINT_SCHEMA_VERSION}"
        )

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
