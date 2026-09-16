from symbiont_lab.studies.social_runtime_longitudinal import run_social_runtime_longitudinal_study


def test_prolonged_runtime_ecology_is_deterministic_and_replayable() -> None:
    first = run_social_runtime_longitudinal_study(ticks=24, members=4)
    second = run_social_runtime_longitudinal_study(ticks=24, members=4)
    assert first == second
    assert first.interactions > 0
    assert first.unique_pairs >= 2
    assert first.checkpoint_replay_equal
    assert first.continuation_replay_equal
    assert first.isolated_members == 0
