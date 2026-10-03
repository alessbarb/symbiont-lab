from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition.structural_candidates import StructuralContention


def _graph(limits: KernelLimits) -> CognitiveGraph:
    return CognitiveGraph(
        nodes=(PlasticNode("sense_a", NodeKind.SENSE),),
        edges=(),
        kernel_limits=limits,
    )


def test_structural_contention_backpressures_one_nominee_per_producer() -> None:
    limits = KernelLimits()
    contention = StructuralContention(kernel_limits=limits, identity="organism-a")

    assert contention.register(
        candidate_id="concept:a",
        family="concept",
        mutations=(
            Mutation(
                kind="add_node",
                payload={"node_id": "concept_a", "kind": NodeKind.CONCEPT},
            ),
        ),
        eligible_tick=1,
    )
    assert not contention.register(
        candidate_id="concept:b",
        family="concept",
        mutations=(
            Mutation(
                kind="add_node",
                payload={"node_id": "concept_b", "kind": NodeKind.CONCEPT},
            ),
        ),
        eligible_tick=1,
    )


def test_structural_contention_selects_without_committing_graph() -> None:
    limits = KernelLimits()
    graph = _graph(limits)
    contention = StructuralContention(kernel_limits=limits, identity="organism-a")
    mutation = Mutation(
        kind="add_node",
        payload={"node_id": "readout_motor:x", "kind": NodeKind.READOUT},
    )
    contention.register(
        candidate_id="motor:x",
        family="motor_readout",
        mutations=(mutation,),
        eligible_tick=1,
    )

    winner_id, mutations, losers = contention.select(
        graph=graph,
        mutation_slots=4,
        node_slots=4,
        edge_slots=4,
        frozen=False,
    )

    assert winner_id == "motor:x"
    assert mutations == (mutation,)
    assert losers == ()
    assert graph.node_by_id("readout_motor:x") is None
