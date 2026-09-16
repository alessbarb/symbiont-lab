import json
from pathlib import Path

from observatory.adapter import project_tick
from observatory.schema_validate import validate
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import RelationLedger


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
