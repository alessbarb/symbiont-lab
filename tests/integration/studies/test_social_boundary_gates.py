from symbiont_lab.studies.social_boundary_gates import run_social_boundary_gate_study


def test_social_boundary_gate_matrix_passes_without_runtime_labels() -> None:
    result = run_social_boundary_gate_study()
    assert result.all_gates_pass
    assert result == run_social_boundary_gate_study()
