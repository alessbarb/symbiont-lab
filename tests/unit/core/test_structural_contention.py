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


def test_contention_uses_access_debt_not_candidate_family():
    bridge = _bridge()
    bridge._register_structural_candidate(
        candidate_id="motor:a",
        family="motor_readout",
        mutations=_candidate_mutation("readout_motor:a"),
        eligible_tick=1,
    )
    bridge._register_structural_candidate(
        candidate_id="primitive:b",
        family="primitive_readout",
        mutations=_candidate_mutation("readout_primitive:b"),
        eligible_tick=1,
    )
    bridge._structural_candidates["primitive:b"].contention_losses = 2

    winner, mutations, losers = bridge._select_structural_candidate(
        graph=bridge.graph,
        mutation_slots=8,
        node_slots=8,
        edge_slots=8,
        active_motor_ids=("a",),
        active_primitive_ids=("b",),
    )

    assert winner == "primitive:b"
    assert mutations == _candidate_mutation("readout_primitive:b")
    assert losers == ("motor:a",)


def test_contention_state_changes_only_after_successful_commit():
    bridge = _bridge()
    bridge._register_structural_candidate(
        candidate_id="motor:a",
        family="motor_readout",
        mutations=_candidate_mutation("readout_motor:a"),
        eligible_tick=1,
    )
    bridge._register_structural_candidate(
        candidate_id="primitive:b",
        family="primitive_readout",
        mutations=_candidate_mutation("readout_primitive:b"),
        eligible_tick=1,
    )

    winner, mutations, losers = bridge._select_structural_candidate(
        graph=bridge.graph,
        mutation_slots=8,
        node_slots=8,
        edge_slots=8,
        active_motor_ids=("a",),
        active_primitive_ids=("b",),
    )

    assert winner is not None
    assert all(
        candidate.contention_losses == 0
        for candidate in bridge._structural_candidates.values()
    )
    assert winner in bridge._structural_candidates

    updated = apply_mutations(
        bridge.graph,
        mutations,
        KernelLimits(),
        frozen=False,
    )
    assert updated is not bridge.graph
    bridge._graph = updated
    bridge._commit_contention_result(
        winner_id=winner,
        loser_ids=losers,
    )

    assert winner not in bridge._structural_candidates
    assert len(losers) == 1
    assert bridge._structural_candidates[losers[0]].contention_losses == 1


def test_contention_tie_break_is_deterministic_and_order_independent():
    left = _bridge()
    right = _bridge()
    registrations = (
        ("motor:a", "motor_readout", "readout_motor:a"),
        ("primitive:b", "primitive_readout", "readout_primitive:b"),
    )
    for candidate_id, family, node_id in registrations:
        left._register_structural_candidate(
            candidate_id=candidate_id,
            family=family,
            mutations=_candidate_mutation(node_id),
            eligible_tick=1,
        )
    for candidate_id, family, node_id in reversed(registrations):
        right._register_structural_candidate(
            candidate_id=candidate_id,
            family=family,
            mutations=_candidate_mutation(node_id),
            eligible_tick=1,
        )

    left_result = left._select_structural_candidate(
        graph=left.graph,
        mutation_slots=8,
        node_slots=8,
        edge_slots=8,
        active_motor_ids=("a",),
        active_primitive_ids=("b",),
    )
    right_result = right._select_structural_candidate(
        graph=right.graph,
        mutation_slots=8,
        node_slots=8,
        edge_slots=8,
        active_motor_ids=("a",),
        active_primitive_ids=("b",),
    )
    assert left_result[0] == right_result[0]


def test_structural_candidate_registry_survives_checkpoint():
    bridge = _bridge()
    bridge._register_structural_candidate(
        candidate_id="primitive:b",
        family="primitive_readout",
        mutations=_candidate_mutation("readout_primitive:b"),
        eligible_tick=7,
    )
    bridge._structural_candidates["primitive:b"].contention_losses = 3
    bridge._consolidation_generation = 11

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
    )

    assert restored is not None
    candidate = restored._structural_candidates["primitive:b"]
    assert candidate.eligible_tick == 7
    assert candidate.contention_losses == 3
    assert restored._consolidation_generation == 11


def test_one_node_admission_per_consolidation_round():
    bridge = _bridge()

    bridge.tick(
        {},
        tick=1,
        active_primitive_ids=("a", "b"),
    )
    primitive_nodes = {
        node.node_id
        for node in bridge.graph.nodes
        if node.node_id.startswith("readout_primitive:")
    }
    assert len(primitive_nodes) == 1

    bridge.tick(
        {},
        tick=2,
        active_primitive_ids=("a", "b"),
    )
    primitive_nodes = {
        node.node_id
        for node in bridge.graph.nodes
        if node.node_id.startswith("readout_primitive:")
    }
    assert primitive_nodes == {
        "readout_primitive:a",
        "readout_primitive:b",
    }
