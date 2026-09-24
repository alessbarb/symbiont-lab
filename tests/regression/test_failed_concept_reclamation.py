from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge, TopologyHealth


def test_failed_concept_bundle_is_pruned_then_garbage_collected() -> None:
    limits = KernelLimits(reacclimation_ticks=1)
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 59, 4))
    genome = replace(
        genome,
        development=replace(genome.development, consolidation_interval_ticks=2),
        structure=replace(
            genome.structure,
            minimum_support=2,
            grow_threshold=0.0,
            tentative_lifetime_ticks=4,
        ),
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    for tick in range(1, 7):
        bridge.tick(
            {"sense_alpha": float(tick), "sense_beta": float(2 * tick)},
            tick=tick,
        )

    assert any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert any(node.kind is NodeKind.READOUT for node in bridge.graph.nodes)
    assert len(bridge.graph.edges) >= 3

    # Model a genuinely failed hypothesis: make every incident edge weak and
    # stop plastic updates from rebuilding it while the source signals vanish.
    for edge in bridge.graph.edges:
        edge.weight = 0.0
        edge.plasticity = 0.0
        edge.support = genome.structure.minimum_support
        edge.last_use_tick = 6
    bridge._concept_last_active_tick.clear()

    for tick in range(7, 19):
        bridge.tick({}, tick=tick)

    assert bridge.graph.edges == ()
    assert not any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert not any(node.kind is NodeKind.READOUT for node in bridge.graph.nodes)
    assert bridge.concept_lineage == ()
    assert bridge.topology_health is TopologyHealth.GERMINAL
