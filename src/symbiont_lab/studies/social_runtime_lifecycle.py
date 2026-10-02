"""Evaluator-only social restart, lineage and death-boundary study."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont import __version__ as symbiont_version
from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits
from symbiont.core.embodiment.metabolism import MetabolicLedger
from symbiont.core.embodiment.physiology import PhysiologyController
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.organism_profile import HISTORICAL_V0
from symbiont.core.social import SocialHabitat
from symbiont.core.social.interactions import EcologicalResourcePool
from symbiont_lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud


@dataclass(frozen=True, slots=True)
class SocialRuntimeLifecycleStudy:
    restored_identity: bool
    replay_equal: bool
    resumed_after_restore: bool
    child_generation: int
    child_traceable_to_parent: bool
    parent_released_after_death: bool
    child_remains_live: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_lifecycle_study() -> SocialRuntimeLifecycleStudy:
    """Check social checkpoint/restart alongside bounded birth and death."""
    major, minor, patch = (int(part) for part in (symbiont_version.split(".") + ["0", "0"])[:3])
    version = (major, minor, patch)
    genome = load_base_genome(kernel_limits=KernelLimits(), running_version=version)
    authority = HabitatBirthAuthority(habitat_id="social-lifecycle", capacity=2)
    social = SocialHabitat(EcologicalResourcePool({"food": 4.0}), max_members=3)
    social.admit("parent")
    social.admit("peer")
    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    metabolism = MetabolicLedger(replenishment=zero)
    parent = OrganismRuntime(
        profile=HISTORICAL_V0,
        organism_id="parent",
        genome=genome,
        social_habitat=social,
        metabolism=metabolism,
        explicit_metabolism=True,
        physiology=PhysiologyController(),
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    parent.request_social_exchange("peer", "food", 0.5)
    parent.suspend_social_interaction("peer")
    runtime_payload = parent.checkpoint()
    social_payload = social.checkpoint()
    authority_payload = authority.checkpoint()

    restored_social = SocialHabitat.from_checkpoint(social_payload)
    restored_authority = HabitatBirthAuthority.from_checkpoint(authority_payload)
    restored = OrganismRuntime.from_checkpoint(
        runtime_payload,
        social_habitat=restored_social,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    if restored.organism_id not in restored_authority.live_ids:
        raise RuntimeError("restored subject is missing from laboratory population")
    replay_equal = restored.social_ledger.checkpoint() == parent.social_ledger.checkpoint()
    resumed_after_restore = restored.resume_social_interaction("peer")

    parent.living_body_state.growth_progress = 1.0
    child = materialize_clonal_bud(parent, authority=authority)
    if child is None:
        raise RuntimeError("social lifecycle study could not materialize child")
    child_record = next(
        row for row in authority.checkpoint()["lineage"] if row["organism_id"] == child.organism_id
    )
    social.admit(child.organism_id)
    metabolism.charge("maintenance", 8.0)
    parent.tick()
    authority.observe_death(parent)

    return SocialRuntimeLifecycleStudy(
        restored_identity=restored.organism_id == parent.organism_id,
        replay_equal=replay_equal,
        resumed_after_restore=resumed_after_restore,
        child_generation=child.generation,
        child_traceable_to_parent=child_record["parent_ids"] == ["parent"],
        parent_released_after_death="parent" not in social.members
        and "parent" not in authority.live_ids,
        child_remains_live=child.organism_id in authority.live_ids,
    )


__all__ = ["SocialRuntimeLifecycleStudy", "run_social_runtime_lifecycle_study"]
