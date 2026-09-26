from __future__ import annotations

from symbiont_lab.studies.learning.generative_counterfactual_utility import (
    run_generative_counterfactual_utility_study,
)


def test_gc_e3_matched_control_requires_discriminating_probe() -> None:
    study = run_generative_counterfactual_utility_study(seeds=(101, 127, 149))

    assert study.passed
    assert study.treatment_selection_rate == 1.0
    assert study.treatment_selection_rate > study.control_discriminating_selection_rate
    assert study.mean_discrimination_gain > 0.0
    assert study.all_factual_contamination_free
    assert all(
        result.treatment_discrimination == 1.0 and result.control_discrimination == 0.0
        for result in study.results
    )


def test_gc_e3_is_deterministic_for_identical_seeds() -> None:
    first = run_generative_counterfactual_utility_study(seeds=(101, 127))
    second = run_generative_counterfactual_utility_study(seeds=(101, 127))

    assert first.as_dict() == second.as_dict()
