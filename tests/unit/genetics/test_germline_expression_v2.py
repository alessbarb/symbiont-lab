from __future__ import annotations

import json
from dataclasses import replace
from importlib import resources

import pytest

from symbiont.core.orchestration.symbiont import Symbiont
from symbiont.genetics.expression import GeneExpressionState
from symbiont.genetics.genome import Genome, GenomeCodec
from symbiont.genetics.germline import EpigeneticMark, GermlineState


def _base_genome(genome_id: str = "genome_test_canonical") -> Genome:
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    payload["genome_id"] = genome_id
    return GenomeCodec().load(payload)


def test_inherited_mark_changes_birth_expression_without_changing_genotype() -> None:
    genome = _base_genome()
    genotype_hash = genome.genotype_hash
    mark = EpigeneticMark(
        locus="plasticity.learning_rate.baseline",
        delta=0.02,
        strength=0.5,
        generations_left=3,
    )
    germline = GermlineState.from_genome(
        genome,
        inherited_marks=(mark,),
    )

    expression = GeneExpressionState.from_genome(
        genome,
        germline=germline,
    )

    assert expression.effective_learning_rate == pytest.approx(
        genome.plasticity.learning_rate.baseline + 0.01
    )
    assert genome.genotype_hash == genotype_hash


def test_symbiont_uses_canonical_germline_expression_at_birth() -> None:
    genome = _base_genome("genome_test_symbiont_expression")
    mark = EpigeneticMark(
        locus="sensorimotor.spontaneous_activity_baseline",
        delta=0.3,
        strength=0.5,
        generations_left=2,
    )
    germline = GermlineState.from_genome(
        genome,
        inherited_marks=(mark,),
    )
    symbiont = Symbiont(
        "symbiont.test.expression",
        seed=123,
        genome=genome,
        germline=germline,
    )

    expected = min(
        1.0,
        genome.sensorimotor.spontaneous_activity_baseline + 0.15,
    )
    assert symbiont.exploration_rate == pytest.approx(expected)
    assert symbiont.gene_expression_state is not None
    assert symbiont.gene_expression_state.exploration_drive == pytest.approx(expected)


def test_different_genome_locus_changes_operating_learning_phenotype() -> None:
    base = _base_genome("genome_test_learning_base")
    slow_range = replace(
        base.plasticity.learning_rate,
        baseline=0.005,
        minimum=0.001,
        maximum=0.08,
    )
    fast_range = replace(
        base.plasticity.learning_rate,
        baseline=0.06,
        minimum=0.001,
        maximum=0.08,
    )
    slow = replace(
        base,
        genome_id="genome_test_learning_slow",
        plasticity=replace(
            base.plasticity,
            learning_rate=slow_range,
        ),
    )
    fast = replace(
        base,
        genome_id="genome_test_learning_fast",
        plasticity=replace(
            base.plasticity,
            learning_rate=fast_range,
        ),
    )

    slow_symbiont = Symbiont(
        "symbiont.same",
        seed=77,
        genome=slow,
        germline=GermlineState.from_genome(slow),
    )
    fast_symbiont = Symbiont(
        "symbiont.same",
        seed=77,
        genome=fast,
        germline=GermlineState.from_genome(fast),
    )

    assert slow_symbiont.learning_rate == pytest.approx(0.005)
    assert fast_symbiont.learning_rate == pytest.approx(0.06)
    assert slow_symbiont.sensorimotor_model.learning_rate == pytest.approx(0.005)
    assert fast_symbiont.sensorimotor_model.learning_rate == pytest.approx(0.06)
    assert slow.genotype_hash != fast.genotype_hash
