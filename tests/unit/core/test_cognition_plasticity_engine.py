from __future__ import annotations

from symbiont.cognition.checkpoint import quantize_weight
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition.plasticity_state import PlasticityEngine


def test_plasticity_engine_preserves_construction_weight_class_until_consolidated() -> None:
    limits = KernelLimits()
    edge = PlasticEdge(
        source_id="sense_a",
        target_id="readout_core",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=0,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("sense_a", NodeKind.SENSE),
            PlasticNode("readout_core", NodeKind.READOUT),
        ),
        edges=(edge,),
        kernel_limits=limits,
    )
    engine = PlasticityEngine(kernel_limits=limits)
    engine.seed_new_edges(graph)

    edge.weight = 1.9

    overrides = engine.weight_class_overrides(graph)
    assert overrides[("sense_a", "readout_core", EdgeKind.EXCITATORY.value)] == quantize_weight(0.5)



def test_plasticity_engine_applies_homeostatic_value_to_existing_action_relation() -> None:
    limits = KernelLimits()
    edge = PlasticEdge(
        source_id="concept_a",
        target_id="readout_motor:hip",
        kind=EdgeKind.EXCITATORY,
        weight=0.5,
        plasticity=0.5,
        delay_ticks=1,
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode("concept_a", NodeKind.CONCEPT),
            PlasticNode("readout_motor:hip", NodeKind.READOUT),
        ),
        edges=(edge,),
        kernel_limits=limits,
    )
    engine = PlasticityEngine(kernel_limits=limits)

    changed = engine.apply_homeostatic_value(
        graph,
        concept_ids={"concept_a"},
        readout_id="readout_motor:hip",
        value=0.5,
        tick=7,
    )

    assert changed is True
    assert edge.weight == 0.6
    assert edge.last_use_tick == 7
    assert edge.support == 1



def test_plasticity_engine_decay_retiring_edge_preserves_reversible_schedule() -> None:
    edge = PlasticEdge(
        source_id="predictor_a",
        target_id="readout_core",
        kind=EdgeKind.PREDICTIVE,
        weight=1.0,
        plasticity=0.5,
        delay_ticks=0,
    )
    engine = PlasticityEngine(kernel_limits=KernelLimits())

    engine.decay_retiring_edge(
        edge,
        tick=8,
        retiring_predictors={"predictor_a": 0},
        structural_wait=0,
        tentative_lifetime_ticks=4,
    )

    assert edge.weight == 0.99
