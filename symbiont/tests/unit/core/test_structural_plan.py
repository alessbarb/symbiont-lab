from __future__ import annotations

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition.structural_planner import StructuralPlan


def _graph(limits: KernelLimits) -> CognitiveGraph:
    return CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("concept_a", NodeKind.CONCEPT),
        ),
        edges=(),
        kernel_limits=limits,
    )


def test_structural_plan_exposes_prior_stage_to_later_planning() -> None:
    limits = KernelLimits()
    plan = StructuralPlan.begin(
        _graph(limits),
        kernel_limits=limits,
        frozen=False,
        mutation_cap=4,
    )
    add_edge = Mutation(
        kind="add_edge",
        payload={
            "source_id": "sense_a",
            "target_id": "concept_a",
            "kind": EdgeKind.EXCITATORY,
            "weight": 0.1,
            "plasticity": 0.5,
            "delay_ticks": 1,
        },
    )
    assert plan.stage((add_edge,))
    assert len(plan.graph.edges) == 1
    assert len(plan.base_graph.edges) == 0


def test_terminal_unvalidated_mutation_can_reject_whole_transaction() -> None:
    limits = KernelLimits()
    plan = StructuralPlan.begin(
        _graph(limits),
        kernel_limits=limits,
        frozen=False,
        mutation_cap=4,
    )
    valid = Mutation(
        kind="add_node",
        payload={"node_id": "readout_core", "kind": NodeKind.READOUT},
    )
    invalid = Mutation(
        kind="add_edge",
        payload={
            "source_id": "missing",
            "target_id": "readout_core",
            "kind": EdgeKind.EXCITATORY,
            "weight": 0.1,
            "plasticity": 0.5,
            "delay_ticks": 1,
        },
    )
    assert plan.stage((valid,))
    assert plan.append_unvalidated((invalid,))

    candidate = plan.commit_candidate()

    assert candidate is plan.base_graph
    assert plan.base_graph.node_by_id("readout_core") is None
