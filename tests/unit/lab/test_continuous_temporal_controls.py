from __future__ import annotations

from symbiont_lab.studies.learning.continuous_temporal_controls import (
    run_continuous_temporal_controls,
)


def test_continuous_temporal_controls_measure_action_conditioned_causality():
    result = run_continuous_temporal_controls(
        seeds=(101,),
        ticks=192,
    )

    seed = result.per_seed[0]
    assert seed.causal.test_loss >= 0.0
    assert seed.action_shuffled.test_loss >= 0.0
    assert seed.no_action.test_loss >= 0.0
    assert isinstance(seed.causal_beats_controls, bool)
    assert result.mean_causal_margin == seed.causal_margin_over_best_control
