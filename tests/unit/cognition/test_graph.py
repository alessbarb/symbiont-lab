from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode, TickContext
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


def test_load_graph_definition_builds_a_valid_graph():
    from symbiont.cognition.graph import load_graph_definition

    payload = {
        "nodes": [
            {"node_id": "sense-a", "kind": "sense"},
            {"node_id": "concept-a", "kind": "concept", "bias": 0.1, "tau": 1.2},
        ],
        "edges": [
            {"source_id": "sense-a", "target_id": "concept-a", "kind": "excitatory", "weight": 0.6, "plasticity": 0.5, "delay_ticks": 0}
        ],
    }
    graph = load_graph_definition(payload, kernel_limits=KernelLimits())
    assert {n.node_id for n in graph.nodes} == {"sense-a", "concept-a"}
    concept = next(n for n in graph.nodes if n.node_id == "concept-a")
    assert concept.bias == pytest.approx(0.1)
    assert concept.tau == pytest.approx(1.2)
    assert graph.edges[0].weight == pytest.approx(0.6)


def test_load_graph_definition_applies_field_defaults():
    from symbiont.cognition.graph import load_graph_definition

    payload = {
        "nodes": [{"node_id": "sense-a", "kind": "sense"}, {"node_id": "concept-a", "kind": "concept"}],
        "edges": [{"source_id": "sense-a", "target_id": "concept-a", "kind": "excitatory", "weight": 0.5}],
    }
    graph = load_graph_definition(payload, kernel_limits=KernelLimits())
    concept = next(n for n in graph.nodes if n.node_id == "concept-a")
    assert concept.bias == 0.0
    assert concept.tau == 1.0
    assert graph.edges[0].plasticity == 0.5
    assert graph.edges[0].delay_ticks == 1


def test_load_graph_definition_reuses_construction_validation():
    from symbiont.cognition.graph import load_graph_definition

    payload = {
        "nodes": [{"node_id": "sense-a", "kind": "sense"}, {"node_id": "concept-a", "kind": "concept"}],
        "edges": [{"source_id": "sense-a", "target_id": "concept-a", "kind": "excitatory", "weight": 99.0}],
    }
    with pytest.raises(GraphError):
        load_graph_definition(payload, kernel_limits=KernelLimits())


def test_allows_two_edges_same_endpoints_different_kind():
    nodes = (_sense_node(), _concept_node())
    edges = (_edge(kind=EdgeKind.EXCITATORY), _edge(kind=EdgeKind.GATING))
    CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())


# --- activation ---


def test_activate_echoes_sense_inputs_directly():
    graph = CognitiveGraph(nodes=(_sense_node(),), edges=(), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 0.7}, context=TickContext(tick=1))
    assert frame.activations["sense-a"] == 0.7


def test_activate_computes_bias_only_with_no_edges():
    import math

    graph = CognitiveGraph(nodes=(_concept_node(bias=0.5, tau=1.0),), edges=(), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={}, context=TickContext(tick=1))
    assert frame.activations["concept-a"] == pytest.approx(math.tanh(0.5))


def test_delay_zero_sense_edge_reacts_immediately():
    graph = CognitiveGraph(
        nodes=(_sense_node(), _concept_node()), edges=(_edge(delay_ticks=0),), kernel_limits=KernelLimits()
    )
    frame = graph.activate(inputs={"sense-a": 1.0}, context=TickContext(tick=1))
    assert frame.activations["concept-a"] > 0.5


def test_delay_one_edge_ignores_this_ticks_input_uses_previous():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    graph = CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={}, context=TickContext(tick=2), previous={"a": 1.0, "b": 0.0})
    assert frame.activations["b"] > 0.5


def test_cold_start_with_no_previous_treats_delay_one_sources_as_zero():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    graph = CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={}, context=TickContext(tick=1), previous=None)
    assert frame.activations["b"] == pytest.approx(0.0)


