from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.temporal_causality_challenge import (
    run_temporal_causality_challenge_study,
)


def test_e3_is_deterministic_and_bounded():
    result = run_temporal_causality_challenge_study(
        seeds=(101, 127, 149),
        steps=200,
    )
    replay = run_temporal_causality_challenge_study(
        seeds=(101, 127, 149),
        steps=200,
    )
    assert result == replay
    assert result.replay_deterministic
    for rate in (
        result.delay0_detection_rate,
        result.delay1_detection_rate,
        result.delay3_detection_rate,
        result.variable_delay_detection_rate,
        result.immediate_external_false_positive_rate,
    ):
        assert 0.0 <= rate <= 1.0


def test_e3_reports_delayed_and_external_controls_without_forcing_h1():
    result = run_temporal_causality_challenge_study(seeds=(101,), steps=200)
    seed = result.per_seed[0]
    assert 0.0 <= seed.delay0_confidence <= 1.0
    assert 0.0 <= seed.delay1_confidence <= 1.0
    assert 0.0 <= seed.delay3_confidence <= 1.0
    assert 0.0 <= seed.variable_delay_confidence <= 1.0
    assert 0.0 <= seed.immediate_external_confidence <= 1.0
    assert isinstance(result.h1_supported, bool)


def test_e3_protocol_is_registered():
    protocol = get_protocol("embodiment.temporal-causality-challenge")
    result = protocol(seeds=(101,), steps=100)
    assert result.seeds == (101,)
    assert result.steps == 100


def test_e3_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        run_temporal_causality_challenge_study(seeds=(), steps=100)
    with pytest.raises(ValueError):
        run_temporal_causality_challenge_study(seeds=(101,), steps=10)
