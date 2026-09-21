import pytest

from symbiont.core.metabolism import MetabolicLedger, ResourcePressure


def test_ledger_charges_and_classifies_bounded_pressure():
    ledger = MetabolicLedger(capacity={k: 1.0 for k in ("observation", "cognition", "persistence", "maintenance")})
    ledger.charge("observation", 2.2)
    assert ledger.snapshot().pressure is ResourcePressure.ELEVATED
    ledger.charge("observation", 10.0)
    assert ledger.snapshot().reserve["observation"] == -1.0
    assert ledger.snapshot().pressure is ResourcePressure.UNRECOVERABLE


def test_advance_replenishes_and_charges_retention():
    ledger = MetabolicLedger()
    ledger.charge("persistence", 0.4)
    snap = ledger.advance(retained_units=0.2)
    assert snap.tick == 1
    assert snap.spent["maintenance"] == 0.2
    assert ledger.snapshot().spent["observation"] == 0.0


def test_checkpoint_round_trip_and_validation():
    ledger = MetabolicLedger(tick=3)
    ledger.charge("cognition", 0.25)
    restored = MetabolicLedger.from_checkpoint(ledger.checkpoint())
    assert restored.tick == 3
    assert restored.snapshot().reserve == ledger.snapshot().reserve
    with pytest.raises(ValueError):
        MetabolicLedger.from_checkpoint({"schema_version": 2})


def test_checkpoint_round_trip_preserves_bounded_negative_reserve():
    ledger = MetabolicLedger(tick=7)
    ledger.charge("maintenance", 1.25)

    assert ledger.snapshot().reserve["maintenance"] == pytest.approx(-0.25)

    restored = MetabolicLedger.from_checkpoint(ledger.checkpoint())

    assert restored.tick == 7
    assert restored.snapshot().reserve == pytest.approx(ledger.snapshot().reserve)
    # A negative accounting balance no longer means the organism has no
    # physical energy. Viability follows the common pool, not one category.
    assert restored.snapshot().pressure is ResourcePressure.NORMAL
    assert restored.body_state.energy_reserve == pytest.approx(2.75)


def test_explicit_intake_restores_one_physical_pool_without_compartment_gating() -> None:
    from symbiont.core.physiology import LivingBodyState

    state = LivingBodyState(energy_reserve=1.0, max_energy=2.0)
    ledger = MetabolicLedger(
        replenishment={k: 0.0 for k in ("observation", "cognition", "persistence", "maintenance")},
        body_state=state,
    )
    ledger.charge("observation", 0.75)
    assert state.energy_reserve == pytest.approx(0.25)

    assert ledger.intake("observation", 0.75) == pytest.approx(0.75)
    assert state.energy_reserve == pytest.approx(1.0)
    assert ledger.snapshot().reserve["observation"] == pytest.approx(1.0)

    # The accounting channel is full, but the common physical pool still has
    # headroom and therefore accepts additional external energy.
    assert ledger.intake("observation", 0.5) == pytest.approx(0.5)
    assert ledger.snapshot().reserve["observation"] == pytest.approx(1.0)
    assert state.energy_reserve == pytest.approx(1.5)



def test_finalize_cycle_merges_post_advance_costs_without_leaking() -> None:
    ledger = MetabolicLedger(
        replenishment={
            kind: 0.0
            for kind in ("observation", "cognition", "persistence", "maintenance")
        }
    )

    base = ledger.advance(retained_units=0.1)
    ledger.charge("maintenance", 0.02)
    finalized = ledger.finalize_cycle(base)

    assert finalized.spent["maintenance"] == pytest.approx(0.12)
    assert ledger.snapshot().spent["maintenance"] == 0.0

    next_tick = ledger.advance()
    assert next_tick.spent["maintenance"] == 0.0


def test_all_cost_kinds_draw_from_the_same_physical_energy_pool() -> None:
    ledger = MetabolicLedger(
        replenishment={k: 0.0 for k in ("observation", "cognition", "persistence", "maintenance")}
    )
    before = ledger.body_state.energy_reserve

    ledger.charge("observation", 0.10)
    ledger.charge("cognition", 0.20)
    ledger.charge("persistence", 0.15)
    ledger.charge("maintenance", 0.05)

    assert ledger.body_state.energy_reserve == pytest.approx(before - 0.50)


def test_accounting_replenishment_never_mints_physical_energy() -> None:
    ledger = MetabolicLedger()
    ledger.charge("cognition", 0.25)
    before = ledger.body_state.energy_reserve

    ledger.advance()

    assert ledger.body_state.energy_reserve == pytest.approx(before)


def test_checkpoint_preserves_physical_pool_and_rejects_old_schema() -> None:
    ledger = MetabolicLedger()
    ledger.charge("maintenance", 0.3)
    restored = MetabolicLedger.from_checkpoint(ledger.checkpoint())

    assert restored.body_state.energy_reserve == pytest.approx(
        ledger.body_state.energy_reserve
    )
    assert restored.body_state.max_energy == pytest.approx(
        ledger.body_state.max_energy
    )
    with pytest.raises(ValueError):
        MetabolicLedger.from_checkpoint({"schema_version": 1})
