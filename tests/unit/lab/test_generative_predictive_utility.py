from __future__ import annotations

from lab.studies.learning.generative_predictive_utility import (
    run_generative_predictive_utility_study,
)


def test_multi_step_rollout_beats_persistence_and_one_step_at_longer_horizons() -> None:
    result = run_generative_predictive_utility_study(seeds=(101, 127, 149), horizons=(1, 2, 4))

    assert result.passed
    assert result.multi_step_accuracy == 1.0
    assert result.persistence_accuracy == 0.0
    assert result.one_step_accuracy == 1 / 3
    assert result.all_generated_origins_non_observed
    assert all(item.multi_step_termination == "completed" for item in result.trials)


def test_multi_step_predictive_utility_gate_is_deterministic() -> None:
    first = run_generative_predictive_utility_study().as_dict()
    second = run_generative_predictive_utility_study().as_dict()

    assert first == second
