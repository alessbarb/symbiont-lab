"""Evaluator-only reciprocity and revision study for Milestone K.

The harness supplies bounded synthetic events; it does not label them for a
runtime or install a preference for cooperation.  Results are observations of
the relation ledger and can be replayed from the seed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.social import RelationValence, SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialReciprocityStudy:
    reciprocal_observations: int
    one_way_observations: int
    conflicted_relations: int
    positive_relations: int
    negative_relations: int
    isolated_members: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_reciprocity_study() -> SocialReciprocityStudy:
    """Exercise reciprocal exchange, opportunism, conflict and isolation."""
    habitat = SocialHabitat(EcologicalResourcePool({"food": 8.0}), max_members=4)
    for member in ("giver", "receiver", "opportunist", "isolated"):
        habitat.admit(member)

    # A later reverse exchange is evidence of reciprocity for the first pair.
    habitat.exchange("giver", "receiver", "food", 1.0)
    habitat.exchange("receiver", "giver", "food", 1.0)
    # One-way support followed by resource contention creates mixed evidence.
    habitat.exchange("opportunist", "giver", "food", 1.0)
    habitat.engine.ledger.observe("opportunist", "giver", cost=1.0, conflict=True, tick=4)

    relations = habitat.engine.ledger.relations
    return SocialReciprocityStudy(
        reciprocal_observations=sum(r.reciprocal_observations for r in relations),
        one_way_observations=sum(
            r.observations for r in relations if r.reciprocal_observations == 0
        ),
        conflicted_relations=sum(r.conflicts > 0 for r in relations),
        positive_relations=sum(r.valence is RelationValence.POSITIVE for r in relations),
        negative_relations=sum(r.valence is RelationValence.NEGATIVE for r in relations),
        isolated_members=len(set(habitat.members) - {"giver", "receiver", "opportunist"}),
    )


__all__ = ["SocialReciprocityStudy", "run_social_reciprocity_study"]
