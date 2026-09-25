import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cognition_state_accepts_remove_node_mutations() -> None:
    schema = json.loads((ROOT / "cognition_state.schema.json").read_text(encoding="utf-8"))
    mutation_kind = schema["properties"]["mutations"]["items"]["properties"]["kind"]
    assert "remove_node" in mutation_kind["enum"]
