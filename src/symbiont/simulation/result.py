from __future__ import annotations

from dataclasses import dataclass
from .metrics import rate


@dataclass(slots=True)
class SimulationResult:
    hosts: int
    steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positive_investigations: int
    false_positive_investigations: int
    false_negatives: int
    classification_true_positives: int
    classification_false_positives: int
    classification_true_negatives: int
    classification_false_negatives: int
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float
    reasoning_hypotheses: int
    top_reasoning_priority: float
    curiosity_probes: int
    top_probe_utility: float
    self_confidence: float
    epistemic_pressure: float
    metacognitive_status: str
    calibration_error: float
    brier_score: float
    overconfidence_rate: float
    blind_spot_rate: float
    high_confidence_miss_rate: float
    drift_step: int
    drifted_hosts: int
    drift_adaptations: int
    drift_false_positive_rate: float
    recent_drift_false_positive_rate: float
    evaluation_breakdown: dict[str, object]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return rate(numerator, denominator)

    @property
    def attention_recall(self) -> float | None:
        return rate(self.true_positive_investigations, self.pathogen_events)

    @property
    def attention_precision(self) -> float | None:
        return rate(self.true_positive_investigations, self.investigated)

    @property
    def attention_false_positive_rate(self) -> float | None:
        return rate(self.false_positive_investigations, self.benign_events)

    @property
    def classification_recall(self) -> float | None:
        return rate(self.classification_true_positives, self.pathogen_events)

    @property
    def classification_precision(self) -> float | None:
        return rate(
            self.classification_true_positives,
            self.classification_true_positives + self.classification_false_positives,
        )

    @property
    def classification_false_positive_rate(self) -> float | None:
        return rate(self.classification_false_positives, self.benign_events)

    @property
    def classification_miss_rate(self) -> float | None:
        return rate(self.classification_false_negatives, self.pathogen_events)

    # Backwards-compatible aliases.
    @property
    def detection_rate(self) -> float:
        return self.attention_recall or 0.0

    @property
    def precision(self) -> float:
        return self.attention_precision or 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.attention_false_positive_rate or 0.0
