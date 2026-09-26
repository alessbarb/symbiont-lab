from __future__ import annotations

from symbiont_lab.studies.learning.generative_model_correction import (
    run_generative_model_correction_study,
)


def test_model_correction_reconciles_contradiction_and_improves_next_prediction() -> None:
    result = run_generative_model_correction_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.contradiction_rate == 1.0
    assert result.corrected_prediction_rate == 1.0
    assert result.all_factual_contamination_free
    assert result.all_agenda_contamination_free
    assert result.all_generated_origins_non_observed
    assert all(item.reconciliation_count == 2 for item in result.trials)
    assert all(item.contradicted_hypothesis_count == 1 for item in result.trials)


def test_model_correction_gate_is_deterministic() -> None:
    first = run_generative_model_correction_study().as_dict()
    second = run_generative_model_correction_study().as_dict()

    assert first == second
