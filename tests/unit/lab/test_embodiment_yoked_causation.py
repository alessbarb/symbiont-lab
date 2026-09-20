from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.yoked_external_causation import (
    run_yoked_external_causation_study,
)


def test_e1_yoked_external_causation_is_deterministic_and_bounded():
    study = run_yoked_external_causation_study(
        seeds=(101, 127, 149),
        steps=200,
    )
    replay = run_yoked_external_causation_study(
        seeds=(101, 127, 149),
        steps=200,
    )

    assert study == replay
    assert study.replay_deterministic
    assert 0.0 <= study.mean_false_positive_rate <= 1.0
    assert 0.0 <= study.mean_true_positive_rate <= 1.0
    assert 0.0 <= study.broken_yoke_rejection_rate <= 1.0
    assert len(study.per_seed) == 3

    for result in study.per_seed:
        for confidence in (
            result.genuine_confidence,
            result.exact_yoked_confidence,
            result.jittered_yoked_confidence,
            result.anticausal_confidence,
            result.independent_confidence,
            result.broken_yoke_final_confidence,
        ):
            assert 0.0 <= confidence <= 1.0
        assert -1.0 <= result.exact_lag0_correlation <= 1.0
        assert -1.0 <= result.exact_lag1_correlation <= 1.0
        assert result.broken_yoke_rejection_latency is None or result.broken_yoke_rejection_latency >= 0


def test_e1_contains_positive_and_negative_controls():
    study = run_yoked_external_causation_study(seeds=(101,), steps=300)
    result = study.per_seed[0]

    assert result.genuine_confidence > 0.0

    # Controls are reported independently. Do not assert H1 here: a failed H1
    # gate is a legitimate scientific result, not a software regression.
    assert isinstance(result.exact_yoked_agentic, bool)
    assert isinstance(result.jittered_yoked_agentic, bool)
    assert isinstance(result.anticausal_agentic, bool)
    assert isinstance(result.independent_agentic, bool)
    assert isinstance(study.h1_supported, bool)


def test_e1_protocol_is_registered():
    protocol = get_protocol("embodiment.yoked-external-causation")
    result = protocol(seeds=(101,), steps=100)
    assert result.seeds == (101,)
    assert result.steps == 100


def test_e1_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        run_yoked_external_causation_study(seeds=(), steps=100)
    with pytest.raises(ValueError):
        run_yoked_external_causation_study(seeds=(101, 101), steps=100)
    with pytest.raises(ValueError):
        run_yoked_external_causation_study(seeds=(101,), steps=50)
