import pytest

from symbiont_lab.studies.prediction_promotion import run_prediction_promotion_study


def test_shadow_promotion_requires_longitudinal_gain() -> None:
    result = run_prediction_promotion_study()
    assert result.signal_promotable
    assert result.signal_gain > 0.0
    assert not result.noise_promotable
    assert result.noise_gain <= 0.0


def test_shadow_promotion_rejects_short_evidence() -> None:
    with pytest.raises(ValueError):
        run_prediction_promotion_study(trials=7)
