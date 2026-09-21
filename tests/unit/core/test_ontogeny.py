import pytest

from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.ontogeny import OntogenyController, PhysicalLifeStage
from symbiont.core.physiology import LivingBodyState, VitalState
from symbiont.core.physiology_config import PhysiologyConfig


def _zero_replenishment():
    return {
        kind: 0.0
        for kind in ("observation", "cognition", "persistence", "maintenance")
    }


def test_growth_is_constitutive_and_consumes_physical_energy() -> None:
    state = LivingBodyState(energy_reserve=1.0, max_energy=2.0)
    ledger = MetabolicLedger(
        replenishment=_zero_replenishment(),
        body_state=state,
    )
    controller = OntogenyController(
        config=PhysiologyConfig(
            growth_rate_per_tick=0.1,
            growth_energy_fraction_per_progress=0.5,
        ),
        body_state=state,
    )
    before = state.energy_reserve

    snapshot = controller.constitutive_step(ledger)

    assert snapshot.stage is PhysicalLifeStage.GROWING
    assert state.growth_progress == pytest.approx(0.1)
    assert snapshot.growth_energy_cost == pytest.approx(0.1)
    assert state.energy_reserve == pytest.approx(before - 0.1)


def test_growth_cannot_create_progress_without_physical_energy() -> None:
    state = LivingBodyState(
        energy_reserve=0.0,
        max_energy=2.0,
        vital_state=VitalState.DEAD,
        death_tick=0,
    )
    ledger = MetabolicLedger(
        replenishment=_zero_replenishment(),
        body_state=state,
    )
    controller = OntogenyController(
        config=PhysiologyConfig(),
        body_state=state,
    )

    snapshot = controller.constitutive_step(ledger)

    assert state.growth_progress == pytest.approx(0.0)
    assert snapshot.growth_energy_cost == pytest.approx(0.0)
    assert snapshot.stage is PhysicalLifeStage.DEAD
    assert not snapshot.reproductively_ready


def test_reproductive_readiness_depends_only_on_body_state() -> None:
    state = LivingBodyState(
        energy_reserve=1.5,
        max_energy=2.0,
        growth_progress=1.0,
        structural_integrity=1.0,
    )
    controller = OntogenyController(
        config=PhysiologyConfig(),
        body_state=state,
    )

    assert controller.reproductively_ready()

    state.structural_integrity = 0.5
    assert not controller.reproductively_ready()

    state.structural_integrity = 1.0
    state.senescence = 0.9
    assert not controller.reproductively_ready()

    state.senescence = 0.0
    state.energy_reserve = 0.1
    assert not controller.reproductively_ready()


def test_senescence_starts_from_age_and_causes_constitutive_wear() -> None:
    state = LivingBodyState(
        energy_reserve=1.0,
        max_energy=2.0,
        growth_progress=1.0,
        age_ticks=10,
        structural_integrity=1.0,
    )
    ledger = MetabolicLedger(
        replenishment=_zero_replenishment(),
        body_state=state,
    )
    controller = OntogenyController(
        config=PhysiologyConfig(
            senescence_start_ticks=10,
            senescence_rate_per_tick=0.2,
            senescence_wear_rate=0.1,
        ),
        body_state=state,
    )

    snapshot = controller.constitutive_step(ledger)

    assert snapshot.stage is PhysicalLifeStage.SENESCENT
    assert state.senescence == pytest.approx(0.2)
    assert snapshot.senescence_wear == pytest.approx(0.02)
    assert state.structural_integrity == pytest.approx(0.98)


def test_living_body_checkpoint_preserves_ontogeny_state() -> None:
    state = LivingBodyState(
        growth_progress=0.42,
        senescence=0.17,
        age_ticks=123,
    )

    restored = LivingBodyState.from_checkpoint(state.checkpoint())

    assert restored.growth_progress == pytest.approx(0.42)
    assert restored.senescence == pytest.approx(0.17)
    assert restored.age_ticks == 123
    assert restored.checkpoint()["schema_version"] == 3
