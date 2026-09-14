from __future__ import annotations

import math

import pytest

from symbiont.core.consolidation import ConsolidationSignal, MemoryError, MemoryKind


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
