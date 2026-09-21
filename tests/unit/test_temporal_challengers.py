from __future__ import annotations

import math

import pytest

from symbiont.modeling import TemporalMechanism
from symbiont_lab.modeling import (
    DecayedVariableOrderMarkov,
    SparseEchoStateRegressor,
)


def test_decayed_vomm_learns_variable_order_alternation_without_semantic_role():
    model = DecayedVariableOrderMarkov(max_order=4, decay=0.99)
    for symbol in (0, 1) * 32:
        model.observe(symbol)

    prediction = model.predict()

    assert prediction is not None
    assert prediction.mechanism_id == "vomm-decayed-v1"
    assert prediction.value == 0
    assert prediction.confidence > 0.9
    assert isinstance(model, TemporalMechanism)
    usage = model.resource_usage()
    assert usage.observations == 64
    assert usage.learned_values > 0


def test_decayed_vomm_adapts_to_recent_regime():
    model = DecayedVariableOrderMarkov(max_order=3, decay=0.8)
    for symbol in (0, 1) * 24:
        model.observe(symbol)
    for _ in range(32):
        model.observe(1)

    prediction = model.predict()

    assert prediction is not None
    assert prediction.value == 1
    assert prediction.confidence > 0.8


def test_sparse_esn_nlms_learns_online_without_quadratic_rls_state():
    model = SparseEchoStateRegressor(
        input_dim=1,
        output_dim=1,
        reservoir_size=24,
        connectivity=0.15,
        learning_rate=0.5,
        seed=7,
    )

    for _ in range(256):
        model.observe((1.0,))
        model.learn((0.5,))

    prediction = model.predict()

    assert prediction is not None
    assert prediction.value[0] == pytest.approx(0.5, abs=0.05)
    usage = model.resource_usage()
    expected_readout = 1 * (1 + 1 + 24)
    assert usage.learned_values == expected_readout
    assert usage.updates == 256
    assert model.fixed_values > 0
    assert math.isfinite(prediction.value[0])


def test_sparse_esn_rejects_unsupported_multistep_prediction():
    model = SparseEchoStateRegressor(input_dim=1, output_dim=1, seed=3)
    model.observe((0.0,))

    with pytest.raises(ValueError, match="horizon=1"):
        model.predict(horizon=2)
