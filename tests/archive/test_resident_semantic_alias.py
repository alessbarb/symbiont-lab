from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from symbiont.core.runtime import OrganismRuntime

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.host.adaptive import AdaptiveSenseModel
from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
from symbiont.host.lifecycle import LifecycleSnapshot
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

_GENOME_PAYLOAD = {
    "schema_version": 2,
    "genome_id": "genome_v2_continuity00000000000000",
    "kernel_compatibility": ">=0.80,<1.00",
    "development": {
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "sense_node_budget": 32,
        "capacity_growth_sensitivity": 0.5,
        "consolidation_interval_ticks": 32,
    },
    "plasticity": {
        "learning_rate": {"baseline": 0.02, "min": 0.001, "max": 0.08, "adaptation_rate": 0.002},
        "eligibility_decay": 0.9,
        "structural_plasticity": {
            "baseline": 0.5,
            "min": 0.05,
            "max": 1.0,
            "adaptation_rate": 0.01,
        },
    },
    "regulation": {
        "uncertainty_gain": 0.5,
        "novelty_gain": 0.4,
        "prediction_error_gain": 0.5,
        "controllability_loss_gain": 0.5,
        "embodiment_mismatch_gain": 0.7,
        "regulation_smoothing": 0.1,
        "regulation_decay": 0.02,
    },
    "sensorimotor": {
        "spontaneous_activity_baseline": 0.1,
        "uncertainty_exploration_gain": 0.5,
        "prediction_error_exploration_gain": 0.5,
        "exploration_habituation": 0.01,
        "reacclimation_sensitivity": 0.7,
    },
    "structure": {
        "growth_threshold": {
            "baseline": 0.18,
            "min": 0.0,
            "max": 0.5800000000000001,
            "adaptation_rate": 0.01,
        },
        "pruning_threshold": {
            "baseline": 0.01,
            "min": 0.0,
            "max": 0.21000000000000002,
            "adaptation_rate": 0.005,
        },
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "evolvability": {
        "development_mutation_scale": 0.05,
        "plasticity_mutation_scale": 0.05,
        "regulation_mutation_scale": 0.05,
        "sensorimotor_mutation_scale": 0.05,
        "structure_mutation_scale": 0.05,
        "recombination_linkage": 0.5,
    },
}


def _genome():
    return GenomeCodec().load(_GENOME_PAYLOAD)


def _reading(capability_id: str, value: float, tick: int = 1) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="fixture",
        value=value,
        unit=Unit.COUNT,
        monotonic_timestamp_ns=tick,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


@pytest.mark.superseded(
    by="tests/unit/core/test_semantic_bootstrap_aliasing.py::test_without_semantic_bootstrap_the_example_graph_stays_legitimately_disconnected",
    reason="Asserts the semantic graph alias of a hand-labelled sense; semantic bootstrap is not part of the canonical profile v1.",
)
def test_mature_opaque_sense_keeps_semantic_graph_alias_without_double_counting() -> None:
    adaptive = AdaptiveSenseModel(
        min_samples=2,
        active_limit=1,
        max_candidates=8,
        relation_window=4,
        exploration_limit=4,
        probe_limit=1,
    )
    adaptive.observe(
        (
            _reading("compute.logical_cpu", 4.0, 1),
            _reading("candidate.variable", 1.0, 1),
        )
    )
    adaptive.observe(
        (
            _reading("compute.logical_cpu", 4.0, 2),
            _reading("candidate.variable", 10.0, 2),
        )
    )
    learned_name = adaptive.developed_percept_names()["compute.logical_cpu"]
    assert "compute.logical_cpu" not in adaptive.percept_names()

    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="system_load", kind=NodeKind.SENSE),
            PlasticNode(node_id="readout_pressure", kind=NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(
                source_id="system_load",
                target_id="readout_pressure",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
            ),
        ),
        kernel_limits=limits,
    )
    runtime = OrganismRuntime(
        discover_senses=True,
        bootstrap_semantic_senses=True,
        adaptive_senses=adaptive,
        genome=_genome(),
        kernel_limits=limits,
        cognitive_graph=graph,
        min_samples=1,
        investigate_ticks=0,
    )
    capability = Capability("compute.logical_cpu", CapabilityKind.SIGNAL, "fixture")
    snapshot = LifecycleSnapshot(
        1,
        HostManifest(1, (capability,), ()),
        (_reading("compute.logical_cpu", 8.0, 3),),
        (),
        (),
        ("compute.logical_cpu",),
    )
    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: snapshot, clock=time.perf_counter)

    result = runtime.tick()

    assert [percept.name for percept in result.percepts] == [learned_name]
    assert set(result.drift_observations) == {learned_name}
    assert result.cognition is not None
    assert abs(result.cognition.activations["system_load"]) > 0.1
    assert abs(result.cognition.readouts["readout_pressure"]) > 0.01
