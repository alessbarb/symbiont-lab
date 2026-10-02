from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

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

CHECKPOINT_SCHEMA_VERSION = 11
# v10 -> v11 (Longitudinal Integrity v1 §4-§5) changes no organism state. From
# v11 on, checkpoint_lineage.checkpoint_id covers the complete organism payload
# of the runtime that saved it and is verified on restore, and fields the
# continuity register marks as required may not be absent. Older schemas keep
# their documented migration defaults and are not identity-verified: their
# identifier covered only the base runtime fields and was never checked.
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
# v8 -> v9 removes the contaminated typed local-action-selection subsystem
# (ActionKind/ExpectedOutcome/LocalActionModel and its scalar utility
# function) from canonical symbiont.core.runtime.  See _migrate_v8_to_v9:
# it is a validation gate, not a compatibility shim.  A v8 checkpoint that
# carries ``action_evidence``/``action_model``/``interoceptive_action_model``/
# ``pending_action_observation`` payloads, or an ``autonomous_behavior``/
# ``behavior_exploration`` effective_config, is hard-rejected with
# CheckpointError; there is no decontaminated equivalent to migrate that
# state into.  A v8 checkpoint that never populated those fields (the
# canonical default) carries forward unchanged.
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
    """By the time this runs, normalize_checkpoint has already migrated any
    older payload up to CHECKPOINT_SCHEMA_VERSION (design §14) -- only the
    consolidated {center_class, scale_class, maturity_class} shape ever
    reaches here now. The PR3 dual-read fallback this replaced is retired
    now that _migrate_v5_to_v6 handles the boundary properly."""
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


def _migrate_v3_to_v4(payload: dict[str, Any]) -> dict[str, Any]:
    """v3 self_model entries predate per-sense last_observed_tick (roadmap
    v0.54) — v4 backfills it to saved_at_tick (or 0) for every existing
    entry, the most conservative assumption: as if every sense was observed
    at the moment of the last save, so nothing decays as artificially idle
    immediately after migrating an old checkpoint."""
    migrated = dict(payload)
    migrated["schema_version"] = 4
    fallback_tick = migrated.get("saved_at_tick") or 0
    self_model = dict(migrated.get("self_model", {}))
    for sense_id, entry in self_model.items():
        if isinstance(entry, dict) and "last_observed_tick" not in entry:
            entry = dict(entry)
            entry["last_observed_tick"] = fallback_tick
            self_model[sense_id] = entry
    migrated["self_model"] = self_model
    return migrated


def _migrate_v4_to_v5(payload: dict[str, Any]) -> dict[str, Any]:
    """v5 makes resident continuity explicit without inventing historical
    telemetry that v4 intentionally did not persist.

    Established sensory states already contain their capability ids, so
    their one-way recognition fingerprints can be derived safely. Immature
    candidates omitted by v4 for privacy cannot be reconstructed and remain
    unknown until they are sampled again. Cognitive previous-frame and
    structural-candidate state likewise did not exist in v4; their migration
    defaults are therefore empty rather than fabricated.
    """
    migrated = dict(payload)
    migrated["schema_version"] = 5

    raw_sensory = migrated.get("sensory_development")
    if isinstance(raw_sensory, dict):
        sensory = dict(raw_sensory)
        fingerprints: list[str] = []
        for entry in sensory.get("states", []):
            if not isinstance(entry, dict):
                continue
            capability_id = entry.get("capability_id")
            if not isinstance(capability_id, str) or not capability_id:
                continue
            fingerprint = _capability_fingerprint(capability_id)
            if fingerprint not in fingerprints:
                fingerprints.append(fingerprint)
        sensory.setdefault("known_capability_fingerprints", fingerprints)
        migrated["sensory_development"] = sensory

    raw_bridge = migrated.get("cognitive_bridge")
    if isinstance(raw_bridge, dict):
        bridge = dict(raw_bridge)
        bridge.setdefault("previous_frame", {})
        bridge.setdefault("structural_plasticity", {})
        migrated["cognitive_bridge"] = bridge

    return migrated


def _migrate_acclimation_style_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if "center_class" in entry:
        return entry
    seed = consolidate_baseline(
        CapabilityBaseline(count=entry["count"], mean=entry["mean"], variance=entry["variance"])
    )
    return _seed_payload(seed)


