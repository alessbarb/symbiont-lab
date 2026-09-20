import json
import zipfile

from symbiont_lab.physics3d.persistence import (
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
