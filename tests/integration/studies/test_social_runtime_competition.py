from symbiont_lab.studies.social_runtime_competition import run_social_runtime_competition_study


def test_runtime_competition_uses_local_negative_evidence_and_finite_habitat() -> None:
    result = run_social_runtime_competition_study()
    assert result.proposals == 2
    assert result.granted == 0.2
    assert result.peer_attributed_losses == 2
    assert result.finite_resource_remaining == 0.3
    assert result.no_global_label
