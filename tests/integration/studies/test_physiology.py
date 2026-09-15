import pytest

from symbiont_lab.studies.physiology import run_physiology_study


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
