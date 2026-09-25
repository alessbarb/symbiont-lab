"""L8 Prospective Agency — organism-side package.

Public contracts only. Never imports from symbiont_lab, Physics3D, World or
evaluator. All types are immutable and semantically opaque.
"""

from __future__ import annotations

from .candidates import competence_candidates
from .checkpoint import PROSPECTIVE_AGENCY_SCHEMA_VERSION
from .policy import EvaluatedCandidate, ProspectivePolicy
from .prospective import ProspectiveAgency
from .readiness import AgencyReadiness, check_readiness
from .types import (
    CounterfactualPrediction,
    OutcomeValueEstimate,
    ProspectiveCandidate,
    ProspectiveDecision,
)
from .value import MAX_OUTCOME_VALUES, OutcomeValueLedger

__all__ = [
    # Types
    "ProspectiveCandidate",
    "CounterfactualPrediction",
    "OutcomeValueEstimate",
    "ProspectiveDecision",
    # Value
    "MAX_OUTCOME_VALUES",
    "OutcomeValueLedger",
    # Policy
    "EvaluatedCandidate",
    "ProspectivePolicy",
    # Agency
    "ProspectiveAgency",
    # Readiness
    "AgencyReadiness",
    "check_readiness",
    # Candidates
    "competence_candidates",
    # Checkpoint
    "PROSPECTIVE_AGENCY_SCHEMA_VERSION",
]
