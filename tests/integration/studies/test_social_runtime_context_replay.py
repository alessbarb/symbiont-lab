from symbiont_lab.studies.social_runtime_context_replay import (
    run_social_runtime_context_replay_study,
)


def test_social_context_live_and_replay_remain_in_parity() -> None:
    result = run_social_runtime_context_replay_study()
    assert result.choice_before == "peer-a"
    assert result.choice_after_live == "peer-b"
    assert result.choice_after_restore == "peer-b"
    assert result.checkpoint_equal
    assert result.post_restore_parity
    assert result.suspension_parity
