from symbiont.core.metabolism import MetabolicSnapshot, ResourcePressure
from symbiont.core.physiology import PhysiologyController, VitalState

def snap(p): return MetabolicSnapshot(1, {"x":1}, {"x":-1}, {}, p)
def test_unrecoverable_pressure_causes_irreversible_death():
    c=PhysiologyController(); assert c.advance(snap(ResourcePressure.UNRECOVERABLE),tick=4).state is VitalState.DEAD
    assert c.advance(snap(ResourcePressure.NORMAL),tick=5).state is VitalState.DEAD
