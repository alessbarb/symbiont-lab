from __future__ import annotations

from symbiont.core.cognition.bridge import CognitiveBridge
from symbiont.cognition.graph import CognitiveGraph
from symbiont.cognition.types import NodeKind, EdgeKind
from symbiont.cognition.graph import PlasticNode, PlasticEdge
from symbiont.core.cognition.bridge import _CORE_READOUT_ID
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.genome import GenomeCodec

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


def test_stranded_route_repair():
    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    c1 = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT)
    r = PlasticNode(node_id=_CORE_READOUT_ID, kind=NodeKind.READOUT)
    
    e1 = PlasticEdge(source_id="s1", target_id="c1", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    
    graph = CognitiveGraph(nodes=(s1, c1, r), edges=(e1,), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits(), develop_senses=True)
    
    # Simulate c1 being unrouted and active
    bridge._unrouted_since_tick["c1"] = 0
    bridge._concept_last_active_tick["c1"] = 0
    
    result = bridge.tick({"s1": 1.0}, tick=20)
    
    assert len(result.recycling_events) == 1
    event = result.recycling_events[0]
    assert event["reason"] == "stranded_route_repair"
    assert event["concept_id"] == "c1"
    
    edges_to_r = [e for e in bridge.graph.edges if e.source_id == "c1" and e.target_id == _CORE_READOUT_ID]
    assert len(edges_to_r) == 1

def test_save_and_restore_preserves_unrouted_durations():
    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    c1 = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT)
    r = PlasticNode(node_id=_CORE_READOUT_ID, kind=NodeKind.READOUT)
    e1 = PlasticEdge(source_id="s1", target_id="c1", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1)
    graph = CognitiveGraph(nodes=(s1, c1, r), edges=(e1,), kernel_limits=KernelLimits())
    bridge = CognitiveBridge(graph=graph, genome=_genome(), kernel_limits=KernelLimits(), develop_senses=True)
    bridge._unrouted_since_tick["c1"] = 7
    payload = bridge.export_checkpoint()

    assert "unrouted_since_tick" in payload
    assert payload["unrouted_since_tick"]["c1"] == 7

    restored = CognitiveBridge.restore(payload, genome=_genome(), kernel_limits=KernelLimits())
    assert restored is not None
    assert restored.unrouted_since_tick["c1"] == 7
