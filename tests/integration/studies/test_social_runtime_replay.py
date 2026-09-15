from symbiont_lab.studies.social_runtime_replay import run_social_runtime_replay_study


def test_social_runtime_replay_preserves_local_evidence_and_releases_death() -> None:
    result = run_social_runtime_replay_study()
    assert result.replay_equal
    assert result.local_relation_support == 0.5
    assert result.restored_members == ("a", "b")
    assert result.dead_member_released
