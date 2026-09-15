import json
from pathlib import Path
from types import SimpleNamespace

from observatory.adapter import _cognition_state


ROOT = Path(__file__).parent


def test_cognition_schema_declares_reversible_topology_health_states() -> None:
    schema = json.loads((ROOT / "cognition_state.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["topology_health"]["enum"] == [
        "germinal",
        "developing",
        "connected",
        "adaptive",
        "degenerate",
        "recovering",
    ]
    assert schema["properties"]["recovering"] == {"type": "boolean"}


def test_adapter_projects_topology_health_without_raw_structural_state() -> None:
    cognition = SimpleNamespace(
        topology_revision=29,
        topology_health=SimpleNamespace(value="recovering"),
        recovering=True,
        readouts={"readout_core": 0.0},
        prediction_errors=(),
        mutations=(),
        consecutive_failures=0,
        frozen=False,
    )

    state = _cognition_state(cognition)

    assert state["topology_revision"] == 29
    assert state["topology_health"] == "recovering"
    assert state["recovering"] is True
    assert "graph" not in state
    assert "weights" not in state
