"""Agency readiness gate for L8 Prospective Agency.

Encapsulates the conditions under which deliberation is permitted to proceed.
All checks are structural/capacity-based — no environmental or evaluator
metrics appear here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgencyReadiness:
    """Result of the agency readiness check."""

    ready: bool
    reasons: tuple[str, ...]


def check_readiness(
    *,
    has_active_model: bool,
    competence_count: int,
    has_competence_readouts: bool,
    context_token_count: int,
    has_outcome_evidence: bool,
    organism_alive: bool,
) -> AgencyReadiness:
    """Check whether prospective deliberation is permitted.

    P0 gate conditions:
    - ACTIVE private model present
    - At least 1 motor competence available
    - At least 1 competence readout available
    - Cognitive context is non-empty
    - At least 1 outcome with learned value exists
    - Organism is alive

    Returns:
        AgencyReadiness with ready=True and empty reasons on success, or
        ready=False with one reason string per failed gate.
    """
    failed: list[str] = []

    if not organism_alive:
        failed.append("organism_dead")
    if not has_active_model:
        failed.append("no_active_model")
    if competence_count < 1:
        failed.append("no_competences")
    if not has_competence_readouts:
        failed.append("no_competence_readouts")
    if context_token_count < 1:
        failed.append("empty_context")
    if not has_outcome_evidence:
        failed.append("no_outcome_evidence")

    if failed:
        return AgencyReadiness(ready=False, reasons=tuple(failed))
    return AgencyReadiness(ready=True, reasons=())


__all__ = [
    "AgencyReadiness",
    "check_readiness",
]