def test_activation_is_independent_of_node_and_edge_construction_order():
    nodes_forward = (_sense_node(), _concept_node("c1"), _concept_node("c2"))
    edges_forward = (_edge(target="c1"), _edge(target="c2"))
    graph_forward = CognitiveGraph(nodes=nodes_forward, edges=edges_forward, kernel_limits=KernelLimits())

    nodes_reversed = tuple(reversed(nodes_forward))
    edges_reversed = tuple(reversed(edges_forward))
    graph_reversed = CognitiveGraph(nodes=nodes_reversed, edges=edges_reversed, kernel_limits=KernelLimits())

    frame_forward = graph_forward.activate(inputs={"sense-a": 0.6}, context=TickContext(tick=1))
    frame_reversed = graph_reversed.activate(inputs={"sense-a": 0.6}, context=TickContext(tick=1))
    assert dict(frame_forward.activations) == dict(frame_reversed.activations)


def test_extreme_inputs_never_produce_nan_or_inf():
    graph = CognitiveGraph(
        nodes=(_sense_node(), _concept_node(bias=1e6)), edges=(_edge(weight=2.0),), kernel_limits=KernelLimits()
    )
    frame = graph.activate(inputs={"sense-a": 1e12}, context=TickContext(tick=1))
    import math

    for value in frame.activations.values():
        assert math.isfinite(value)


def test_readouts_contains_only_readout_kind_nodes():
    nodes = (_sense_node(), _concept_node(), PlasticNode(node_id="r1", kind=NodeKind.READOUT, bias=0.1))
    edges = (_edge(target="concept-a"),)
    graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 0.5}, context=TickContext(tick=1))
    assert set(frame.readouts.keys()) == {"r1"}
    assert "concept-a" not in frame.readouts


# --- gating ---


def test_gating_edge_near_zero_suppresses_a_co_targeting_edge():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gating = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gating), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={"gate-source": 0.0, "signal-source": 1.0}, context=TickContext(tick=1))
    assert abs(frame.activations["concept-a"]) < 0.05


def test_gating_edge_near_one_passes_signal_through():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gating = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gating), kernel_limits=KernelLimits())

    frame_open = graph.activate(inputs={"gate-source": 1.0, "signal-source": 1.0}, context=TickContext(tick=1))
    ungated_graph = CognitiveGraph(
        nodes=(_sense_node("signal-source"), _concept_node()), edges=(contributing,), kernel_limits=KernelLimits()
    )
    frame_ungated = ungated_graph.activate(inputs={"signal-source": 1.0}, context=TickContext(tick=1))
    assert frame_open.activations["concept-a"] == pytest.approx(frame_ungated.activations["concept-a"], abs=1e-6)


def test_two_gating_edges_combine_by_product():
    nodes = (_sense_node("gate-a"), _sense_node("gate-b"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gate_a = PlasticEdge(
        source_id="gate-a", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    gate_b = PlasticEdge(
        source_id="gate-b", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gate_a, gate_b), kernel_limits=KernelLimits())

    frame_both_open = graph.activate(
        inputs={"gate-a": 1.0, "gate-b": 1.0, "signal-source": 1.0}, context=TickContext(tick=1)
    )
    frame_one_closed = graph.activate(
        inputs={"gate-a": 1.0, "gate-b": 0.0, "signal-source": 1.0}, context=TickContext(tick=1)
    )
    assert abs(frame_one_closed.activations["concept-a"]) < abs(frame_both_open.activations["concept-a"])


@pytest.mark.parametrize("bad_id", ["", "../../etc/passwd", "has space", "rm -rf ~", "a" * 129])
def test_rejects_malformed_node_id(bad_id):
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(PlasticNode(node_id=bad_id, kind=NodeKind.SENSE),), edges=(), kernel_limits=KernelLimits())


def test_predictor_node_without_predicts_node_id_is_rejected():
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(predictor,), edges=(), kernel_limits=KernelLimits())


def test_predictor_node_with_dangling_predicts_node_id_is_rejected():
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR, predicts_node_id="ghost")
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(predictor,), edges=(), kernel_limits=KernelLimits())


def test_non_predictor_node_with_predicts_node_id_is_rejected():
    bad_concept = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT, predicts_node_id="c1")
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(bad_concept,), edges=(), kernel_limits=KernelLimits())


def test_valid_predictor_node_constructs_successfully():
    target = _concept_node("target")
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR, predicts_node_id="target")
    CognitiveGraph(nodes=(target, predictor), edges=(), kernel_limits=KernelLimits())


def test_gating_edge_weight_scales_before_clipping():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    negative_gate = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=-1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, negative_gate), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={"gate-source": 1.0, "signal-source": 1.0}, context=TickContext(tick=1))
    assert abs(frame.activations["concept-a"]) < 0.05
