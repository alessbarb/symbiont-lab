from __future__ import annotations

from symbiont_lab.studies.perception.autonomous_selection import (
    run_autonomous_sensory_selection,
    run_experience_conditioned_phenotype,
    run_sensory_null_selection,
    run_sensory_regime_reversal,
)


def test_autonomous_selection_prefers_evaluator_best_without_receiving_label() -> None:
    result = run_autonomous_sensory_selection(seed=101, samples=192)
    assert result["selected_role"] == "difference"
    assert result["evaluator_best_role"] == "difference"
    assert result["selection_matches_best"]
    assert result["beats_random"]


def test_selection_reverses_after_environmental_regime_shift() -> None:
    for seed in (101, 127, 149):
        result = run_sensory_regime_reversal(seed=seed, samples=320)
        assert result["preference_before"] == "difference"
        assert result["preference_after"] == "integrate"
        assert result["switched_delta_to_integrate"]
        assert result["switch_delay"] is not None


def test_null_world_does_not_create_strong_false_specialisation() -> None:
    for seed in (101, 127, 149):
        result = run_sensory_null_selection(seed=seed, samples=256)
        assert result["no_strong_false_specialisation"]
        assert result["max_utility"] < 0.25
        assert result["max_selection_credit"] < 0.25


def test_microexperience_study_characterizes_outcome_without_forcing_divergence() -> None:
    result = run_experience_conditioned_phenotype(seed=101, samples=256)
    assert result["organisms"] == 6
    assert result["converged"] is not result["diverged"]
    assert result["unique_role_count"] >= 1
