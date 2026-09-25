from __future__ import annotations

from dataclasses import replace

import pytest
from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    SymbiontGenome,
    create_germline_state,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.symbiont import Symbiont

from symbiont.genetics.germline import EpigeneticProtocol


def _genome_with(genome_id: str, **overrides: float | int) -> SymbiontGenome:
    base = create_standard_genome(genome_id)
    learning_value = float(overrides.get("learning_rate", base.plasticity.learning_rate.baseline))
    learning = replace(
        base.plasticity.learning_rate,
        baseline=learning_value,
        maximum=max(base.plasticity.learning_rate.maximum, learning_value + 0.20),
    )
    sensorimotor = replace(
        base.sensorimotor,
        spontaneous_activity_baseline=float(
            overrides.get("exploration_rate", base.sensorimotor.spontaneous_activity_baseline)
        ),
    )
    return replace(
        base,
        genome_id=f"genome_{genome_id}",
        plasticity=replace(base.plasticity, learning_rate=learning),
        sensorimotor=sensorimotor,
    )


def test_genome_learning_rate_is_actual_sensorimotor_phenotype():
    slow_genome = _genome_with("slow", learning_rate=0.03)
    fast_genome = _genome_with("fast", learning_rate=0.31)

    slow = Symbiont(
        "sym-slow",
        genome=slow_genome,
        germline=create_germline_state(slow_genome),
    )
    fast = Symbiont(
        "sym-fast",
        genome=fast_genome,
        germline=create_germline_state(fast_genome),
    )

    assert slow.learning_rate == pytest.approx(0.03)
    assert fast.learning_rate == pytest.approx(0.31)
    assert slow.sensorimotor_model.learning_rate == pytest.approx(0.03)
    assert fast.sensorimotor_model.learning_rate == pytest.approx(0.31)
    assert slow.expressed_loci["learning_rate"] == pytest.approx(0.03)
    assert fast.expressed_loci["learning_rate"] == pytest.approx(0.31)


def test_epigenetic_mark_modulates_actual_cognitive_phenotype():
    genome = _genome_with("epi-parent", learning_rate=0.10)
    germline = GermlineState.from_genome(
        genome,
        inherited_marks=(
            EpigeneticMark(
                locus="plasticity.learning_rate.baseline",
                delta=0.10,
                strength=0.5,
                generations_left=3,
            ),
        ),
    )

    sym = Symbiont("sym-epi", genome=genome, germline=germline)

    assert sym.learning_rate == pytest.approx(0.15)
    assert sym.sensorimotor_model.learning_rate == pytest.approx(0.15)


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
        germline=create_germline_state(genome),
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
        germline=create_germline_state(low_genome),
    )
    high = Symbiont(
        "same-cognitive-id",
        seed=991,
        genome=high_genome,
        germline=create_germline_state(high_genome),
    )

    for sym in (low, high):
        sym.register_output_channels(("out.0",))
        sym.attach_execution_surface("surface:test")

    low_trace = [low.step({})["out.0"] for _ in range(20)]
    high_trace = [high.step({})["out.0"] for _ in range(20)]

    assert low_trace != high_trace


def test_inherited_epigenetic_predisposition_changes_phenotype_without_learned_state():
    parent_genome = _genome_with(
        "parent-expression",
        learning_rate=0.10,
    )
    parent_germline = GermlineState.from_genome(
        parent_genome,
        inherited_marks=(
            EpigeneticMark(
                locus="plasticity.learning_rate.baseline",
                delta=0.10,
                strength=1.0,
                generations_left=3,
            ),
        ),
    )

    package = create_offspring_package(
        parent_genome=parent_genome,
        parent_germline=parent_germline,
        seed=123,
        generation=1,
        epigenetic_protocol=EpigeneticProtocol(enabled=True, decay=0.20),
    )
    child_germline = GermlineState.from_genome(
        package.genome,
        inherited_marks=package.epigenetic_marks,
    )
    child = Symbiont(
        "child-expression",
        seed=123,
        genome=package.genome,
        germline=child_germline,
    )

    transmitted = {mark.locus: mark for mark in package.epigenetic_marks}
    assert "plasticity.learning_rate.baseline" in transmitted
    expected = child_germline.effective_value(
        package.genome,
        "plasticity.learning_rate.baseline",
    )
    assert child.learning_rate == pytest.approx(expected)

    # Predisposition crosses; concrete lifetime solution state does not.
    assert child.sensorimotor_model.relation_count == 0
    assert child.causal_evidence.evidence == ()
    assert child.agency_model.estimates == ()
    assert child.controllability_model.estimates == ()
    assert child.body_schema.boundary_confidence == 0.0
    assert child.body_schema.self_caused_channels == ()
