from symbiont.core.metabolism import MetabolicSnapshot, ResourcePressure
from symbiont.core.physiology import PhysiologyController, VitalState

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
