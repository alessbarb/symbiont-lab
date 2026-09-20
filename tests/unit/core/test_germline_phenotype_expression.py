from __future__ import annotations

import pytest

from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    SymbiontGenome,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.symbiont import Symbiont


def _genome_with(genome_id: str, **overrides: float | int) -> SymbiontGenome:
    base = create_standard_genome(genome_id)
    return SymbiontGenome(
        genome_id=genome_id,
        loci_values={**dict(base.loci_values), **overrides},
        specs=base.specs,
    )


def test_genome_learning_rate_is_actual_sensorimotor_phenotype():
    slow_genome = _genome_with("slow", learning_rate=0.03)
    fast_genome = _genome_with("fast", learning_rate=0.31)

    slow = Symbiont(
        "sym-slow",
        genome=slow_genome,
        germline=GermlineState(birth_expression=dict(slow_genome.loci_values)),
    )
    fast = Symbiont(
        "sym-fast",
        genome=fast_genome,
        germline=GermlineState(birth_expression=dict(fast_genome.loci_values)),
    )

    assert slow.learning_rate == pytest.approx(0.03)
    assert fast.learning_rate == pytest.approx(0.31)
    assert slow.sensorimotor_model.learning_rate == pytest.approx(0.03)
    assert fast.sensorimotor_model.learning_rate == pytest.approx(0.31)
    assert slow.expressed_loci["learning_rate"] == pytest.approx(0.03)
    assert fast.expressed_loci["learning_rate"] == pytest.approx(0.31)


def test_epigenetic_mark_modulates_actual_cognitive_phenotype():
    genome = _genome_with("epi-parent", learning_rate=0.20)
    germline = GermlineState(birth_expression=dict(genome.loci_values))
    assert germline.add_mark(
        EpigeneticMark(
            locus="learning_rate",
            delta=0.10,
            strength=0.5,
            generations_left=3,
        )
    )

    sym = Symbiont("sym-epi", genome=genome, germline=germline)

    assert sym.learning_rate == pytest.approx(0.25)
    assert sym.sensorimotor_model.learning_rate == pytest.approx(0.25)


def test_genome_is_authoritative_over_constructor_fallback_when_present():
    genome = _genome_with(
        "authoritative",
        learning_rate=0.17,
        exploration_rate=0.61,
    )
    sym = Symbiont(
        "sym-authoritative",
        learning_rate=0.99,
        exploration_rate=0.01,
        genome=genome,
        germline=GermlineState(birth_expression=dict(genome.loci_values)),
    )

    assert sym.learning_rate == pytest.approx(0.17)
    assert sym.exploration_rate == pytest.approx(0.61)


def test_genomeless_symbiont_preserves_explicit_constructor_fallbacks():
    sym = Symbiont(
        "sym-legacy-free-fallback",
        learning_rate=0.23,
        exploration_rate=0.47,
    )
    assert sym.learning_rate == pytest.approx(0.23)
    assert sym.exploration_rate == pytest.approx(0.47)


def test_exploration_locus_changes_operational_trajectory_under_same_seed():
    low_genome = _genome_with("explore-low", exploration_rate=0.01)
    high_genome = _genome_with("explore-high", exploration_rate=0.80)

    low = Symbiont(
        "same-cognitive-id",
        seed=991,
        genome=low_genome,
        germline=GermlineState(birth_expression=dict(low_genome.loci_values)),
    )
    high = Symbiont(
        "same-cognitive-id",
        seed=991,
        genome=high_genome,
        germline=GermlineState(birth_expression=dict(high_genome.loci_values)),
    )

    for sym in (low, high):
        sym.register_output_channels(("out.0",))
        # Put the assay in the exploitation/perturbation branch where
        # exploration_rate is the operative sigma, without supplying any
        # semantic world information.
        sym.agency_model.agency_confidence["out.0"] = 0.9
        sym.last_activations = {"out.0": 0.5}

    low_trace = [low.step({})["out.0"] for _ in range(20)]
    high_trace = [high.step({})["out.0"] for _ in range(20)]

    assert low_trace != high_trace


def test_inherited_epigenetic_predisposition_changes_phenotype_without_learned_state():
    parent_genome = _genome_with(
        "parent-expression",
        learning_rate=0.20,
        acquired_transmission_rate=1.0,
        epigenetic_decay=0.20,
    )
    parent_germline = GermlineState(
        birth_expression=dict(parent_genome.loci_values)
    )
    assert parent_germline.add_mark(
        EpigeneticMark(
            locus="learning_rate",
            delta=0.10,
            strength=1.0,
            generations_left=3,
        )
    )

    package = create_offspring_package(
        parent_genome=parent_genome,
        parent_germline=parent_germline,
        seed=123,
        generation=1,
    )
    child_germline = GermlineState(
        birth_expression=dict(package.genome.loci_values),
        acquired_marks={mark.locus: mark for mark in package.epigenetic_marks},
    )
    child = Symbiont(
        "child-expression",
        seed=123,
        genome=package.genome,
        germline=child_germline,
    )

    transmitted = {mark.locus: mark for mark in package.epigenetic_marks}
    assert "learning_rate" in transmitted
    expected = child_germline.effective_expression(
        "learning_rate",
        float(package.genome.get("learning_rate")),
        spec=package.genome.specs["learning_rate"],
    )
    assert child.learning_rate == pytest.approx(expected)

    # Predisposition crosses; concrete lifetime solution state does not.
    assert child.sensorimotor_model.weights == {}
    assert child.sensorimotor_model.prediction_errors == {}
    assert child.agency_model.contingency == {}
    assert child.agency_model.agency_confidence == {}
    assert child.body_schema.internal_channels == set()
    assert child.body_schema.regions == []
