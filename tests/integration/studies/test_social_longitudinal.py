import pytest

from symbiont_lab.studies.social_longitudinal import run_social_longitudinal_study


def test_social_longitudinal_study_covers_suspend_resume_and_evidence() -> None:
    result = run_social_longitudinal_study(ticks=12)
    assert result.successful_exchanges == 11
    assert result.rejected_during_suspension == 1
    assert result.resumed
    assert result.relation_observations == 22
    assert 0.0 < result.relation_freshness < 1.0


def test_social_longitudinal_study_rejects_short_runs() -> None:
    with pytest.raises(ValueError):
        run_social_longitudinal_study(ticks=3)
