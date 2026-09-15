import pytest

from symbiont_lab.studies.runtime_prediction_promotion import run_runtime_prediction_promotion_study


def test_runtime_promotion_study_promotes_gain_and_rejects_noise() -> None:
    result = run_runtime_prediction_promotion_study()
    assert result.signal_samples == result.trials - 1
    assert result.signal_gain > 0
    assert result.signal_promoted
    assert result.noise_samples == result.trials - 1
    assert result.noise_gain <= 0
    assert not result.noise_promoted


def test_runtime_promotion_study_rejects_short_evidence() -> None:
    with pytest.raises(ValueError):
        run_runtime_prediction_promotion_study(trials=7)
