from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import (
    Mutation,
    StructuralPlasticity,
    ValidationResult,
    apply_mutations,
    validate_mutation,
)
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def test_no_proposal_before_minimum_support_reached():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=5, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(4):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=4)
    assert mutations == ()


def test_proposal_fires_once_minimum_support_reached():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(3):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(mutations) == 1
    assert mutations[0].kind == "add_edge"
    assert mutations[0].payload["source_id"] == "a"
    assert mutations[0].payload["target_id"] == "b"


def test_no_coactivation_never_reaches_support():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(10):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=False, tick=tick
        )
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=10)
    assert mutations == ()


def test_already_connected_pair_is_never_reproposed():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.types import EdgeKind

    existing = PlasticEdge(
        source_id="a",
        target_id="b",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(existing,), kernel_limits=KernelLimits()
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(5):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=5)
    assert mutations == ()


def test_proposal_withheld_when_kernel_edge_budget_exhausted():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.types import EdgeKind

    filler = PlasticEdge(
        source_id="a",
        target_id="filler",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b"), _concept("filler")),
        edges=(filler,),
        kernel_limits=KernelLimits(max_edges=1),
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(3):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(max_edges=1), tick=3)
    assert mutations == ()


def test_reconcile_drops_coactivation_counts_for_removed_nodes():
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(3):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    plasticity.reconcile({"a"})  # "b" no longer exists
    graph = CognitiveGraph(nodes=(_sense("a"),), edges=(), kernel_limits=KernelLimits())
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert mutations == ()


def test_reconcile_bounds_memory_growth_over_many_distinct_pairs():
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for i in range(1000):
        plasticity.observe_coactivation(
            source_id=f"n{i}", target_id=f"m{i}", source_active=True, target_active=True, tick=0
        )
    plasticity.reconcile({"n0", "m0"})
    assert len(plasticity._coactivation_counts) <= 1
    assert len(plasticity._cooldown_until) <= 2


def test_pair_on_cooldown_after_a_proposal_is_not_reproposed_immediately():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b"), _concept("c")), edges=(), kernel_limits=KernelLimits()
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10
    )
    for tick in range(3):
        plasticity.observe_coactivation(
            source_id="a", target_id="b", source_active=True, target_active=True, tick=tick
        )
    first = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(first) == 1

    for tick in range(3, 6):
        plasticity.observe_coactivation(
            source_id="a", target_id="c", source_active=True, target_active=True, tick=tick
        )
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
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    result = validate_mutation(_add_edge_mutation("a", "b"), graph, KernelLimits())
    assert result == ValidationResult(accepted=True)


def test_validate_mutation_rejects_when_edge_budget_full():
    filler = PlasticEdge(
        source_id="a",
        target_id="filler",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
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
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "b"),), KernelLimits())
    assert len(new_graph.edges) == 1
    assert new_graph.edges[0].source_id == "a"
    assert new_graph.edges[0].target_id == "b"
    assert len(graph.edges) == 0


def test_apply_mutations_silently_skips_a_rejected_mutation():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "ghost"),), KernelLimits())
    assert len(new_graph.edges) == 0
    assert len(new_graph.nodes) == 2


def test_apply_mutations_is_a_noop_when_frozen():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits()
    )
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "b"),), KernelLimits(), frozen=True)
    assert len(new_graph.edges) == 0


def test_apply_mutations_applies_an_add_node_concept_mutation_with_wiring():
    from symbiont.cognition.structure import Mutation

    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    mutation = Mutation(
        kind="add_node",
        payload={"node_id": "concept_new", "kind": NodeKind.CONCEPT, "source_ids": ("a", "b")},
    )
    new_graph = apply_mutations(graph, (mutation,), KernelLimits())
    assert any(n.node_id == "concept_new" and n.kind is NodeKind.CONCEPT for n in new_graph.nodes)
    wired = {(e.source_id, e.target_id) for e in new_graph.edges}
    assert ("a", "concept_new") in wired
    assert ("b", "concept_new") in wired


def test_apply_mutations_rejects_add_node_when_concept_budget_exhausted():
    from symbiont.cognition.structure import Mutation

    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("existing")),
        edges=(),
        kernel_limits=KernelLimits(max_concepts=1),
    )
    mutation = Mutation(
        kind="add_node",
        payload={"node_id": "concept_new", "kind": NodeKind.CONCEPT, "source_ids": ("a",)},
    )
    new_graph = apply_mutations(graph, (mutation,), KernelLimits(max_concepts=1))
    assert not any(n.node_id == "concept_new" for n in new_graph.nodes)


def test_apply_mutations_applies_remove_edge():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.structure import Mutation

    existing = PlasticEdge(
        source_id="a",
        target_id="b",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(existing,), kernel_limits=KernelLimits()
    )
    mutation = Mutation(
        kind="remove_edge",
        payload={"source_id": "a", "target_id": "b", "kind": EdgeKind.EXCITATORY},
    )
    new_graph = apply_mutations(graph, (mutation,), KernelLimits())
    assert len(new_graph.edges) == 0


