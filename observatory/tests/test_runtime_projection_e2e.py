import json
from pathlib import Path

from observatory.adapter import project_tick
from observatory.schema_validate import validate
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import RelationLedger
from symbiont.core.social.relations import ResourceEvidence


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


def test_embodiment_projection_is_bounded_passive_and_schema_valid():
    runtime = OrganismRuntime()
    result = runtime.tick()
    embodiment = {
        "embodiment_id": "embodiment.test",
        "body_id": "body.test",
        "epoch": 3,
        "embodiment_tick": 41,
        "contract_fingerprint": "a" * 64,
        "state": "active",
        "adaptation": {
            "prediction_error_recent": 0.125,
            "prediction_shock": 0.25,
            "schema_uncertainty": 0.30,
            "causal_confidence": 0.60,
            "controllability_confidence": 0.55,
            "competence_revalidation_ratio": 0.40,
            "disruption_score": 0.30,
            "adaptation_ticks": 41,
            "recovery_tick": None,
            "private_raw_state": {"must": "not escape"},
        },
        "dynamics": {
            "relation_count": 17,
            "mean_prediction_error": 0.125,
            "weights": {"private": 1.0},
        },
        "embodied_competences": {
            "count": 4,
            "executable": 2,
            "items": [{"private": True}],
        },
        "physical_anatomy": {"joint_names": ["forbidden"]},
    }
    snapshot = project_tick(result, embodiment_state=embodiment)
    schema_path = Path(__file__).parents[1] / "schemas" / "snapshot.schema.json"
    validate(
        snapshot,
        json.loads(schema_path.read_text(encoding="utf-8")),
        schema_root=schema_path.parent,
    )

    assert snapshot["schema_version"] == 3
    projected = snapshot["organism"]["embodiment"]
    assert projected["embodiment_id"] == "embodiment.test"
    assert projected["body_id"] == "body.test"
    assert projected["epoch"] == 3
    assert projected["embodiment_tick"] == 41
    assert projected["execution"] == {
        "binding_count": 4,
        "executable_count": 2,
    }
    assert snapshot["organism"]["body_schema"]["state"] == "undeveloped"
    serialized = json.dumps(projected)
    assert "joint_names" not in serialized
    assert "physical_anatomy" not in serialized
    assert "weights" not in serialized
    assert "private_raw_state" not in serialized


def test_invalid_embodiment_projection_fails_closed_without_changing_snapshot_version():
    runtime = OrganismRuntime()
    result = runtime.tick()
    snapshot = project_tick(
        result,
        embodiment_state={
            "embodiment_id": "",
            "body_id": "body.test",
            "contract_fingerprint": "x",
        },
    )
    assert snapshot["schema_version"] == 1
    assert "embodiment" not in snapshot["organism"]
