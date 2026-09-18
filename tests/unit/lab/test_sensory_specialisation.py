from __future__ import annotations

from symbiont_lab.studies.perception.sensory_specialisation import (
    run_adaptive_delta_discovery,
    run_identity_equivalence,
    run_temporal_scale_specialisation,
)


def test_identity_sensory_bridge_is_exact():
    result = run_identity_equivalence(samples=48)
    assert result.equivalent
    assert result.max_absolute_error <= 1e-12
    assert result.sensor_count == 1


def test_delta_receptor_exposes_change_without_evaluator_feedback():
    for seed in (101, 127, 149):
        result = run_adaptive_delta_discovery(seed=seed, samples=96)
        assert result.modality_id == "modality.alpha"
        assert result.specialised_mae < result.identity_mae
        assert result.improvement > 0.0


def test_temporal_modalities_have_distinct_functional_niches():
    for seed in (101, 127, 149):
        result = run_temporal_scale_specialisation(seed=seed, samples=128)
        assert result.fast_specialisation_gain > 0.0
        assert result.slow_specialisation_gain > 0.0
