"""Evaluator-only replay and death-boundary study for runtime social state."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeReplayStudy:
    replay_equal: bool
    resumed_after_restore: bool
    local_relation_support: float
    restored_members: tuple[str, ...]
    dead_member_released: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_replay_study() -> SocialRuntimeReplayStudy:
    habitat = SocialHabitat(EcologicalResourcePool({"food": 2.0}), max_members=2)
    habitat.admit("a")
    habitat.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=habitat)
    runtime.request_social_exchange("b", "food", 0.5)
    runtime.suspend_social_interaction("b")
    runtime_payload = runtime.checkpoint()
    habitat_payload = habitat.checkpoint()
    restored_habitat = SocialHabitat.from_checkpoint(habitat_payload)
    restored = OrganismRuntime.from_checkpoint(
        runtime_payload, social_habitat=restored_habitat,
        bootstrap_semantic_senses=False, discover_senses=False,
    )
    replay_equal = restored.social_ledger.checkpoint() == runtime.social_ledger.checkpoint()
    local_relation_support = restored.social_ledger.relations[0].support
    resumed_after_restore = restored.resume_social_interaction("b")
    if resumed_after_restore:
        restored.request_social_exchange("b", "food", 0.1)

    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    metabolism = MetabolicLedger(replenishment=zero)
    metabolism.charge("maintenance", 2.0)
    dying = OrganismRuntime(organism_id="b", social_habitat=habitat, metabolism=metabolism,
                            explicit_metabolism=True, physiology=PhysiologyController())
    dying.tick()
    return SocialRuntimeReplayStudy(
        replay_equal=replay_equal,
        resumed_after_restore=resumed_after_restore,
        local_relation_support=local_relation_support,
        restored_members=restored_habitat.members,
        dead_member_released="b" not in habitat.members,
    )


__all__ = ["SocialRuntimeReplayStudy", "run_social_runtime_replay_study"]
