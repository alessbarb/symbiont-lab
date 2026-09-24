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


__all__ = ["competence_candidates"]
