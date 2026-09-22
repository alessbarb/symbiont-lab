from __future__ import annotations

from symbiont_lab.studies.learning.prospective_agency_controls import (
    run_prospective_agency_controls_study,
)


def test_prospective_agency_controls_pass_preregistered_mechanism_gates():
    study = run_prospective_agency_controls_study(seeds=(101, 127, 149))

    assert study.gate_prediction_discrimination
    assert study.gate_context_sensitive_choice
    assert study.gate_model_control
    assert study.gate_value_control
    assert study.gate_causal_benefit
    assert study.all_gates_pass

    for seed in study.per_seed:
        assert seed.full_selected_optimal
        assert seed.model_shuffle_degraded
        assert seed.value_shuffle_degraded
        assert seed.context_sensitive
        assert seed.prediction_diversity >= 2


def test_prospective_agency_control_study_is_replay_deterministic():
    first = run_prospective_agency_controls_study(seeds=(101, 127, 149))
    second = run_prospective_agency_controls_study(seeds=(101, 127, 149))

    assert first == second
