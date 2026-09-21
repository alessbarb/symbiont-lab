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
    assert "actuator.test" not in result.readouts_for_family("motor")

    result = bridge.tick(
        {"sense_a": 3.0},
        tick=2,
        active_motor_actuator_ids=("actuator.test",),
        motor_effect_actuator_ids=("actuator.test",),
    )
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
    assert "primitive.test" not in result.readouts_for_family("primitive")

    result = bridge.tick(
        {"sense_a": 3.0},
        tick=2,
        active_primitive_ids=("primitive.test",),
    )
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
    bridge.tick(
        {"sense_a": 2.5},
        tick=2,
        active_primitive_ids=("primitive.keep", "primitive.drop"),
    )
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.keep" in node_ids
    assert "readout_primitive:primitive.drop" in node_ids

    bridge.tick(
        {"sense_a": 3.0},
        tick=3,
        active_primitive_ids=("primitive.keep",),
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.keep" in node_ids
    assert "readout_primitive:primitive.drop" not in node_ids



def test_primitive_choice_credit_does_not_remove_sibling_readouts():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    result = bridge.tick(
        {"sense_a": 2.0},
        tick=1,
        active_primitive_ids=("primitive.a", "primitive.b"),
    )
    result = bridge.tick(
        {"sense_a": 2.5},
        tick=2,
        active_primitive_ids=("primitive.a", "primitive.b"),
    )
    assert {
        "readout_primitive:primitive.a",
        "readout_primitive:primitive.b",
    }.issubset({node.node_id for node in bridge.graph.nodes})

    bridge.observe_primitive_execution(
        "primitive.a",
        concept_ids=result.active_concept_ids,
        tick=2,
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.a" in node_ids
    assert "readout_primitive:primitive.b" in node_ids



def test_newly_verified_primitive_waits_for_normal_readout_admission():
    bridge = CognitiveBridge(
        graph=_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    bridge.tick(
        {"sense_a": 2.0},
        tick=1,
        active_primitive_ids=("primitive.sibling",),
    )
    assert bridge.observe_primitive_execution(
        "primitive.new",
        concept_ids=("concept_a",),
        tick=1,
    ) is False

    # The next normal cognition tick admits the verified skill within the
    # ordinary mutation budget; only then can state→action evidence be stored.
    bridge.tick(
        {"sense_a": 3.0},
        tick=2,
        active_primitive_ids=("primitive.sibling", "primitive.new"),
    )
    assert bridge.observe_primitive_execution(
        "primitive.new",
        concept_ids=("concept_a",),
        tick=2,
    ) is True

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "readout_primitive:primitive.new" in node_ids
    assert "readout_primitive:primitive.sibling" in node_ids



def _full_predictor_graph() -> CognitiveGraph:
    nodes = (
        PlasticNode(node_id="sense_a", kind=NodeKind.SENSE),
        PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT),
        PlasticNode(node_id="readout_core", kind=NodeKind.READOUT),
        PlasticNode(
            node_id="predictor_bad",
            kind=NodeKind.PREDICTOR,
            predicts_node_id="concept_a",
        ),
    )
    edges = (
        PlasticEdge(
            source_id="sense_a",
            target_id="concept_a",
            kind=EdgeKind.EXCITATORY,
            weight=0.5,
            plasticity=0.0,
            delay_ticks=0,
            support=32,
        ),
        PlasticEdge(
            source_id="concept_a",
            target_id="readout_core",
            kind=EdgeKind.EXCITATORY,
            weight=0.8,
            plasticity=0.0,
            delay_ticks=1,
            support=32,
        ),
        PlasticEdge(
            source_id="sense_a",
            target_id="predictor_bad",
            kind=EdgeKind.PREDICTIVE,
            weight=1.0,
            plasticity=0.0,
            delay_ticks=0,
            support=32,
        ),
    )
    return CognitiveGraph(
        nodes=nodes,
        edges=edges,
        kernel_limits=KernelLimits(),
    )


def _capacity_genome():
    genome = _genome()
    # Keep the cognitive budget deliberately saturated at four nodes.
    from dataclasses import replace
    return replace(
        genome,
        development=replace(
            genome.development,
            soft_node_budget=4,
            soft_edge_budget=64,
            consolidation_interval_ticks=1,
        ),
        structure=replace(
            genome.structure,
            tentative_lifetime_ticks=1,
        ),
    )


def test_verified_skill_reclaims_capacity_progressively_without_reserved_slots():
    bridge = CognitiveBridge(
        graph=_full_predictor_graph(),
        genome=_capacity_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    bridge.tick({"sense_a": 0.5}, tick=1)
    bridge.tick({"sense_a": -0.5}, tick=2)
    utility = bridge._predictor_utility["predictor_bad"]
    utility.samples = 8
    utility.model_loss = 8.0
    utility.persistence_loss = 0.0
    utility.recent_gain = -1.0
    utility.negative_streak = 8
    utility.positive_streak = 0

    # Make the predictor's only incident edge already weak and unused so the
    # ordinary lifecycle, not a monolithic reclaim batch, can retire it.
    predictor_edge = next(
        edge for edge in bridge.graph.edges
        if edge.target_id == "predictor_bad"
    )
    predictor_edge.weight = 0.001
    predictor_edge.last_use_tick = 0

    # Epoch 1: capacity pressure quarantines the predictor; the weak edge is
    # removed by ordinary maintenance. The skill is still waiting.
    bridge.tick(
        {"sense_a": 0.25},
        tick=3,
        active_primitive_ids=("primitive.learned",),
    )
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "predictor_bad" in node_ids
    assert "predictor_bad" in bridge._predictor_retirement
    assert not any(
        edge.source_id == "predictor_bad" or edge.target_id == "predictor_bad"
        for edge in bridge.graph.edges
    )
    assert "readout_primitive:primitive.learned" not in node_ids

    # Epoch 2: detached predictor GC releases one slot. The contention arbiter
    # may assign that real vacancy in the same atomic consolidation.
    bridge.tick(
        {"sense_a": 0.25},
        tick=4,
        active_primitive_ids=("primitive.learned",),
    )
    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "predictor_bad" not in node_ids
    assert "readout_primitive:primitive.learned" in node_ids
    assert len(node_ids) == 4


def test_capacity_competition_protects_predictively_useful_representation():
    bridge = CognitiveBridge(
        graph=_full_predictor_graph(),
        genome=_capacity_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    # Seed already-earned internal evidence that this predictor beats
    # persistence. The consolidation mechanism must not evict it merely
    # because a skill is waiting for admission.
    bridge.tick({"sense_a": 0.25}, tick=1)
    bridge.tick({"sense_a": 0.25}, tick=2)
    utility = bridge._predictor_utility["predictor_bad"]
    utility.samples = 8
    utility.model_loss = 0.0
    utility.persistence_loss = 8.0
    utility.recent_gain = 1.0
    utility.negative_streak = 0
    utility.positive_streak = 8

    bridge.tick(
        {"sense_a": 0.25},
        tick=3,
        active_primitive_ids=("primitive.waiting",),
    )

    node_ids = {node.node_id for node in bridge.graph.nodes}
    assert "predictor_bad" in node_ids
    assert "readout_primitive:primitive.waiting" not in node_ids
    assert len(node_ids) == 4


def test_predictor_retention_evidence_survives_checkpoint_before_competition():
    bridge = CognitiveBridge(
        graph=_full_predictor_graph(),
        genome=_capacity_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge.tick({"sense_a": 0.5}, tick=1)
    bridge.tick({"sense_a": -0.5}, tick=2)
    before = bridge._predictor_utility["predictor_bad"]
    before.samples = 8
    before.model_loss = 8.0
    before.persistence_loss = 0.0
    before.recent_gain = -1.0
    before.negative_streak = 8
    before.positive_streak = 0
    bridge._update_predictor_retirement_state(tick=3)
    assert "predictor_bad" in bridge._predictor_retirement

    payload = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(
        payload,
        genome=_capacity_genome(),
        kernel_limits=KernelLimits(),
    )
    assert restored is not None
    after = restored._predictor_utility["predictor_bad"]
    assert after.samples == before.samples
    assert after.model_loss == before.model_loss
    assert after.persistence_loss == before.persistence_loss
    assert after.recent_gain == before.recent_gain
    assert after.negative_streak == before.negative_streak
    assert "predictor_bad" in restored._predictor_retirement
    assert (
        restored._predictor_retirement["predictor_bad"].entered_tick
        == bridge._predictor_retirement["predictor_bad"].entered_tick
    )



def test_predictor_retirement_is_reversible_before_detachment():
    bridge = CognitiveBridge(
        graph=_full_predictor_graph(),
        genome=_capacity_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge.tick({"sense_a": 0.5}, tick=1)
    bridge.tick({"sense_a": -0.5}, tick=2)

    utility = bridge._predictor_utility["predictor_bad"]
    utility.samples = 8
    utility.model_loss = 8.0
    utility.persistence_loss = 0.0
    utility.recent_gain = -1.0
    utility.negative_streak = 8
    utility.positive_streak = 0

    bridge.tick(
        {"sense_a": 0.25},
        tick=3,
        active_primitive_ids=("primitive.waiting",),
    )
    assert "predictor_bad" in bridge._predictor_retirement

    edge = next(
        edge for edge in bridge.graph.edges
        if edge.target_id == "predictor_bad"
    )
    weight_after_quarantine = edge.weight

    utility.recent_gain = 1.0
    utility.positive_streak = 8
    utility.negative_streak = 0
    utility.model_loss = 0.0
    utility.persistence_loss = 8.0

    bridge.tick(
        {"sense_a": 0.25},
        tick=4,
        active_primitive_ids=("primitive.waiting",),
    )

    assert "predictor_bad" not in bridge._predictor_retirement
    edge = next(
        edge for edge in bridge.graph.edges
        if edge.target_id == "predictor_bad"
    )
    # Plasticity is zero in this fixture, so cancellation of quarantine means
    # no further soft-pruning occurs.
    assert edge.weight == weight_after_quarantine


def test_retirement_requires_capacity_pressure():
    genome = _capacity_genome()
    from dataclasses import replace
    roomy_genome = replace(
        genome,
        development=replace(genome.development, soft_node_budget=8),
    )
    bridge = CognitiveBridge(
        graph=_full_predictor_graph(),
        genome=roomy_genome,
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge.tick({"sense_a": 0.5}, tick=1)
    bridge.tick({"sense_a": -0.5}, tick=2)
    utility = bridge._predictor_utility["predictor_bad"]
    utility.samples = 8
    utility.model_loss = 8.0
    utility.persistence_loss = 0.0
    utility.recent_gain = -1.0
    utility.negative_streak = 8

    bridge.tick({"sense_a": 0.25}, tick=3)

    assert bridge._predictor_retirement == {}



def test_capacity_pressure_retires_only_one_predictor_at_a_time():
    nodes = (
        PlasticNode(node_id="sense_a", kind=NodeKind.SENSE),
        PlasticNode(node_id="readout_core", kind=NodeKind.READOUT),
        PlasticNode(
            node_id="predictor_a",
            kind=NodeKind.PREDICTOR,
            predicts_node_id="readout_core",
        ),
        PlasticNode(
            node_id="predictor_b",
            kind=NodeKind.PREDICTOR,
            predicts_node_id="readout_core",
        ),
    )
    edges = (
        PlasticEdge(
            source_id="sense_a",
            target_id="predictor_a",
            kind=EdgeKind.PREDICTIVE,
            weight=1.0,
            plasticity=0.0,
            delay_ticks=0,
            support=32,
        ),
        PlasticEdge(
            source_id="sense_a",
            target_id="predictor_b",
            kind=EdgeKind.PREDICTIVE,
            weight=1.0,
            plasticity=0.0,
            delay_ticks=0,
            support=32,
        ),
    )
    graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())

    from dataclasses import replace
    genome = _capacity_genome()
    genome = replace(
        genome,
        development=replace(genome.development, soft_node_budget=4),
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )

    bridge.tick({"sense_a": 0.5}, tick=1)
    bridge.tick({"sense_a": -0.5}, tick=2)
    for predictor_id in ("predictor_a", "predictor_b"):
        utility = bridge._predictor_utility[predictor_id]
        utility.samples = 8
        utility.model_loss = 8.0
        utility.persistence_loss = 0.0
        utility.recent_gain = -1.0
        utility.negative_streak = 8
        utility.positive_streak = 0

    bridge.tick({"sense_a": 0.25}, tick=3)

    assert len(bridge._predictor_retirement) == 1
    assert next(iter(bridge._predictor_retirement)) in {
        "predictor_a",
        "predictor_b",
    }
