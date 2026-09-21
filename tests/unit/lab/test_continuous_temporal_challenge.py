from __future__ import annotations

from symbiont_lab.studies.learning.continuous_temporal_challenge import (
    run_continuous_temporal_challenge,
)


def test_continuous_temporal_challenge_reports_regime_adaptation_and_cost():
    result = run_continuous_temporal_challenge(
        seeds=(101,),
        ticks=200,
    )

    trial = result.trials[0]
    assert trial.shift_tick == 100
    assert trial.learned_values > 0
    assert trial.fixed_values > 0
    assert trial.esn_pre_shift_loss >= 0.0
    assert trial.esn_post_shift_early_loss >= 0.0
    assert trial.esn_post_shift_late_loss >= 0.0
    assert 0.0 <= trial.adaptation_recovery_ratio <= 1.0