def _migrate_v5_to_v6(payload: dict[str, Any]) -> dict[str, Any]:
    """v6 makes the biological-memory-consolidation model (design
    docs/design/cognicion-y-plasticidad.md) the durable checkpoint
    shape. This is a privacy-reducing projection, not a lossless migration
    (§14): exact acclimation/rhythm/drift aggregates become consolidated
    classes, and self_model's exact last_observed_tick becomes a
    RecencyClass computed from this checkpoint's own saved_at_tick -- the
    one migration step in this chain that legitimately derives from real
    per-organism history, since it re-derives the *same* organism's own
    already-recorded state at the moment it was actually saved, not a
    fresh restart's fabricated history.
    """
    migrated = dict(payload)
    migrated["schema_version"] = 6
    saved_at_tick = migrated.get("saved_at_tick") or 0

    raw_acclimation = migrated.get("acclimation")
    if isinstance(raw_acclimation, dict):
        migrated["acclimation"] = {
            capability_id: _migrate_acclimation_style_entry(entry)
            for capability_id, entry in raw_acclimation.items()
            if isinstance(entry, dict)
        }

    raw_rhythms = migrated.get("rhythms")
    if isinstance(raw_rhythms, list):
        migrated_rhythms = []
        for entry in raw_rhythms:
            if not isinstance(entry, dict):
                continue
            stats = {
                key: value
                for key, value in entry.items()
                if key not in ("percept_name", "time_bucket")
            }
            converted = _migrate_acclimation_style_entry(stats)
            migrated_rhythms.append(
                {
                    "percept_name": entry["percept_name"],
                    "time_bucket": entry["time_bucket"],
                    **converted,
                }
            )
        migrated["rhythms"] = migrated_rhythms

    raw_drift = migrated.get("drift")
    if isinstance(raw_drift, dict):
        migrated["drift"] = {
            name: _migrate_acclimation_style_entry(entry)
            for name, entry in raw_drift.items()
            if isinstance(entry, dict)
        }

    raw_self_model = migrated.get("self_model")
    if isinstance(raw_self_model, dict):
        from ..core.cognition.host_self_model import (
            RecencyClass,  # local import: avoids a host->core module-load cycle
        )

        thresholds = (
            (10, RecencyClass.CURRENT),
            (40, RecencyClass.SHORT_IDLE),
            (120, RecencyClass.IDLE),
            (400, RecencyClass.LONG_IDLE),
        )

        def _idle_ticks_to_recency_class(idle_ticks: int) -> RecencyClass:
            for threshold, recency in thresholds:
                if idle_ticks < threshold:
                    return recency
            return RecencyClass.DORMANT

        migrated_self_model = {}
        for sense_id, entry in raw_self_model.items():
            if not isinstance(entry, dict):
                continue
            if "last_observed_tick" in entry and "recency_class" not in entry:
                idle_ticks = max(0, saved_at_tick - entry["last_observed_tick"])
                entry = {key: value for key, value in entry.items() if key != "last_observed_tick"}
                entry["recency_class"] = _idle_ticks_to_recency_class(idle_ticks).value
            migrated_self_model[sense_id] = entry
        migrated["self_model"] = migrated_self_model

    return migrated


_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
    4: _migrate_v4_to_v5,
    5: _migrate_v5_to_v6,
}


def _migrate_v6_to_v7(payload: dict[str, Any]) -> dict[str, Any]:
    """Add the opaque signal-knowledge block without reconstructing history."""
    migrated = dict(payload)
    migrated["schema_version"] = 7
    # Older checkpoints have no valid identity key or claims.  Starting with
    # NOTE(legacy): an empty block is explicit and safer than deriving knowledge from legacy
    # narrative, adaptive correlations, or exact aggregates.
    migrated.setdefault(
        "signal_knowledge", {"schema_version": 1, "last_tick": None, "profiles": []}
    )
    return migrated


_MIGRATIONS[6] = _migrate_v6_to_v7


def _migrate_v7_to_v8(payload: dict[str, Any]) -> dict[str, Any]:
    """Introduce organism-owned sensory phenotype persistence.

    v7 knows external-source development and signal knowledge but has no
    durable SensorState.  Migration therefore records an empty sensory
    system rather than reconstructing acquired receptors from source
    statistics or cognitive weights. Identity sensors are recreated
    deterministically when those sources are actually observed again.
    """
    migrated = dict(payload)
    migrated["schema_version"] = 8
    migrated.setdefault("sensory_system", None)
    effective = migrated.get("effective_config")
    if isinstance(effective, dict):
        effective = dict(effective)
        effective.setdefault("sensory_plasticity", False)
        migrated["effective_config"] = effective
    return migrated


