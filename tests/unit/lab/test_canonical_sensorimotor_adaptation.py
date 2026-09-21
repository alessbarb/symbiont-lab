from symbiont_lab.studies.learning.canonical_sensorimotor_adaptation import (
    AdaptationStudy,
    AdaptationTrial,
)


def _trial(**overrides):
    values = {
        "seed": 101,
        "checkpoint_tick": 17,
        "primitive_id": "primitive.opaque",
        "target_actuator_id": "actuator.opaque",
        "horizon_ticks": 96,
        "target_delivered_intact": 4,
        "target_delivered_damaged": 0,
        "mean_sensory_divergence": 0.01,
        "initial_model_size": 2,
        "max_primitive_channels": 2,
        "intact_model_size": 4,
        "damaged_model_size": 5,
        "damaged_novel_primitives": 1,
        "damaged_replayed_novel_primitives": 1,
        "known_primitives_replayed_damaged": 1,
        "model_changed_after_damage": True,
        "initial_state_identical": True,
    }
    values.update(overrides)
    return AdaptationTrial(**values)


def test_adaptation_gate_requires_damage_and_model_reorganization():
    assert _trial().adaptation_validated is True
    assert _trial(target_delivered_damaged=1).adaptation_validated is False
    assert _trial(model_changed_after_damage=False).adaptation_validated is False
    assert _trial(damaged_novel_primitives=0).adaptation_validated is False
    assert _trial(damaged_replayed_novel_primitives=0).adaptation_validated is False
    assert _trial(known_primitives_replayed_damaged=0).adaptation_validated is False
    assert _trial(max_primitive_channels=1).adaptation_validated is False


def test_adaptation_study_requires_every_trial_to_pass():
    study = AdaptationStudy(
        seeds=(101, 127),
        warmup_ticks=64,
        horizon_ticks=96,
        trials=(_trial(seed=101), _trial(seed=127, mean_sensory_divergence=0.0)),
    )

    assert study.validated is False
