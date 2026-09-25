from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge, TopologyHealth


def _fast_germinal(
    *,
    sense_budget: int = 8,
    lifetime_ticks: int = 8,
    minimum_support: int = 2,
    grow_threshold: float = 0.0,
) -> tuple[KernelLimits, object, CognitiveBridge]:
    limits = KernelLimits(reacclimation_ticks=1)
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 16))
    genome = replace(
        genome,
        development=replace(
            genome.development,
            consolidation_interval_ticks=2,
            sense_node_budget=sense_budget,
        ),
        structure=replace(
            genome.structure,
            minimum_support=minimum_support,
            growth_threshold=replace(
                genome.structure.growth_threshold,
                baseline=grow_threshold,
                minimum=0.0,
                maximum=1.0,
            ),
            tentative_lifetime_ticks=lifetime_ticks,
        ),
    )
    return limits, genome, CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)


def _assert_viable(bridge: CognitiveBridge) -> None:
    sense_count = sum(1 for node in bridge.graph.nodes if node.kind is NodeKind.SENSE)
    assert len(bridge.graph.nodes) <= bridge._soft_node_limit
    assert len(bridge.graph.edges) <= bridge._soft_edge_limit
    assert sense_count <= bridge._sense_node_limit
    assert bridge.topology_health is not TopologyHealth.DEGENERATE
    assert not (bridge.recovery_pending and bridge.topology_health is not TopologyHealth.RECOVERING)


def test_germinal_graph_remains_viable_for_2000_ticks_across_checkpoint_restart() -> None:
    limits, genome, bridge = _fast_germinal(lifetime_ticks=8)

    for tick in range(1, 1001):
        bridge.tick(
            {"sense_alpha": float(tick), "sense_beta": float(2 * tick)},
            tick=tick,
        )
        if tick % 100 == 0:
            _assert_viable(bridge)

    assert bridge._has_sense_to_readout_path()
    checkpoint = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(checkpoint, genome=genome, kernel_limits=limits)
    assert restored is not None

    for tick in range(1001, 2001):
        restored.tick(
            {"sense_alpha": float(tick), "sense_beta": float(2 * tick)},
            tick=tick,
        )
        if tick % 100 == 0:
            _assert_viable(restored)

    assert restored._has_sense_to_readout_path()
    assert restored.topology_health in (TopologyHealth.CONNECTED, TopologyHealth.ADAPTIVE)
    assert not restored._orphan_latent_ids()


def test_sensory_turnover_reclaims_stale_disconnected_senses_and_admits_new_ones() -> None:
    _, _, bridge = _fast_germinal(
        sense_budget=4,
        lifetime_ticks=4,
        grow_threshold=1.0,  # normalized SENSE activation cannot reach 1.0
    )
    old = {f"old_{index}": float(index + 1) for index in range(4)}
    new = {f"new_{index}": float(index + 11) for index in range(4)}

    for tick in range(1, 5):
        bridge.tick(old, tick=tick)
    assert {node.node_id for node in bridge.graph.nodes} == set(old)

    # Admission is initially full. Once the old leases cross retention, the
    # maintenance pass removes them; the following tick can admit the new set.
    for tick in range(5, 262):
        bridge.tick(new, tick=tick)

    sense_ids = {node.node_id for node in bridge.graph.nodes if node.kind is NodeKind.SENSE}
    assert sense_ids == set(new)
    _assert_viable(bridge)


def _legacy_worker3_payload(*, limits: KernelLimits, genome) -> dict[str, object]:
    senses = tuple(PlasticNode(f"sense_{index:02d}", NodeKind.SENSE) for index in range(58))
    concepts = tuple(PlasticNode(f"concept_{index:02d}", NodeKind.CONCEPT) for index in range(5))
    graph = CognitiveGraph(
        nodes=senses + concepts + (PlasticNode("readout_core", NodeKind.READOUT),),
        edges=(),
        kernel_limits=limits,
    )
    source = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    payload = source.export_checkpoint()
    payload["topology_revision"] = 29
    for field in ("concept_lineage", "sense_last_seen_tick", "orphan_since_tick", "recovery_pending"):
        payload.pop(field, None)
    return payload


def test_exact_worker3_fixture_recovers_then_learns_a_new_connected_topology() -> None:
    limits = KernelLimits(reacclimation_ticks=1)
    genome, _ = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 16))
    genome = replace(
        genome,
        structure=replace(genome.structure, minimum_support=4),
    )
    bridge = CognitiveBridge.restore(
        _legacy_worker3_payload(limits=limits, genome=genome),
        genome=genome,
        kernel_limits=limits,
    )
    assert bridge is not None
    assert bridge.topology_health is TopologyHealth.RECOVERING

    for tick in (1088, 1120, 1152, 1184):
        bridge.tick({}, tick=tick)
    assert bridge.topology_health is TopologyHealth.GERMINAL
    assert bridge.graph.nodes == ()
    assert bridge.graph.edges == ()

    # The recovery never guesses the lost worker-3 wiring. New structure is
    # earned from fresh post-recovery evidence using two retained opaque senses.
    for tick in range(1185, 1249):
        bridge.tick(
            {"sense_56": float(tick), "sense_57": float(2 * tick)},
            tick=tick,
        )

    assert bridge._has_sense_to_readout_path()
    assert bridge.topology_health in (TopologyHealth.CONNECTED, TopologyHealth.ADAPTIVE)
    assert any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert any(node.kind is NodeKind.READOUT for node in bridge.graph.nodes)
    _assert_viable(bridge)


def test_repeated_turnover_without_concepts_never_exhausts_sense_budget() -> None:
    _, _, bridge = _fast_germinal(
        sense_budget=6,
        lifetime_ticks=4,
        grow_threshold=1.0,
    )

    tick = 0
    for generation in range(50):
        names = {f"g{generation:02d}_sense_{index}": float(generation * 10 + index + 1) for index in range(6)}
        for _ in range(6):
            tick += 1
            bridge.tick(names, tick=tick)
        _assert_viable(bridge)

    final_senses = [node for node in bridge.graph.nodes if node.kind is NodeKind.SENSE]
    assert len(final_senses) <= 6
    assert len(bridge.graph.nodes) < bridge._soft_node_limit


def test_owner_authored_graph_is_byte_shape_stable_through_long_runtime() -> None:
    limits, genome, _ = _fast_germinal(lifetime_ticks=4)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("owner_sense", NodeKind.SENSE),
            PlasticNode("owner_concept", NodeKind.CONCEPT),
            PlasticNode("owner_readout", NodeKind.READOUT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    before = tuple((node.node_id, node.kind) for node in bridge.graph.nodes)

    for tick in range(1, 513):
        bridge.tick({}, tick=tick)

    after = tuple((node.node_id, node.kind) for node in bridge.graph.nodes)
    assert bridge.develop_senses is False
    assert before == after
    assert bridge.graph.edges == ()
    assert bridge.recovery_pending is False
