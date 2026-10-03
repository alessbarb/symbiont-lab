from __future__ import annotations

from lab.studies.learning.generative_planning_utility import (
    run_generative_planning_utility_study,
)


def test_multi_step_planning_improves_matched_action_selection() -> None:
    result = run_generative_planning_utility_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.control_success_rate == 0.0
    assert result.treatment_success_rate == 1.0
    assert result.planning_gain == 1.0
    assert result.all_factual_counts_equal
    assert result.all_factual_contamination_free
    assert result.all_generated_origins_non_observed


def test_planning_utility_gate_is_deterministic() -> None:
    assert (
        run_generative_planning_utility_study().as_dict()
        == run_generative_planning_utility_study().as_dict()
    )
