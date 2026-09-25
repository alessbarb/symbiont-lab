from symbiont_lab.studies.social_runtime_preference import run_social_runtime_preference_study


def test_runtime_preference_is_local_and_replayable() -> None:
    first = run_social_runtime_preference_study(ticks=8)
    assert first == run_social_runtime_preference_study(ticks=8)
    assert first.selected_positive == 8
    assert first.selected_negative == 0
    assert first.selected_unknown == 0
    assert first.deterministic


def test_runtime_preference_rejects_invalid_horizon() -> None:
    import pytest

    with pytest.raises(ValueError):
        run_social_runtime_preference_study(ticks=0)
