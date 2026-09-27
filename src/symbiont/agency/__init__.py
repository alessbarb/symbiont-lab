"""L8 Prospective Agency — organism-side package.

Public contracts only. Never imports from symbiont_lab, Physics3D, World or
evaluator. All types are immutable and semantically opaque.
"""

from __future__ import annotations

from .affordance import ActionAffordance
from .affordances import AffordanceResolver
from .candidates import competence_candidates
from .checkpoint import PROSPECTIVE_AGENCY_SCHEMA_VERSION
from .intention import ActionIntent, AdmissionRoute, IntentStatus
from .policy import EvaluatedCandidate, ProspectivePolicy
from .prospective import (
    ExecutiveAdmissionPolicy,
    GenerativeAnticipation,
    ProspectiveAgency,
    ProspectiveDecision,
    admit_afforded_action,
)
from .readiness import AgencyReadiness, check_readiness
from .types import (
    CounterfactualPrediction,
    DeliberationOutcome,
    OutcomeValueEstimate,
    ProspectiveCandidate,
)
from .value import MAX_OUTCOME_VALUES, OutcomeValueLedger

__all__ = [
    # Agency Acquisition & Executive Action v1
    "ActionAffordance",
    "AffordanceResolver",
    "ActionIntent",
    "AdmissionRoute",
    "IntentStatus",
    "ExecutiveAdmissionPolicy",
    "GenerativeAnticipation",
    "ProspectiveDecision",
    "admit_afforded_action",
    # Types
    "ProspectiveCandidate",
    "CounterfactualPrediction",
    "OutcomeValueEstimate",
    "DeliberationOutcome",
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
