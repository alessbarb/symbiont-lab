from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import StructuralPlasticity
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge


def test_generic_edge_candidate_pool_rejects_sense_targets_before_accumulation() -> None:
    plasticity = StructuralPlasticity(
        min_candidate_support=2,
        tentative_lifetime_ticks=16,
        cooldown_ticks=0,
    )

    for tick in (1, 2):
        plasticity.observe_coactivation(
            source_id="sense_a",
            target_id="sense_b",
            source_active=True,
            target_active=True,
            tick=tick,
            source_kind=NodeKind.SENSE,
            target_kind=NodeKind.SENSE,
        )
        plasticity.observe_coactivation(
            source_id="concept_a",
            target_id="sense_b",
            source_active=True,
            target_active=True,
            tick=tick,
            source_kind=NodeKind.CONCEPT,
            target_kind=NodeKind.SENSE,
        )

    assert plasticity.export_checkpoint()["coactivation_counts"] == []


def test_generic_edge_candidate_pool_still_accepts_legal_sense_to_concept_pair() -> None:
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=2,
        tentative_lifetime_ticks=16,
        cooldown_ticks=0,
    )

    for tick in (1, 2):
        plasticity.observe_coactivation(
            source_id="sense_a",
            target_id="concept_a",
            source_active=True,
            target_active=True,
            tick=tick,
            source_kind=NodeKind.SENSE,
            target_kind=NodeKind.CONCEPT,
        )

    mutations = plasticity.propose(graph, kernel_limits=limits, tick=3)
    assert len(mutations) == 1
    assert mutations[0].kind == "add_edge"
    assert mutations[0].payload["source_id"] == "sense_a"
    assert mutations[0].payload["target_id"] == "concept_a"


def test_edge_support_tracks_transmission_without_requiring_active_target() -> None:
    limits = KernelLimits()
    genome, _ = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 16))
    edge = PlasticEdge(
        source_id="sense_a",
        target_id="concept_a",
        kind=EdgeKind.EXCITATORY,
        weight=0.05,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
        ),
        edges=(edge,),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=False,
    )

    result = bridge.tick({"sense_a": 1.0}, tick=1)

    assert abs(result.activations["concept_a"]) < 0.1
    assert bridge.graph.edges[0].support == 1
    assert bridge.graph.edges[0].last_use_tick == 1


def test_first_germinal_bundle_survives_beyond_tentative_lifetime() -> None:
    limits = KernelLimits()
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 16))
    genome = replace(
        genome,
        development=replace(genome.development, consolidation_interval_ticks=2),
        structure=replace(
            genome.structure,
            minimum_support=2,
            growth_threshold=replace(
                genome.structure.growth_threshold,
                baseline=0.0,
                minimum=0.0,
            ),
            tentative_lifetime_ticks=4,
        ),
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    for tick in range(1, 11):
        bridge.tick(
            {
                "sense_alpha": float(tick),
                "sense_beta": float(tick * 2),
            },
            tick=tick,
        )

    concepts = [node for node in bridge.graph.nodes if node.kind is NodeKind.CONCEPT]
    readouts = [node for node in bridge.graph.nodes if node.kind is NodeKind.READOUT]
    assert len(concepts) == 1
    assert len(readouts) == 1
    assert len(bridge.graph.edges) == 3
    assert all(edge.target_id not in {"sense_alpha", "sense_beta"} for edge in bridge.graph.edges)
    assert all(edge.support >= genome.structure.minimum_support for edge in bridge.graph.edges)

    concept_id = concepts[0].node_id
    readout_id = readouts[0].node_id
    pairs = {(edge.source_id, edge.target_id) for edge in bridge.graph.edges}
    assert ("sense_alpha", concept_id) in pairs
    assert ("sense_beta", concept_id) in pairs
    assert (concept_id, readout_id) in pairs
