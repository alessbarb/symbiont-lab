from __future__ import annotations

from typing import Any

from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .proposer import ActuatorProposer


def export_actuation_state(proposer: ActuatorProposer) -> dict[str, Any]:
    """Serialize established motor-discovery state (spec §11).

    Only aggregates already gated by ActuatorCandidateState.to_payload's
    own min-sample withholding are included — no raw activation/percept
    history crosses this boundary.
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

    Any candidate referencing an actuator_id outside this organism's own
    ActuatorConstitution is a corrupted or foreign checkpoint (spec §15) —
    this raises rather than silently dropping or renaming it.

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
    """
    if "candidates" not in payload:
        raise ValueError("checkpoint payload missing required key 'candidates'")
    if "probe_cursor" not in payload:
        raise ValueError("checkpoint payload missing required key 'probe_cursor'")

    known_ids = set(constitution.actuator_ids)
    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, dict):
        raise ValueError("candidates must be an object")

    proposer = ActuatorProposer(
        constitution,
        organism_id=organism_id,
        min_probing_windows=min_probing_windows,
        effect_threshold=effect_threshold,
        window_ticks=window_ticks,
        probe_limit=probe_limit,
    )
    for actuator_id, raw_state in raw_candidates.items():
        if actuator_id not in known_ids:
            raise ValueError(
                f"checkpoint candidate {actuator_id!r} is not part of this organism's ActuatorConstitution"
            )
        proposer._states[actuator_id] = ActuatorCandidateState.from_payload(raw_state)  # noqa: SLF001

    proposer._probe_cursor = int(payload["probe_cursor"])  # noqa: SLF001
    return proposer
