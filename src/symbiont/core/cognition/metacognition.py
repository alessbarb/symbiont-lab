from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from ..foundation.model import Assessment
from ..social.ledger import SocialEvidenceLedger


@dataclass(slots=True, frozen=True)
class MetacognitiveState:
    """Internal self-assessment computed without simulator ground truth."""

    self_confidence: float
    epistemic_pressure: float
    mean_uncertainty: float
    mean_novelty: float
    mean_curiosity: float
    social_uncertainty_pressure: float
    social_contradiction_pressure: float
    unresolved_social_pressure: float
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
        ledger: SocialEvidenceLedger,
    ) -> MetacognitiveState:
        items = list(assessments)

        # Calculate social pressures
        total_claims = len(ledger.claims)
        unresolved_claims = len(ledger.unresolved_claims())
        unresolved_social_pressure = unresolved_claims / max(total_claims, 1)

        # Very coarse approximation for these pressures
        contradictions = sum(s.contradictions for s in ledger.source_states.values())
        social_contradiction_pressure = min(1.0, contradictions / max(total_claims, 1))
        social_uncertainty_pressure = min(
            1.0, unresolved_social_pressure + social_contradiction_pressure
        )

        if not items:
            return MetacognitiveState(
                self_confidence=0.0,
                epistemic_pressure=0.0,
                mean_uncertainty=1.0,
                mean_novelty=0.0,
                mean_curiosity=0.0,
                social_uncertainty_pressure=social_uncertainty_pressure,
                social_contradiction_pressure=social_contradiction_pressure,
                unresolved_social_pressure=unresolved_social_pressure,
                status="unformed",
            )

        mean_uncertainty = sum(a.uncertainty for a in items) / len(items)
        mean_novelty = sum(a.novelty for a in items) / len(items)
        mean_curiosity = sum(a.curiosity for a in items) / len(items)

        epistemic_pressure = min(
            1.0,
            0.55 * mean_uncertainty + 0.35 * mean_novelty + 0.10 * min(mean_curiosity * 8.0, 1.0),
        )
        self_confidence = max(0.0, min(1.0, 1.0 - epistemic_pressure))

        if self_confidence < 0.40:
            status = "uncertain"
        elif mean_novelty > 0.30:
            status = "novel"
        elif unresolved_social_pressure > 0.62:
            status = "contested"
        elif self_confidence > 0.72 and unresolved_social_pressure < 0.10:
            status = "stable"
        else:
            status = "watchful"

        return MetacognitiveState(
            self_confidence=self_confidence,
            epistemic_pressure=epistemic_pressure,
            mean_uncertainty=mean_uncertainty,
            mean_novelty=mean_novelty,
            mean_curiosity=mean_curiosity,
            social_uncertainty_pressure=social_uncertainty_pressure,
            social_contradiction_pressure=social_contradiction_pressure,
            unresolved_social_pressure=unresolved_social_pressure,
            status=status,
        )
