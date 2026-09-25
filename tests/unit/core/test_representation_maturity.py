from __future__ import annotations

from symbiont.core.cognition_bridge import CognitiveBridge, RepresentationMaturity

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from tests.unit.core.test_actuation_cognition_p1 import _genome


def _bridge() -> CognitiveBridge:
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="sense", kind=NodeKind.SENSE),
            PlasticNode(node_id="concept", kind=NodeKind.CONCEPT),
        ),
        edges=(
            PlasticEdge(
                source_id="sense",
                target_id="concept",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=1,
                support=32,
                age_ticks=32,
                stable_ticks=32,
                last_use_tick=32,
            ),
        ),
        kernel_limits=limits,
    )
    return CognitiveBridge(
        graph=graph,
        genome=_genome(),
        kernel_limits=limits,
        develop_senses=True,
    )


def test_internal_representation_must_age_activate_and_integrate_before_growth():
    bridge = _bridge()
    bridge._node_born_tick["concept"] = 10
    bridge._tick = 10
    bridge._node_observation_count["concept"] = 100
    bridge._node_active_count["concept"] = 100

    assert bridge._representation_maturity("concept") is RepresentationMaturity.NASCENT
    assert not bridge._representation_mature_enough_as_target("concept")

    grace = bridge._genome.structure.tentative_lifetime_ticks
    bridge._tick = 10 + grace

    assert bridge._representation_maturity("concept") in {
        RepresentationMaturity.MATURE,
        RepresentationMaturity.STABLE,
    }
    assert bridge._representation_mature_enough_as_target("concept")


def test_sense_is_stable_without_internal_maturation_policy():
    bridge = _bridge()

    assert bridge._representation_maturity("sense") is RepresentationMaturity.STABLE
    assert bridge._representation_mature_enough_as_target("sense")


def test_maturation_evidence_survives_checkpoint_roundtrip():
    bridge = _bridge()
    bridge._node_born_tick["concept"] = 3
    bridge._node_observation_count["concept"] = 19
    bridge._node_active_count["concept"] = 11

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
    )

    assert restored is not None
    assert restored._node_born_tick["concept"] == 3
    assert restored._node_observation_count["concept"] == 19
    assert restored._node_active_count["concept"] == 11


def test_tick_representation_maturity_histogram_matches_direct_classification():
    bridge = _bridge()
    bridge._node_born_tick["concept"] = 0
    bridge._node_observation_count["concept"] = 100
    bridge._node_active_count["concept"] = 100
    bridge._tick = bridge._genome.structure.tentative_lifetime_ticks

    result = bridge.tick(
        {"sense": 0.75},
        tick=bridge._tick + 1,
        attended_sense_ids={"sense"},
        sense_modulation={"sense": 1.0},
        plasticity_enabled=False,
    )

    expected = {
        maturity.value: sum(
            bridge._representation_maturity(node.node_id) is maturity for node in bridge.graph.nodes
        )
        for maturity in RepresentationMaturity
    }
    assert result.representation_maturity == expected
    assert sum(result.representation_maturity.values()) == len(bridge.graph.nodes)
