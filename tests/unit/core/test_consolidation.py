from __future__ import annotations

import math

import pytest

from symbiont.core.consolidation import (
    ConsolidationSignal,
    MemoryError,
    MemoryKind,
    novelty_from_drift_kind,
    surprise_from_loss,
)
from symbiont.host.drift import DriftKind


def test_memory_kind_is_closed_and_has_exactly_three_values():
    assert {kind.value for kind in MemoryKind} == {"statistical", "salient_event", "structural"}


def test_consolidation_signal_rejects_out_of_range_fields():
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=1.5, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=0.0, surprise=-0.1, attention=0.0, reliability=0.0, coherence=0.0)
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=math.nan, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)


def test_consolidation_signal_score_matches_the_kernel_weighted_sum():
    signal = ConsolidationSignal(novelty=1.0, surprise=1.0, attention=1.0, reliability=1.0, coherence=1.0)
    assert signal.score() == pytest.approx(1.0)

    signal = ConsolidationSignal(novelty=0.0, surprise=1.0, attention=0.0, reliability=0.0, coherence=0.0)
    assert signal.score() == pytest.approx(0.30)

    signal = ConsolidationSignal(novelty=0.0, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)
    assert signal.score() == pytest.approx(0.0)


def test_novelty_from_drift_kind_matches_the_kernel_mapping():
    assert novelty_from_drift_kind(DriftKind.NONE) == pytest.approx(0.00)
    assert novelty_from_drift_kind(DriftKind.GRADUAL) == pytest.approx(0.35)
    assert novelty_from_drift_kind(DriftKind.CREEP) == pytest.approx(0.50)
    assert novelty_from_drift_kind(DriftKind.ISOLATED) == pytest.approx(0.70)
    assert novelty_from_drift_kind(DriftKind.REGIME_SHIFT) == pytest.approx(0.90)
    assert novelty_from_drift_kind(None) == pytest.approx(0.0)


def test_surprise_from_loss_is_bounded_and_saturating():
    assert surprise_from_loss(None) == pytest.approx(0.0)
    assert surprise_from_loss(0.0) == pytest.approx(0.0)
    assert surprise_from_loss(0.5) == pytest.approx(0.5)
    assert surprise_from_loss(1.0) == pytest.approx(1.0)
    assert surprise_from_loss(50.0) == pytest.approx(1.0)
    assert surprise_from_loss(float("nan")) == pytest.approx(0.0)
