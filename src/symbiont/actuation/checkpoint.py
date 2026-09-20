from __future__ import annotations

from typing import Any

from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .proposer import ActuatorProposer
from .types import _require_nonneg_int


def export_actuation_state(proposer: ActuatorProposer) -> dict[str, Any]:
    """Serialize established motor-discovery state (spec §11).

    Every candidate's full state round-trips unconditionally — this is the
    organism's own internal checkpoint, not a filtered report to an
    external observer (spec §16.6 rev5). No raw activation/percept
    HISTORY crosses this boundary (PairAccumulator stores bounded Welford
    aggregates, never a sample log), but nothing is withheld by sample
    count.
    """
    return {
        "candidates": {state.actuator_id: state.to_payload() for state in proposer.states},
        "probe_cursor": proposer._probe_cursor,  # noqa: SLF001 — checkpoint owns proposer internals by design
    }


def restore_actuation_state(
    payload: dict[str, Any],
    constitution: ActuatorConstitution,
    *,
    organism_id: str,
    min_probing_windows: int = 2,
    effect_threshold: float = 0.5,
    window_ticks: int = 8,
    probe_limit: int = 1,
) -> ActuatorProposer:
    """Rebuild an ActuatorProposer from a checkpoint payload.

    ``payload["candidates"]`` must contain EXACTLY one entry per
    ``constitution.actuator_ids`` — no more, no fewer (spec §15/P0.2).
    ``export_actuation_state`` always exports every candidate, so a payload
    missing one, or one that carries an unknown actuator_id, is a corrupted
    or foreign checkpoint. Silently accepting a partial candidate set would
    let a truncated checkpoint masquerade as "this organism never explored
    some of its actuators" — a plausible-looking but false developmental
    history. Each candidate's own ``actuator_id`` field must also match the
    dict key it is stored under, so a payload cannot smuggle candidate B's
    state in under key A (both being otherwise-known ids).

    ``min_probing_windows``/``effect_threshold``/``window_ticks``/
    ``probe_limit`` are proposer *configuration*, not discovered state, and
    are not part of this payload — the caller supplies construct-equivalent
    config out of band (e.g. from ActuatorConstitution/genome-derived
    defaults). They default to ``ActuatorProposer``'s own defaults so
    existing callers that don't pass them get identical behavior. Only
    discovered candidate state and the probe cursor round-trip via the
    payload itself.

    Both ``"candidates"`` and ``"probe_cursor"`` must be explicitly present
    in ``payload`` — a payload missing either key entirely is treated as a
    malformed/truncated checkpoint (spec §11/§15) and raises, distinct from
    a valid, explicit empty state (``"candidates": {}``, ``"probe_cursor": 0``).

    Each candidate's own fields are also checked for cross-field
    consistency (spec §15 — corruption must raise, never silently accept an
    internally-impossible state). Active candidates may have reached activity
    by either replicated probing windows or by the canonical natural-evidence
    path used by spontaneous motor exploration: ``windows_with_effect`` can never exceed
    ``windows_completed`` (replication can't be credited for windows that
    haven't elapsed), ``tick_in_window`` must be strictly less than
    ``window_ticks`` (an out-of-range value would only surface later, as an
    index error inside ``probing_calendar`` several ticks after restore,
    far from its actual cause), and an ``active`` candidate's own recorded
    evidence must contain a valid historical promotion proof. Replicated
    probing windows remain sufficient even if the later cumulative
    correlation weakens; naturally promoted candidates persist the exact
    sample threshold at the promotion event. Legacy natural checkpoints
    without that marker use the stricter historical fallback.
    """
    if "candidates" not in payload:
        raise ValueError("checkpoint payload missing required key 'candidates'")
    if "probe_cursor" not in payload:
        raise ValueError("checkpoint payload missing required key 'probe_cursor'")

    known_ids = set(constitution.actuator_ids)
    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, dict):
        raise ValueError("candidates must be an object")

    payload_ids = set(raw_candidates)
    if payload_ids != known_ids:
        missing = known_ids - payload_ids
        unknown = payload_ids - known_ids
        raise ValueError(
            "checkpoint candidates do not match this organism's ActuatorConstitution — "
            f"missing={sorted(missing)} unknown={sorted(unknown)}"
        )

    proposer = ActuatorProposer(
        constitution,
        organism_id=organism_id,
        min_probing_windows=min_probing_windows,
        effect_threshold=effect_threshold,
        window_ticks=window_ticks,
        probe_limit=probe_limit,
    )
    for actuator_id, raw_state in raw_candidates.items():
        state = ActuatorCandidateState.from_payload(raw_state)
        if state.actuator_id != actuator_id:
            raise ValueError(
                f"checkpoint candidate stored under key {actuator_id!r} but its own "
                f"actuator_id field is {state.actuator_id!r} — key/field mismatch"
            )
        if state.windows_with_effect > state.windows_completed:
            raise ValueError(
                f"checkpoint candidate {actuator_id!r}: windows_with_effect "
                f"({state.windows_with_effect}) exceeds windows_completed "
                f"({state.windows_completed}) — internally impossible state"
            )
        if state.tick_in_window >= window_ticks:
            raise ValueError(
                f"checkpoint candidate {actuator_id!r}: tick_in_window "
                f"({state.tick_in_window}) must be less than window_ticks ({window_ticks})"
            )
        if state.probing_state == "active":
            # Promotion is a historical event. Current cumulative correlation
            # may legitimately weaken after promotion as the organism gathers
            # more experience, so restore must validate the evidence that
            # promotion happened, not require today's effect_strength to still
            # clear the old threshold.
            probing_promoted = (
                state.windows_completed >= min_probing_windows
                and state.windows_with_effect >= min_probing_windows
            )
            strongest_relation_count = max(
                (relation.count for relation in state.effect_relations.values()),
                default=0,
            )

            # New checkpoints persist natural_promotion_samples only at the
            # exact moment consider_natural_evidence() legitimately promotes
            # the candidate. That marker is therefore historical promotion
            # evidence in its own right; later correlation decay must not
            # invalidate it.
            if state.natural_promotion_samples > 0:
                natural_min_samples = state.natural_promotion_samples
                natural_promoted = strongest_relation_count >= natural_min_samples
            else:
                # Legacy checkpoints predate the explicit promotion marker.
                # The historical production contract used min_samples=12, so
                # retain the stricter fallback: enough samples AND the current
                # aggregate still clears the threshold.
                natural_min_samples = 12
                natural_promoted = (
                    strongest_relation_count >= natural_min_samples
                    and state.effect_strength >= effect_threshold
                )

            if not (probing_promoted or natural_promoted):
                raise ValueError(
                    f"checkpoint candidate {actuator_id!r} claims probing_state='active' but its "
                    "own evidence does not satisfy either promotion route "
                    f"(windows_completed={state.windows_completed}, "
                    f"windows_with_effect={state.windows_with_effect}, "
                    f"strongest_relation_count={strongest_relation_count}, "
                    f"natural_min_samples={natural_min_samples}, "
                    f"effect_strength={state.effect_strength}, "
                    f"min_probing_windows={min_probing_windows}, "
                    f"effect_threshold={effect_threshold})"
                )
        proposer._states[actuator_id] = state  # noqa: SLF001

    proposer._probe_cursor = _require_nonneg_int(payload["probe_cursor"], "probe_cursor")  # noqa: SLF001
    return proposer
