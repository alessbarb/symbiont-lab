from __future__ import annotations

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge


def _genome():
    return GenomeCodec().load(
        {
            "schema_version": 1,
            "genome_id": "genome_motorp10000000000000000000",
            "parent_ids": [],
            "kernel_compatibility": ">=0.55,<0.60",
            "development": {
                "initial_concepts": 1,
                "soft_node_budget": 32,
                "soft_edge_budget": 64,
                "consolidation_interval_ticks": 1,
            },
            "plasticity": {
                "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
                "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
                "eligibility_decay": 0.9,
            },
            "structure": {
                "grow_threshold": 0.1,
                "prune_threshold": 0.001,
                "minimum_support": 2,
                "tentative_lifetime_ticks": 64,
            },
            "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
        }
    )


def _graph() -> CognitiveGraph:
    nodes = (
        PlasticNode(node_id="sense_a", kind=NodeKind.SENSE),
        PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT),
        PlasticNode(node_id="readout_core", kind=NodeKind.READOUT),
    )
    edges = (
        PlasticEdge(
            source_id="sense_a",
            target_id="concept_a",
            kind=EdgeKind.EXCITATORY,
            weight=0.8,
            plasticity=0.5,
            delay_ticks=0,
        ),
        PlasticEdge(
            source_id="concept_a",
            target_id="readout_core",
            kind=EdgeKind.EXCITATORY,
            weight=0.8,
            plasticity=0.5,
            delay_ticks=1,
            support=4,
        ),
    )
    return CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())


def test_p1_motor_readout_is_lazy_and_does_not_change_core_reachability():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    before = bridge._nodes_with_path_to_core_readout()
    assert "concept_a" in before

    result = bridge.tick(
        {"sense_a": 2.0},
        tick=1,
        active_motor_actuator_ids=("actuator.test",),
        motor_effect_actuator_ids=("actuator.test",),
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_motor:actuator.test" in node_ids
    assert bridge._nodes_with_path_to_core_readout() == before
    assert result.readouts_for_family("core") == result.readouts
    assert "actuator.test" in result.readouts_for_family("motor")


def test_p1_motor_association_grows_tentative_edge_without_fake_target_activation():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    for tick in (1, 2, 3):
        bridge.tick(
            {"sense_a": 2.0 * tick},
            tick=tick,
            active_motor_actuator_ids=("actuator.test",),
            motor_effect_actuator_ids=("actuator.test",),
        )

    assert any(
        edge.source_id == "concept_a"
        and edge.target_id == "readout_motor:actuator.test"
        for edge in bridge.graph.edges
    )
    assert "concept_a" in bridge._nodes_with_path_to_motor_readout("actuator.test")
    assert "concept_a" in bridge._nodes_with_path_to_core_readout()


def test_p1_motor_only_route_never_counts_as_core_route():
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT),
            PlasticNode(node_id="readout_motor:actuator.test", kind=NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(
                source_id="concept_a",
                target_id="readout_motor:actuator.test",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=1,
            ),
        ),
        kernel_limits=KernelLimits(),
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    assert "concept_a" not in bridge._nodes_with_path_to_core_readout()
    assert "concept_a" in bridge._nodes_with_path_to_motor_readout("actuator.test")



def test_verified_motor_primitive_gets_its_own_readout_family():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    result = bridge.tick(
        {"sense_a": 2.0},
        tick=1,
        active_primitive_ids=("primitive.test",),
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.test" in node_ids
    assert "primitive.test" in result.readouts_for_family("primitive")
    assert "readout_primitive:primitive.test" not in result.readouts_for_family("core")


def test_primitive_association_can_grow_without_becoming_core_route():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    for tick in (1, 2, 3):
        result = bridge.tick(
            {"sense_a": 2.0 * tick},
            tick=tick,
            active_primitive_ids=("primitive.test",),
        )
        bridge.observe_primitive_execution(
            "primitive.test",
            concept_ids=result.active_concept_ids,
            tick=tick,
        )

    # One additional consolidation tick applies the accumulated structural
    # association evidence.
    bridge.tick(
        {"sense_a": 8.0},
        tick=4,
        active_primitive_ids=("primitive.test",),
    )

    assert any(
        edge.source_id == "concept_a"
        and edge.target_id == "readout_primitive:primitive.test"
        for edge in bridge.graph.edges
    )
    assert "concept_a" in bridge._nodes_with_path_to_primitive_readout(
        "primitive.test"
    )
    assert "concept_a" in bridge._nodes_with_path_to_core_readout()



def test_refuted_primitive_readout_is_removed_from_graph():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    bridge.tick(
        {"sense_a": 2.0},
        tick=1,
        active_primitive_ids=("primitive.keep", "primitive.drop"),
    )
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.keep" in node_ids
    assert "readout_primitive:primitive.drop" in node_ids

    bridge.tick(
        {"sense_a": 3.0},
        tick=2,
        active_primitive_ids=("primitive.keep",),
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.keep" in node_ids
    assert "readout_primitive:primitive.drop" not in node_ids
