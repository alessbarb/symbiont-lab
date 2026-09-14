from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont.cognition.checkpoint import (
    export_graph_checkpoint,
    restore_graph_checkpoint,
    restore_safety_state,
)
from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, apply_mutations, validate_mutation
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge
from symbiont.core.evidence import EvidenceRevisionLedger
from symbiont.core.runtime import OrganismRuntime
from symbiont.host.checkpoint import CheckpointError

ROOT = Path(__file__).resolve().parents[2]


def _genome():
    payload = json.loads((ROOT / "examples" / "cognition" / "genome.json").read_text(encoding="utf-8"))
    return GenomeCodec().load(payload)


def _edge(source: str, target: str, *, plasticity: float = 0.5, delay_ticks: int = 1) -> PlasticEdge:
    return PlasticEdge(
        source_id=source,
        target_id=target,
        kind=EdgeKind.EXCITATORY,
        weight=0.2,
        plasticity=plasticity,
        delay_ticks=delay_ticks,
    )


def test_graph_rejects_non_finite_bias_at_construction() -> None:
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(PlasticNode("bad", NodeKind.CONCEPT, bias=float("nan")),),
            edges=(),
            kernel_limits=KernelLimits(),
        )


def test_structural_validation_rejects_an_incoming_edge_to_sense() -> None:
    graph = CognitiveGraph(
        nodes=(PlasticNode("concept", NodeKind.CONCEPT), PlasticNode("sense", NodeKind.SENSE)),
        edges=(),
        kernel_limits=KernelLimits(),
    )
    mutation = Mutation(
        kind="add_edge",
        payload={
            "source_id": "concept",
            "target_id": "sense",
            "kind": EdgeKind.EXCITATORY,
            "weight": 0.05,
            "plasticity": 0.5,
            "delay_ticks": 1,
        },
    )
    result = validate_mutation(mutation, graph, KernelLimits())
    assert not result.accepted


def test_structural_batch_over_kernel_mutation_cap_is_atomic_noop() -> None:
    limits = KernelLimits(max_structural_mutations_per_consolidation=1)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("s", NodeKind.SENSE),
            PlasticNode("a", NodeKind.CONCEPT),
            PlasticNode("b", NodeKind.CONCEPT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    mutations = tuple(
        Mutation(
            kind="add_edge",
            payload={
                "source_id": "s",
                "target_id": target,
                "kind": EdgeKind.EXCITATORY,
                "weight": 0.05,
                "plasticity": 0.5,
                "delay_ticks": 1,
            },
        )
        for target in ("a", "b")
    )
    result = apply_mutations(graph, mutations, limits)
    assert result is graph
    assert graph.edges == ()


def test_checkpoint_rejects_negative_edge_lifecycle_metadata() -> None:
    graph = CognitiveGraph(
        nodes=(PlasticNode("s", NodeKind.SENSE), PlasticNode("c", NodeKind.CONCEPT)),
        edges=(_edge("s", "c"),),
        kernel_limits=KernelLimits(),
    )
    payload = export_graph_checkpoint(graph)
    assert payload is not None
    payload["edges"][0]["support"] = -1
    with pytest.raises(GraphError):
        restore_graph_checkpoint(payload, kernel_limits=KernelLimits())


def test_checkpoint_rejects_truthy_string_as_safety_boolean() -> None:
    with pytest.raises(GraphError):
        restore_safety_state({"consecutive_failures": 0, "frozen": "false"})


def test_bridge_learning_requires_attention_reachability() -> None:
    edge = _edge("s", "c", plasticity=1.0, delay_ticks=0)
    graph = CognitiveGraph(
        nodes=(PlasticNode("s", NodeKind.SENSE), PlasticNode("c", NodeKind.CONCEPT)),
        edges=(edge,),
        kernel_limits=KernelLimits(),
    )
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits())
    before = edge.weight
    bridge.tick({"s": 1.0}, tick=1, attended_sense_ids=set(), sense_modulation={})
    assert edge.weight == pytest.approx(before)


def test_bridge_learning_is_scaled_by_edge_plasticity() -> None:
    edge = _edge("s", "c", plasticity=0.0, delay_ticks=0)
    graph = CognitiveGraph(
        nodes=(PlasticNode("s", NodeKind.SENSE), PlasticNode("c", NodeKind.CONCEPT)),
        edges=(edge,),
        kernel_limits=KernelLimits(),
    )
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits())
    before = edge.weight
    bridge.tick(
        {"s": 1.0},
        tick=1,
        attended_sense_ids={"s"},
        sense_modulation={"s": 1.0},
    )
    assert edge.weight == pytest.approx(before)


def test_bridge_topology_revision_survives_checkpoint_roundtrip() -> None:
    graph = CognitiveGraph(
        nodes=(PlasticNode("s", NodeKind.SENSE), PlasticNode("c", NodeKind.CONCEPT)),
        edges=(_edge("s", "c"),),
        kernel_limits=KernelLimits(),
    )
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())
    bridge._topology_revision = 7
    restored = CognitiveBridge.restore(bridge.export_checkpoint(), genome=genome, kernel_limits=KernelLimits())
    assert restored is not None
    assert restored.topology_revision == 7


def test_dissent_aggregate_memory_survives_checkpoint_without_numeric_evidence() -> None:
    ledger = EvidenceRevisionLedger()
    ledger._conflict_counts["sense-a"] = 3
    payload = ledger.export_checkpoint()
    assert payload == {"conflict_counts": [{"capability_id": "sense-a", "count": 3}]}
    restored = EvidenceRevisionLedger.restore_checkpoint(payload, allowed_capability_ids={"sense-a"})
    assert restored.conflict_counts == {"sense-a": 3}
    assert restored.dissent_history == ()


def test_kernel_checkpoint_size_limit_is_enforced_before_write(tmp_path: Path) -> None:
    runtime = OrganismRuntime(
        investigate_ticks=0,
        kernel_limits=KernelLimits(max_plastic_checkpoint_bytes=1),
    )
    state_file = tmp_path / "state.json"
    with pytest.raises(CheckpointError):
        runtime.save(state_file)
    assert not state_file.exists()
