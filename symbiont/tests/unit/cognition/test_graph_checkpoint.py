from __future__ import annotations

import pytest

from symbiont.cognition.checkpoint import export_graph_checkpoint, restore_graph_checkpoint
from symbiont.cognition.graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense(node_id: str = "s") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept(node_id: str = "c") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT, bias=0.2, tau=1.5)


def _edge(weight: float = 0.75, eligibility: float = 3.2) -> PlasticEdge:
    edge = PlasticEdge(
        source_id="s",
        target_id="c",
        kind=EdgeKind.EXCITATORY,
        weight=weight,
        plasticity=0.5,
        delay_ticks=0,
    )
    edge.eligibility = eligibility
    edge.support = 42
    edge.age_ticks = 17
    edge.last_use_tick = 9
    return edge


def test_none_graph_round_trips_to_none():
    assert export_graph_checkpoint(None) is None
    assert restore_graph_checkpoint(None, kernel_limits=KernelLimits()) is None


def test_exported_payload_round_trips_topology_and_static_fields():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()), edges=(_edge(),), kernel_limits=KernelLimits()
    )
    payload = export_graph_checkpoint(graph)
    restored = restore_graph_checkpoint(payload, kernel_limits=KernelLimits())

    assert {n.node_id for n in restored.nodes} == {"s", "c"}
    restored_concept = next(n for n in restored.nodes if n.node_id == "c")
    assert restored_concept.bias == pytest.approx(0.2)
    assert restored_concept.tau == pytest.approx(1.5)

    restored_edge = restored.edges[0]
    assert restored_edge.source_id == "s"
    assert restored_edge.target_id == "c"
    assert restored_edge.plasticity == pytest.approx(0.5)
    assert restored_edge.support == 42
    assert restored_edge.age_ticks == 17
    assert restored_edge.last_use_tick == 9


def test_weight_survives_quantized_round_trip_approximately():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()),
        edges=(_edge(weight=0.75, eligibility=3.2),),
        kernel_limits=KernelLimits(),
    )
    payload = export_graph_checkpoint(graph)
    restored = restore_graph_checkpoint(payload, kernel_limits=KernelLimits())
    restored_edge = restored.edges[0]
    assert restored_edge.weight == pytest.approx(0.75, abs=0.2)


def test_eligibility_is_never_exported_and_always_zero_on_restore():
    """Labile (design §10.3, P5): eligibility is never durable."""
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()),
        edges=(_edge(weight=0.75, eligibility=3.2),),
        kernel_limits=KernelLimits(),
    )
    payload = export_graph_checkpoint(graph)
    assert "eligibility_class" not in payload["edges"][0]

    restored = restore_graph_checkpoint(payload, kernel_limits=KernelLimits())
    assert restored.edges[0].eligibility == 0.0


def test_two_consecutive_checkpoints_cannot_be_differenced_to_recover_exact_weight():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()), edges=(_edge(weight=0.750001),), kernel_limits=KernelLimits()
    )
    before = export_graph_checkpoint(graph)
    graph.edges[0].weight = 0.750002  # a change far smaller than one quantization bin
    after = export_graph_checkpoint(graph)
    assert before["edges"][0]["weight_class"] == after["edges"][0]["weight_class"]


def test_restore_rejects_a_payload_that_would_violate_kernel_limits():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()), edges=(_edge(),), kernel_limits=KernelLimits()
    )
    payload = export_graph_checkpoint(graph)
    with pytest.raises(GraphError):
        restore_graph_checkpoint(payload, kernel_limits=KernelLimits(max_nodes=1))


def test_restore_rejects_malformed_payload_type():
    with pytest.raises(GraphError):
        restore_graph_checkpoint({"nodes": "not-a-list", "edges": []}, kernel_limits=KernelLimits())


def test_restore_rejects_unknown_weight_codec_version():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()), edges=(_edge(),), kernel_limits=KernelLimits()
    )
    payload = export_graph_checkpoint(graph)
    payload["weight_codec_version"] = 99
    with pytest.raises(GraphError, match="codec version"):
        restore_graph_checkpoint(payload, kernel_limits=KernelLimits())


def test_weight_codec_rejects_non_finite_live_weights():
    from symbiont.cognition.checkpoint import quantize_weight

    with pytest.raises(ValueError, match="finite"):
        quantize_weight(float("nan"))


# --- SafetyState checkpoint ---

from symbiont.cognition.checkpoint import export_safety_state, restore_safety_state  # noqa: E402
from symbiont.cognition.metaplasticity import SafetyState  # noqa: E402


def test_safety_state_none_round_trips_to_a_fresh_state():
    restored = restore_safety_state(None)
    assert restored.consecutive_failures == 0
    assert not restored.frozen


def test_frozen_safety_state_survives_round_trip():
    state = SafetyState()
    for _ in range(3):
        state.record_failure()
    assert state.frozen

    payload = export_safety_state(state)
    restored = restore_safety_state(payload)

    assert restored.frozen  # a restart must not silently un-freeze a legitimately frozen network
    assert restored.consecutive_failures == 3


# --- SensoryNormalizer checkpoint ---

from symbiont.cognition.activation import SensoryNormalizer  # noqa: E402
from symbiont.cognition.checkpoint import (  # noqa: E402
    export_sensory_normalizers,
    restore_sensory_normalizers,
)


def test_unestablished_normalizer_is_not_exported():
    normalizers = {"s": SensoryNormalizer()}
    normalizers["s"].normalize(1.0)  # only 1 sample, not established
    payload = export_sensory_normalizers(normalizers)
    assert "s" not in payload


def test_established_normalizer_round_trips():
    normalizer = SensoryNormalizer()
    for value in [1.0, 2.0, 3.0, 4.0, 5.0]:
        normalizer.normalize(value)
    payload = export_sensory_normalizers({"s": normalizer})
    restored = restore_sensory_normalizers(payload)
    assert restored["s"].mean == pytest.approx(normalizer.mean)
    assert restored["s"].variance == pytest.approx(normalizer.variance)
    assert restored["s"].count == normalizer.count


def test_tentative_weight_does_not_collapse_to_zero_in_codec_v3():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()),
        edges=(_edge(weight=0.05, eligibility=0.0),),
        kernel_limits=KernelLimits(),
    )

    payload = export_graph_checkpoint(graph)
    restored = restore_graph_checkpoint(payload, kernel_limits=KernelLimits())

    assert payload["weight_codec_version"] == 3
    assert payload["edges"][0]["weight_class"] != 8
    assert restored.edges[0].weight != 0.0
    assert restored.edges[0].weight == pytest.approx(0.05, abs=0.02)


def test_codec_v2_checkpoint_restores_with_legacy_linear_weight_mapping():
    graph = CognitiveGraph(
        nodes=(_sense(), _concept()),
        edges=(_edge(weight=0.75),),
        kernel_limits=KernelLimits(),
    )
    payload = export_graph_checkpoint(graph)
    payload["weight_codec_version"] = 2
    payload["edges"][0]["weight_class"] = 11

    restored = restore_graph_checkpoint(payload, kernel_limits=KernelLimits())

    assert restored.edges[0].weight == pytest.approx(0.75)
