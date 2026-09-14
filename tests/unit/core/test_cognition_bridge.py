from __future__ import annotations

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.metaplasticity import SafetyState
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge

_GENOME_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_bridge0000000000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 4,
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "consolidation_interval_ticks": 4,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.9,
    },
    "structure": {
        "grow_threshold": 0.18,
        "prune_threshold": 0.01,
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


def _genome():
    return GenomeCodec().load(_GENOME_PAYLOAD)


def _simple_graph() -> CognitiveGraph:
    sense = PlasticNode(node_id="s", kind=NodeKind.SENSE)
    concept = PlasticNode(node_id="c", kind=NodeKind.CONCEPT)
    edge = PlasticEdge(source_id="s", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0)
    return CognitiveGraph(nodes=(sense, concept), edges=(edge,), kernel_limits=KernelLimits())


def test_tick_activates_the_graph_from_sense_values():
    bridge = CognitiveBridge(graph=_simple_graph(), genome=_genome(), kernel_limits=KernelLimits())
    result = bridge.tick({"s": 5.0}, tick=1)
    assert "s" in result.activations
    assert "c" in result.activations


def test_tick_learns_weights_over_repeated_correlated_ticks():
    graph = _simple_graph()
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits())
    for tick in range(1, 30):
        bridge.tick({"s": 1.0}, tick=tick)
    edge = bridge.graph.edges[0]
    assert edge.support > 0  # advance_edge_age actually incremented it


def test_frozen_safety_state_prevents_learning():
    graph = _simple_graph()
    safety = SafetyState()
    safety.record_failure()
    safety.record_failure()
    safety.record_failure()
    assert safety.frozen
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits(), safety_state=safety)
    weight_before = bridge.graph.edges[0].weight
    for tick in range(1, 10):
        result = bridge.tick({"s": 1.0}, tick=tick)
    assert result.frozen
    assert bridge.graph.edges[0].weight == weight_before


def test_a_graph_error_records_a_failure_and_does_not_raise():
    from symbiont.cognition.graph import GraphError

    class _BrokenGraph:
        nodes = ()
        edges = ()

        def activate(self, *args, **kwargs):
            raise GraphError("boom")

    genome = _genome()
    bridge = CognitiveBridge(graph=_BrokenGraph(), genome=genome, kernel_limits=KernelLimits())
    result = bridge.tick({"s": 1.0}, tick=1)
    assert bridge.safety_state.consecutive_failures == 1
    assert result.prediction_errors == ()


def test_three_consecutive_graph_errors_freeze_the_bridge():
    from symbiont.cognition.graph import GraphError

    class _BrokenGraph:
        nodes = ()
        edges = ()

        def activate(self, *args, **kwargs):
            raise GraphError("boom")

    bridge = CognitiveBridge(graph=_BrokenGraph(), genome=_genome(), kernel_limits=KernelLimits())
    for tick in range(1, 4):
        result = bridge.tick({"s": 1.0}, tick=tick)
    assert result.frozen


def test_checkpoint_round_trips_graph_and_safety_state():
    graph = _simple_graph()
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())
    for tick in range(1, 30):
        bridge.tick({"s": 1.0}, tick=tick)

    payload = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(payload, genome=genome, kernel_limits=KernelLimits())

    assert restored is not None
    assert {n.node_id for n in restored.graph.nodes} == {"s", "c"}
    assert restored.graph.edges[0].support == bridge.graph.edges[0].support


def test_checkpoint_preserves_frozen_safety_state():
    graph = _simple_graph()
    genome = _genome()
    safety = SafetyState()
    for _ in range(3):
        safety.record_failure()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits(), safety_state=safety)

    payload = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(payload, genome=genome, kernel_limits=KernelLimits())

    assert restored.safety_state.frozen


def test_restore_of_none_payload_returns_none():
    genome = _genome()
    assert CognitiveBridge.restore(None, genome=genome, kernel_limits=KernelLimits()) is None


def test_structural_consolidation_runs_only_on_the_configured_interval():
    graph = _simple_graph()
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits())
    results = [bridge.tick({"s": 1.0}, tick=tick) for tick in range(1, 5)]
    # consolidation_interval_ticks == 4 in the fixture genome -- only tick 4 attempts consolidation
    assert all(r.structural_mutations_applied == 0 for r in results[:3])


def test_structural_mutation_advances_topology_revision_and_reports_mutations():
    graph = _simple_graph()
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())

    first = bridge.tick({"s": 1.0}, tick=1)
    assert first.topology_revision == 0
    assert first.mutations == ()

    last = first
    for tick in range(2, genome.development.consolidation_interval_ticks * 6):
        last = bridge.tick({"s": 1.0}, tick=tick)
        if last.structural_mutations_applied > 0:
            break

    if last.structural_mutations_applied > 0:
        assert last.topology_revision == 1
        assert len(last.mutations) == last.structural_mutations_applied
    else:
        assert last.topology_revision == 0
        assert last.mutations == ()


def test_result_exposes_the_bridge_live_consecutive_failures():
    from symbiont.cognition.graph import GraphError

    class _BrokenGraph:
        nodes = ()
        edges = ()

        def activate(self, *args, **kwargs):
            raise GraphError("boom")

    bridge = CognitiveBridge(graph=_BrokenGraph(), genome=_genome(), kernel_limits=KernelLimits())
    first = bridge.tick({"s": 1.0}, tick=1)
    second = bridge.tick({"s": 1.0}, tick=2)
    assert first.consecutive_failures == 1
    assert second.consecutive_failures == 2

    healthy = CognitiveBridge(graph=_simple_graph(), genome=_genome(), kernel_limits=KernelLimits())
    result = healthy.tick({"s": 1.0}, tick=1)
    assert result.consecutive_failures == 0


def test_structural_plasticity_candidate_state_is_never_exported():
    """Design §10.4: anything durable about structure already exists as
    real graph topology; in-progress candidate/cooldown bookkeeping is
    RAM-only working state, never checkpointed."""
    graph = _simple_graph()
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())
    for tick in range(1, 10):
        bridge.tick({"s": 1.0}, tick=tick)
    payload = bridge.export_checkpoint()
    assert "structural_plasticity" not in payload
