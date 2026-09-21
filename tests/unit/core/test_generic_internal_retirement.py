from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge

from tests.unit.core.test_actuation_cognition_p1 import _genome


def test_generic_internal_orphans_are_reclaimed_after_grace():
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="state_x", kind=NodeKind.STATE),
            PlasticNode(node_id="gate_x", kind=NodeKind.GATE),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=_genome(),
        kernel_limits=limits,
        develop_senses=True,
    )

    grace = bridge._genome.structure.tentative_lifetime_ticks
    bridge._tick = grace + 1
    bridge._orphan_since_tick["state_x"] = 0
    bridge._orphan_since_tick["gate_x"] = 0

    mutations = bridge._orphan_node_mutations(
        tick=grace + 1,
        max_mutations=2,
    )

    removed = {
        mutation.payload["node_id"]
        for mutation in mutations
        if mutation.kind == "remove_node"
    }
    assert removed == {"gate_x", "state_x"}


def test_reconcile_keeps_generic_internal_orphan_age():
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="state_x", kind=NodeKind.STATE),),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=_genome(),
        kernel_limits=limits,
        develop_senses=True,
    )
    bridge._orphan_since_tick["state_x"] = 7

    bridge._reconcile_node_metadata()

    assert bridge._orphan_since_tick["state_x"] == 7
