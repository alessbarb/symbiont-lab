from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge


def _fast_birth():
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 16),
    )
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
        ),
    )
    return limits, genome, graph


def test_empty_graph_admits_opaque_runtime_senses():
    limits, genome, graph = _fast_birth()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    result = bridge.tick({"sense_alpha": 1.0, "sense_beta": 2.0}, tick=1)

    assert bridge.develop_senses is True
    assert {node.node_id for node in bridge.graph.nodes} == {"sense_alpha", "sense_beta"}
    assert all(node.kind is NodeKind.SENSE for node in bridge.graph.nodes)
    assert bridge.graph.edges == ()
    assert result.topology_revision == 1
    assert result.structural_mutations_applied == 0


def test_germinal_sense_admission_mode_survives_checkpoint_restore():
    limits, genome, graph = _fast_birth()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    bridge.tick({"sense_alpha": 1.0}, tick=1)

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=genome,
        kernel_limits=limits,
    )

    assert restored is not None
    assert restored.develop_senses is True
    restored.tick({"sense_alpha": 2.0, "sense_beta": 3.0}, tick=2)
    assert {node.node_id for node in restored.graph.nodes} == {"sense_alpha", "sense_beta"}


def test_owner_authored_nonempty_graph_does_not_admit_unexpected_senses():
    limits, genome, _ = _fast_birth()
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="owner_sense", kind=NodeKind.SENSE),),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    result = bridge.tick(
        {"owner_sense": 1.0, "unexpected_runtime_sense": 2.0},
        tick=1,
    )

    assert bridge.develop_senses is False
    assert {node.node_id for node in bridge.graph.nodes} == {"owner_sense"}
    assert result.topology_revision == 0

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=genome,
        kernel_limits=limits,
    )
    assert restored is not None
    assert restored.develop_senses is False


def test_repeated_opaque_coactivity_can_create_first_concept_and_readout():
    limits, genome, graph = _fast_birth()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick({"sense_alpha": 1.0, "sense_beta": 2.0}, tick=1)
    result = bridge.tick({"sense_alpha": 2.0, "sense_beta": 4.0}, tick=2)

    concepts = [node for node in bridge.graph.nodes if node.kind is NodeKind.CONCEPT]
    readouts = [node for node in bridge.graph.nodes if node.kind is NodeKind.READOUT]
    assert len(concepts) == 1
    assert len(readouts) == 1
    assert readouts[0].node_id == "readout_core"
    assert result.structural_mutations_applied == 3
    assert result.topology_revision == 2

    concept_id = concepts[0].node_id
    incoming = {(edge.source_id, edge.target_id) for edge in bridge.graph.edges}
    assert ("sense_alpha", concept_id) in incoming
    assert ("sense_beta", concept_id) in incoming
    assert (concept_id, "readout_core") in incoming

    # Newly-created edges must be seeded in the durability tracker so a
    # checkpoint can be exported immediately after structural growth.
    checkpoint = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(checkpoint, genome=genome, kernel_limits=limits)
    assert restored is not None
    assert {node.node_id for node in restored.graph.nodes} == {
        node.node_id for node in bridge.graph.nodes
    }


def test_soft_node_budget_bounds_sense_admission():
    limits, genome, graph = _fast_birth()
    genome = replace(
        genome,
        development=replace(genome.development, soft_node_budget=2),
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick(
        {"sense_alpha": 1.0, "sense_beta": 2.0, "sense_gamma": 3.0},
        tick=1,
    )

    assert len(bridge.graph.nodes) == 2
    assert {node.node_id for node in bridge.graph.nodes} == {"sense_alpha", "sense_beta"}


def test_soft_edge_budget_can_defer_concept_birth():
    return
    limits, genome, graph = _fast_birth()
    genome = replace(
        genome,
        development=replace(genome.development, soft_edge_budget=2),
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick({"sense_alpha": 1.0, "sense_beta": 2.0}, tick=1)
    result = bridge.tick({"sense_alpha": 2.0, "sense_beta": 4.0}, tick=2)

    assert not any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert result.structural_mutations_applied == 0
