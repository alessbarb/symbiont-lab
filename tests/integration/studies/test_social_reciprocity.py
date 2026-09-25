from symbiont_lab.studies.social_reciprocity import run_social_reciprocity_study


def test_reciprocity_study_keeps_directional_evidence_and_isolation() -> None:
    result = run_social_reciprocity_study()
    assert result.reciprocal_observations >= 1
    assert result.one_way_observations >= 1
    assert result.conflicted_relations == 1
    assert result.isolated_members == 1
