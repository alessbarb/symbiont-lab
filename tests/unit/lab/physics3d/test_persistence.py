import json
import zipfile
from dataclasses import dataclass

from symbiont_lab.physics3d.persistence import (
    TelemetryWriter,
    load_symbiont_bundle,
    save_symbiont_bundle,
)


def test_portable_symbiont_bundle_carries_runtime_and_private_model_artifacts(tmp_path):
    model_id = "a" * 64
    models = tmp_path / "models"
    models.mkdir()
    (models / f"{model_id}.json").write_text('{"manifest":true}', encoding="utf-8")
    (models / f"{model_id}.pt").write_bytes(b"weights")
    (models / f"{model_id}.tokenizer.json").write_text(
        json.dumps({"vocabulary": ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>"]}),
        encoding="utf-8",
    )
    payload = {
        "organism_id": "portable",
        "saved_at_tick": 123,
        "private_model_registry": {
            "records": [{"model_id": model_id}],
        },
    }

    bundle = save_symbiont_bundle(payload, models, tmp_path / "subject.symbiont")

    with zipfile.ZipFile(bundle, "r") as archive:
        names = set(archive.namelist())
    assert "runtime.json" in names
    assert f"models/{model_id}.json" in names
    assert f"models/{model_id}.pt" in names
    assert f"models/{model_id}.tokenizer.json" in names

    restored_models = tmp_path / "restored-models"
    restored = load_symbiont_bundle(bundle, restored_models)
    assert restored == payload
    assert (restored_models / f"{model_id}.pt").read_bytes() == b"weights"


def test_portable_bundle_does_not_contain_body_state(tmp_path):
    payload = {
        "organism_id": "portable",
        "saved_at_tick": 5,
        "private_model_registry": {"records": []},
    }
    bundle = save_symbiont_bundle(
        payload,
        tmp_path / "models",
        tmp_path / "subject.symbiont",
    )

    with zipfile.ZipFile(bundle, "r") as archive:
        runtime = json.loads(archive.read("runtime.json"))
        names = set(archive.namelist())

    assert runtime["organism_id"] == "portable"
    assert "body_state" not in runtime
    assert not any("body" in name for name in names)


def test_telemetry_writer_persists_new_dataclass_metrics_without_whitelist(tmp_path):
    @dataclass
    class Record:
        tick: int
        sensorimotor_patterns: int
        cognitive_motor_primitives: int
        passive_baseline_samples: int

    path = tmp_path / "telemetry.ndjson"
    writer = TelemetryWriter(path, flush_every=1)
    try:
        writer.append(
            Record(
                tick=7,
                sensorimotor_patterns=23,
                cognitive_motor_primitives=2,
                passive_baseline_samples=5,
            )
        )
    finally:
        writer.close()

    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload == {
        "cognitive_motor_primitives": 2,
        "passive_baseline_samples": 5,
        "sensorimotor_patterns": 23,
        "tick": 7,
    }


def test_load_telemetry_records(tmp_path):
    import pytest

    from symbiont_lab.physics3d.persistence import load_telemetry_records

    path = tmp_path / "telemetry.ndjson"
    lines = [
        json.dumps({"tick": 1, "schema_confidence": 0.2}),
        "   ",
        "invalid json line",
        json.dumps({"tick": 2, "schema_confidence": 0.5}),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

    # Strict mode raises ValueError
    with pytest.raises(ValueError, match="corrupt telemetry record at line 3"):
        load_telemetry_records(path)

    # Resilient mode ignores invalid lines
    records = load_telemetry_records(path, ignore_errors=True)
    assert len(records) == 2
    assert records[0]["tick"] == 1
    assert records[0]["schema_confidence"] == 0.2
    assert records[1]["tick"] == 2
    assert records[1]["schema_confidence"] == 0.5


def test_load_telemetry_records_nonexistent_raises():
    from pathlib import Path

    import pytest

    from symbiont_lab.physics3d.persistence import load_telemetry_records

    with pytest.raises(FileNotFoundError):
        load_telemetry_records(Path("/nonexistent/file.ndjson"))
