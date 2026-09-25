from __future__ import annotations

from dataclasses import replace

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, StructuralPlasticity
from symbiont.cognition.types import EdgeKind, NodeKind


def _base(*, reacclimation_ticks: int = 1):
    limits = KernelLimits(reacclimation_ticks=reacclimation_ticks)
    genome, _ = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 16),
    )
    return limits, genome


def _path_graph(limits: KernelLimits) -> CognitiveGraph:
    return CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
            PlasticNode("readout_core", NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(
                source_id="sense_a",
                target_id="concept_a",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
                support=8,
            ),
            PlasticEdge(
                source_id="concept_a",
                target_id="readout_core",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=1,
                support=8,
            ),
        ),
        kernel_limits=limits,
    )


def test_adversarial_terminal_failure_rolls_back_entire_graph_transaction(
    monkeypatch,
) -> None:
    limits, genome = _base()
    genome = replace(
        genome,
        development=replace(
            genome.development,
            consolidation_interval_ticks=1,
        ),
        structure=replace(
            genome.structure,
            tentative_lifetime_ticks=2,
        ),
    )
    edge = PlasticEdge(
        source_id="sense_a",
        target_id="concept_a",
        kind=EdgeKind.EXCITATORY,
        weight=0.05,
        plasticity=0.5,
        delay_ticks=0,
        support=0,
        age_ticks=2,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
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

    def invalid_terminal_proposal(
        self,
        active_graph,
        *,
        kernel_limits,
        tick,
        max_mutations=None,
    ):
        del self, active_graph, kernel_limits, tick, max_mutations
        return (
            Mutation(
                kind="add_edge",
                payload={
                    "source_id": "missing_source",
                    "target_id": "concept_a",
                    "kind": EdgeKind.EXCITATORY,
                    "weight": 0.05,
                    "plasticity": 0.5,
                    "delay_ticks": 1,
                },
            ),
        )

    monkeypatch.setattr(
        StructuralPlasticity,
        "propose",
        invalid_terminal_proposal,
    )

    result = bridge.tick({"sense_a": 1.0}, tick=1)

    assert bridge.graph is graph
    assert bridge.graph.edges == (edge,)
    assert result.structural_mutations_applied == 0
    assert result.mutations == ()
    assert result.topology_revision == 0


def test_adversarial_checkpoint_restore_is_a_durable_state_fixed_point() -> None:
    limits, genome = _base()
    bridge = CognitiveBridge(
        graph=_path_graph(limits),
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    for tick in range(1, 13):
        bridge.tick({"sense_a": 1.0}, tick=tick)

    payload = bridge.export_checkpoint()
    restored = CognitiveBridge.restore(
        payload,
        genome=genome,
        kernel_limits=limits,
    )

    assert restored is not None
    assert restored.export_checkpoint() == payload


def test_adversarial_primitive_retraction_is_visible_before_activation() -> None:
    limits, genome = _base()
    primitive_id = "walk"
    readout_id = f"readout_primitive:{primitive_id}"
    edge = PlasticEdge(
        source_id="concept_a",
        target_id=readout_id,
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=1,
        support=8,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("concept_a", NodeKind.CONCEPT),
            PlasticNode(readout_id, NodeKind.READOUT),
        ),
        edges=(edge,),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=False,
    )

    result = bridge.tick({}, tick=1, active_primitive_ids=())

    assert bridge.graph.node_by_id(readout_id) is None
    assert bridge.graph.edges == ()
    assert result.primitive_readouts == {}
    assert result.topology_revision == 1
