import pytest

from symbiont_lab.studies.physiology import run_sustained_repair_study


def test_sustained_repair_consumes_intake_and_replays() -> None:
    result = run_sustained_repair_study()
    assert result.repaired_total == pytest.approx(0.6)
    assert result.final_integrity == pytest.approx(1.0)
    assert result.no_intake_repaired == 0.0
    assert result.checkpoint_replay_equal


def test_sustained_repair_rejects_invalid_schedule() -> None:
    with pytest.raises(ValueError):
        run_sustained_repair_study(cycles=1)
