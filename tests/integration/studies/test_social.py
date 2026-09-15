import pytest

from symbiont_lab.studies.social import run_social_study


def test_social_study_exhibits_exchange_and_competition_without_policy() -> None:
    result = run_social_study(resource=1.0, request=0.8)
    assert result.exchange_granted == 0.8
    assert sum(result.competition_granted) == pytest.approx(0.2)
    assert result.positive_relations == 1
    assert result.negative_relations == 2
    assert result.members_after_release == ("a", "c")
    assert result.restarted_members == ("a", "c")
    assert result.restarted_resource == pytest.approx(0.0)
