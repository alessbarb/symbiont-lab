"""Synthetic niche-differentiation study; never feeds labels into cognition."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialSpecializationStudy:
    ticks: int
    a_food: float
    a_water: float
    b_food: float
    b_water: float
    distinct_niches: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_specialization_study(*, ticks: int = 8) -> SocialSpecializationStudy:
    if ticks < 1:
        raise ValueError("ticks must be positive")
    habitat = SocialHabitat(EcologicalResourcePool({"food": float(ticks), "water": float(ticks)}))
    habitat.admit("a"); habitat.admit("b")
    totals = {("a", "food"): 0.0, ("a", "water"): 0.0,
              ("b", "food"): 0.0, ("b", "water"): 0.0}
    for tick in range(ticks):
        for organism_id, resource in (("a", "food"), ("b", "water")):
            outcome = habitat.compete([(organism_id, resource, 1.0)])[0]
            totals[(organism_id, resource)] += outcome.granted
    return SocialSpecializationStudy(
        ticks, totals[("a", "food")], totals[("a", "water")],
        totals[("b", "food")], totals[("b", "water")],
        totals[("a", "food")] > totals[("a", "water")] and
        totals[("b", "water")] > totals[("b", "food")],
    )


__all__ = ["SocialSpecializationStudy", "run_social_specialization_study"]
