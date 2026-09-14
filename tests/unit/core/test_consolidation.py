from __future__ import annotations

import math

import pytest

from symbiont.core.consolidation import (
    ConsolidationCandidate,
    ConsolidationSignal,
    MemoryError,
    MemoryKind,
    SalientEventTrace,
    maturity_class_from_support_epochs,
    novelty_from_drift_kind,
    quantize_unit,
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


def test_consolidation_candidate_defaults():
    candidate = ConsolidationCandidate(key="sense_a", kind=MemoryKind.STATISTICAL)
    assert candidate.support_epochs == 0
    assert candidate.last_support_epoch is None
    assert candidate.strength == 0.0
    assert candidate.latest_signal is None


def test_maturity_class_is_monotone_and_coarse():
    assert maturity_class_from_support_epochs(0) == 0
    assert maturity_class_from_support_epochs(1) == 1
    assert maturity_class_from_support_epochs(3) == 2
    assert maturity_class_from_support_epochs(4) == 3
    assert maturity_class_from_support_epochs(10) == 4
    assert maturity_class_from_support_epochs(20) == 5
    assert maturity_class_from_support_epochs(40) == 6
    assert maturity_class_from_support_epochs(1000) == 7

    classes = [maturity_class_from_support_epochs(n) for n in range(0, 200, 3)]
    assert classes == sorted(classes)


def test_quantize_unit_is_bounded_and_monotone():
    assert quantize_unit(0.0, 16) == 0
    assert quantize_unit(1.0, 16) == 15
    assert quantize_unit(0.5, 16) == 8
    assert quantize_unit(-1.0, 16) == 0
    assert quantize_unit(2.0, 16) == 15


def test_salient_event_trace_rejects_out_of_range_classes():
    SalientEventTrace(
        pattern_id="sense_a", novelty_class=15, surprise_class=15,
        reliability_class=15, context_class=0, recurrence_class=0,
    )
    with pytest.raises(MemoryError):
        SalientEventTrace(
            pattern_id="sense_a", novelty_class=16, surprise_class=0,
            reliability_class=0, context_class=0, recurrence_class=0,
        )
    with pytest.raises(MemoryError):
        SalientEventTrace(
            pattern_id="sense_a", novelty_class=0, surprise_class=-1,
            reliability_class=0, context_class=0, recurrence_class=0,
        )
