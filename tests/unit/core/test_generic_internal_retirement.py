from __future__ import annotations

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
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
        mutation.payload["node_id"] for mutation in mutations if mutation.kind == "remove_node"
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


def test_active_action_readout_is_not_reclaimed_as_orphan():
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(
                node_id="readout_primitive:primitive.keep",
                kind=NodeKind.READOUT,
            ),
            PlasticNode(
                node_id="readout_primitive:primitive.drop",
                kind=NodeKind.READOUT,
            ),
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
    bridge._orphan_since_tick["readout_primitive:primitive.keep"] = 0
    bridge._orphan_since_tick["readout_primitive:primitive.drop"] = 0

    mutations = bridge._orphan_node_mutations(
        tick=grace + 1,
        max_mutations=2,
        protected_node_ids=("readout_primitive:primitive.keep",),
    )

    removed = {
        mutation.payload["node_id"] for mutation in mutations if mutation.kind == "remove_node"
    }
    assert "readout_primitive:primitive.keep" not in removed
    assert "readout_primitive:primitive.drop" in removed
