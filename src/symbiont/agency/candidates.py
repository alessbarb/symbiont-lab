"""Prospective candidate repertoire from learned motor competences."""
from __future__ import annotations

from collections.abc import Collection, Mapping

from symbiont.actuation.competence import CompetenceMaturity, MotorCompetence
from .types import ProspectiveCandidate

_MAX_CANDIDATES = 8


def competence_candidates(
    competences: Collection[MotorCompetence],
    competence_readouts: Mapping[str, float],
    *,
    max_candidates: int = _MAX_CANDIDATES,
) -> tuple[ProspectiveCandidate, ...]:
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be an integer")
    limit = min(max(0, int(max_candidates)), _MAX_CANDIDATES)
    eligible = sorted(
        competence.competence_id
        for competence in competences
        if competence.maturity
        in {CompetenceMaturity.ESTABLISHED, CompetenceMaturity.ROBUST}
        and competence.competence_id in competence_readouts
    )
    return tuple(
        ProspectiveCandidate(action_id=competence_id, family="competence")
        for competence_id in eligible[:limit]
    )


def motor_competence_candidates(
    primitives: Collection[object],
    readouts: Mapping[str, float],
    *,
    max_candidates: int = _MAX_CANDIDATES,
) -> tuple[ProspectiveCandidate, ...]:
    """Return admitted learned motor competences in deterministic order.

    The learner's temporal controller representation is deliberately kept
    behind a small structural interface here. The agency layer consumes only
    its identifier and evidence-derived maturity; it must not rank candidates
    by the readout value.
    """
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be an integer")
    limit = min(max(0, max_candidates), _MAX_CANDIDATES)
    eligible = sorted(
        primitive.primitive_id
        for primitive in primitives
        if primitive.maturity
        in {CompetenceMaturity.ESTABLISHED, CompetenceMaturity.ROBUST}
        and primitive.primitive_id in readouts
    )
    return tuple(
        ProspectiveCandidate(action_id=primitive_id, family="competence")
        for primitive_id in eligible[:limit]
    )


__all__ = ["competence_candidates", "motor_competence_candidates"]
