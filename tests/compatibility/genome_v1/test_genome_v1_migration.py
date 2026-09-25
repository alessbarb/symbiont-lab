from __future__ import annotations

import pytest

from symbiont.genetics.migration import migrate_v1_genome, migrate_v1_payload

V1_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_historical_fixture",
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


def test_v1_migrates_to_v2_without_retired_fields_entering_runtime():
    payload = migrate_v1_payload(V1_PAYLOAD)
    genome = migrate_v1_genome(V1_PAYLOAD)

    assert payload["schema_version"] == 2
    assert genome.schema_version == 2
    assert genome.genome_id == "genome_v2_historical_fixture"
    assert "parent_ids" not in payload
    assert "mutation_policy" not in payload
    assert not hasattr(genome, "parent_ids")


def test_v1_migration_rejects_wrong_source_version():
    with pytest.raises(ValueError):
        migrate_v1_payload({**V1_PAYLOAD, "schema_version": 2})


def test_v1_migration_rejects_malformed_source():
    malformed = {**V1_PAYLOAD, "plasticity": {}}
    with pytest.raises(ValueError):
        migrate_v1_payload(malformed)
