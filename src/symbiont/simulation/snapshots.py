from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from symbiont.core.cognition.reasoning import Hypothesis
    from symbiont.core.curiosity import CuriosityProbe


@dataclass(slots=True, frozen=True)
class SimulationSnapshot:
    step: int
    total_steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positives: int
    false_positives: int
    false_negatives: int
    detection_rate: float
    precision: float
    false_positive_rate: float
    attention_recall: float
    attention_precision: float
    attention_false_positive_rate: float
    classification_recall: float
    classification_precision: float
    classification_false_positive_rate: float
    classification_miss_rate: float
    high_confidence_miss_rate: float
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float
    reasoning_hypotheses: tuple[Hypothesis, ...]
    reasoning_priority: float
    curiosity_probes: tuple[CuriosityProbe, ...]
    curiosity_focus: float
    self_confidence: float
    epistemic_pressure: float
    mean_uncertainty: float
    mean_novelty: float
    disagreement_pressure: float
    metacognitive_status: str
    calibration_error: float
    brier_score: float
    overconfidence_rate: float
    blind_spot_rate: float
    drift_active: bool
    drift_step: int
    drifted_hosts: int
    drift_adaptations: int
    drift_false_positive_rate: float
    recent_drift_false_positive_rate: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
