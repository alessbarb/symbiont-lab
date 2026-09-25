from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge, TopologyHealth


def _base(*, reacclimation_ticks: int = 32):
    limits = KernelLimits(reacclimation_ticks=reacclimation_ticks)
    genome, _ = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 16))
    return limits, genome


def _path_graph(*, support: int, limits: KernelLimits) -> CognitiveGraph:
    return CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
            PlasticNode("readout_core", NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(
                source_id="sense_a",
                target_id="concept_a",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
                support=support,
            ),
            PlasticEdge(
                source_id="concept_a",
                target_id="readout_core",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=1,
                support=support,
            ),
        ),
        kernel_limits=limits,
    )


def test_topology_health_distinguishes_germinal_connected_and_adaptive() -> None:
    limits, genome = _base()
    empty = CognitiveGraph(nodes=(), edges=(), kernel_limits=limits)
    assert CognitiveBridge(graph=empty, genome=genome, kernel_limits=limits).topology_health is TopologyHealth.GERMINAL

    connected = CognitiveBridge(
        graph=_path_graph(support=0, limits=limits),
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    assert connected.topology_health is TopologyHealth.CONNECTED

    adaptive = CognitiveBridge(
        graph=_path_graph(support=genome.structure.minimum_support, limits=limits),
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    assert adaptive.topology_health is TopologyHealth.ADAPTIVE


def test_maintenance_planning_sees_orphan_created_by_same_tick_prune() -> None:
    limits, genome = _base()
    genome = replace(
        genome,
        development=replace(genome.development, consolidation_interval_ticks=1),
        structure=replace(genome.structure, tentative_lifetime_ticks=2),
    )
    edge = PlasticEdge(
        source_id="sense_a",
        target_id="concept_a",
        kind=EdgeKind.EXCITATORY,
        weight=0.05,
        plasticity=0.5,
        delay_ticks=0,
        support=0,
        age_ticks=2,
    )
    graph = CognitiveGraph(
        nodes=(PlasticNode("sense_a", NodeKind.SENSE), PlasticNode("concept_a", NodeKind.CONCEPT)),
        edges=(edge,),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    result = bridge.tick({"sense_a": 1.0}, tick=1)

    assert any(mutation.kind == "remove_edge" for mutation in result.mutations)
    assert bridge.graph.edges == ()
    assert bridge.export_checkpoint()["orphan_since_tick"]["concept_a"] == 1


def _worker3_graph(limits: KernelLimits) -> CognitiveGraph:
    senses = tuple(PlasticNode(f"sense_{index:02d}", NodeKind.SENSE) for index in range(58))
    concepts = tuple(PlasticNode(f"concept_{index:02d}", NodeKind.CONCEPT) for index in range(5))
    readout = (PlasticNode("readout_core", NodeKind.READOUT),)
    return CognitiveGraph(nodes=senses + concepts + readout, edges=(), kernel_limits=limits)


def _legacy_worker3_payload(*, limits: KernelLimits, genome) -> dict[str, object]:
    source = CognitiveBridge(
        graph=_worker3_graph(limits),
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    payload = source.export_checkpoint()
    payload["topology_revision"] = 29
    for field in ("concept_lineage", "sense_last_seen_tick", "orphan_since_tick", "recovery_pending"):
        payload.pop(field, None)
    return payload


def test_restore_detects_exact_worker3_deadlock_and_enters_recovery() -> None:
    limits, genome = _base(reacclimation_ticks=1)
    restored = CognitiveBridge.restore(
        _legacy_worker3_payload(limits=limits, genome=genome),
        genome=genome,
        kernel_limits=limits,
    )

    assert restored is not None
    assert len(restored.graph.nodes) == 64
    assert restored.graph.edges == ()
    assert restored.recovery_pending is True
    assert restored.topology_health is TopologyHealth.RECOVERING
    assert restored.topology_revision == 29


def test_worker3_deadlock_releases_orphans_and_excess_senses_without_fabricating_edges() -> None:
    limits, genome = _base(reacclimation_ticks=1)
    restored = CognitiveBridge.restore(
        _legacy_worker3_payload(limits=limits, genome=genome),
        genome=genome,
        kernel_limits=limits,
    )
    assert restored is not None

    # Recovery releases the legacy deadlock graph without fabricating new
    # senses or edges. New sensory structure must be earned from observations.
    for tick in (1088, 1120, 1152, 1184):
        restored.tick({}, tick=tick)

    senses = [node for node in restored.graph.nodes if node.kind is NodeKind.SENSE]
    assert senses == []
    assert restored.graph.nodes == ()
    assert restored.graph.edges == ()
    assert restored.recovery_pending is False
    assert restored.topology_health is TopologyHealth.GERMINAL
    assert restored.topology_revision == 33


def test_owner_authored_degenerate_shape_is_not_automatically_recovered() -> None:
    limits, genome = _base(reacclimation_ticks=1)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("owner_concept", NodeKind.CONCEPT),
            PlasticNode("owner_readout", NodeKind.READOUT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    assert bridge.develop_senses is False

    for tick in (32, 64, 96, 128):
        bridge.tick({}, tick=tick)

    assert bridge.recovery_pending is False
    assert bridge.topology_health is TopologyHealth.DEVELOPING
    assert {node.node_id for node in bridge.graph.nodes} == {"owner_concept", "owner_readout"}
