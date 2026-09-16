from symbiont_lab.studies import run_social_development_gate_study


def test_social_development_gate_matrix_passes_without_runtime_labels() -> None:
    result = run_social_development_gate_study()
    assert result.all_gates_pass
    assert result.boundary_contract
    assert result.longitudinal_replay
    assert result.lineage_replay
    assert result.resource_revision
    assert result.denial_revision
    assert result.niche_differentiation
