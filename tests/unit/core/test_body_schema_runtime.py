from __future__ import annotations

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.runtime import OrganismRuntime


def _cognitive_runtime() -> OrganismRuntime:
    limits = KernelLimits()
    genome = GenomeCodec().load(
        {
            "schema_version": 1,
            "genome_id": "genome_body_schema_runtime000001",
            "parent_ids": [],
            "kernel_compatibility": ">=0.55,<0.60",
            "development": {
                "initial_concepts": 1,
                "soft_node_budget": 16,
                "soft_edge_budget": 32,
                "consolidation_interval_ticks": 32,
                "sense_node_budget": 8,
                "sense_retention_ticks": 256,
            },
            "plasticity": {
                "learning_rate": {"initial": 0.02, "min": 0.001, "max": 0.08},
                "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
                "eligibility_decay": 0.9,
            },
            "structure": {
                "grow_threshold": 0.18,
                "prune_threshold": 0.05,
                "minimum_support": 16,
                "tentative_lifetime_ticks": 256,
            },
            "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
        }
    )
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(
                node_id="private_concept_runtime_fixture",
                kind=NodeKind.CONCEPT,
                bias=0.8,
                tau=1.0,
            ),
        ),
        edges=(),
        kernel_limits=limits,
    )
    return OrganismRuntime(
        discover_senses=False,
        bootstrap_semantic_senses=False,
        min_samples=1,
        investigate_ticks=0,
        genome=genome,
        kernel_limits=limits,
        cognitive_graph=graph,
    )


def test_runtime_starts_with_undeveloped_body_schema():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)

    assert runtime.body_schema.state == "undeveloped"
    assert runtime.body_schema.part_count == 0
    assert runtime.checkpoint()["body_schema"]["state"] == "undeveloped"


def test_runtime_learns_developing_sensory_body_from_established_self_model():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)

    runtime.run(10)
    payload = runtime.body_schema.export_representation(current_tick=runtime.tick_count)

    assert payload["state"] in {"developing", "established", "revising"}
    assert payload["parts"]
    assert all(part["kind"] == "sense" for part in payload["parts"])
    assert payload["dependencies"] == []
    assert "id_salt" not in payload
    # BodySchema ids are its own opaque namespace, not host capability ids.
    assert all(part["part_id"].startswith("part.sense.") for part in payload["parts"])


def test_runtime_cognitive_activity_consolidates_region_without_exposing_node_identity():
    runtime = _cognitive_runtime()

    runtime.run(4)
    public = runtime.body_schema.export_representation(current_tick=runtime.tick_count)
    private = runtime.checkpoint()["body_schema"]

    regions = [part for part in public["parts"] if part["kind"] == "cognitive_region"]
    assert len(regions) == 1
    assert regions[0]["part_id"].startswith("part.region.")
    assert "private_concept_runtime_fixture" not in repr(public)
    assert "private_concept_runtime_fixture" not in repr(private)
    assert "channel.cognition." not in repr(public)
    assert "channel.cognition." in repr(private["cognitive_learning"])


def test_equal_cognitive_graphs_use_distinct_private_channel_namespaces_per_organism():
    first = _cognitive_runtime()
    second = _cognitive_runtime()

    first.tick()
    second.tick()
    first_learning = first.checkpoint()["body_schema"]["cognitive_learning"]
    second_learning = second.checkpoint()["body_schema"]["cognitive_learning"]
    first_channel = first_learning["channel_support"][0]["channel_id"]
    second_channel = second_learning["channel_support"][0]["channel_id"]

    assert first_channel != second_channel


def test_cognitive_body_schema_checkpoint_round_trip_preserves_region_and_namespace():
    runtime = _cognitive_runtime()
    runtime.run(4)
    checkpoint = runtime.checkpoint()
    before = runtime.body_schema.export_representation(current_tick=runtime.tick_count)

    restored = OrganismRuntime.from_checkpoint(
        checkpoint,
        discover_senses=False,
        bootstrap_semantic_senses=False,
        min_samples=1,
        investigate_ticks=0,
    )

    assert restored.body_schema.export(current_tick=restored.tick_count) == checkpoint["body_schema"]
    assert restored.body_schema.export_representation(current_tick=restored.tick_count) == before


def test_runtime_checkpoint_round_trip_preserves_body_schema_and_private_identity_namespace():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()
    before_representation = runtime.body_schema.export_representation(current_tick=runtime.tick_count)

    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0)

    assert restored.body_schema.export(current_tick=restored.tick_count) == checkpoint["body_schema"]
    assert restored.body_schema.export_representation(current_tick=restored.tick_count) == before_representation
    assert "id_salt" in checkpoint["body_schema"]
    assert "id_salt" not in before_representation


def test_old_checkpoint_without_body_schema_restores_cold_and_learns_later():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()
    checkpoint.pop("body_schema")

    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0)

    assert restored.body_schema.state == "undeveloped"
    restored.tick()
    assert restored.body_schema.state in {"developing", "established", "revising"}


def test_checkpoint_body_schema_never_contains_raw_self_model_keys():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()

    serialized_body = repr(checkpoint["body_schema"])
    for sense_id in checkpoint["self_model"]:
        assert sense_id not in serialized_body
