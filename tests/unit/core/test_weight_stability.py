from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.core.weight_stability import WeightStabilityTracker


def test_seed_sets_the_durable_class_before_any_observation():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->b", 5)
    assert tracker.durable_class("a->b") == 5
    assert tracker.candidate_class("a->b") is None
    assert tracker.is_ready("a->b") is False


def test_p12_class_change_within_the_same_epoch_does_not_accumulate_support():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    for weight_class in (3, 4, 3, 5, 3):
        tracker.observe("a->b", weight_class, tick=1)
    assert tracker.is_ready("a->b") is False


def test_p12_class_change_across_epochs_resets_support_to_one():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch, cls in enumerate([7, 7, 7, 8]):
        tracker.observe("a->b", cls, tick=epoch * epoch_ticks + 1)
    tracker.observe("a->b", 8, tick=4 * epoch_ticks + 1)
    assert tracker.candidate_class("a->b") == 8
    assert tracker.is_ready("a->b") is False


def test_stable_class_across_enough_epochs_becomes_ready():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->b", 7, tick=epoch * epoch_ticks + 1)
    assert tracker.candidate_class("a->b") == 7
    assert tracker.is_ready("a->b") is True
