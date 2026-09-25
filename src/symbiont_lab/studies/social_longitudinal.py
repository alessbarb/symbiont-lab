"""Bounded longitudinal social evidence study (evaluator-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialLongitudinalStudy:
    ticks: int
    successful_exchanges: int
    rejected_during_suspension: int
    resumed: bool
    relation_observations: int
    relation_freshness: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_longitudinal_study(*, ticks: int = 12) -> SocialLongitudinalStudy:
    if ticks < 4:
        raise ValueError("ticks must be at least 4")
    habitat = SocialHabitat(EcologicalResourcePool({"food": float(ticks)}))
    habitat.admit("a")
    habitat.admit("b")
    successful = rejected = 0
    resumed_once = False
    suspension_tick = ticks // 2
    for tick in range(ticks):
        if tick == suspension_tick:
            habitat.suspend("a", "b")
        if tick == suspension_tick + 1:
            resumed_once = habitat.resume("a", "b") or resumed_once
        try:
            outcome = habitat.exchange("a", "b", "food", 1.0)
            successful += int(outcome.granted > 0.0)
            # Tick is attached to the aggregate evidence without changing the
            # allocation contract.
            habitat.engine.ledger.observe("a", "b", benefit=0.0, tick=tick, channel="food")
        except ValueError:
            rejected += 1
    relation = habitat.engine.ledger.relations[0]
    return SocialLongitudinalStudy(
        ticks, successful, rejected, resumed_once, relation.observations, relation.freshness(ticks)
    )


__all__ = ["SocialLongitudinalStudy", "run_social_longitudinal_study"]
