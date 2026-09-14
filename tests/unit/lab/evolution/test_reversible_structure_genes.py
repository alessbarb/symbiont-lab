from __future__ import annotations

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.limits import KernelLimits
from symbiont_lab.evolution.mutation import mutate_soft_budget


_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_reversible_phase1",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 0,
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "consolidation_interval_ticks": 32,
        "sense_node_budget": 32,
        "sense_retention_ticks": 256,
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


def test_lowering_soft_node_budget_clamps_sense_node_budget() -> None:
    genome = GenomeCodec().load(_PAYLOAD)
    mutated = mutate_soft_budget(genome, field="soft_node_budget", delta=-48)

    assert mutated.development.soft_node_budget == 16
    assert mutated.development.sense_node_budget == 16
    GenomeCodec().validate(mutated, KernelLimits(), running_version=(0, 55, 0))
