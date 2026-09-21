from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, apply_mutations
from symbiont.cognition.types import NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge

from tests.unit.core.test_actuation_cognition_p1 import _genome


def _bridge() -> CognitiveBridge:
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="readout_core", kind=NodeKind.READOUT),),
        edges=(),
        kernel_limits=KernelLimits(),
    )
    return CognitiveBridge(
        graph=graph,
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )


def _candidate_mutation(node_id: str) -> tuple[Mutation, ...]:
    return (
        Mutation(
            kind="add_node",
            payload={"node_id": node_id, "kind": NodeKind.READOUT},
        ),
    )


def _select(
    bridge: CognitiveBridge,
    *,
    motor_ids: tuple[str, ...] = (),
    primitive_ids: tuple[str, ...] = (),
    node_slots: int = 8,
):
    return bridge._select_structural_candidate(
        graph=bridge.graph,
        mutation_slots=8,
        node_slots=node_slots,
        edge_slots=8,
        active_motor_ids=motor_ids,
        active_primitive_ids=primitive_ids,
    )


def test_one_outstanding_nominee_per_producer_backpressures_multiplicity():
    bridge = _bridge()

    assert bridge._register_structural_candidate(
        candidate_id="a:1",
        family="experimental",
        producer_id="producer.a",
        mutations=_candidate_mutation("readout_a1"),
        eligible_tick=1,
    )
    assert not bridge._register_structural_candidate(
        candidate_id="a:2",
        family="experimental",
        producer_id="producer.a",
        mutations=_candidate_mutation("readout_a2"),
        eligible_tick=1,
    )

    assert tuple(bridge._structural_candidates) == ("a:1",)
    assert bridge._structural_candidates["a:1"].producer_id == "producer.a"


def test_producer_round_robin_gives_bounded_access_without_debt():
    bridge = _bridge()
    assert bridge._register_structural_candidate(
        candidate_id="a:1",
        family="experimental",
        producer_id="producer.a",
        mutations=_candidate_mutation("readout_a1"),
        eligible_tick=1,
    )
    assert bridge._register_structural_candidate(
        candidate_id="b:1",
        family="experimental",
        producer_id="producer.b",
        mutations=_candidate_mutation("readout_b1"),
        eligible_tick=1,
    )

    winner1, mutations1, losers1 = _select(bridge)
    assert winner1 in {"a:1", "b:1"}
    assert losers1 == ()

    winner1_candidate = bridge._structural_candidates[winner1]
    first_producer = winner1_candidate.producer_id
    updated = apply_mutations(bridge.graph, mutations1, KernelLimits(), frozen=False)
    assert updated is not bridge.graph
    bridge._graph = updated
    bridge._commit_contention_result(winner_id=winner1, loser_ids=losers1)

    other_id = "b:1" if winner1 == "a:1" else "a:1"
    other_producer = bridge._structural_candidates[other_id].producer_id

    assert bridge._register_structural_candidate(
        candidate_id=f"{first_producer}:2",
        family="experimental",
        producer_id=first_producer,
        mutations=_candidate_mutation(f"readout_{first_producer}_2"),
        eligible_tick=2,
    )

    winner2, _, losers2 = _select(bridge)
    assert losers2 == ()
    assert bridge._structural_candidates[winner2].producer_id == other_producer


def test_candidate_multiplicity_cannot_create_global_voting_power():
    bridge = _bridge()

    assert bridge._register_structural_candidate(
        candidate_id="flood:0",
        family="experimental",
        producer_id="producer.flood",
        mutations=_candidate_mutation("readout_flood_0"),
        eligible_tick=1,
    )
    for index in range(1, 1000):
        assert not bridge._register_structural_candidate(
            candidate_id=f"flood:{index}",
            family="experimental",
            producer_id="producer.flood",
            mutations=_candidate_mutation(f"readout_flood_{index}"),
            eligible_tick=1,
        )

    assert bridge._register_structural_candidate(
        candidate_id="rare:0",
        family="experimental",
        producer_id="producer.rare",
        mutations=_candidate_mutation("readout_rare_0"),
        eligible_tick=1,
    )

    assert len(bridge._structural_candidates) == 2
    assert {
        candidate.producer_id for candidate in bridge._structural_candidates.values()
    } == {"producer.flood", "producer.rare"}


def test_atomic_multi_node_structural_proposal_is_supported():
    bridge = _bridge()
    mutations = (
        Mutation(
            kind="add_node",
            payload={"node_id": "concept_x", "kind": NodeKind.CONCEPT},
        ),
        Mutation(
            kind="add_node",
            payload={"node_id": "readout_x", "kind": NodeKind.READOUT},
        ),
    )
    assert bridge._register_structural_candidate(
        candidate_id="atomic:x",
        family="experimental",
        producer_id="producer.atomic",
        mutations=mutations,
        eligible_tick=1,
    )

    winner, selected, _ = _select(bridge, node_slots=2)
    assert winner == "atomic:x"
    assert selected == mutations

    blocked_winner, blocked, _ = bridge._select_structural_candidate(
        graph=bridge.graph,
        mutation_slots=8,
        node_slots=1,
        edge_slots=8,
        active_motor_ids=(),
        active_primitive_ids=(),
    )
    assert blocked_winner is None
    assert blocked == ()


def test_structural_producer_state_survives_checkpoint():
    bridge = _bridge()
    bridge._register_structural_candidate(
        candidate_id="primitive:b",
        family="primitive_readout",
        mutations=_candidate_mutation("readout_primitive:b"),
        eligible_tick=7,
    )
    producer_id = bridge._structural_candidates["primitive:b"].producer_id
    bridge._last_consolidated_producer_id = producer_id
    bridge._consolidation_generation = 11

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
    )

    assert restored is not None
    candidate = restored._structural_candidates["primitive:b"]
    assert candidate.eligible_tick == 7
    assert candidate.producer_id == producer_id
    assert candidate.contention_losses == 0
    assert restored._last_consolidated_producer_id == producer_id
    assert restored._consolidation_generation == 11


def test_primitive_producer_admits_one_nominee_per_round():
    bridge = _bridge()

    bridge.tick({}, tick=1, active_primitive_ids=("a", "b"))
    primitive_nodes = {
        node.node_id
        for node in bridge.graph.nodes
        if node.node_id.startswith("readout_primitive:")
    }
    assert len(primitive_nodes) == 1

    bridge.tick({}, tick=2, active_primitive_ids=("a", "b"))
    primitive_nodes = {
        node.node_id
        for node in bridge.graph.nodes
        if node.node_id.startswith("readout_primitive:")
    }
    assert primitive_nodes == {
        "readout_primitive:a",
        "readout_primitive:b",
    }
