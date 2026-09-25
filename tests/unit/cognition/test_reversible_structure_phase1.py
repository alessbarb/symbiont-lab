from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, apply_mutations, validate_mutation
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def _edge(source: str, target: str) -> PlasticEdge:
    return PlasticEdge(
        source_id=source,
        target_id=target,
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=1,
    )


def _remove_edge(source: str, target: str) -> Mutation:
    return Mutation(
        kind="remove_edge",
        payload={"source_id": source, "target_id": target, "kind": EdgeKind.EXCITATORY},
    )


def _remove_node(node_id: str) -> Mutation:
    return Mutation(kind="remove_node", payload={"node_id": node_id})


def test_remove_node_accepts_an_isolated_node() -> None:
    graph = CognitiveGraph(
        nodes=(_sense("sense_a"), _concept("concept_a")),
        edges=(),
        kernel_limits=KernelLimits(),
    )

    result = validate_mutation(_remove_node("concept_a"), graph, KernelLimits())
    assert result.accepted

    updated = apply_mutations(graph, (_remove_node("concept_a"),), KernelLimits())
    assert {node.node_id for node in updated.nodes} == {"sense_a"}
    assert {node.node_id for node in graph.nodes} == {"sense_a", "concept_a"}


def test_remove_node_rejects_a_node_with_incident_edges() -> None:
    graph = CognitiveGraph(
        nodes=(_sense("sense_a"), _concept("concept_a")),
        edges=(_edge("sense_a", "concept_a"),),
        kernel_limits=KernelLimits(),
    )

    result = validate_mutation(_remove_node("concept_a"), graph, KernelLimits())
    assert not result.accepted
    assert "incident edges" in (result.reason or "")


def test_remove_edge_then_remove_node_is_valid_in_one_atomic_batch() -> None:
    graph = CognitiveGraph(
        nodes=(_sense("sense_a"), _concept("concept_a")),
        edges=(_edge("sense_a", "concept_a"),),
        kernel_limits=KernelLimits(),
    )

    updated = apply_mutations(
        graph,
        (_remove_edge("sense_a", "concept_a"), _remove_node("concept_a")),
        KernelLimits(),
    )

    assert {node.node_id for node in updated.nodes} == {"sense_a"}
    assert updated.edges == ()


def test_remove_node_before_remove_edge_rejects_the_whole_batch() -> None:
    graph = CognitiveGraph(
        nodes=(_sense("sense_a"), _concept("concept_a")),
        edges=(_edge("sense_a", "concept_a"),),
        kernel_limits=KernelLimits(),
    )

    updated = apply_mutations(
        graph,
        (_remove_node("concept_a"), _remove_edge("sense_a", "concept_a")),
        KernelLimits(),
    )

    assert updated is graph
    assert len(updated.nodes) == 2
    assert len(updated.edges) == 1


def test_remove_node_rejects_unknown_node() -> None:
    graph = CognitiveGraph(nodes=(_sense("sense_a"),), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_remove_node("ghost"), graph, KernelLimits())
    assert not result.accepted
    assert "no such node" in (result.reason or "")


def test_remove_node_preserves_non_edge_graph_invariants() -> None:
    predictor = PlasticNode(
        node_id="predictor_a", kind=NodeKind.PREDICTOR, predicts_node_id="concept_a"
    )
    graph = CognitiveGraph(
        nodes=(_concept("concept_a"), predictor),
        edges=(),
        kernel_limits=KernelLimits(),
    )

    result = validate_mutation(_remove_node("concept_a"), graph, KernelLimits())
    assert not result.accepted
    assert "predicts_node_id" in (result.reason or "")
