from __future__ import annotations

import random

import pytest

from symbiont.cognition.genome import Genome, GenomeCodec
from symbiont_lab.evolution.mutation import derive_child_genome, mutate_continuous_fields, mutate_soft_budget

_VALID_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_parent0000000000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 4,
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


def _parent_genome() -> Genome:
    return GenomeCodec().load(_VALID_PAYLOAD)


def test_mutate_continuous_fields_returns_a_new_genome_object():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=0.01, max_fields=3, rng=random.Random(1))
    assert mutated is not parent
    assert isinstance(mutated, Genome)


def test_mutate_continuous_fields_stays_within_each_fields_own_bounds():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=1.0, max_fields=3, rng=random.Random(1))
    lr = mutated.plasticity.learning_rate
    assert lr.minimum <= lr.initial <= lr.maximum
    assert 0.0 <= mutated.plasticity.eligibility_decay <= 1.0
    assert 0.0 <= mutated.structure.grow_threshold <= 1.0
    assert 0.0 <= mutated.structure.prune_threshold <= 1.0


def test_mutate_continuous_fields_is_deterministic_for_the_same_seed():
    parent = _parent_genome()
    a = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(7))
    b = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(7))
    assert a == b


def test_mutate_continuous_fields_different_seeds_can_diverge():
    parent = _parent_genome()
    a = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(1))
    b = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(2))
    assert a != b


def test_mutate_soft_budget_changes_only_the_targeted_field():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=8)
    assert mutated.development.soft_node_budget == 72
    assert mutated.development.soft_edge_budget == parent.development.soft_edge_budget


def test_mutate_soft_budget_never_goes_negative():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=-9999)
    assert mutated.development.soft_node_budget >= 1


def test_derive_child_genome_sets_parent_ids_and_new_id():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=8)
    child = derive_child_genome(parent, new_genome_id="genome_child00000000000000000000", mutated=mutated)
    assert child.genome_id == "genome_child00000000000000000000"
    assert child.parent_ids == (parent.genome_id,)
    assert child.development.soft_node_budget == 72


def test_derive_child_genome_round_trips_through_the_codec():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=0.01, max_fields=2, rng=random.Random(3))
    child = derive_child_genome(parent, new_genome_id="genome_child00000000000000000001", mutated=mutated)
    reloaded = GenomeCodec().load(
        {
            "schema_version": child.schema_version,
            "genome_id": child.genome_id,
            "parent_ids": list(child.parent_ids),
            "kernel_compatibility": child.kernel_compatibility,
            "development": {
                "initial_concepts": child.development.initial_concepts,
                "soft_node_budget": child.development.soft_node_budget,
                "soft_edge_budget": child.development.soft_edge_budget,
                "consolidation_interval_ticks": child.development.consolidation_interval_ticks,
            },
            "plasticity": {
                "learning_rate": {
                    "initial": child.plasticity.learning_rate.initial,
                    "min": child.plasticity.learning_rate.minimum,
                    "max": child.plasticity.learning_rate.maximum,
                },
                "forgetting_rate": {
                    "initial": child.plasticity.forgetting_rate.initial,
                    "min": child.plasticity.forgetting_rate.minimum,
                    "max": child.plasticity.forgetting_rate.maximum,
                },
                "eligibility_decay": child.plasticity.eligibility_decay,
            },
            "structure": {
                "grow_threshold": child.structure.grow_threshold,
                "prune_threshold": child.structure.prune_threshold,
                "minimum_support": child.structure.minimum_support,
                "tentative_lifetime_ticks": child.structure.tentative_lifetime_ticks,
            },
            "mutation_policy": {
                "continuous_sigma": child.mutation_policy.continuous_sigma,
                "max_fields_per_generation": child.mutation_policy.max_fields_per_generation,
            },
        }
    )
    assert reloaded == child
