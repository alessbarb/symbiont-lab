from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_communication_view_is_passive_and_opaque():
    source = (ROOT / "render" / "communication.js").read_text()
    assert "Communication Live" in source
    assert "ground_truth" not in source
    assert "data.meaning" not in source
    assert "button" not in source.lower()


def test_sequence_fields_are_projected_without_evaluator_payload():
    adapter = (ROOT / "adapter.py").read_text()
    projection = (ROOT / "projection" / "snapshot.js").read_text()
    assert '"sequence_decisions"' in adapter
    assert "sequenceDecisions" in projection
    assert "ground_truth" not in adapter
