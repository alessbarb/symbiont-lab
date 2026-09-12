"""Evidence collection, shadow-mode second-look, and noise sweep studies."""

from .noise_sweep import (
    NOISE_METRICS,
    EvidenceNoiseSweep,
    NoiseMetricSummary,
    NoisePairedDelta,
    NoiseStrategySummary,
    run_evidence_noise_sweep,
)
from .replicated import (
    EVIDENCE_METRICS,
    EvidenceMetricSummary,
    EvidencePairedDelta,
    EvidenceStrategySummary,
    ReplicatedEvidenceStudy,
    run_replicated_evidence_study,
)
from .second_look import (
    SecondLookOutcome,
    SecondLookStudy,
    run_second_look_study,
)

__all__ = [
    "EVIDENCE_METRICS",
    "NOISE_METRICS",
    "EvidenceMetricSummary",
    "EvidenceNoiseSweep",
    "EvidencePairedDelta",
    "EvidenceStrategySummary",
    "NoiseMetricSummary",
    "NoisePairedDelta",
    "NoiseStrategySummary",
    "ReplicatedEvidenceStudy",
    "SecondLookOutcome",
    "SecondLookStudy",
    "run_evidence_noise_sweep",
    "run_replicated_evidence_study",
    "run_second_look_study",
]