def test_apply_mutations_quarantine_edge_is_a_validated_noop():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.structure import Mutation

    existing = PlasticEdge(
        source_id="a",
        target_id="b",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(_sense("a"), _concept("b")), edges=(existing,), kernel_limits=KernelLimits()
    )
    mutation = Mutation(
        kind="quarantine_edge",
        payload={"source_id": "a", "target_id": "b", "kind": EdgeKind.EXCITATORY},
    )
    result = validate_mutation(mutation, graph, KernelLimits())
    assert result.accepted
    new_graph = apply_mutations(graph, (mutation,), KernelLimits())
    assert len(new_graph.edges) == 1  # unchanged -- quarantine state is derived, not stored


# --- concept creation ---

import random  # noqa: E402

from symbiont.cognition.structure import propose_concept  # noqa: E402


def test_propose_concept_rejects_too_few_candidates():
    graph = CognitiveGraph(nodes=(_sense("a"),), edges=(), kernel_limits=KernelLimits())
    assert (
        propose_concept(("a",), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1))
        is None
    )


def test_propose_concept_rejects_too_many_candidates():
    nodes = tuple(_sense(f"n{i}") for i in range(5))
    graph = CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits())
    ids = tuple(node.node_id for node in nodes)
    assert (
        propose_concept(ids, graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1))
        is None
    )


def test_propose_concept_rejects_unknown_node_id():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    assert (
        propose_concept(
            ("a", "ghost"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)
        )
        is None
    )


def test_propose_concept_rejects_when_concept_budget_exhausted():
    graph = CognitiveGraph(
        nodes=(_sense("a"), _sense("b"), _concept("c")), edges=(), kernel_limits=KernelLimits()
    )
    result = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(max_concepts=1), rng=random.Random(1)
    )
    assert result is None


def test_propose_concept_returns_an_add_node_mutation_with_opaque_id():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    mutation = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)
    )
    assert mutation is not None
    assert mutation.kind == "add_node"
    assert mutation.payload["node_id"].startswith("concept_")
    assert mutation.payload["node_id"] not in ("a", "b")


def test_propose_concept_is_deterministic_for_the_same_seed():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    first = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(42)
    )
    second = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(42)
    )
    assert first.payload["node_id"] == second.payload["node_id"]


def test_propose_concept_different_seeds_yield_different_ids():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    first = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)
    )
    second = propose_concept(
        ("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(2)
    )
    assert first.payload["node_id"] != second.payload["node_id"]


# --- pruning lifecycle ---

from symbiont.cognition.structure import EdgeLifecycleState, evaluate_edge_lifecycle  # noqa: E402


def _lifecycle_edge(weight: float, support: int, last_use_tick: int) -> PlasticEdge:
    return PlasticEdge(
        source_id="a",
        target_id="b",
        kind=EdgeKind.EXCITATORY,
        weight=weight,
        plasticity=0.5,
        delay_ticks=0,
        support=support,
        last_use_tick=last_use_tick,
    )


def test_strong_established_edge_is_active():
    edge = _lifecycle_edge(weight=1.5, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(
        edge, current_tick=10, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50
    )
    assert state == EdgeLifecycleState.ACTIVE


def test_unestablished_weak_edge_within_tentative_lifetime_is_still_active():
    edge = _lifecycle_edge(weight=0.01, support=2, last_use_tick=10)
    edge.age_ticks = 5
    state = evaluate_edge_lifecycle(
        edge,
        current_tick=10,
        prune_threshold=0.1,
        minimum_support=16,
        quarantine_window_ticks=50,
        tentative_lifetime_ticks=100,
    )
    assert state == EdgeLifecycleState.ACTIVE


def test_unestablished_edge_past_tentative_lifetime_is_removed():
    edge = _lifecycle_edge(weight=0.01, support=2, last_use_tick=10)
    edge.age_ticks = 150
    state = evaluate_edge_lifecycle(
        edge,
        current_tick=10,
        prune_threshold=0.1,
        minimum_support=16,
        quarantine_window_ticks=50,
        tentative_lifetime_ticks=100,
    )
    assert state == EdgeLifecycleState.REMOVED


def test_advance_edge_age_increments_age_always_and_support_only_when_used():
    from symbiont.cognition.structure import advance_edge_age

    edge = _lifecycle_edge(weight=0.5, support=0, last_use_tick=0)
    advance_edge_age(edge, tick=5, used=False)
    assert edge.age_ticks == 1
    assert edge.support == 0
    advance_edge_age(edge, tick=6, used=True)
    assert edge.age_ticks == 2
    assert edge.support == 1
    assert edge.last_use_tick == 6


def test_established_weak_edge_recently_used_is_weak():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(
        edge, current_tick=15, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50
    )
    assert state == EdgeLifecycleState.WEAK


def test_established_weak_edge_stale_past_window_is_quarantined():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(
        edge, current_tick=61, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50
    )
    assert state == EdgeLifecycleState.QUARANTINED


def test_quarantined_edge_stale_past_second_window_is_removed():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(
        edge, current_tick=111, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50
    )
    assert state == EdgeLifecycleState.REMOVED


def test_edge_that_recovered_weight_returns_to_active():
    edge = _lifecycle_edge(weight=1.0, support=100, last_use_tick=60)
    state = evaluate_edge_lifecycle(
        edge, current_tick=61, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50
    )
    assert state == EdgeLifecycleState.ACTIVE
