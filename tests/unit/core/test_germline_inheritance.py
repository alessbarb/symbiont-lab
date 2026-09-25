"""Genome v2 inheritance and germline invariants."""

from __future__ import annotations

from dataclasses import replace

import pytest
from symbiont.core.germline import create_standard_genome

from symbiont.genetics import (
    DEFAULT_GENOME_SCHEMA,
    EpigeneticMark,
    EpigeneticProtocol,
    GermlineState,
    InheritancePackage,
    canonical_gene_bindings,
    create_offspring_package,
    mutate_genome,
    recombine_genomes,
)


def test_standard_genome_is_canonical_v2_without_legacy_bridge():
    genome = create_standard_genome("genome_alpha")
    assert genome.schema_version == 2
    assert genome.development.initial_concepts == 0
    assert not hasattr(genome, "loci_values")
    assert not hasattr(genome, "parent_ids")
    assert not hasattr(genome, "motor")


def test_every_locus_has_a_typed_schema_and_runtime_binding():
    bindings = {item.locus: item for item in canonical_gene_bindings()}
    assert bindings.keys() == DEFAULT_GENOME_SCHEMA.specs.keys()
    assert all(binding.consumer_id for binding in bindings.values())


def test_typed_mutation_is_deterministic_and_valid():
    genome = create_standard_genome("genome_mutation_parent")
    a = mutate_genome(genome, seed=42)
    b = mutate_genome(genome, seed=42)
    assert a == b
    DEFAULT_GENOME_SCHEMA.validate_flat(
        __import__("symbiont.genetics.genome", fromlist=["flatten_genes"]).flatten_genes(a)
    )


def test_recombination_keeps_genealogy_outside_genotype():
    a = create_standard_genome("genome_parent_a")
    b = create_standard_genome("genome_parent_b")
    b = replace(
        b,
        plasticity=replace(
            b.plasticity,
            learning_rate=replace(
                b.plasticity.learning_rate,
                baseline=0.04,
            ),
        ),
    )

    child = recombine_genomes(
        a,
        b,
        seed=7,
        new_genome_id="genome_child_ab",
    )

    assert child.genome_id == "genome_child_ab"
    assert not hasattr(child, "parent_ids")
    assert child.plasticity.learning_rate.baseline in (
        a.plasticity.learning_rate.baseline,
        b.plasticity.learning_rate.baseline,
    )


def test_epigenetic_mark_decay_is_bounded():
    mark = EpigeneticMark(
        locus="plasticity.learning_rate.baseline",
        delta=0.01,
        strength=1.0,
        generations_left=3,
    )
    gen1 = mark.decay(0.2)
    assert gen1 is not None
    assert gen1.strength == pytest.approx(0.8)
    assert gen1.generations_left == 2
    gen2 = gen1.decay(0.2)
    assert gen2 is not None
    assert gen2.generations_left == 1
    assert gen2.decay(0.2) is None


def test_acquired_epigenetic_capture_is_disabled_by_default():
    genome = create_standard_genome("genome_epigenetic_parent")
    state = GermlineState.from_genome(
        genome,
        acquired_capture_enabled=True,
    )
    current = {
        "plasticity.learning_rate.baseline": genome.plasticity.learning_rate.baseline + 0.03,
    }

    assert (
        state.capture_acquired_variation(
            current,
            genome=genome,
        )
        == ()
    )
    assert state.acquired_marks == {}


def test_explicit_epigenetic_protocol_can_capture_only_regulable_loci():
    genome = create_standard_genome("genome_epigenetic_protocol")
    state = GermlineState.from_genome(
        genome,
        acquired_capture_enabled=True,
    )
    protocol = EpigeneticProtocol(
        enabled=True,
        acquired_capture_enabled=True,
        min_capture_delta=0.001,
    )

    captured = state.capture_acquired_variation(
        {
            "plasticity.learning_rate.baseline": genome.plasticity.learning_rate.baseline + 0.02,
            "development.soft_node_budget": float(genome.development.soft_node_budget + 32),
        },
        genome=genome,
        protocol=protocol,
    )

    assert captured == ("plasticity.learning_rate.baseline",)
    assert "development.soft_node_budget" not in state.acquired_marks


def test_offspring_package_contains_genome_and_lineage_metadata_not_learning():
    parent = create_standard_genome("genome_parent_package")
    germline = GermlineState.from_genome(parent)
    package = create_offspring_package(
        parent_genome=parent,
        parent_germline=germline,
        seed=11,
        generation=2,
    )

    assert isinstance(package, InheritancePackage)
    assert package.generation == 2
    assert package.parent_ids == (parent.genome_id,)
    assert package.epigenetic_marks == ()
    assert not hasattr(package, "body_schema")
    assert not hasattr(package, "motor_primitives")
    assert not hasattr(package, "experience")


def test_epigenetic_transmission_requires_explicit_protocol():
    parent = create_standard_genome("genome_parent_epi")
    germline = GermlineState.from_genome(parent)
    germline.acquired_marks["plasticity.learning_rate.baseline"] = EpigeneticMark(
        locus="plasticity.learning_rate.baseline",
        delta=0.01,
        strength=1.0,
        generations_left=3,
    )

    default_package = create_offspring_package(
        parent_genome=parent,
        parent_germline=germline,
        seed=2,
        generation=1,
    )
    assert default_package.epigenetic_marks == ()

    explicit_package = create_offspring_package(
        parent_genome=parent,
        parent_germline=germline,
        seed=2,
        generation=1,
        epigenetic_protocol=EpigeneticProtocol(
            enabled=True,
            decay=0.2,
        ),
    )
    assert len(explicit_package.epigenetic_marks) == 1
    assert explicit_package.epigenetic_marks[0].strength == pytest.approx(0.8)
