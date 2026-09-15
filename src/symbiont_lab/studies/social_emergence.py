"""Seeded, policy-free interaction trace for bounded emergence measurements."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.social import RelationValence, SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialEmergenceStudy:
    seed: int
    ticks: int
    interactions: int
    positive_relations: int
    negative_relations: int
    neutral_or_unknown: int
    isolated_members: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_emergence_study(*, seed: int = 7, ticks: int = 32, members: int = 6) -> SocialEmergenceStudy:
    if ticks < 1 or members < 2:
        raise ValueError("invalid emergence study parameters")
    rng = random.Random(seed)
    habitat = SocialHabitat(EcologicalResourcePool({"food": float(ticks * members // 2)}), max_members=members)
    ids = tuple(f"org-{index}" for index in range(members))
    for organism_id in ids:
        habitat.admit(organism_id)
    interactions = 0
    touched: set[str] = set()
    for _ in range(ticks):
        source, target = rng.sample(ids, 2)
        touched.update((source, target)); interactions += 1
        if rng.random() < 0.5:
            habitat.exchange(source, target, "food", 1.0)
        else:
            habitat.compete([(source, "food", 1.0), (target, "food", 1.0)])
    relations = habitat.engine.ledger.relations
    positive = sum(item.valence is RelationValence.POSITIVE for item in relations)
    negative = sum(item.valence is RelationValence.NEGATIVE for item in relations)
    return SocialEmergenceStudy(seed, ticks, interactions, positive, negative,
                                len(relations) - positive - negative, len(set(ids) - touched))


__all__ = ["SocialEmergenceStudy", "run_social_emergence_study"]
