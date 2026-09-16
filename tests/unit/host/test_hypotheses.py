from __future__ import annotations

import pytest

from symbiont.host.hypotheses import HypothesisStatus, HypothesisTracker


def test_tracker_updates_lifecycle_only_from_bounded_correlation():
    tracker = HypothesisTracker()
    tracker.observe(("a", "b"), correlation=0.8, samples=3, min_samples=3, tick=1)
    assert tracker.items[0].status is HypothesisStatus.PROVISIONAL

    tracker.observe(("b", "a"), correlation=0.8, samples=6, min_samples=3, tick=2)
    assert tracker.items[0].status is HypothesisStatus.SUPPORTED


def test_tracker_retires_a_sustained_contradiction_and_does_not_revive_it():
    tracker = HypothesisTracker()
    for tick, samples in enumerate((3, 6, 9, 12, 15, 18), start=1):
        tracker.observe(("a", "b"), correlation=0.1, samples=samples, min_samples=3, tick=tick)

    item = tracker.items[0]
    assert item.status is HypothesisStatus.RETIRED
    assert item.contradiction_streak == 3

    tracker.observe(("a", "b"), correlation=0.9, samples=21, min_samples=3, tick=7)
    assert tracker.items[0].status is HypothesisStatus.RETIRED


@pytest.mark.parametrize("correlation", [float("nan"), float("inf"), -1.1, 1.1, True])
def test_tracker_rejects_invalid_correlation(correlation):
    with pytest.raises(ValueError):
        HypothesisTracker().observe(("a", "b"), correlation=correlation, samples=3, min_samples=3, tick=0)


@pytest.mark.parametrize("source_ids", [("a",), ("a", "a"), ("", "b"), ("a", 3)])
def test_tracker_rejects_invalid_source_ids(source_ids):
    with pytest.raises(ValueError):
        HypothesisTracker().observe(source_ids, correlation=None, samples=0, min_samples=3, tick=0)


def test_tracker_rejects_ambiguous_counts_and_ticks():
    tracker = HypothesisTracker()
    with pytest.raises(ValueError):
        tracker.observe(("a", "b"), correlation=None, samples=True, min_samples=3, tick=0)
    with pytest.raises(ValueError):
        tracker.observe(("a", "b"), correlation=None, samples=0, min_samples=2, tick=0)
    with pytest.raises(ValueError):
        tracker.observe(("a", "b"), correlation=None, samples=0, min_samples=3, tick=-1)
