import pytest

from symbiont.core.metabolism import MetabolicLedger, ResourcePressure


def test_ledger_charges_and_classifies_bounded_pressure():
    ledger = MetabolicLedger(capacity={k: 1.0 for k in ("observation", "cognition", "persistence", "maintenance")})
    ledger.charge("observation", 0.7)
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
