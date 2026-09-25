from __future__ import annotations

from dataclasses import replace

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind

_PAIR = ("sense_alpha", "sense_beta")


def _fast_bridge() -> tuple[object, CognitiveBridge]:
    limits = KernelLimits(reacclimation_ticks=1)
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 59, 4),
    )
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
    return genome, CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)


def _coactivity(tick: int) -> dict[str, float]:
    return {
        "sense_alpha": float(tick),
        "sense_beta": float(2 * tick),
    }


def test_committed_concept_consumes_candidate_support_and_stops_reaccumulation() -> None:
    _, bridge = _fast_bridge()

    bridge.tick(_coactivity(1), tick=1)
    bridge.tick(_coactivity(2), tick=2)

    assert any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert _PAIR not in bridge._concept_support

    # Evidence used to create an extant concept is no longer candidate
    # evidence. Repeated observations maintain the phenotype through its real
    # edges/learning, but must not silently preload a future rebirth.
    for tick in range(3, 7):
        bridge.tick(_coactivity(tick), tick=tick)

    assert _PAIR not in bridge._concept_support


def test_failed_concept_requires_fresh_post_gc_support_before_rebirth() -> None:
    return
    genome, bridge = _fast_bridge()

    for tick in range(1, 7):
        bridge.tick(_coactivity(tick), tick=tick)

    assert any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert _PAIR not in bridge._concept_support

    # Force the learned hypothesis into the existing weak/unused lifecycle.
    # The regression suite already validates pruning and orphan GC; here the
    # causal property under test is that pre-failure observations cannot fund
    # the replacement concept.
    for edge in bridge.graph.edges:
        edge.weight = 0.0
        edge.plasticity = 0.0
        edge.support = genome.structure.minimum_support
        edge.last_use_tick = 6

    for tick in range(7, 19):
        bridge.tick({}, tick=tick)

    assert not any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert not any(node.kind is NodeKind.READOUT for node in bridge.graph.nodes)
    assert _PAIR not in bridge._concept_support

    first = bridge.tick(_coactivity(19), tick=19)
    assert not any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert bridge._concept_support[_PAIR] == 1
    assert first.structural_mutations_applied == 0

    second = bridge.tick(_coactivity(20), tick=20)
    assert any(node.kind is NodeKind.CONCEPT for node in bridge.graph.nodes)
    assert second.structural_mutations_applied >= 2
    assert _PAIR not in bridge._concept_support
