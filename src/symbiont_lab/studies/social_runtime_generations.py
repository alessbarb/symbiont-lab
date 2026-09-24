"""Evaluator-only multi-generation social lifecycle study."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont import __version__ as symbiont_version
from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeGenerationsStudy:
    generations: int
    lineage_depth: int
    social_membership_survived: bool
    checkpoint_replay_equal: bool
    parent_release_count: int
    final_child_live: bool
    lineage_closed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_generations_study(*, generations: int = 3) -> SocialRuntimeGenerationsStudy:
    """Exercise bounded social continuity across several births and deaths."""
    if generations < 1:
        raise ValueError("generations must be positive")
    version = tuple(int(part) for part in (symbiont_version.split(".") + ["0", "0"])[:3])
    genome = load_base_genome(kernel_limits=KernelLimits(), running_version=version)
    authority = HabitatBirthAuthority(habitat_id="social-generations", capacity=2)
    social = SocialHabitat(EcologicalResourcePool({"food": 8.0}), max_members=3)
    social.admit("peer")
    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    active = OrganismRuntime(
        organism_id="generation-0", genome=genome, birth_authority=authority,
        social_habitat=social,
        metabolism=MetabolicLedger(replenishment=zero), explicit_metabolism=True,
        physiology=PhysiologyController(), bootstrap_semantic_senses=False, discover_senses=False,
    )
    assert active.join_social_habitat(social)
    release_count = 0
    membership_survived = True
    replay_equal = True
    lineage: list[tuple[str, tuple[str, ...]]] = []

    for index in range(generations):
        active.living_body_state.growth_progress = 1.0
        checkpoint = active.checkpoint()
        restored = OrganismRuntime.from_checkpoint(
            checkpoint, social_habitat=social, birth_authority=authority,
            bootstrap_semantic_senses=False, discover_senses=False,
        )
        replay_equal &= restored.social_ledger.checkpoint() == active.social_ledger.checkpoint()
        print("Loop", index, "Auth live:", len(authority.live_ids), "cap:", authority.capacity, "ready:", active._ontogeny.reproductively_ready())
        child = active.materialize_clonal_bud()
        print(f"Loop {index}: child is None? {child is None}")
        if child is not None:
            print(f"Loop {index}: join? {child.join_social_habitat(social)}")
        if child is None or not child.join_social_habitat(social):
            raise RuntimeError("multi-generation social birth failed")
        record = next(row for row in authority.checkpoint()["lineage"] if row["organism_id"] == child.organism_id)
        lineage.append((child.organism_id, tuple(record["parent_ids"])))
        membership_survived &= child.organism_id in social.members
        active.request_social_exchange("peer", "food", 0.25)
        active.metabolism.charge("maintenance", 8.0)
        active.tick()
        release_count += int(active.organism_id not in authority.live_ids and active.organism_id not in social.members)
        active = child

    final_live = active.organism_id in authority.live_ids and active.organism_id in social.members
    lineage_closed = len(lineage) == generations and all(parents for _, parents in lineage)
    return SocialRuntimeGenerationsStudy(
        generations=generations, lineage_depth=len(lineage),
        social_membership_survived=membership_survived,
        checkpoint_replay_equal=replay_equal, parent_release_count=release_count,
        final_child_live=final_live, lineage_closed=lineage_closed,
    )


__all__ = ["SocialRuntimeGenerationsStudy", "run_social_runtime_generations_study"]
