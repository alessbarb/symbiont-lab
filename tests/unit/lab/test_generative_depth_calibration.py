from __future__ import annotations

from symbiont_lab.studies.learning.generative_depth_calibration import (
    run_generative_depth_calibration_study,
)


def test_depth_calibration_records_factual_comparisons_at_each_depth() -> None:
    result = run_generative_depth_calibration_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.depths == (1, 2, 4)
    assert result.uncertainty_increases_with_depth
    assert result.observed_error_increases_with_depth
    assert result.all_comparisons_recorded
    assert result.all_factual_contamination_free
    assert result.all_generated_origins_non_observed
    assert all(item.comparable_count == 1 for item in result.trials)


def test_depth_calibration_gate_is_deterministic() -> None:
    first = run_generative_depth_calibration_study().as_dict()
    second = run_generative_depth_calibration_study().as_dict()

    assert first == second
