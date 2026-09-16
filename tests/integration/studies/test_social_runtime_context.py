from symbiont_lab.studies.social_runtime_context import run_social_runtime_context_study


def test_runtime_context_shift_is_deterministic_and_bounded() -> None:
    result = run_social_runtime_context_study()
    assert result == run_social_runtime_context_study()
    assert result.neighbors == 3
    assert result.interactions == 3
    assert result.choice_before == "peer-a"
    assert result.choice_after_contradiction == "peer-b"
    assert result.choice_after_suspension == "isolated"
    assert result.suspended_rejections == 1
    assert result.contention_granted == 0.5
    assert result.isolated_opportunities == 1
