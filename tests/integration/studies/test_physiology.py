import pytest

from symbiont_lab.studies.physiology import (
    run_physiology_study,
    run_runtime_recovery_study,
    run_runtime_replay_study,
    run_sustained_recovery_study,
)


def test_starvation_study_reaches_terminal_death_without_free_replenishment() -> None:
    result = run_physiology_study(ticks=64, maintenance_cost=0.2)
    assert result.death_tick is not None
    assert result.states[-1] == "dead"


def test_explicit_intake_delays_or_prevents_death() -> None:
    starved = run_physiology_study(ticks=8, maintenance_cost=0.1)
    fed = run_physiology_study(ticks=8, maintenance_cost=0.1, intake=[0.2] * 8)
    assert fed.death_tick is None
    assert fed.final_reserve > starved.final_reserve


def test_study_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        run_physiology_study(ticks=0)
    with pytest.raises(ValueError):
        run_physiology_study(intake=[-1.0])


def test_resting_schedule_records_dormancy_without_free_replenishment() -> None:
    result = run_physiology_study(ticks=12, maintenance_cost=0.1,
                                  resting=[True] * 12)
    assert result.dormant_ticks > 0
    assert result.final_reserve < 1.0


def test_runtime_replay_preserves_physiology_trajectory() -> None:
    assert run_runtime_replay_study()


def test_runtime_recovery_requires_intake_and_preserves_rest_intent() -> None:
    result = run_runtime_recovery_study()
    assert result.repaired == 0.25
    assert result.integrity_after_repair == 0.75
    assert result.maintenance_spent == 0.25
    assert result.rest_checkpoint_equal
    assert result.resumed


def test_sustained_recovery_requires_intake_and_replays_from_deficit_checkpoint() -> None:
    result = run_sustained_recovery_study()
    assert result.dormant_ticks == 1
    assert result.recovered
    assert result.recovery_tick == 5
    assert not result.no_intake_recovered
    assert result.checkpoint_replay_equal


def test_sustained_recovery_rejects_invalid_schedule() -> None:
    with pytest.raises(ValueError):
        run_sustained_recovery_study(deficit_ticks=0)
    with pytest.raises(ValueError):
        run_sustained_recovery_study(deficit_cost=0.0)
    with pytest.raises(ValueError):
        run_sustained_recovery_study(recovery_intake=-1.0)
