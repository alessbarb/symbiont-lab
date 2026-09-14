from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits


def test_defaults_match_the_design_doc_table():
    limits = KernelLimits()
    assert limits.max_nodes == 128
    assert limits.max_concepts == 32
    assert limits.max_edges == 1024
    assert limits.max_tentative_edges == 128
    assert limits.max_structural_mutations_per_consolidation == 8
    assert limits.consolidation_interval_ticks == 32
    assert limits.max_plastic_checkpoint_bytes == 2 * 1024 * 1024


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
