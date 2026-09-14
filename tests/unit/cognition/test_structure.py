from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, StructuralPlasticity, ValidationResult, apply_mutations, validate_mutation
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def test_no_proposal_before_minimum_support_reached():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=5, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(4):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=4)
    assert mutations == ()


def test_proposal_fires_once_minimum_support_reached():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(mutations) == 1
    assert mutations[0].kind == "add_edge"
    assert mutations[0].payload["source_id"] == "a"
    assert mutations[0].payload["target_id"] == "b"


def test_no_coactivation_never_reaches_support():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(10):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=False, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=10)
    assert mutations == ()


def test_already_connected_pair_is_never_reproposed():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.types import EdgeKind

    existing = PlasticEdge(source_id="a", target_id="b", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0)
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(existing,), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(5):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=5)
    assert mutations == ()


def test_proposal_withheld_when_kernel_edge_budget_exhausted():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.types import EdgeKind

    filler = PlasticEdge(
        source_id="a", target_id="filler", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b"), _concept("filler")),
        edges=(filler,),
        kernel_limits=KernelLimits(max_edges=1),
    )
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(max_edges=1), tick=3)
    assert mutations == ()


def test_pair_on_cooldown_after_a_proposal_is_not_reproposed_immediately():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b"), _concept("c")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    first = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(first) == 1

    for tick in range(3, 6):
        plasticity.observe_coactivation(source_id="a", target_id="c", source_active=True, target_active=True, tick=tick)
    second = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=6)
    assert second == ()


# --- validate_mutation / apply_mutations ---


def _add_edge_mutation(source: str, target: str) -> Mutation:
    return Mutation(
        kind="add_edge",
        payload={
            "source_id": source,
            "target_id": target,
            "kind": EdgeKind.EXCITATORY,
            "weight": 0.05,
            "plasticity": 0.5,
            "delay_ticks": 1,
        },
    )


def test_validate_mutation_accepts_a_sound_add_edge():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_add_edge_mutation("a", "b"), graph, KernelLimits())
    assert result == ValidationResult(accepted=True)


def test_validate_mutation_rejects_when_edge_budget_full():
    filler = PlasticEdge(
        source_id="a", target_id="filler", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b"), _concept("filler")),
        edges=(filler,),
        kernel_limits=KernelLimits(max_edges=1),
    )
    result = validate_mutation(_add_edge_mutation("a", "b"), graph, KernelLimits(max_edges=1))
    assert not result.accepted
    assert result.reason is not None


def test_validate_mutation_rejects_dangling_endpoint():
    graph = CognitiveGraph(nodes=(_sense("a"),), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_add_edge_mutation("a", "ghost"), graph, KernelLimits())
    assert not result.accepted


def test_apply_mutations_produces_a_new_graph_containing_the_edge():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "b"),), KernelLimits())
    assert len(new_graph.edges) == 1
    assert new_graph.edges[0].source_id == "a"
    assert new_graph.edges[0].target_id == "b"
    assert len(graph.edges) == 0


def test_apply_mutations_silently_skips_a_rejected_mutation():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "ghost"),), KernelLimits())
    assert len(new_graph.edges) == 0
    assert len(new_graph.nodes) == 2
