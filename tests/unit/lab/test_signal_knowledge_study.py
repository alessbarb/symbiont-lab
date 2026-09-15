import pytest

from symbiont_lab.studies.learning.signal_knowledge import (
    run_signal_knowledge,
    run_acceptance_scenarios,
    run_acceptance_suite,
    summarize_acceptance,
)


def test_signal_knowledge_study_is_reproducible_and_keeps_truth_outside_engine():
    first = run_signal_knowledge(101)
    second = run_signal_knowledge(101)
    assert first == second
    assert first.ticks == 192
    assert first.profiles == 2
    assert first.claims >= 2


def test_acceptance_matrix_is_deterministic_and_exercises_gaps_and_id_change():
    first = run_acceptance_scenarios(101)
    second = run_acceptance_scenarios(101)
    assert first == second
    assert {item.name for item in first} == {
        "constant", "positive_ar", "negative_ar", "lag", "common_source", "gaps", "id_change"
    }
    assert next(item for item in first if item.name == "gaps").coverage < 1.0
    assert next(item for item in first if item.name == "id_change").profiles >= 3


def test_frozen_acceptance_seeds_support_the_lag_case_without_using_labels():
    results = run_acceptance_suite()
    lag = [item for item in results if item.name == "lag"]
    assert [item.seed for item in lag] == [101, 127, 149]
    assert all(item.supported >= 1 for item in lag)


def test_acceptance_summary_reports_evaluator_only_precision_and_recall():
    report = summarize_acceptance(run_acceptance_suite())
    assert report.total_scenarios == 21
    assert report.expected_positive_scenarios == 3
    assert report.true_positive_scenarios == 3
    assert report.false_positive_scenarios == 2
    assert report.support_precision == pytest.approx(0.6)
    assert report.lag_recall == pytest.approx(1.0)
    assert report.mean_coverage == pytest.approx((18 * 1.0 + 3 * 0.80078125) / 21)
    assert report.mean_discovery_latency == pytest.approx(217.6)
    assert report.total_selected_observations == 21 * 256 - 3 * (256 // 5)


def test_acceptance_summary_rejects_empty_results():
    with pytest.raises(ValueError, match="non-empty"):
        summarize_acceptance(())
