from __future__ import annotations

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, KernelLimits, PlasticEdge, PlasticNode
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge, ConceptLineage, _CORE_READOUT_ID

_GENOME_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_recycling00000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 2,
        "soft_node_budget": 6,  # Tight soft budget: 3 senses (s1, s2, s3) + 2 concepts (c1, c2) + 1 readout = 6 nodes
        "soft_edge_budget": 16,
        "consolidation_interval_ticks": 2,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.9,
    },
    "structure": {
        "grow_threshold": 0.18,
        "prune_threshold": 0.01,
        "minimum_support": 4,
        "tentative_lifetime_ticks": 10,  # Grace period is 10 ticks
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


def _genome():
    return GenomeCodec().load(_GENOME_PAYLOAD)


def _setup_full_budget_bridge_with_sink(*, born_tick: int = 0, unrouted_since: int = 0) -> CognitiveBridge:
    # 6 nodes = 3 senses (s1, s2, s3) + 2 concepts (c1, c2) + 1 readout (_CORE_READOUT_ID)
    # c1 is routed: s1 -> c1 -> _CORE_READOUT_ID
    # c2 is a sink (unrouted): s2 -> c2 (no edge to _CORE_READOUT_ID)
    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    s2 = PlasticNode(node_id="s2", kind=NodeKind.SENSE)
    s3 = PlasticNode(node_id="s3", kind=NodeKind.SENSE)
    c1 = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT)
    c2 = PlasticNode(node_id="c2", kind=NodeKind.CONCEPT)
    r = PlasticNode(node_id=_CORE_READOUT_ID, kind=NodeKind.READOUT)

    e1 = PlasticEdge(source_id="s1", target_id="c1", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    e2 = PlasticEdge(source_id="c1", target_id=_CORE_READOUT_ID, kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    e3 = PlasticEdge(source_id="s2", target_id="c2", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)

    graph = CognitiveGraph(nodes=(s1, s2, s3, c1, c2, r), edges=(e1, e2, e3), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits(), develop_senses=True)

    bridge._concept_lineage["c1"] = ConceptLineage("c1", ("s1", "s2"), 0)
    bridge._concept_lineage["c2"] = ConceptLineage("c2", ("s1", "s2"), born_tick)
    if unrouted_since is not None:
        bridge._unrouted_since_tick["c2"] = unrouted_since

    return bridge


def test_1_full_budget_expendable_concept_and_admissible_candidate_replaces_validly():
    # Budget is 6 nodes, graph has 6 nodes.
    # c2 is born at tick 0, unrouted since tick 0.
    # At tick 20 (grace=10), c2 is expendable (20 - 0 >= 10).
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)

    # Supply sufficient support for new candidate pair ("s2", "s3")
    bridge._concept_support[("s2", "s3")] = 10

    result = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)

    # Replacement occurred!
    assert len(result.recycling_events) == 1
    event = result.recycling_events[0]
    assert event["retired_concept_id"] == "c2"
    assert event["reason"] == "unrouted_under_budget_pressure"

    # c2 is gone, new concept is added
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "c2" not in node_ids
    assert len(node_ids) == 6  # Maintained budget limit!
    new_concept_id = event["new_concept_id"]
    assert new_concept_id in node_ids
    assert new_concept_id != "c2"

    # New concept has path to core readout
    edges_to_r = [e for e in bridge.graph.edges if e.source_id == new_concept_id and e.target_id == _CORE_READOUT_ID]
    assert len(edges_to_r) == 1


def test_2_young_concept_without_path_is_conserved_during_grace_period():
    # c2 is born at tick 15. At tick 20, tick - born_tick = 5 < grace (10).
    bridge = _setup_full_budget_bridge_with_sink(born_tick=15, unrouted_since=15)
    bridge._concept_support[("s2", "s3")] = 10

    result = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)

    # No recycling because c2 is still in grace period
    assert len(result.recycling_events) == 0
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "c2" in node_ids


