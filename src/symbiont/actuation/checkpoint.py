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
    internally-impossible state): ``windows_with_effect`` can never exceed
    ``windows_completed`` (replication can't be credited for windows that
    haven't elapsed), ``tick_in_window`` must be strictly less than
    ``window_ticks`` (an out-of-range value would only surface later, as an
    index error inside ``probing_calendar`` several ticks after restore,
    far from its actual cause), and an ``active`` candidate's own recorded
    evidence must actually satisfy the promotion condition it claims to
    have already met (``windows_completed``/``windows_with_effect`` >=
    ``min_probing_windows`` and ``effect_strength`` >= ``effect_threshold``)
    — a payload cannot claim "already promoted" without the evidence to
    back it up.
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
        if state.probing_state == "active" and not (
            state.windows_completed >= min_probing_windows
            and state.windows_with_effect >= min_probing_windows
            and state.effect_strength >= effect_threshold
        ):
            raise ValueError(
                f"checkpoint candidate {actuator_id!r} claims probing_state='active' but its "
                "own evidence (windows_completed="
                f"{state.windows_completed}, windows_with_effect={state.windows_with_effect}, "
                f"effect_strength={state.effect_strength}) does not satisfy the promotion "
                f"condition for min_probing_windows={min_probing_windows}, "
                f"effect_threshold={effect_threshold}"
            )
        proposer._states[actuator_id] = state  # noqa: SLF001

    proposer._probe_cursor = _require_nonneg_int(payload["probe_cursor"], "probe_cursor")  # noqa: SLF001
    return proposer
