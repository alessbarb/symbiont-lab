"""Evaluator-only emergence scenarios for Milestone K."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.social import RelationValence, SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialStudy:
    exchange_granted: float
    competition_granted: tuple[float, ...]
    positive_relations: int
    negative_relations: int
    members_after_release: tuple[str, ...]
    restarted_members: tuple[str, ...] = ()
    restarted_resource: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_study(*, resource: float = 1.0, request: float = 0.8) -> SocialStudy:
    if resource <= 0.0 or request <= 0.0:
        raise ValueError("invalid social study parameters")
    habitat = SocialHabitat(EcologicalResourcePool({"food": resource}))
    for organism_id in ("a", "b", "c"):
        habitat.admit(organism_id)
    exchange = habitat.exchange("a", "b", "food", min(request, resource))
    competition = habitat.compete([("a", "food", request), ("c", "food", request)])
    relations = habitat.engine.ledger.relations
    positive = sum(relation.valence is RelationValence.POSITIVE for relation in relations)
    negative = sum(relation.valence is RelationValence.NEGATIVE for relation in relations)
    habitat.release("b")
    checkpoint = habitat.checkpoint()
    restored = SocialHabitat.from_checkpoint(checkpoint)
    return SocialStudy(exchange.granted, tuple(item.granted for item in competition),
                       positive, negative, habitat.members, restored.members,
                       restored.engine.pool.snapshot()["food"])


__all__ = ["SocialStudy", "run_social_study"]
