"""Candidate repertoire builder for L8 Prospective Agency.

Constructs the set of motor primitives the organism is eligible to consider
prospectively. Only cognitively available (is_competence) primitives with
active readouts and below the selection threshold are included. The sequence
implementation of each primitive is never exposed to agency.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping

from .types import ProspectiveCandidate

# Default maximum candidates per deliberation cycle (P0)
_MAX_CANDIDATES = 8

# Motor primitives below this readout threshold are considered "not active"
# and are valid prospective candidates (currently executing ones are skipped).
_ACTIVE_READOUT_THRESHOLD = 0.5


def primitive_candidates(
    primitives: Collection["MotorPrimitive"],  # type: ignore[name-defined]  # noqa: F821
    primitive_readouts: Mapping[str, float],
    *,
    max_candidates: int = _MAX_CANDIDATES,
) -> tuple[ProspectiveCandidate, ...]:
    """Build the organism's current prospective action repertoire.

    Conditions for inclusion:
    1. ``primitive.is_competence`` — evidence gate must be satisfied
    2. A readout for the primitive exists in ``primitive_readouts``
    3. The primitive is not currently active (readout <= _ACTIVE_READOUT_THRESHOLD)

    Controllability is used as a competence gate (``is_competence`` already
    incorporates it) but is NOT used as a ranking criterion here. The order
    is deterministic by ``primitive_id`` so repeated calls with the same
    inputs produce the same set.

    Args:
        primitives: All known motor primitives from the sensorimotor learner.
        primitive_readouts: Current cognitive readout strengths by primitive ID.
        max_candidates: Hard cap on returned candidates (min(8, arg) in P0).

    Returns:
        A tuple of ProspectiveCandidate, sorted by primitive_id (deterministic).
    """
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be an integer")
    limit = min(int(max_candidates), _MAX_CANDIDATES)

    eligible: list[str] = []
    for primitive in primitives:
        pid = primitive.primitive_id
        # Gate 1: evidence-backed competence
        if not primitive.is_competence:
            continue
        # Gate 2: readout must exist
        if pid not in primitive_readouts:
            continue
        # Gate 3: not currently active (readout value is below active threshold)
        readout = float(primitive_readouts[pid])
        if readout > _ACTIVE_READOUT_THRESHOLD:
            continue
        eligible.append(pid)

    # Deterministic order: sorted by primitive_id string
    eligible.sort()

    return tuple(
        ProspectiveCandidate(action_id=pid, family="primitive")
        for pid in eligible[:limit]
    )


__all__ = [
    "primitive_candidates",
]
