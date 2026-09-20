import json

from symbiont.core.portable import (
    export_symbiont,
    load_symbiont_file,
    restore_symbiont,
    save_symbiont_file,
)
from symbiont.core.symbiont import Symbiont


def _experienced_subject() -> Symbiont:
    subject = Symbiont("portable-subject", seed=91)
    subject.register_output_channels(["out.0", "out.1", "out.2"])
    for tick in range(24):
        subject.step(
            {
                "in.0": (tick % 5) / 4.0,
                "in.1": ((tick * 3) % 7) / 6.0,
            }
        )
    return subject


def test_portable_symbiont_round_trip_preserves_cognitive_continuity():
    original = _experienced_subject()
    restored = restore_symbiont(export_symbiont(original))

    assert restored.symbiont_id == original.symbiont_id
    assert restored.total_ticks == original.total_ticks
    assert restored.body_schema.overall_confidence == original.body_schema.overall_confidence
    assert restored.sensorimotor_model.weights == original.sensorimotor_model.weights
    assert restored.agency_model.agency_confidence == original.agency_model.agency_confidence

    # RNG continuity matters: the same next experience must produce the same
    # exploratory action after a save/restore boundary.
    next_input = {"in.0": 0.23, "in.1": 0.77}
    assert restored.step(next_input) == original.step(next_input)


def test_portable_file_is_body_independent(tmp_path):
    subject = _experienced_subject()
    path = save_symbiont_file(subject, tmp_path / "one.symbiont.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["artifact_type"] == "portable-symbiont"
    assert "body_id" not in payload
    assert "embodiment_id" not in payload
    assert "physical_state" not in payload

    restored = load_symbiont_file(path)
    assert restored.total_ticks == subject.total_ticks
    assert restored.symbiont_id == subject.symbiont_id


def test_previous_body_channels_remain_experience_not_physical_bindings():
    subject = _experienced_subject()
    restored = restore_symbiont(export_symbiont(subject))

    assert restored.current_output_channels == {"out.0", "out.1", "out.2"}
    # Implantation may replace the current surface while retaining history.
    restored.register_output_channels(["out.0", "out.1"])
    assert restored.current_output_channels == {"out.0", "out.1"}
    assert {"out.0", "out.1", "out.2"} <= restored.historical_output_channels
