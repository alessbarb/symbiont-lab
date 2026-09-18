import json
from pathlib import Path

from observatory.adapter import project_tick
from observatory.schema_validate import validate
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import RelationLedger, ResourceEvidence


def test_real_runtime_tick_projects_to_valid_v3_snapshot():
    runtime = OrganismRuntime()
    result = runtime.tick()
    snapshot = project_tick(
        result,
        body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
        signal_knowledge=result.signal_knowledge,
        knowledge_events=result.knowledge_events,
        signal_references=result.signal_references,
    )
    schema_path = Path(__file__).parents[1] / "schemas" / "snapshot.schema.json"
    validate(
        snapshot,
        json.loads(schema_path.read_text(encoding="utf-8")),
        schema_root=schema_path.parent,
    )
    assert snapshot["schema_version"] == 3
    assert "body_schema" in snapshot["organism"]
    assert "signal_knowledge" in snapshot["organism"]
    assert snapshot["organism"]["metabolism"]["pressure"] in {"normal", "elevated", "severe", "unrecoverable", "unknown"}
    assert snapshot["organism"]["physiology"]["resting_requested"] is False


def test_social_projection_preserves_directional_evidence_fields():
    runtime = OrganismRuntime()
    result = runtime.tick()
    ledger = RelationLedger()
    relation = ledger.observe("a", "b", benefit=1.5, cost=0.25, reciprocal=True, conflict=True, tick=0)
    snapshot = project_tick(result, body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count), social_relations=(relation,))
    validate(snapshot, json.loads((Path(__file__).parents[1] / "schemas" / "snapshot.schema.json").read_text()), schema_root=Path(__file__).parents[1] / "schemas")
    assert snapshot["organism"]["social_relations"][0]["reciprocal_observations"] == 1
    assert snapshot["organism"]["social_relations"][0]["conflicts"] == 1
    assert snapshot["organism"]["social_relations"][0]["rejections"] == 0
    assert snapshot["organism"]["social_relations"][0]["support"] == 1.5
    assert snapshot["organism"]["social_relations"][0]["harm"] == 0.25
    assert 0.0 < snapshot["organism"]["social_relations"][0]["freshness"] <= 1.0


def test_social_resource_projection_preserves_local_availability_evidence():
    runtime = OrganismRuntime()
    result = runtime.tick()
    snapshot = project_tick(
        result,
        body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
        social_resource_evidence=(ResourceEvidence("opaque-token", requested=2.0, granted=1.0,
                                                   observations=2, denied=1, last_tick=0),),
    )
    validate(snapshot, json.loads((Path(__file__).parents[1] / "schemas" / "snapshot.schema.json").read_text()), schema_root=Path(__file__).parents[1] / "schemas")
    item = snapshot["organism"]["social_resource_evidence"][0]
    assert item["token"] == "opaque-token"
    assert item["availability"] == 0.5
    assert item["denied"] == 1


def test_runtime_projection_exposes_bounded_degradation_counters():
    runtime = OrganismRuntime()
    result = runtime.tick()
    snapshot = project_tick(
        result,
        body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
    )
    validate(snapshot, json.loads((Path(__file__).parents[1] / "schemas" / "snapshot.schema.json").read_text()), schema_root=Path(__file__).parents[1] / "schemas")
    assert snapshot["organism"]["degradation"] == {"retained_items": 0, "excreted_units": 0}


def test_social_projection_preserves_context_and_reliability():
    runtime = OrganismRuntime()
    result = runtime.tick()
    ledger = RelationLedger()
    relation = ledger.observe("a", "b", benefit=1.0, conflict=True, tick=0, channel="opaque-food")
    snapshot = project_tick(result, body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count), social_relations=(relation,))
    item = snapshot["organism"]["social_relations"][0]
    assert item["channel"] == "opaque-food"
    assert 0.0 <= item["reliability"] <= 1.0


def test_observer_provenance_projects_without_entering_organism():
    runtime = OrganismRuntime()
    result = runtime.tick()
    signal_id = "signal." + "b" * 64
    snapshot = project_tick(
        result,
        body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
        observer_provenance=({
            "signal_id": signal_id,
            "label": "Temperature",
            "category": "thermal",
            "scope": "external",
            "value": 51.25,
            "unit": "°C",
            "quality": "nominal",
        },),
    )
    schema_path = Path(__file__).parents[1] / "schemas" / "snapshot.schema.json"
    validate(snapshot, json.loads(schema_path.read_text(encoding="utf-8")), schema_root=schema_path.parent)
    assert snapshot["observer"]["signal_provenance"][0]["label"] == "Temperature"
    assert "observer" not in snapshot["organism"]
