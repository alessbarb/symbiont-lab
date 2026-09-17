import json
import ast
from pathlib import Path

from ._node_harness import call_js, requires_node


ROOT = Path(__file__).parents[1]


def test_telemetry_projection_and_views_are_passive_and_separate():
    adapter = (ROOT / "adapter.py").read_text()
    projection = (ROOT / "projection" / "snapshot.js").read_text()
    view = (ROOT / "render" / "population-communication.js").read_text()
    assert "population_telemetry" in adapter
    assert "boundedPopulationTelemetry" in projection
    assert "ground_truth" not in adapter
    assert "meaning =" not in view
    assert "No meaning or historical relation is inferred" in view


def test_aggregator_only_builds_edges_from_exported_delivery_events():
    source = (ROOT / "communication" / "aggregator.js").read_text()
    assert '"DELIVER", "RECEIVE", "RETRANSMIT"' in source
    assert "without an underlying runtime event" in source
    assert "ground_truth" not in source


def test_runtime_package_does_not_import_observatory():
    imported = []
    for path in (ROOT.parent / "src" / "symbiont").rglob("*.py"):
        tree = ast.parse(path.read_text())
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        imported.extend(alias.name.lower() for node in imports for alias in node.names)
    assert not any("observatory" in name for name in imported)


@requires_node
def test_aggregator_reconstructs_edges_only_from_exported_events():
    result = call_js(ROOT / "communication" / "aggregator.js", "aggregateCommunicationTelemetry", {
        "events": [
            {"eventId": "e1", "tick": 1, "kind": "DELIVER", "senderId": "A", "receiverId": "B", "messageId": "m", "symbols": ["S1"], "cost": 1},
            {"eventId": "e2", "tick": 2, "kind": "EMIT", "senderId": "B", "receiverId": "C", "messageId": "m", "symbols": ["S1"], "cost": 1},
        ],
    })
    assert result["edges"] == [{"senderId": "A", "receiverId": "B", "count": 1, "firstTick": 1, "lastTick": 1, "messages": ["m"]}]
    assert result["messages"][0]["useCount"] == 2


@requires_node
def test_aggregator_honours_source_truncation_boundary():
    result = call_js(ROOT / "communication" / "aggregator.js", "aggregateCommunicationTelemetry", {
        "events": [
            {"eventId": "old", "tick": 1, "kind": "DELIVER", "senderId": "A", "receiverId": "B", "messageId": "m", "symbols": ["S1"], "cost": 1},
            {"eventId": "new", "tick": 5, "kind": "DELIVER", "senderId": "B", "receiverId": "C", "messageId": "m", "symbols": ["S1"], "cost": 1},
        ], "historyTruncated": True, "earliestAvailableTick": 5,
    })
    assert result["edges"] == [{"senderId": "B", "receiverId": "C", "count": 1, "firstTick": 5, "lastTick": 5, "messages": ["m"]}]
    assert result["historyTruncated"] is True


def test_population_telemetry_view_has_no_mutating_controls():
    source = (ROOT / "render" / "population-communication.js").read_text()
    assert "fetch(" not in source
    assert "updateUiState" not in source
    assert "innerHTML" in source


def test_local_snapshot_telemetry_is_aggregated_without_changing_runtime_state():
    app = (ROOT / "app.js").read_text()
    assert "createCommunicationAggregator" in app
    assert "localCommunicationAggregator.ingest(projection.populationTelemetry" in app
    assert "localCommunication" in app
    assert "updateUiState" in app
