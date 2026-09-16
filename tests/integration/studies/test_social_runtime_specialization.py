from symbiont_lab.studies.social_runtime_specialization import (
    run_social_runtime_specialization_study,
)


def test_local_contention_can_produce_differentiated_resource_choices() -> None:
    result = run_social_runtime_specialization_study(ticks=8)
    assert result.member_a_resource == "food"
    assert result.member_b_resource == "water"
    assert result.distinct_resource_count == 2
    assert result.checkpoint_replay_equal
    assert result.member_a_choices == ("food",) * 8
    assert result.member_b_choices == ("water",) * 7
    assert result.continuation_replay_equal