_MIGRATIONS[7] = _migrate_v7_to_v8


_CONTAMINATED_TOP_LEVEL_KEYS = (
    "action_evidence",
    "action_model",
    "interoceptive_action_model",
    "pending_action_observation",
)
_CONTAMINATED_EFFECTIVE_CONFIG_KEYS = ("autonomous_behavior", "behavior_exploration")


def _migrate_v8_to_v9(payload: dict[str, Any]) -> dict[str, Any]:
    """Refuse the removed typed local-action-selection subsystem outright.

    v9 removes ``symbiont.core.behavior`` (``ActionKind``/``ExpectedOutcome``/
    ``LocalActionModel`` and its scalar utility function) from canonical
    ``symbiont.core.runtime``.  This is not a migration of that state: there
    is no decontaminated equivalent to migrate it into.  A v8 checkpoint
    that never populated these fields (the canonical default, since
    ``autonomous_behavior`` always defaulted to ``False``) carries forward
    unchanged; one that does is hard-rejected rather than silently dropped,
    so a checkpoint that depended on the removed behavior never resumes as
    if that dependency were harmlessly absent.
    """
    present = [key for key in _CONTAMINATED_TOP_LEVEL_KEYS if payload.get(key) is not None]
    effective = payload.get("effective_config")
    if isinstance(effective, dict):
        present.extend(key for key in _CONTAMINATED_EFFECTIVE_CONFIG_KEYS if key in effective)
    if present:
        raise CheckpointError(
            "checkpoint carries the removed typed local-action-selection subsystem "
            f"({', '.join(sorted(present))}); it cannot be restored"
        )
    migrated = dict(payload)
    migrated["schema_version"] = 9
    return migrated


_MIGRATIONS[8] = _migrate_v8_to_v9


def _migrate_v9_to_v10(payload: dict[str, Any]) -> dict[str, Any]:
    """ADR-0042: rhythm contexts become internal macro-cycle phases.

    v9 rhythm baselines were keyed by a wall-clock time-of-day bucket read
    from the host OS. They cannot be re-keyed to the organism's internal
    phase without inventing an alignment, so they are intentionally
    discarded (both the public projection and the replay accumulators);
    rhythms are relearned from causal ticks.
    """
    migrated = dict(payload)
    migrated["schema_version"] = 10
    migrated.pop("rhythms", None)
    migrated.pop("rhythms_replay", None)
    return migrated


_MIGRATIONS[9] = _migrate_v9_to_v10


def _migrate_v10_to_v11(payload: dict[str, Any]) -> dict[str, Any]:
    """Longitudinal Integrity v1: v11 only tightens identity and required fields."""
    migrated = dict(payload)
    migrated["schema_version"] = 11
    return migrated


_MIGRATIONS[10] = _migrate_v10_to_v11


def checkpoint_state_hash(payload: dict[str, Any]) -> str:
    """Content hash of organism state, key order independent.

    Excludes ``checkpoint_lineage`` (save events), ``runtime_provenance`` (what
    produced the save) and apparatus-owned embodiment history. Two checkpoints
    of the same organism state hash identically whenever they were taken.
    """
    state = {key: value for key, value in payload.items() if key not in _IDENTITY_EXCLUDED_FIELDS}
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False)
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

    Restore paths default an absent field to a fresh subsystem so that older
    schemas can migrate. For a checkpoint saved by a current runtime the same
    absence is loss, not history, and must not become a healthy empty subsystem.
    """
    if not _saved_by_current_schema(payload):
        return
    for field in sorted(required_checkpoint_fields(layer)):
        if field not in payload:
            raise CheckpointError(f"current-schema checkpoint is missing required field {field!r}")


def normalize_checkpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Return one current-schema checkpoint for all restore consumers.

    Runtime subsystems must all read the same migrated object. Historically
    :func:`import_checkpoint` migrated a private copy while callers then read
    newer top-level fields from the original payload, so a migration could
    be effective for acclimation but invisible to the self-model or cognitive
    bridge. Normalizing once at the runtime boundary removes that split-brain
    restore path. The input object is never mutated.
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

    normalized = dict(payload)
    version = schema_version
    seen: set[int] = set()
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
        normalized = migration(normalized)
        next_version = normalized.get("schema_version")
        if isinstance(next_version, bool) or not isinstance(next_version, int):
            raise CheckpointError("checkpoint migration produced a non-integer schema_version")
        version = next_version
    return normalized


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
