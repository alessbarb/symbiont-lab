from __future__ import annotations

from symbiont_lab.studies.perception.sensory_specialisation import (
    run_adaptive_delta_discovery,
    run_identity_equivalence,
    run_temporal_scale_specialisation,
    run_modality_specialisation,
    run_duplication_divergence,
    run_sensory_ablation,
    run_multisource_specialisation,
    run_same_world_phenotype_divergence,
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


def test_modality_characterization_exposes_distinct_niches():
    result = run_modality_specialisation(seed=101, samples=128)
    assert result["fast_niche"]
    assert result["slow_niche"]
    assert result["distributed_niche"]


def test_duplication_divergence_is_bounded():
    result = run_duplication_divergence(seed=101, samples=96)
    assert result["bounded"]
    assert result["diverged"]


def test_targeted_sensor_ablation_has_larger_error_than_intact_receptor():
    result = run_sensory_ablation(seed=101, samples=128)
    assert result["targeted_ablation_effect"] > 0.0


def test_multisource_study_reports_frozen_control_instead_of_hiding_it():
    result = run_multisource_specialisation(seed=101, samples=128)
    assert "frozen_multisource_mae" in result
    assert result["beats_single_source"]


def test_same_world_study_reports_convergence_or_divergence_without_forcing_outcome():
    result = run_same_world_phenotype_divergence(seed=101, samples=96)
    assert result["organisms"] == 3
    assert result["converged"] is not result["diverged"]
