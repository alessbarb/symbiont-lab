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
