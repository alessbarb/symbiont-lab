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
    payload: dict[str, Any], constitution: ActuatorConstitution, *, organism_id: str
) -> ActuatorProposer:
    """Rebuild an ActuatorProposer from a checkpoint payload.

    Any candidate referencing an actuator_id outside this organism's own
    ActuatorConstitution is a corrupted or foreign checkpoint (spec §15) —
    this raises rather than silently dropping or renaming it.

    Note (P0 scope limit): ``min_probing_windows``/``effect_threshold``/
    ``window_ticks``/``probe_limit`` are proposer *configuration*, not
    discovered state, and are not part of this payload — the caller must
    construct-equivalent config out of band (e.g. from ActuatorConstitution/
    genome-derived defaults) exactly as P2 will when this wires into World's
    own checkpoint. Only discovered candidate state and the probe cursor
    round-trip here.
    """
    known_ids = set(constitution.actuator_ids)
    raw_candidates = payload.get("candidates", {})
    if not isinstance(raw_candidates, dict):
        raise ValueError("candidates must be an object")

    proposer = ActuatorProposer(constitution, organism_id=organism_id)
    for actuator_id, raw_state in raw_candidates.items():
        if actuator_id not in known_ids:
            raise ValueError(
                f"checkpoint candidate {actuator_id!r} is not part of this organism's ActuatorConstitution"
            )
        proposer._states[actuator_id] = ActuatorCandidateState.from_payload(raw_state)  # noqa: SLF001

    proposer._probe_cursor = int(payload.get("probe_cursor", 0))  # noqa: SLF001
    return proposer
