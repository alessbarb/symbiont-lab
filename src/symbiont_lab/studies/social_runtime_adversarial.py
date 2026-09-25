"""Evaluator-only runtime social boundary scenarios for Milestone K.

The harness supplies bounded environmental events (contention and suspension)
and records what the authorized habitat and local runtimes expose.  It does not
assign a social objective or return scenario labels to any organism.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeAdversarialStudy:
    cooperation_granted: float
    contention_granted: float
    contention_requested: float
    isolated_opportunities: int
    one_way_observations: int
    rejected_exchange_blocked: bool
    resumed_exchange_granted: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_adversarial_study() -> SocialRuntimeAdversarialStudy:
    """Exercise support, finite contention and deliberate channel isolation."""
    habitat = SocialHabitat(EcologicalResourcePool({"food": 3.0}), max_members=4)
    ids = ("a", "b", "c", "isolated")
    for organism_id in ids:
        habitat.admit(organism_id)
    runtimes = {
        organism_id: OrganismRuntime(organism_id=organism_id, social_habitat=habitat)
        for organism_id in ids
    }

    cooperation = runtimes["a"].request_social_exchange("b", "food", 0.5)

    # The habitat mediates simultaneous demand; no organism receives a label
    # describing the scenario or a guaranteed allocation.
    contention = habitat.compete([("b", "food", 2.0), ("c", "food", 2.0)])
    contention_granted = sum(item.granted for item in contention)

    # A directional refusal is an observable boundary, not a global social
    # label.  Run it after contention so this probe does not change the
    # independent finite-contention measurement above.
    runtimes["a"].reject_social_interaction("c")
    try:
        runtimes["a"].request_social_exchange("c", "food", 0.25)
    except ValueError:
        rejected_exchange_blocked = True
    else:
        rejected_exchange_blocked = False
    runtimes["a"].resume_social_interaction("c")
    habitat.engine.pool.replenish("food", 0.25)
    resumed_exchange = runtimes["a"].request_social_exchange("c", "food", 0.25)

    for target_id in ("a", "b", "c"):
        runtimes["isolated"].suspend_social_interaction(target_id)
    isolated_opportunities = int(runtimes["isolated"].select_social_opportunity() is None)
    one_way_observations = sum(
        relation.observations
        for relation in runtimes["a"].social_ledger.relations
        if relation.source_id == "a"
        and relation.target_id == "b"
        and relation.reciprocal_observations == 0
    )
    return SocialRuntimeAdversarialStudy(
        cooperation_granted=cooperation.granted,
        contention_granted=contention_granted,
        contention_requested=4.0,
        isolated_opportunities=isolated_opportunities,
        one_way_observations=one_way_observations,
        rejected_exchange_blocked=rejected_exchange_blocked,
        resumed_exchange_granted=resumed_exchange.granted,
    )


__all__ = ["SocialRuntimeAdversarialStudy", "run_social_runtime_adversarial_study"]
