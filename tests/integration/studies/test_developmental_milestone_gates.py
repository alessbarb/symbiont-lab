from symbiont_lab.studies import run_developmental_milestone_gate_study


def test_active_developmental_milestones_have_independent_passing_gates() -> None:
    result = run_developmental_milestone_gate_study()
    assert result.physiology_i
    assert result.predictive_j
    assert result.social_k
    assert result.all_gates_pass
