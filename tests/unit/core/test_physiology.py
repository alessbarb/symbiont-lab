from symbiont.core.metabolism import MetabolicSnapshot, ResourcePressure
from symbiont.core.physiology import PhysiologyController, VitalState
import pytest

def snap(p): return MetabolicSnapshot(1, {"x":1}, {"x":-1}, {}, p)
def test_unrecoverable_pressure_causes_irreversible_death():
    c=PhysiologyController(); assert c.advance(snap(ResourcePressure.UNRECOVERABLE),tick=4).state is VitalState.DEAD
    assert c.advance(snap(ResourcePressure.NORMAL),tick=5).state is VitalState.DEAD


def test_runtime_refuses_execution_after_death() -> None:
    from symbiont.core.runtime import OrganismDeadError, OrganismRuntime
    runtime = OrganismRuntime(physiology=PhysiologyController(state=VitalState.DEAD, death_tick=1))
    try:
        runtime.tick()
    except OrganismDeadError:
        pass
    else:
        raise AssertionError("dead organism must not execute another tick")


def test_runtime_explicit_metabolism_disables_automatic_replenishment() -> None:
    from symbiont.core.runtime import OrganismRuntime
    runtime = OrganismRuntime(explicit_metabolism=True)
    assert all(value == 0.0 for value in runtime.metabolism.checkpoint()["replenishment"].values())
    assert runtime.effective_configuration()["explicit_metabolism"] is True


def test_environmental_damage_is_bounded_and_requires_resource_backed_repair() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.runtime import OrganismRuntime

    metabolism = MetabolicLedger(
        replenishment={kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    )
    runtime = OrganismRuntime(metabolism=metabolism, explicit_metabolism=True)
    metabolism.charge("maintenance", 1.0)
    assert runtime.apply_environmental_damage(0.2) == pytest.approx(0.2)
    assert runtime.homeostasis.integrity == pytest.approx(0.8)
    assert runtime.repair(0.1) == 0.0
    metabolism.intake("maintenance", 0.2)
    assert runtime.repair(0.1) == pytest.approx(0.1)
    try:
        runtime.apply_environmental_damage(0.26)
    except ValueError:
        pass
    else:
        raise AssertionError("damage must remain bounded")


def test_dormant_runtime_scales_declared_activity_costs() -> None:
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.metabolism import MetabolicLedger
    metabolism = MetabolicLedger(
        replenishment={kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    )
    runtime = OrganismRuntime(metabolism=metabolism, physiology=PhysiologyController(state=VitalState.DORMANT))
    result = runtime.tick()
    assert result.metabolism.spent["observation"] <= 0.25


def test_runtime_reproductive_pressure_and_authorized_budding() -> None:
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from types import SimpleNamespace
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.runtime import OrganismRuntime
    # A genome is optional for cognition, but required to materialize a child.
    genome = SimpleNamespace(genome_id="genome_test")
    authority = HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=2.0)
    pressure = ReproductivePressure(threshold_ticks=1)
    runtime = OrganismRuntime(organism_id="parent", genome=genome,
                              birth_authority=authority, reproductive_pressure=pressure,
                              bootstrap_semantic_senses=False, discover_senses=False)
    status = runtime.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    assert status.ready
    child = runtime.attempt_clonal_bud()
    assert child is not None and child.parent_ids == ("parent",)
    assert runtime.metabolism.snapshot().reserve["maintenance"] < 1.0
    assert runtime.attempt_clonal_bud() is None


def test_birth_denial_does_not_consume_parent_reproductive_pressure() -> None:
    from types import SimpleNamespace
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.runtime import OrganismRuntime

    authority = HabitatBirthAuthority(habitat_id="full", capacity=1, resource_budget=1.0)
    pressure = ReproductivePressure(threshold_ticks=1)
    runtime = OrganismRuntime(organism_id="parent", genome=SimpleNamespace(genome_id="g"),
                              birth_authority=authority, reproductive_pressure=pressure,
                              bootstrap_semantic_senses=False, discover_senses=False)
    before = pressure.reserve
    assert runtime.observe_reproductive_pressure(
        adaptive=True, capacity_exhausted=True, blocked_growth=True,
    ).ready
    assert runtime.attempt_clonal_bud() is None
    assert pressure.reserve == before
    assert authority.live_ids == ("parent",)


def test_runtime_checkpoint_preserves_reproductive_pressure() -> None:
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.runtime import OrganismRuntime
    pressure = ReproductivePressure(threshold_ticks=3)
    runtime = OrganismRuntime(reproductive_pressure=pressure,
                              bootstrap_semantic_senses=False, discover_senses=False)
    runtime.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(),
                                                bootstrap_semantic_senses=False,
                                                discover_senses=False)
    assert restored.reproductive_pressure is not None
    assert restored.reproductive_pressure.blocked_ticks == 1


