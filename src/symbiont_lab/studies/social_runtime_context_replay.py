"""Evaluator-only live/replay parity for multi-neighbor social decisions."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeContextReplayStudy:
    choice_before: str
    choice_after_live: str
    choice_after_restore: str
    checkpoint_equal: bool
    post_restore_parity: bool
    suspension_parity: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_context_replay_study() -> SocialRuntimeContextReplayStudy:
    habitat = SocialHabitat(EcologicalResourcePool({"food": 6.0}), max_members=3)
    for member in ("observer", "peer-a", "peer-b"):
        habitat.admit(member)
    live = OrganismRuntime(organism_id="observer", social_habitat=habitat)
    live.social_ledger.observe("observer", "peer-a", benefit=2.0, tick=0)
    live.social_ledger.observe("observer", "peer-b", benefit=1.0, tick=0)
    before = live.select_social_opportunity()
    runtime_payload = live.checkpoint()
    habitat_payload = habitat.checkpoint()
    restored_habitat = SocialHabitat.from_checkpoint(habitat_payload)
    restored = OrganismRuntime.from_checkpoint(
        runtime_payload, social_habitat=restored_habitat,
        bootstrap_semantic_senses=False, discover_senses=False,
    )
    checkpoint_equal = restored.social_ledger.checkpoint() == live.social_ledger.checkpoint()

    # Apply the same new evidence to both branches after the checkpoint.
    for runtime in (live, restored):
        runtime.social_ledger.observe("observer", "peer-a", cost=4.0, conflict=True, tick=1)
    live_choice = live.select_social_opportunity()
    restored_choice = restored.select_social_opportunity()
    live.suspend_social_interaction("peer-b")
    restored.suspend_social_interaction("peer-b")
    suspension_parity = (live.select_social_opportunity().target_id
                         == restored.select_social_opportunity().target_id)
    return SocialRuntimeContextReplayStudy(
        choice_before=before.target_id if before else "none",
        choice_after_live=live_choice.target_id if live_choice else "none",
        choice_after_restore=restored_choice.target_id if restored_choice else "none",
        checkpoint_equal=checkpoint_equal,
        post_restore_parity=live_choice == restored_choice,
        suspension_parity=suspension_parity,
    )


__all__ = ["SocialRuntimeContextReplayStudy", "run_social_runtime_context_replay_study"]
