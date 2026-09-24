from __future__ import annotations

from dataclasses import replace

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge


def _genome(*, interval: int = 1, lifetime: int = 2, sense_budget: int = 32, retention: int = 256):
    limits = KernelLimits()
    genome, _ = load_base_cognition(kernel_limits=limits, running_version=(0, 59, 4))
    genome = replace(
        genome,
        development=replace(
            genome.development,
            consolidation_interval_ticks=interval,
            sense_node_budget=sense_budget,
            sense_retention_ticks=retention,
        ),
        structure=replace(
            genome.structure,
            minimum_support=2,
            grow_threshold=0.0,
            tentative_lifetime_ticks=lifetime,
        ),
    )
    return limits, genome


def test_sense_budget_reserves_total_node_capacity_for_latent_cognition() -> None:
    limits, genome = _genome(sense_budget=4)
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=limits)
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick({f"sense_{index}": float(index + 1) for index in range(12)}, tick=1)

    senses = [node for node in bridge.graph.nodes if node.kind is NodeKind.SENSE]
    assert len(senses) == 4
    assert len(bridge.graph.nodes) < genome.development.soft_node_budget


def test_concept_lineage_survives_checkpoint_restore() -> None:
    limits, genome = _genome(interval=2, lifetime=8)
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=limits)
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick({"sense_alpha": 1.0, "sense_beta": 2.0}, tick=1)
    bridge.tick({"sense_alpha": 2.0, "sense_beta": 4.0}, tick=2)

    assert len(bridge.concept_lineage) == 1
    lineage = bridge.concept_lineage[0]
    assert lineage.parent_ids == ("sense_alpha", "sense_beta")
    assert lineage.born_tick == 2

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=genome,
        kernel_limits=limits,
    )
    assert restored is not None
    assert restored.concept_lineage == bridge.concept_lineage


def test_lineage_keeps_concept_signature_after_all_incident_edges_are_lost() -> None:
    limits, genome = _genome(interval=2, lifetime=8)
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=limits)
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    bridge.tick({"sense_alpha": 1.0, "sense_beta": 2.0}, tick=1)
    bridge.tick({"sense_alpha": 2.0, "sense_beta": 4.0}, tick=2)
    assert bridge.concept_lineage

    bridge._graph = CognitiveGraph(
        nodes=bridge.graph.nodes,
        edges=(),
        kernel_limits=limits,
    )
    bridge._seed_new_edges()

    assert bridge._concept_signature_exists(("sense_alpha", "sense_beta"))
    assert bridge._concept_signature_exists(("sense_beta", "sense_alpha"))


def test_concept_signature_cache_tracks_graph_identity_independently() -> None:
    limits, genome = _genome(interval=2, lifetime=8)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_alpha", NodeKind.SENSE),
            PlasticNode("sense_beta", NodeKind.SENSE),
            PlasticNode("concept_existing", NodeKind.CONCEPT),
        ),
        edges=(
            PlasticEdge(
                source_id="sense_alpha",
                target_id="concept_existing",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
            ),
            PlasticEdge(
                source_id="sense_beta",
                target_id="concept_existing",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
            ),
        ),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    assert bridge._concept_signature_exists(("sense_alpha", "sense_beta"))

    bridge._graph = CognitiveGraph(
        nodes=graph.nodes,
        edges=(),
        kernel_limits=limits,
    )
    bridge._topology_cache()  # must not make the independent signature cache look current

    assert not bridge._concept_signature_exists(("sense_alpha", "sense_beta"))


