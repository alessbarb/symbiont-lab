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
