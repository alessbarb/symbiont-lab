from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense_node(node_id: str = "sense-a") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept_node(node_id: str = "concept-a", bias: float = 0.0, tau: float = 1.0) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT, bias=bias, tau=tau)


def _edge(
    source: str = "sense-a",
    target: str = "concept-a",
    kind: EdgeKind = EdgeKind.EXCITATORY,
    weight: float = 1.0,
    delay_ticks: int = 0,
) -> PlasticEdge:
    return PlasticEdge(
        source_id=source, target_id=target, kind=kind, weight=weight, plasticity=0.5, delay_ticks=delay_ticks
    )


def test_valid_graph_constructs_without_error():
    CognitiveGraph(nodes=(_sense_node(), _concept_node()), edges=(_edge(),), kernel_limits=KernelLimits())


def test_rejects_duplicate_node_id():
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(_sense_node("x"), _concept_node("x")), edges=(), kernel_limits=KernelLimits())


def test_rejects_dangling_edge_source():
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_concept_node(),),
            edges=(_edge(source="ghost", target="concept-a"),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_dangling_edge_target():
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_sense_node(),),
            edges=(_edge(source="sense-a", target="ghost"),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_node_count_exceeding_kernel_limit():
    nodes = tuple(_concept_node(f"c{i}") for i in range(3))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits(max_nodes=2))


def test_rejects_edge_count_exceeding_kernel_limit():
    nodes = (_sense_node(), _concept_node("c1"), _concept_node("c2"))
    edges = (_edge(target="c1"), _edge(target="c2"))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits(max_edges=1))


def test_rejects_concept_count_exceeding_kernel_limit():
    nodes = tuple(_concept_node(f"c{i}") for i in range(3))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits(max_concepts=2))


@pytest.mark.parametrize("tau", [0.05, 10.5])
def test_rejects_tau_outside_range(tau):
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(_concept_node(tau=tau),), edges=(), kernel_limits=KernelLimits())


@pytest.mark.parametrize("weight", [-2.5, 2.5])
def test_rejects_weight_outside_range(weight):
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_sense_node(), _concept_node()),
            edges=(_edge(weight=weight),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_plasticity_outside_range():
    nodes = (_sense_node(), _concept_node())
    bad_edge = PlasticEdge(
        source_id="sense-a", target_id="concept-a", kind=EdgeKind.EXCITATORY, weight=1.0, plasticity=1.5, delay_ticks=0
    )
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_delay_outside_zero_or_one():
    nodes = (_sense_node(), _concept_node())
    bad_edge = PlasticEdge(
        source_id="sense-a", target_id="concept-a", kind=EdgeKind.EXCITATORY, weight=1.0, plasticity=0.5, delay_ticks=2
    )
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_delay_zero_from_a_non_sense_source():
    nodes = (_concept_node("a"), _concept_node("b"))
    bad_edge = _edge(source="a", target="b", delay_ticks=0)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_accepts_delay_one_from_a_non_sense_source():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())


def test_rejects_a_sense_node_with_an_incoming_edge():
    nodes = (_concept_node("a"), _sense_node("s"))
    bad_edge = _edge(source="a", target="s", delay_ticks=1)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_duplicate_source_target_kind_edge():
    nodes = (_sense_node(), _concept_node())
    edges = (_edge(), _edge())
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())


def test_allows_two_edges_same_endpoints_different_kind():
    nodes = (_sense_node(), _concept_node())
    edges = (_edge(kind=EdgeKind.EXCITATORY), _edge(kind=EdgeKind.GATING))
    CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())
