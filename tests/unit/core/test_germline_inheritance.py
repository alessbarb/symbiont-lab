"""Tests for multidimensional evolutionary inheritance, genetics and epigenetics (P14-P22)."""
from __future__ import annotations

import random
import pytest

from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    LocusSpec,
    LocusType,
    STANDARD_COGNITIVE_LOCI,
    SymbiontGenome,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.heredity import HeritableGenome


def test_locus_spec_validation_and_mutation():
    """P15: LocusSpec enforces typed boundaries and typed mutation."""
    spec_int = LocusSpec(
        name="test_int",
        locus_type=LocusType.INT,
        minimum=1,
        maximum=10,
        default_value=5,
        mutation_rate=1.0,
    )
    spec_float = LocusSpec(
        name="test_float",
        locus_type=LocusType.FLOAT,
        minimum=0.0,
        maximum=1.0,
        default_value=0.5,
        mutation_rate=1.0,
        mutation_sigma=0.1,
    )

    # Validation
    assert spec_int.validate(7) == 7
    with pytest.raises(ValueError):
        spec_int.validate(15)  # Out of bounds
    with pytest.raises(ValueError):
        spec_int.validate(4.5)  # Wrong type
    with pytest.raises(ValueError):
        spec_int.validate(True)  # Booleans rejected

    assert spec_float.validate(0.8) == 0.8
    with pytest.raises(ValueError):
        spec_float.validate(1.5)

    # Mutation preserves type and bounds
    rng = random.Random(42)
    mut_int = spec_int.mutate(5, rng)
    assert isinstance(mut_int, int)
    assert 1 <= mut_int <= 10

    mut_float = spec_float.mutate(0.5, rng)
    assert isinstance(mut_float, float)
    assert 0.0 <= mut_float <= 1.0


def test_symbiont_genome_and_heritable_bridge():
    """P14, P16: SymbiontGenome unifies loci and bridges legacy HeritableGenome."""
    genome = create_standard_genome("genome_alpha")
    assert genome.get("learning_rate") == 0.1
    assert genome.get("initial_concepts") == 3
    assert genome.identity.startswith("genome_")

    # Bridge to HeritableGenome
    hg = genome.to_heritable_genome()
    assert isinstance(hg, HeritableGenome)
    hg_dict = dict(hg.loci)
    assert "learning_rate" in hg_dict
    assert hg_dict["learning_rate"] == 0.1

    # Bridge back from HeritableGenome
    restored = SymbiontGenome.from_heritable_genome(hg)
    assert restored.get("learning_rate") == 0.1


def test_epigenetic_mark_lifecycle_and_decay():
    """P17, P20: EpigeneticMark persists for bounded generations and decays."""
    mark = EpigeneticMark(locus="learning_rate", delta=0.05, strength=1.0, generations_left=3)
    assert mark.locus == "learning_rate"
    assert mark.strength == 1.0
    assert mark.generations_left == 3

    # Generation 1
    gen1 = mark.decay(0.2)
    assert gen1 is not None
    assert gen1.generations_left == 2
    assert gen1.strength == pytest.approx(0.8)

    # Generation 2
    gen2 = gen1.decay(0.2)
    assert gen2 is not None
    assert gen2.generations_left == 1
    assert gen2.strength == pytest.approx(0.64)

    # Generation 3 -> expires to None
    gen3 = gen2.decay(0.2)
    assert gen3 is None


def test_germline_state_strictly_bounds_marks_to_loci():
    """P18, P19: Acquired capture allowed only on declared loci; concepts rejected."""
    germline = GermlineState(birth_expression={"learning_rate": 0.1})

    # Legitimate locus mark succeeds
    legit_mark = EpigeneticMark(locus="learning_rate", delta=0.05, strength=1.0)
    assert germline.add_mark(legit_mark)
    assert "learning_rate" in germline.acquired_marks
    assert germline.effective_expression("learning_rate", 0.1) == pytest.approx(0.15)

    # Attempting to add an invented locus or learned concept must fail closed (Invariant B)
    illegal_concept_mark = EpigeneticMark(locus="learned_threat_concept", delta=1.0)
    assert not germline.add_mark(illegal_concept_mark)
    assert "learned_threat_concept" not in germline.acquired_marks


def test_sexual_recombination_and_offspring_package():
    """P21, P22: Sexual reproduction recombines independent loci and transmits epigenetics."""
    parent_a = create_standard_genome("parent_a")
    parent_b = create_standard_genome("parent_b")

    # Differentiate parents
    parent_a = SymbiontGenome(
        genome_id="parent_a",
        loci_values={**parent_a.loci_values, "learning_rate": 0.05, "initial_concepts": 2},
    )
    parent_b = SymbiontGenome(
        genome_id="parent_b",
        loci_values={**parent_b.loci_values, "learning_rate": 0.25, "initial_concepts": 6},
    )

    child_genome = parent_a.recombine_with(parent_b, seed=123)
    assert child_genome.parent_ids == ("parent_a", "parent_b")
    # Loci are chosen independently from either parent
    assert child_genome.get("learning_rate") in (0.05, 0.25)
    assert child_genome.get("initial_concepts") in (2, 6)

    # Test offspring package creation
    germline_a = GermlineState()
    germline_a.add_mark(EpigeneticMark(locus="learning_rate", delta=0.02, strength=1.0, generations_left=2))

    package = create_offspring_package(
        parent_genome=parent_a,
        parent_germline=germline_a,
        second_parent_genome=parent_b,
        generation=2,
        seed=42,
    )
    assert isinstance(package, InheritancePackage)
    assert package.generation == 2
    assert "parent_a" in package.parent_ids
    assert "parent_b" in package.parent_ids

    # Marks transmitted have decayed
    if package.epigenetic_marks:
        for mark in package.epigenetic_marks:
            assert mark.generations_left <= 2
            assert mark.strength < 1.0


def test_inheritance_genes_evolution():
    """P22: Heritability parameters (transmission rate, decay) are evolvable loci."""
    genome = create_standard_genome("evolvable_parent")
    assert "acquired_transmission_rate" in genome.loci_values
    assert "epigenetic_decay" in genome.loci_values

    # Mutating genome can mutate transmission rate and decay rate
    mutants = [genome.mutate(seed=s) for s in range(20)]
    transmission_rates = {m.get("acquired_transmission_rate") for m in mutants}
    # Should observe variation across mutant seeds
    assert len(transmission_rates) > 1