def test_orphan_concept_and_readout_are_collected_after_grace_period() -> None:
    limits, genome = _genome(interval=1, lifetime=2)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("concept_orphan", NodeKind.CONCEPT),
            PlasticNode("readout_core", NodeKind.READOUT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    bridge.tick({}, tick=1)
    bridge.tick({}, tick=2)
    assert len(bridge.graph.nodes) == 2

    result = bridge.tick({}, tick=3)
    assert bridge.graph.nodes == ()
    assert {mutation.kind for mutation in result.mutations} == {"remove_node"}


def test_stale_disconnected_sense_is_evicted_but_connected_sense_is_preserved() -> None:
    limits, genome = _genome(interval=1, lifetime=8, sense_budget=3, retention=2)
    edge = PlasticEdge(
        source_id="sense_connected",
        target_id="concept_live",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_connected", NodeKind.SENSE),
            PlasticNode("sense_stale", NodeKind.SENSE),
            PlasticNode("concept_live", NodeKind.CONCEPT),
        ),
        edges=(edge,),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    bridge.tick({}, tick=1)
    bridge.tick({}, tick=2)

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "sense_connected" in node_ids
    assert "sense_stale" not in node_ids
    assert "concept_live" in node_ids


def test_owner_authored_graph_does_not_enter_automatic_gc_or_eviction() -> None:
    limits, genome = _genome(interval=1, lifetime=1, sense_budget=1, retention=1)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("owner_sense_a", NodeKind.SENSE),
            PlasticNode("owner_sense_b", NodeKind.SENSE),
            PlasticNode("owner_concept", NodeKind.CONCEPT),
            PlasticNode("owner_readout", NodeKind.READOUT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    assert bridge.develop_senses is False

    for tick in range(1, 5):
        bridge.tick({}, tick=tick)

    assert {node.node_id for node in bridge.graph.nodes} == {
        "owner_sense_a",
        "owner_sense_b",
        "owner_concept",
        "owner_readout",
    }



def test_retrospective_support_enters_normal_concept_birth_path() -> None:
    limits, genome = _genome(interval=1, lifetime=8)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_alpha", NodeKind.SENSE),
            PlasticNode("sense_beta", NodeKind.SENSE),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    applied = bridge.observe_retrospective_support(
        ("sense_alpha", "sense_beta"),
        support_epochs=2,
    )
    assert applied == 2
    assert bridge.observe_retrospective_support(
        ("sense_alpha", "sense_beta"),
        support_epochs=2,
    ) == 0

    bridge.tick({}, tick=1)

    assert len(bridge.concept_lineage) == 1
    assert bridge.concept_lineage[0].parent_ids == (
        "sense_alpha",
        "sense_beta",
    )



def test_retrospective_support_does_not_add_to_live_support() -> None:
    limits, genome = _genome(interval=1, lifetime=8)
    genome = replace(
        genome,
        structure=replace(genome.structure, minimum_support=3),
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_alpha", NodeKind.SENSE),
            PlasticNode("sense_beta", NodeKind.SENSE),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    bridge._concept_support[("sense_alpha", "sense_beta")] = 2
    bridge.observe_retrospective_support(
        ("sense_alpha", "sense_beta"),
        support_epochs=2,
    )
    bridge.tick({}, tick=1)
    assert bridge.concept_lineage == ()

    bridge.observe_retrospective_support(
        ("sense_alpha", "sense_beta"),
        support_epochs=3,
    )
    bridge.tick({}, tick=2)
    assert len(bridge.concept_lineage) == 1



def test_developmental_node_budget_expands_when_supported_structure_is_blocked() -> None:
    limits, genome = _genome(interval=1, lifetime=8, sense_budget=2)
    genome = replace(
        genome,
        development=replace(
            genome.development,
            soft_node_budget=3,
            soft_edge_budget=8,
        ),
        structure=replace(genome.structure, minimum_support=2),
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_alpha", NodeKind.SENSE),
            PlasticNode("sense_beta", NodeKind.SENSE),
            PlasticNode("readout_core", NodeKind.READOUT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )
    assert bridge._soft_node_limit == 3

    bridge.observe_retrospective_support(
        ("sense_alpha", "sense_beta"),
        support_epochs=2,
    )
    result = bridge.tick({}, tick=1)

    assert result.node_budget > 3
    assert result.node_budget <= limits.max_nodes
    assert any(
        node.kind is NodeKind.CONCEPT
        for node in bridge.graph.nodes
    )

    restored = CognitiveBridge.restore(
        bridge.export_checkpoint(),
        genome=genome,
        kernel_limits=limits,
    )
    assert restored is not None
    assert restored._soft_node_limit == result.node_budget



def test_legacy_checkpoint_without_adaptive_budgets_restores_birth_budget() -> None:
    limits, genome = _genome(interval=2, lifetime=8)
    genome = replace(
        genome,
        development=replace(
            genome.development,
            soft_node_budget=48,
            soft_edge_budget=192,
            sense_node_budget=24,
        ),
    )
    graph = CognitiveGraph(nodes=(), edges=(), kernel_limits=limits)
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
    )
    payload = bridge.export_checkpoint()
    payload.pop("adaptive_resource_budgets", None)

    restored = CognitiveBridge.restore(
        payload,
        genome=genome,
        kernel_limits=limits,
    )

    assert restored is not None
    assert restored._soft_node_limit == 48
    assert restored._soft_edge_limit == 192
    assert restored._sense_node_limit == 24
