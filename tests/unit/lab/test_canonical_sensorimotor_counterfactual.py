from symbiont_lab.studies.learning.canonical_sensorimotor_counterfactual import (
    CounterfactualReplayStudy,
    CounterfactualReplayTrial,
)


def _trial(**overrides):
    values = {
        "seed": 101,
        "checkpoint_tick": 17,
        "primitive_id": "primitive.opaque",
        "target_actuator_id": "actuator.opaque",
        "target_effector_id": "eff.opaque",
        "horizon_ticks": 8,
        "normal_replay_error": 0.0,
        "target_action_ticks": 3,
        "mean_sensory_divergence": 0.01,
        "peak_sensory_divergence": 0.02,
        "mean_physical_divergence": 0.001,
        "peak_physical_divergence": 0.002,
        "initial_state_identical": True,
    }
    values.update(overrides)
    return CounterfactualReplayTrial(**values)


def test_counterfactual_gate_requires_same_state_replay_and_physical_effect():
    assert _trial().intervention_validated is True
    assert _trial(initial_state_identical=False).intervention_validated is False
    assert _trial(target_action_ticks=0).intervention_validated is False
    assert _trial(mean_sensory_divergence=0.0).intervention_validated is False


def test_counterfactual_study_requires_every_seed_to_pass():
    study = CounterfactualReplayStudy(
        seeds=(101, 127),
        warmup_ticks=64,
        horizon_ticks=8,
        trials=(_trial(seed=101), _trial(seed=127, mean_physical_divergence=0.0)),
    )

    assert study.validated_trials == 1
    assert study.validated is False
