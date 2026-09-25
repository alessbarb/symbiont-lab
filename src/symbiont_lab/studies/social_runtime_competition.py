"""Evaluator-only competition proposals from local negative evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeCompetitionStudy:
    proposals: int
    granted: float
    peer_attributed_losses: int
    finite_resource_remaining: float
    no_global_label: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_competition_study() -> SocialRuntimeCompetitionStudy:
    """Let two runtimes propose contests; only the habitat adjudicates them."""
    habitat = SocialHabitat(EcologicalResourcePool({"opaque-resource": 0.5}), max_members=2)
    habitat.admit("left")
    habitat.admit("right")
    runtimes = tuple(
        OrganismRuntime(organism_id=member, social_habitat=habitat) for member in ("left", "right")
    )
    for runtime, target in zip(runtimes, ("right", "left")):
        runtime.social_ledger.observe(runtime.organism_id, target, cost=1.0, tick=0)
    proposals = tuple(runtime.propose_social_competition() for runtime in runtimes)
    requests = [
        (proposal.source_id, proposal.resource, proposal.amount)
        for proposal in proposals
        if proposal is not None
    ]
    outcomes = habitat.compete(requests)
    losses = sum(1 for outcome in outcomes if outcome.relation.target_id in {"left", "right"})
    return SocialRuntimeCompetitionStudy(
        proposals=len(requests),
        granted=sum(outcome.granted for outcome in outcomes),
        peer_attributed_losses=losses,
        finite_resource_remaining=habitat.engine.pool.snapshot()["opaque-resource"],
        no_global_label=all(not hasattr(runtime, "social_role") for runtime in runtimes),
    )


__all__ = ["SocialRuntimeCompetitionStudy", "run_social_runtime_competition_study"]
