from symbiont_lab.studies.social_runtime_generations import run_social_runtime_generations_study


def test_social_runtime_generations_are_bounded_and_replayable() -> None:
    result = run_social_runtime_generations_study(generations=3)
    assert result.generations == 3
    assert result.lineage_depth == 3
    assert result.social_membership_survived
    assert result.checkpoint_replay_equal
    assert result.parent_release_count == 3
    assert result.final_child_live
    assert result.lineage_closed
