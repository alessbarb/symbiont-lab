from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from ..foundation.model import Assessment
from ..social.collective import CollectiveMemory


@dataclass(slots=True, frozen=True)
class MetacognitiveState:
    """Internal self-assessment computed without simulator ground truth."""

    self_confidence: float
    epistemic_pressure: float
    mean_uncertainty: float
    mean_novelty: float
    mean_curiosity: float
    disagreement_pressure: float
    question_pressure: float
    status: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class MetacognitionEngine:
    """Estimate what the population knows about the quality of its own beliefs.

    This component intentionally receives only agent assessments and collective
    aggregate state. It never sees benign/pathogen labels or evaluator metrics.
    """

    def assess(
        self,
        assessments: Iterable[Assessment],
        collective: CollectiveMemory,
    ) -> MetacognitiveState:
        items = list(assessments)
        if not items:
            return MetacognitiveState(
                self_confidence=0.0,
                epistemic_pressure=0.0,
                mean_uncertainty=1.0,
                mean_novelty=0.0,
                mean_curiosity=0.0,
                disagreement_pressure=1.0,
                question_pressure=0.0,
                status="unformed",
            )

        mean_uncertainty = sum(a.uncertainty for a in items) / len(items)
        mean_novelty = sum(a.novelty for a in items) / len(items)
        mean_curiosity = sum(a.curiosity for a in items) / len(items)
        disagreement_pressure = sum(
            1.0 - abs(a.collective_threat - 0.5) * 2.0 for a in items
        ) / len(items)
        question_pressure = len(collective.open_questions()) / max(len(collective.patterns), 1)
        question_pressure = min(question_pressure, 1.0)

        epistemic_pressure = min(
            1.0,
            0.42 * mean_uncertainty
            + 0.24 * mean_novelty
            + 0.20 * disagreement_pressure
            + 0.10 * question_pressure
            + 0.04 * min(mean_curiosity * 8.0, 1.0),
        )
        self_confidence = max(0.0, min(1.0, 1.0 - epistemic_pressure))

        if self_confidence < 0.40:
            status = "uncertain"
        elif mean_novelty > 0.30:
            status = "novel"
        elif disagreement_pressure > 0.62 and question_pressure > 0.08:
            status = "contested"
        elif self_confidence > 0.72 and question_pressure < 0.10:
            status = "stable"
        else:
            status = "watchful"

        return MetacognitiveState(
            self_confidence=self_confidence,
            epistemic_pressure=epistemic_pressure,
            mean_uncertainty=mean_uncertainty,
            mean_novelty=mean_novelty,
            mean_curiosity=mean_curiosity,
            disagreement_pressure=disagreement_pressure,
            question_pressure=question_pressure,
            status=status,
        )
