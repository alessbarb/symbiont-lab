from __future__ import annotations

import pytest
from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import StructuralPlasticity
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.host.adaptive import AdaptiveSenseModel
from symbiont.host.checkpoint import normalize_checkpoint
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


def test_under_sampled_seen_surface_stays_dormant_after_restore_without_stats() -> None:
    model = AdaptiveSenseModel(
        min_samples=4,
        active_limit=2,
        max_candidates=8,
        relation_window=4,
        exploration_limit=4,
        probe_limit=1,
    )
    model.observe((_reading("candidate.private", 123.25),))

    payload = model.export()

    assert payload["states"] == []
    assert len(payload["known_capability_fingerprints"]) == 1
    assert "candidate.private" not in str(payload["known_capability_fingerprints"])

    restored = AdaptiveSenseModel.restore(payload)
    plan = restored.sampling_plan(("candidate.private", "brand-new"))

    assert restored.states == ()
    assert plan.dormant_count == 1
    assert plan.unknown_count == 1


def test_v4_checkpoint_normalizes_once_for_all_resident_subsystems() -> None:
    v4 = {
        "schema_version": 4,
        "saved_at_tick": 38,
        "sensory_development": {
            "states": [
                {
                    "capability_id": "compute.logical_cpu",
                    "percept_name": "sense_example",
                    "samples": 8,
                    "available_samples": 8,
                    "mean": 1.0,
                    "m2": 2.0,
                    "delta_ewma": 0.1,
                }
            ]
        },
        "cognitive_bridge": {"graph": None},
    }

    normalized = normalize_checkpoint(v4)

    assert v4["schema_version"] == 4
    assert normalized["schema_version"] == 11  # ADR-0042 rhythm step, then v11 identity
    fingerprints = normalized["sensory_development"]["known_capability_fingerprints"]
    assert len(fingerprints) == 1
    assert len(fingerprints[0]) == 64
    assert normalized["cognitive_bridge"]["previous_frame"] == {}
    assert normalized["cognitive_bridge"]["structural_plasticity"] == {}


def test_p5_p11_previous_frame_is_never_exported_and_cold_starts_on_restore() -> None:
    """PR2 supersedes PR #76's continuity guarantee for this exact test
    (design §2.1): the checkpoint must never let a restart reconstruct the
    prior tick's activation. delay_ticks=1 edges therefore see a genuine
    cold (0.0) source on the first post-restore tick, not the pre-restart
    value."""
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="s", kind=NodeKind.SENSE),
            PlasticNode(node_id="c", kind=NodeKind.CONCEPT),
            PlasticNode(node_id="r", kind=NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(
                source_id="s",
                target_id="c",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=0,
            ),
            PlasticEdge(
                source_id="c",
                target_id="r",
                kind=EdgeKind.EXCITATORY,
                weight=0.5,
                plasticity=0.5,
                delay_ticks=1,
            ),
        ),
        kernel_limits=limits,
    )
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    first = bridge.tick({"s": 5.0}, tick=1)
    assert abs(first.activations["c"]) > 0.1  # real, non-trivial activation before any restart

    payload = bridge.export_checkpoint()
    assert "previous_frame" not in payload
    restored = CognitiveBridge.restore(payload, genome=genome, kernel_limits=limits)
    assert restored is not None

    # Cold start: feeding 0.0 this tick, the delay=1 edge (c->r) reads from
    # a previous_frame that is genuinely empty, not the pre-restart "c"
    # activation -- so "r" sees no contribution from "c" this tick.
    second = restored.tick({"s": 0.0}, tick=1)
    assert second.readouts["r"] == pytest.approx(0.0)


def test_structural_candidate_support_survives_restart() -> None:
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="a", kind=NodeKind.CONCEPT),
            PlasticNode(node_id="b", kind=NodeKind.CONCEPT),
        ),
        edges=(),
        kernel_limits=limits,
    )
    plasticity = StructuralPlasticity(
        min_candidate_support=3,
        tentative_lifetime_ticks=16,
        cooldown_ticks=16,
    )
    plasticity.observe_coactivation(
        source_id="a", target_id="b", source_active=True, target_active=True, tick=1
    )
    plasticity.observe_coactivation(
        source_id="a", target_id="b", source_active=True, target_active=True, tick=2
    )

    restored = StructuralPlasticity.restore_checkpoint(
        plasticity.export_checkpoint(),
        min_candidate_support=3,
        tentative_lifetime_ticks=16,
        cooldown_ticks=16,
        allowed_node_ids={"a", "b"},
    )
    restored.observe_coactivation(
        source_id="a", target_id="b", source_active=True, target_active=True, tick=3
    )

    mutations = restored.propose(graph, kernel_limits=limits, tick=3)

    assert len(mutations) == 1
    assert mutations[0].kind == "add_edge"
