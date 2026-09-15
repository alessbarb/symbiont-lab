import pytest

from symbiont_lab.studies.social_specialization import run_social_specialization_study


def test_specialization_study_reports_distinct_resource_niches() -> None:
    result = run_social_specialization_study(ticks=8)
    assert result.distinct_niches
    assert (result.a_food, result.b_water) == pytest.approx((8.0, 8.0))
    assert result.a_water == result.b_food == 0.0


def test_specialization_study_rejects_empty_run() -> None:
    with pytest.raises(ValueError):
        run_social_specialization_study(ticks=0)
