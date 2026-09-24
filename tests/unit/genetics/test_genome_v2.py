from __future__ import annotations

from dataclasses import replace
from importlib import resources
import inspect
import json

from symbiont.cognition.graph import CognitiveGraph
from symbiont.cognition.limits import KernelLimits
from symbiont.core.cognition.bridge import CognitiveBridge
from symbiont.genetics.bindings import canonical_gene_bindings
from symbiont.genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from symbiont.genetics.genome import GenomeCodec
from symbiont.genetics.germline import EpigeneticProtocol, GermlineState
from symbiont.genetics.schema import DEFAULT_GENOME_SCHEMA
from symbiont.actuation.surface import derive_actuator_constitution


def _genome():
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    return GenomeCodec().load(payload)


def test_every_canonical_locus_has_exactly_one_runtime_binding():
    bindings = canonical_gene_bindings()
    assert {item.locus for item in bindings} == set(DEFAULT_GENOME_SCHEMA.specs)
    assert all(item.consumer_id for item in bindings)
    assert all(item.observable_projection for item in bindings)
    assert all(item.mutation_test_id for item in bindings)


def test_genotype_hash_is_independent_from_genome_instance_identity():
    genome = _genome()
    sibling_instance = replace(genome, genome_id="genome_same_genotype_other_instance")

    assert sibling_instance.genome_id != genome.genome_id
    assert sibling_instance.genotype_hash == genome.genotype_hash
    assert sibling_instance.genome_hash != genome.genome_hash
    assert not hasattr(genome, "parent_ids")


def test_expression_update_is_next_state_and_does_not_mutate_current_state():
    genome = _genome()
    current = GeneExpressionState.from_genome(genome)
    before = current.as_dict()

    updated = ExpressionRegulator().update(
        genome,
        current,
        RegulatorySignals(
            uncertainty=1.0,
            novelty=1.0,
            prediction_error=1.0,
            controllability_loss=1.0,
            embodiment_mismatch=1.0,
        ),
    )

    assert current.as_dict() == before
    assert updated.update_count == current.update_count + 1
    assert updated.effective_learning_rate >= current.effective_learning_rate
    assert updated.exploration_drive >= current.exploration_drive


def test_contract_metadata_cannot_enter_regulatory_signal_or_change_genotype():
    genome = _genome()
    state = GeneExpressionState.from_genome(genome)
    signals = RegulatorySignals(
        uncertainty=0.4,
        prediction_error=0.3,
        controllability_loss=0.2,
        embodiment_mismatch=0.3,
    )

    a = derive_actuator_constitution(4, physical_contract="body-contract-a")
    b = derive_actuator_constitution(4, physical_contract="body-contract-b")
    assert a.contract_fingerprint != b.contract_fingerprint
    assert genome.genotype_hash == _genome().genotype_hash
    assert "contract" not in inspect.signature(RegulatorySignals).parameters

    regulator = ExpressionRegulator()
    assert regulator.update(genome, state, signals).as_dict() == regulator.update(
        genome,
        state,
        signals,
    ).as_dict()


def test_developmental_capacity_starts_below_ceiling_and_never_crosses_it():
    genome = _genome()
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    assert bridge._adaptive_node_budget < genome.development.soft_node_budget
    assert bridge._adaptive_edge_budget < genome.development.soft_edge_budget

    for _ in range(128):
        bridge._expand_resource_budgets(
            need_nodes=True,
            need_edges=True,
            need_senses=True,
        )

    assert bridge._adaptive_node_budget == genome.development.soft_node_budget
    assert bridge._adaptive_edge_budget == genome.development.soft_edge_budget
    assert bridge._adaptive_sense_budget == genome.development.sense_node_budget


def test_zero_capacity_growth_sensitivity_freezes_developed_capacity():
    genome = _genome()
    genome = replace(
        genome,
        development=replace(
            genome.development,
            capacity_growth_sensitivity=0.0,
        ),
    )
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    before = (
        bridge._adaptive_node_budget,
        bridge._adaptive_edge_budget,
        bridge._adaptive_sense_budget,
    )

    assert not bridge._expand_resource_budgets(
        need_nodes=True,
        need_edges=True,
        need_senses=True,
    )
    assert (
        bridge._adaptive_node_budget,
        bridge._adaptive_edge_budget,
        bridge._adaptive_sense_budget,
    ) == before


def test_epigenetic_capture_is_disabled_without_explicit_protocol():
    genome = _genome()
    germline = GermlineState.from_genome(
        genome,
        acquired_capture_enabled=True,
    )
    current = {
        "plasticity.learning_rate.baseline":
            genome.plasticity.learning_rate.baseline + 0.05,
    }

    assert germline.capture_acquired_variation(
        current,
        genome=genome,
    ) == ()
    assert germline.capture_acquired_variation(
        current,
        genome=genome,
        protocol=EpigeneticProtocol(
            enabled=True,
            acquired_capture_enabled=True,
            min_capture_delta=0.001,
        ),
    ) == ("plasticity.learning_rate.baseline",)