def test_materialize_clonal_bud_starts_with_germinal_graph() -> None:
    import json
    from dataclasses import replace
    from importlib import resources
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.runtime import OrganismRuntime
    payload = json.loads(resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=2.0)
    runtime = OrganismRuntime(organism_id="parent", genome=genome, birth_authority=authority,
                              reproductive_pressure=ReproductivePressure(threshold_ticks=1),
                              bootstrap_semantic_senses=False, discover_senses=False)
    runtime.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = runtime.materialize_clonal_bud()
    assert child is not None
    assert child.organism_id != runtime.organism_id
    assert child.generation == 1
    assert child.cognitive_bridge is not None
    assert child.tick_count == 0


def test_materialized_child_can_join_parent_social_habitat_and_reproduce() -> None:
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat
    import json
    from dataclasses import replace
    from importlib import resources
    from symbiont.cognition.genome import GenomeCodec
    payload = json.loads(resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=3.0)
    social = SocialHabitat(EcologicalResourcePool({"food": 3.0}), max_members=3)
    social.admit("peer")
    parent = OrganismRuntime(organism_id="parent", genome=genome, birth_authority=authority,
                             social_habitat=social, reproductive_pressure=ReproductivePressure(threshold_ticks=1),
                             bootstrap_semantic_senses=False, discover_senses=False)
    assert parent.join_social_habitat(social)
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = parent.materialize_clonal_bud()
    assert child is not None and child.social_habitat is social
    assert child.reproductive_pressure is not None
    assert child.join_social_habitat(social)
    assert child.organism_id in social.members


def test_runtime_death_releases_birth_authority_once() -> None:
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import PhysiologyController
    from symbiont.core.runtime import OrganismRuntime, OrganismDeadError
    authority = HabitatBirthAuthority(habitat_id="h", capacity=1, resource_budget=1.0)
    metabolism = MetabolicLedger(replenishment={kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")})
    runtime = OrganismRuntime(organism_id="parent", birth_authority=authority, metabolism=metabolism,
                              bootstrap_semantic_senses=False, discover_senses=False)
    metabolism.charge("maintenance", 2.0)
    result = runtime.tick()
    assert result.physiology is not None and result.physiology.state.value == "dead"
    assert authority.live_ids == ()
    assert authority.resource_budget == 1.0
    try:
        runtime.tick()
    except OrganismDeadError:
        pass
    else:
        raise AssertionError("dead runtime must reject further ticks")


def test_runtime_rest_request_is_checkpointed_without_free_replenishment() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.runtime import OrganismRuntime
    metabolism = MetabolicLedger(
        replenishment={kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    )
    runtime = OrganismRuntime(metabolism=metabolism, explicit_metabolism=True,
                              bootstrap_semantic_senses=False, discover_senses=False)
    for kind in ("observation", "cognition", "persistence", "maintenance"):
        metabolism.charge(kind, 0.85)
    runtime.request_rest()
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(),
                                                bootstrap_semantic_senses=False,
                                                discover_senses=False)
    assert restored.resting_requested
    before = restored.metabolism.snapshot().reserve["maintenance"]
    result = restored.tick()
    assert result.physiology is not None and result.physiology.state.value == "dormant"
    assert restored.metabolism.snapshot().reserve["maintenance"] == before
    restored.resume_activity()
    assert not restored.resting_requested
