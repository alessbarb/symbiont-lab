import pytest

from symbiont_lab.studies.runtime_prediction_longitudinal import (
    run_runtime_prediction_longitudinal_study,
)


def test_longitudinal_shadow_evidence_survives_checkpoint_before_promotion() -> None:
    result = run_runtime_prediction_longitudinal_study(trials=32)
    assert result.checkpoint_tick == 16
    assert result.continuation_replay_equal
    assert result.signal_status == "supported"
    assert result.signal_samples == 31
    assert result.signal_promoted
    assert result.predictor_count == 1


def test_longitudinal_prediction_requires_enough_trials() -> None:
    with pytest.raises(ValueError, match="trials"):
        run_runtime_prediction_longitudinal_study(trials=15)
