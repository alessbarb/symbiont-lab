from symbiont_lab.studies.runtime_physiology_gates import run_runtime_physiology_gate_study


def test_runtime_physiology_gate_study_closes_independent_longitudinal_boundaries() -> None:
    result = run_runtime_physiology_gate_study()
    assert result.all_gates_pass
    assert result.repair_replay_equal
    assert result.reproduction_replay_equal
    assert result.capacity_blocked_birth
    assert result.social_continuation_replay_equal
    assert result.repair_without_intake == 0.0
    assert result.social_interactions > 0
