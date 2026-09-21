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


def test_reseeding_a_reborn_edge_drops_previous_lifetime_evidence():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 5)
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->b", 9, tick=epoch * limits.consolidation_epoch_ticks + 1)
    assert tracker.is_ready("a->b") is True

    tracker.seed("a->b", 3)

    assert tracker.durable_class("a->b") == 3
    assert tracker.candidate_class("a->b") is None
    assert tracker.is_ready("a->b") is False


def test_reconcile_forgets_removed_edge_state():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->b", 5)
    tracker.observe("a->b", 6, tick=1)

    tracker.reconcile([])

    assert tracker.candidate_class("a->b") is None
    with pytest.raises(KeyError):
        tracker.durable_class("a->b")


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


def test_consolidate_node_returns_none_when_nothing_changed():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)
    tracker.observe("a->n", 5, tick=1)
    tracker.observe("b->n", 5, tick=1)
    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 0.3, "b->n": 0.3}, max_incoming_norm=8.0)
    assert result is None


def test_p13_node_atomic_commit_blocks_on_one_immature_changed_edge():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 9, tick=epoch * epoch_ticks + 1)
    tracker.observe("b->n", 6, tick=1)

    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.5, "b->n": 0.4}, max_incoming_norm=8.0)
    assert result is None
    assert tracker.durable_class("a->n") == 5
    assert tracker.durable_class("b->n") == 5


def test_node_commits_when_all_changed_edges_are_ready_unchanged_sibling_untouched():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 9, tick=epoch * epoch_ticks + 1)
        tracker.observe("b->n", 5, tick=epoch * epoch_ticks + 1)

    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.5, "b->n": 0.3}, max_incoming_norm=8.0)
    assert result is not None
    assert "a->n" in result
    assert result["b->n"] == tracker.durable_class("b->n") == 5
    assert tracker.durable_class("a->n") == result["a->n"]


def test_homeostatic_l1_normalization_scales_down_when_over_budget():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->n", 0)
    tracker.seed("b->n", 0)
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)
        tracker.observe("b->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)

    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.9, "b->n": 1.9}, max_incoming_norm=8.0)
    assert result is not None

    tracker2 = WeightStabilityTracker(kernel_limits=limits)
    tracker2.seed("a->n", 0)
    tracker2.seed("b->n", 0)
    for epoch in range(limits.slow_support_epochs + 1):
        tracker2.observe("a->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)
        tracker2.observe("b->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)
    scaled = tracker2.consolidate_node(["a->n", "b->n"], {"a->n": 1.9, "b->n": 1.9}, max_incoming_norm=1.0)
    assert scaled is not None
    from symbiont.cognition.checkpoint import dequantize_weight
    total = sum(abs(dequantize_weight(cls)) for cls in scaled.values())
    assert total <= 1.0 + 1e-6
