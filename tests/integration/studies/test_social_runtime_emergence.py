from symbiont_lab.studies.social_runtime_emergence import run_social_runtime_emergence_study


def test_runtime_emergence_study_is_deterministic_and_uses_local_choices() -> None:
    first = run_social_runtime_emergence_study(ticks=10, members=4)
    second = run_social_runtime_emergence_study(ticks=10, members=4)
    assert first == second
    assert first.interactions > 0
    assert first.unique_pairs >= 2
    assert first.isolated_members == 0
    assert first.reciprocal_observations > 0