def test_3_chain_or_cycle_without_readout_path_is_detected_and_recycled():
    # Setup graph where c2 -> c3 -> c2 (cycle with outgoing edges, but neither reaches core readout)
    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    s2 = PlasticNode(node_id="s2", kind=NodeKind.SENSE)
    s3 = PlasticNode(node_id="s3", kind=NodeKind.SENSE)
    c1 = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT)
    c2 = PlasticNode(node_id="c2", kind=NodeKind.CONCEPT)
    c3 = PlasticNode(node_id="c3", kind=NodeKind.CONCEPT)
    r = PlasticNode(node_id=_CORE_READOUT_ID, kind=NodeKind.READOUT)

    e1 = PlasticEdge(source_id="s1", target_id="c1", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    e2 = PlasticEdge(source_id="c1", target_id=_CORE_READOUT_ID, kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    # Cycle c2 <-> c3
    e3 = PlasticEdge(source_id="c2", target_id="c3", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    e4 = PlasticEdge(source_id="c3", target_id="c2", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)

    graph = CognitiveGraph(nodes=(s1, s2, s3, c1, c2, c3, r), edges=(e1, e2, e3, e4), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits(), develop_senses=True)

    bridge._concept_lineage["c1"] = ConceptLineage("c1", ("s1", "s2"), 0)
    bridge._concept_lineage["c2"] = ConceptLineage("c2", ("s1", "s2"), 0)
    bridge._concept_lineage["c3"] = ConceptLineage("c3", ("s1", "s2"), 0)
    bridge._unrouted_since_tick["c2"] = 0
    bridge._unrouted_since_tick["c3"] = 2  # c2 was unrouted earlier than c3

    bridge._concept_support[("s2", "s3")] = 10

    # At tick 20, both c2 and c3 have outgoing edges, but neither reaches _CORE_READOUT_ID!
    result = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)

    # c2 (unrouted since 0) should be retired and recycled
    assert len(result.recycling_events) == 1
    assert result.recycling_events[0]["retired_concept_id"] == "c2"
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "c2" not in node_ids


def test_4_concept_recovering_path_resets_unrouted_counter():
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)
    assert bridge.unrouted_since_tick.get("c2") == 0

    # Add edge from c2 to _CORE_READOUT_ID (connecting it!)
    edge_to_r = PlasticEdge(
        source_id="c2", target_id=_CORE_READOUT_ID, kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1
    )
    new_graph = CognitiveGraph(
        nodes=bridge.graph.nodes, edges=(*bridge.graph.edges, edge_to_r), kernel_limits=KernelLimits()
    )
    bridge._graph = new_graph
    bridge._seed_new_edges()

    # Run consolidation tick
    bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=2)

    # Unrouted tracking for c2 must be cleared (reset)!
    assert "c2" not in bridge.unrouted_since_tick


def test_5_candidate_failing_validation_leaves_original_graph_intact():
    # If the candidate substitution would exceed kernel limits (e.g. max mutations per consolidation = 1)
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)
    bridge._concept_support[("s2", "s3")] = 10

    original_nodes = bridge.graph.nodes
    original_edges = bridge.graph.edges

    # Set max mutations to 1 so the substitution batch (which needs 4 mutations) cannot fit
    limits_strict = KernelLimits(max_structural_mutations_per_consolidation=1)
    bridge._kernel_limits = limits_strict

    result = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)

    assert len(result.recycling_events) == 0
    assert bridge.graph.nodes == original_nodes
    assert bridge.graph.edges == original_edges


def test_6_full_budget_without_admissible_candidate_does_not_recycle():
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)
    # Candidate support is 1, which is below minimum_support (4)
    bridge._concept_support[("s2", "s3")] = 1

    result = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)

    assert len(result.recycling_events) == 0
    assert "c2" in {n.node_id for n in bridge.graph.nodes}


def test_7_save_and_restore_preserves_grace_and_unrouted_durations():
    bridge = _setup_full_budget_bridge_with_sink(born_tick=5, unrouted_since=7)
    payload = bridge.export_checkpoint()

    assert "unrouted_since_tick" in payload
    assert payload["unrouted_since_tick"]["c2"] == 7

    restored = CognitiveBridge.restore(payload, genome=_genome(), kernel_limits=KernelLimits())
    assert restored is not None
    assert restored.unrouted_since_tick["c2"] == 7
    assert restored._concept_lineage["c2"].born_tick == 5


def test_8_prolonged_execution_prevents_immediate_re_eviction():
    # After recycling, the new concept must not be immediately evicted in the next consolidation
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)
    bridge._concept_support[("s2", "s3")] = 10

    # Tick 20: substitution occurs
    res20 = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)
    assert len(res20.recycling_events) == 1
    new_id = res20.recycling_events[0]["new_concept_id"]

    # Provide another high-support candidate
    bridge._concept_support[("s1", "s3")] = 10

    # Tick 22 (next consolidation interval = 2): new concept is only 2 ticks old (grace = 10)
    res22 = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=22)

    # Must NOT evict the newly born concept!
    assert new_id in {n.node_id for n in bridge.graph.nodes}
    # No thrashing/re-eviction of the young concept
    assert all(e["retired_concept_id"] != new_id for e in res22.recycling_events)


def test_9_monotonic_concept_ids_survive_checkpoint_and_gc():
    bridge = _setup_full_budget_bridge_with_sink(born_tick=0, unrouted_since=0)
    bridge._concept_support[("s2", "s3")] = 10

    # Tick 20: substitution occurs, retiring c2 and creating concept_0000000000000001
    res20 = bridge.tick({"s1": 1.0, "s2": 1.0, "s3": 1.0}, tick=20)
    first_id = res20.recycling_events[0]["new_concept_id"]
    assert first_id == "concept_0000000000000001"

    # Export checkpoint: must persist next_concept_index >= 2
    payload = bridge.export_checkpoint()
    assert "next_concept_index" in payload
    assert payload["next_concept_index"] >= 2

    # Restore in a fresh bridge
    restored = CognitiveBridge.restore(payload, genome=_genome(), kernel_limits=KernelLimits())
    assert restored is not None
    assert restored.next_concept_index == payload["next_concept_index"]

    # Generate next concept id: must NOT reuse concept_0000000000000001
    second_id = restored._new_node_id("concept")
    assert second_id != first_id
    assert second_id == "concept_0000000000000002"

