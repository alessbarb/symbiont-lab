"""Evaluator-only multi-neighbor/context shift study for Milestone K."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeContextStudy:
    neighbors: int
    interactions: int
    choice_before: str
    choice_after_contradiction: str
    choice_after_suspension: str
    suspended_rejections: int
    contention_granted: float
    isolated_opportunities: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_context_study() -> SocialRuntimeContextStudy:
    """Exercise local revision with several neighbors and finite scarcity."""
    habitat = SocialHabitat(EcologicalResourcePool({"food": 4.5}), max_members=4)
    for member in ("observer", "peer-a", "peer-b", "isolated"):
        habitat.admit(member)
    observer = OrganismRuntime(organism_id="observer", social_habitat=habitat)
    isolated = OrganismRuntime(organism_id="isolated", social_habitat=habitat)

    # Establish two local evidence channels, then contradict one of them.
    observer.request_social_exchange("peer-a", "food", 2.0)
    observer.request_social_exchange("peer-b", "food", 2.0)
    before = observer.select_social_opportunity()
    observer.social_ledger.observe("observer", "peer-a", cost=2.0, conflict=True, tick=1)
    after_contradiction = observer.select_social_opportunity()

    observer.suspend_social_interaction("peer-b")
    rejected = 0
    try:
        observer.request_social_exchange("peer-b", "food", 2.0)
    except ValueError:
        rejected = 1
    after_suspension = observer.select_social_opportunity()
    observer.resume_social_interaction("peer-b")

    contention = habitat.compete([("peer-a", "food", 0.8), ("peer-b", "food", 0.8)])
    for target in ("observer", "peer-a", "peer-b"):
        isolated.suspend_social_interaction(target)
    isolated_opportunities = int(isolated.select_social_opportunity() is None)
    return SocialRuntimeContextStudy(
        neighbors=3,
        interactions=sum(item.observations for item in observer.social_ledger.relations),
        choice_before=before.target_id if before else "none",
        choice_after_contradiction=after_contradiction.target_id if after_contradiction else "none",
        choice_after_suspension=after_suspension.target_id if after_suspension else "none",
        suspended_rejections=rejected,
        contention_granted=sum(item.granted for item in contention),
        isolated_opportunities=isolated_opportunities,
    )


__all__ = ["SocialRuntimeContextStudy", "run_social_runtime_context_study"]
