from symbiont_lab.studies.learning.signal_knowledge import run_signal_knowledge, run_acceptance_scenarios, run_acceptance_suite


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
