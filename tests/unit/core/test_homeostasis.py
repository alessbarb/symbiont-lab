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


def test_repair_attempt_on_intact_body_consumes_effort_without_repair() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    controller = HomeostaticController()
    metabolism = MetabolicLedger()

    repaired = controller.repair_with_resources(metabolism, 0.1)

    assert repaired == 0.0
    assert controller.integrity == 1.0
    assert metabolism.snapshot().reserve["maintenance"] == 0.9



def test_constitutive_repair_uses_resources_without_cognitive_request() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(structural_integrity=0.5)
    metabolism = MetabolicLedger(body_state=state)
    controller = HomeostaticController(body_state=state)

    before = metabolism.snapshot().reserve["maintenance"]
    repaired = controller.constitutive_step(metabolism)

    assert repaired == controller.config.autonomous_repair_rate
    assert state.structural_integrity == 0.5 + repaired
    assert metabolism.snapshot().reserve["maintenance"] == before - repaired


def test_constitutive_repair_stops_when_maintenance_reserve_is_empty() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(structural_integrity=0.5)
    metabolism = MetabolicLedger(
        replenishment={
            kind: 0.0
            for kind in ("observation", "cognition", "persistence", "maintenance")
        },
        body_state=state,
    )
    metabolism.charge("maintenance", 1.0)
    controller = HomeostaticController(body_state=state)

    assert controller.constitutive_step(metabolism) == 0.0
    assert state.structural_integrity == 0.5


def test_embodied_work_drives_fatigue_heat_and_recovery() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(temperature=0.5)
    metabolism = MetabolicLedger(body_state=state)
    controller = HomeostaticController(body_state=state)

    controller.constitutive_step(
        metabolism,
        embodied_work=0.25,
        resting=False,
    )
    fatigue_after_work = state.fatigue
    temperature_after_work = state.temperature

    assert fatigue_after_work > 0.0
    assert temperature_after_work > 0.5

    controller.constitutive_step(
        metabolism,
        embodied_work=0.0,
        resting=True,
    )

    assert state.fatigue < fatigue_after_work
    assert state.temperature < temperature_after_work


def test_fatigue_reduces_homeostatic_activity_capacity() -> None:
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(fatigue=1.0)
    controller = HomeostaticController(body_state=state)

    snapshot = controller.regulate(ResourcePressure.NORMAL)

    assert snapshot.action is HomeostaticAction.REDUCE_ACTIVITY
    assert snapshot.activity_scale == controller.config.fatigue_activity_floor
