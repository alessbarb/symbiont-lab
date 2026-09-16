from symbiont_lab.studies.social_runtime_lifecycle import run_social_runtime_lifecycle_study


def test_social_runtime_lifecycle_preserves_identity_lineage_and_death_boundary() -> None:
    result = run_social_runtime_lifecycle_study()
    assert result.restored_identity
    assert result.replay_equal
    assert result.resumed_after_restore
    assert result.child_generation == 1
    assert result.child_traceable_to_parent
    assert result.parent_released_after_death
    assert result.child_remains_live
