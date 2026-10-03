from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits


def test_defaults_match_the_design_doc_table():
    limits = KernelLimits()
    assert limits.max_nodes == 768
    assert limits.max_concepts == 192
    assert limits.max_edges == 6144
    assert limits.max_tentative_edges == 512
    assert limits.max_structural_mutations_per_consolidation == 16
    assert limits.consolidation_interval_ticks == 32
    assert limits.max_plastic_checkpoint_bytes == 8 * 1024 * 1024
    assert limits.max_consolidation_candidates == 1024
    assert limits.max_salient_event_traces == 64
    assert limits.consolidation_epoch_ticks == 8
    assert limits.slow_support_epochs == 4
    assert limits.fast_consolidation_threshold == pytest.approx(0.80)
    assert limits.fast_min_reliability == pytest.approx(0.60)
    assert limits.max_incoming_consolidated_weight_norm == pytest.approx(8.0)
    assert limits.reacclimation_ticks == 32


@pytest.mark.parametrize(
    "field",
    [
        "max_nodes",
        "max_concepts",
        "max_edges",
        "max_tentative_edges",
        "max_structural_mutations_per_consolidation",
        "consolidation_interval_ticks",
        "max_plastic_checkpoint_bytes",
        "max_consolidation_candidates",
        "max_salient_event_traces",
        "consolidation_epoch_ticks",
        "slow_support_epochs",
        "fast_consolidation_threshold",
        "fast_min_reliability",
        "max_incoming_consolidated_weight_norm",
        "reacclimation_ticks",
    ],
)
def test_every_field_rejects_non_positive_values(field):
    with pytest.raises(ValueError):
        KernelLimits(**{field: 0})
    with pytest.raises(ValueError):
        KernelLimits(**{field: -1})


def test_kernel_limits_is_frozen():
    limits = KernelLimits()
    with pytest.raises(Exception):
        limits.max_nodes = 999
