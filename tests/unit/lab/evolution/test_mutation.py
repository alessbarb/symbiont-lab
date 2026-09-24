from __future__ import annotations

import random
from dataclasses import replace
from importlib import resources
import json

from symbiont.cognition.genome import Genome, GenomeCodec
from symbiont_lab.evolution.mutation import (
    derive_child_genome,
    mutate_continuous_fields,
    mutate_soft_budget,
)


def _parent_genome() -> Genome:
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    payload["genome_id"] = "genome_parent0000000000000000000"
    return GenomeCodec().load(payload)


def test_mutate_continuous_fields_returns_a_new_genome_object():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(
        parent,
        sigma=0.01,
        max_fields=3,
        rng=random.Random(1),
    )
    assert mutated is not parent
    assert isinstance(mutated, Genome)


def test_mutation_is_typed_and_stays_within_schema_ranges():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(
        parent,
        sigma=1.0,
        max_fields=3,
        rng=random.Random(1),
    )
    lr = mutated.plasticity.learning_rate
    assert lr.minimum <= lr.baseline <= lr.maximum
    assert 0.0 <= mutated.plasticity.eligibility_decay <= 1.0
    assert 0.0 <= mutated.structure.grow_threshold <= 1.0
    assert 0.0 <= mutated.structure.prune_threshold <= 1.0


def test_mutation_is_deterministic_for_same_rng_seed():
    parent = _parent_genome()
    a = mutate_continuous_fields(
        parent,
        sigma=0.02,
        max_fields=3,
        rng=random.Random(7),
    )
    b = mutate_continuous_fields(
        parent,
        sigma=0.02,
        max_fields=3,
        rng=random.Random(7),
    )
    assert a == b


def test_mutate_soft_budget_changes_only_targeted_field():
    parent = _parent_genome()
    mutated = mutate_soft_budget(
        parent,
        field="soft_node_budget",
        delta=8,
    )
    assert mutated.development.soft_node_budget == (
        parent.development.soft_node_budget + 8
    )
    assert (
        mutated.development.soft_edge_budget
        == parent.development.soft_edge_budget
    )


def test_derive_child_genome_changes_instance_not_genealogy_or_genotype():
    parent = _parent_genome()
    child = derive_child_genome(
        parent,
        new_genome_id="genome_child00000000000000000000",
        mutated=parent,
    )
    assert child.genome_id == "genome_child00000000000000000000"
    assert child.genotype_hash == parent.genotype_hash
    assert not hasattr(child, "parent_ids")


def test_genome_v2_round_trips_through_codec_without_lineage_fields():
    parent = _parent_genome()
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    payload["genome_id"] = parent.genome_id
    reloaded = GenomeCodec().load(payload)
    assert reloaded == parent
