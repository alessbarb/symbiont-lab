from symbiont.core.homeostasis import HomeostaticAction, HomeostaticController
from symbiont.core.metabolism import ResourcePressure
import pytest

def test_pressure_reduces_activity_and_pauses_plasticity():
 h=HomeostaticController(); s=h.regulate(ResourcePressure.SEVERE)
 assert s.action is HomeostaticAction.PAUSE_PLASTICITY and not s.plasticity_enabled and s.activity_scale < 1

def test_homeostatic_checkpoint_preserves_shared_integrity() -> None:
    controller = HomeostaticController(integrity=0.5)
    restored = HomeostaticController.from_checkpoint(controller.checkpoint())
    assert restored.integrity == controller.integrity


def test_constitutive_repair_uses_resources_without_cognitive_request() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(structural_integrity=0.5)
    metabolism = MetabolicLedger(body_state=state)
    controller = HomeostaticController(body_state=state)

    before = metabolism.snapshot().reserve["maintenance"]
    physical_before = state.energy_reserve
    repaired = controller.constitutive_step(metabolism)

    assert repaired == controller.config.autonomous_repair_rate
    assert state.structural_integrity == 0.5 + repaired
    assert metabolism.snapshot().reserve["maintenance"] == before - repaired
    assert state.energy_reserve == physical_before - repaired


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


def test_constitutive_repair_cannot_exceed_physical_energy_pool() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(
        energy_reserve=0.005,
        max_energy=1.0,
        structural_integrity=0.5,
    )
    metabolism = MetabolicLedger(body_state=state)
    controller = HomeostaticController(body_state=state)

    repaired = controller.constitutive_step(metabolism)

    assert repaired == pytest.approx(0.005)
    assert state.energy_reserve == pytest.approx(0.0)


def test_homeostatic_deviation_falls_when_internal_energy_recovers():
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.physiology import LivingBodyState

    body = LivingBodyState(
        energy_reserve=0.2,
        max_energy=2.0,
        structural_integrity=1.0,
        temperature=0.5,
        fatigue=0.0,
    )
    controller = HomeostaticController(body_state=body)
    before = controller.deviation()

    body.add_energy(1.2)
    after = controller.deviation()

    assert 0.0 <= after < before <= 1.0


def test_homeostatic_deviation_tracks_worst_internal_viability_error():
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.physiology import LivingBodyState

    body = LivingBodyState(
        energy_reserve=2.0,
        max_energy=2.0,
        structural_integrity=0.4,
        temperature=0.5,
        fatigue=0.2,
    )
    controller = HomeostaticController(body_state=body)

    assert controller.deviation() == pytest.approx(0.6)
