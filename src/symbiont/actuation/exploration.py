"""Contextual exploration without a developmental mode or scalar reward."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExplorationSignals:
    uncertainty: float
    novelty: float
    learning_progress: float
    effect_relevance: float
    controllability_potential: float | None
    physiological_cost: float | None
    risk: float | None


class ExplorationPolicy:
    """Rank opportunities lexicographically from organism-owned evidence.

    The specification intentionally does not freeze a weighted utility formula.
    Unknown controllability remains None rather than being collapsed to zero.
    """

    def rank_key(self, signals: ExplorationSignals) -> tuple[float, ...]:
        safety = 1.0 - min(1.0, max(0.0, signals.risk or 0.0))
        affordability = 1.0 - min(1.0, max(0.0, signals.physiological_cost or 0.0))
        unknown_bonus = 1.0 if signals.controllability_potential is None else 0.0
        learnable = max(0.0, signals.learning_progress)
        return (
            safety,
            affordability,
            learnable,
            unknown_bonus,
            max(0.0, signals.uncertainty),
            max(0.0, signals.novelty),
            max(0.0, signals.effect_relevance),
        )

    def choose(self, opportunities: tuple[tuple[str, ExplorationSignals], ...]) -> str | None:
        if not opportunities:
            return None
        return max(opportunities, key=lambda item: (self.rank_key(item[1]), item[0]))[0]
