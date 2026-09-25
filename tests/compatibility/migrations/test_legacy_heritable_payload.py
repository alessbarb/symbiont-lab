from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.genetics.migration import apply_legacy_heritable_payload, migrate_v1_genome


def test_legacy_loci_are_projected_once_into_current_genome():
    genome = migrate_v1_genome(
        {
            "schema_version": 1,
            "genome_id": "genome_legacy_loci",
            "parent_ids": [],
            "kernel_compatibility": ">=0.55,<0.60",
            "development": {
                "soft_node_budget": 64,
                "soft_edge_budget": 384,
                "consolidation_interval_ticks": 32,
            },
            "plasticity": {
                "learning_rate": {"initial": 0.02, "min": 0.001, "max": 0.08},
                "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
                "eligibility_decay": 0.92,
            },
            "structure": {
                "grow_threshold": 0.18,
                "prune_threshold": 0.01,
                "minimum_support": 16,
                "tentative_lifetime_ticks": 128,
            },
            "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
        }
    )
    migrated = apply_legacy_heritable_payload(
        genome,
        {"genome_id": "legacy", "loci": [("learning_rate", 0.04)]},
        kernel_limits=KernelLimits(),
    )
    assert migrated.schema_version == 2
    assert migrated.plasticity.learning_rate.baseline == pytest.approx(0.04)
    assert not hasattr(migrated, "loci_values")


def test_unknown_or_duplicate_legacy_locus_is_rejected():
    genome = migrate_v1_genome(
        {
            "schema_version": 1,
            "genome_id": "genome_legacy_loci",
            "parent_ids": [],
            "kernel_compatibility": ">=0.55,<0.60",
            "development": {
                "soft_node_budget": 64,
                "soft_edge_budget": 384,
                "consolidation_interval_ticks": 32,
            },
            "plasticity": {
                "learning_rate": {"initial": 0.02, "min": 0.001, "max": 0.08},
                "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
                "eligibility_decay": 0.92,
            },
            "structure": {
                "grow_threshold": 0.18,
                "prune_threshold": 0.01,
                "minimum_support": 16,
                "tentative_lifetime_ticks": 128,
            },
            "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
        }
    )
    with pytest.raises(ValueError):
        apply_legacy_heritable_payload(
            genome,
            {"genome_id": "legacy", "loci": [("parent_ids", 1.0)]},
            kernel_limits=KernelLimits(),
        )
