from symbiont_lab.studies.learning.canonical_sensorimotor_agency import (
    SensorimotorAgencyStudy,
    SensorimotorAgencyTrial,
)


def _trial(**overrides):
    values = {
        "seed": 1,
        "ticks_requested": 16,
        "ticks_completed": 16,
        "alive": True,
        "motor_patterns": 8,
        "motor_primitives": 2,
        "cognitive_motor_primitives": 1,
        "replay_ticks": 4,
        "passive_baseline_samples": 0,
        "best_controllability": 0.1,
        "best_directional_consistency": 0.8,
        "first_cognitive_primitive_tick": 11,
    }
    values.update(overrides)
    return SensorimotorAgencyTrial(**values)


def test_agency_gate_requires_organism_replay_not_only_a_primitive():
    assert _trial().body_model_discovery_validated is True
    assert _trial(replay_ticks=0).body_model_discovery_validated is False
    assert _trial(cognitive_motor_primitives=0).body_model_discovery_validated is False


def test_study_requires_all_independent_seeds_to_pass():
    study = SensorimotorAgencyStudy(
        seeds=(1, 2),
        ticks=16,
        trials=(_trial(seed=1), _trial(seed=2, motor_primitives=0)),
    )

    assert study.validated_trials == 1
    assert study.validated is False
