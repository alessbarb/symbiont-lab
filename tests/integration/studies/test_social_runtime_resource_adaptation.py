from symbiont_lab.studies.social_runtime_resource_adaptation import (
    run_social_runtime_resource_adaptation_study,
)


def test_resource_adaptation_uses_local_opaque_evidence() -> None:
    result = run_social_runtime_resource_adaptation_study()
    assert result.initial_resource == "food"
    assert result.adapted_resource == "water"
    assert result.denied_initial_request
    assert result.checkpoint_replay_equal
