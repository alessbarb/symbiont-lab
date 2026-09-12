"""Comparative studies, automated interpretation, and research campaigns."""

from .campaign import (
    CampaignAssessment,
    CampaignProposal,
    analyze_campaign,
)
from .comparative import (
    COMPARABLE_PARAMETERS,
    METRICS,
    ConditionSummary,
    MetricSummary,
    PairedDeltaSummary,
    StudyResult,
    run_comparative_study,
)
from .interpretation import (
    FollowUpStudy,
    StudyFinding,
    StudyInterpretation,
    interpret_study,
)

__all__ = [
    "COMPARABLE_PARAMETERS",
    "METRICS",
    "CampaignAssessment",
    "CampaignProposal",
    "ConditionSummary",
    "FollowUpStudy",
    "MetricSummary",
    "PairedDeltaSummary",
    "StudyFinding",
    "StudyInterpretation",
    "StudyResult",
    "analyze_campaign",
    "interpret_study",
    "run_comparative_study",
]
