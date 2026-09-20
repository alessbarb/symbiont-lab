from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.somatic_correlation_trap import (
    run_somatic_correlation_trap_study,
)


def test_e5_is_deterministic_and_bounded():
    result = run_somatic_correlation_trap_study(
        seeds=(101, 127, 149),
        steps=200,
    )
    replay = run_somatic_correlation_trap_study(
        seeds=(101, 127, 149),
        steps=200,
    )
    assert result == replay
    assert result.replay_deterministic
    assert 0.0 <= result.true_somatic_rate <= 1.0
    assert 0.0 <= result.external_assimilation_rate <= 1.0
    assert 0.0 <= result.independent_assimilation_rate <= 1.0


def test_e5_reports_positive_and_negative_controls_without_forcing_h1():
    result = run_somatic_correlation_trap_study(seeds=(101,), steps=300)
    seed = result.per_seed[0]

    assert seed.self_caused_detected
    assert isinstance(seed.true_somatic_detected, bool)
    assert isinstance(seed.external_correlated_assimilated, bool)
    assert isinstance(seed.external_independent_assimilated, bool)
    assert isinstance(result.h1_supported, bool)


def test_e5_protocol_is_registered():
    protocol = get_protocol("embodiment.somatic-correlation-trap")
    result = protocol(seeds=(101,), steps=100)
    assert result.seeds == (101,)
    assert result.steps == 100


def test_e5_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        run_somatic_correlation_trap_study(seeds=(), steps=100)
    with pytest.raises(ValueError):
        run_somatic_correlation_trap_study(seeds=(101, 101), steps=100)
    with pytest.raises(ValueError):
        run_somatic_correlation_trap_study(seeds=(101,), steps=10)
