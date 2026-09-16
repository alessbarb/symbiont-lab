from symbiont_lab.studies.predictive_development_gates import run_predictive_development_gate_study


def test_predictive_development_gate_matrix_passes_without_evaluator_feedback():
    result = run_predictive_development_gate_study()

    assert result.all_gates_pass
    assert result.codec_zero_exact
    assert result.codec_deadband_preserved
    assert result.codec_sign_preserved
    assert result.attention_diminishing_returns
    assert result.hypothesis_checkpoint_equal
    assert result.shadow_gain_gate
    assert result.shadow_noise_rejected
    assert result.longitudinal_replay_equal
