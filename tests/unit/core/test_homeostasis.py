from symbiont.core.homeostasis import HomeostaticAction, HomeostaticController
from symbiont.core.metabolism import ResourcePressure

def test_pressure_reduces_activity_and_pauses_plasticity():
 h=HomeostaticController(); s=h.regulate(ResourcePressure.SEVERE)
 assert s.action is HomeostaticAction.PAUSE_PLASTICITY and not s.plasticity_enabled and s.activity_scale < 1

def test_damage_repair_and_checkpoint():
 h=HomeostaticController(integrity=.5); s=h.regulate(ResourcePressure.NORMAL, repairable_damage=.2)
 assert s.action is HomeostaticAction.REPAIR and s.integrity > .5
 assert HomeostaticController.from_checkpoint(h.checkpoint()).integrity == h.integrity


def test_repair_with_resources_is_bounded_and_charged() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    controller = HomeostaticController(integrity=0.5)
    metabolism = MetabolicLedger()
    repaired = controller.repair_with_resources(metabolism, 0.8)
    assert repaired == 0.25
    assert controller.integrity == 0.75
    assert metabolism.snapshot().reserve["maintenance"] == 0.75
