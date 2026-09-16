from symbiont_lab.studies.social_runtime_adaptation import run_social_runtime_adaptation_study


def test_runtime_social_choice_revises_after_contradictory_evidence() -> None:
    result = run_social_runtime_adaptation_study()
    assert result.initial_choice == "candidate"
    assert result.revised_choice == "unknown"
    assert result.final_valence == "negative"
    assert result.evidence_observations == 2
    assert result.changed_after_contradiction
