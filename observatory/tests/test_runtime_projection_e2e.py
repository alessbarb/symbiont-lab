import json
from pathlib import Path

from observatory.adapter import project_tick
from observatory.schema_validate import validate
from symbiont.core.runtime import OrganismRuntime


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
