import json
import zipfile
from dataclasses import dataclass

from lab.physics3d.persistence import (
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

    from lab.physics3d.persistence import load_telemetry_records

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

    from lab.physics3d.persistence import load_telemetry_records

    with pytest.raises(FileNotFoundError):
        load_telemetry_records(Path("/nonexistent/file.ndjson"))


def test_portable_bundle_contains_authoritative_manifest_and_validates_invariants(tmp_path):
    import hashlib

    from lab.physics3d.persistence import (
        read_symbiont_bundle_manifest,
        save_symbiont_bundle,
    )

    payload = {
        "organism_id": "symbiont:3d:test12345678",
        "saved_at_tick": 3785,
        "generation": 2,
        "schema_version": 9,
        "embodiment_lifecycle": {
            "epoch": 3,
            "state": "active",
            "current": {
                "body_id": "body.testbody123",
                "body_kind": "anthropomorphic-v6",
                "embodiment_id": "embodiment.testemb123",
                "receptor_count": 107,
                "effector_count": 62,
                "body_vital_state": "active",
            },
        },
        "living_body": {
            "age_ticks": 1945,
            "senescence": 0.05,
            "vital_state": "active",
        },
        "private_model_registry": {
            "records": [
                {"model_id": "m1", "state": "retired"},
                {"model_id": "m2", "state": "shadow"},
            ],
        },
        "experience_ledger": {
            "records": [{"tick": 1}, {"tick": 2}, {"tick": 3}],
        },
    }

    models = tmp_path / "models"
    models.mkdir()
    for suffix in (".json", ".pt", ".tokenizer.json"):
        (models / f"m2{suffix}").write_bytes(b"artifact")
    bundle = save_symbiont_bundle(
        payload,
        models,
        tmp_path / "subject.symbiont",
    )

    with zipfile.ZipFile(bundle, "r") as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "runtime.json" in names
        runtime_bytes = archive.read("runtime.json")
        expected_sha256 = f"sha256:{hashlib.sha256(runtime_bytes).hexdigest()}"

    manifest = read_symbiont_bundle_manifest(bundle, verify=True)
    assert manifest["saved_at_tick"] == 3785
    assert manifest["symbiont_tick"] == 3785
    assert manifest["tick"] == 3785
    assert manifest["embodiment_epoch"] == 3
    assert manifest["embodiment_id"] == "embodiment.testemb123"
    assert manifest["body_id"] == "body.testbody123"
    assert manifest["body_kind"] == "anthropomorphic-v6"
    assert manifest["body_age_ticks"] == 1945
    assert manifest["body_senescence"] == 0.05
    assert manifest["model_record_count"] == 2
    assert manifest["active_shadow_models"] == 1
    assert manifest["experience_count"] == 3
    assert manifest["checkpoint_hash"] == expected_sha256
    assert manifest["manifest_generated_from_checkpoint_hash"] == expected_sha256


def test_portable_bundle_syncs_external_organism_metadata(tmp_path):
    from lab.physics3d.persistence import (
        read_symbiont_bundle_manifest,
        save_symbiont_bundle,
    )

    org_dir = tmp_path / "organisms" / "org-testsync"
    org_dir.mkdir(parents=True)
    meta_path = org_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "ref": "org-testsync",
                "tick": 753,
                "models": 0,
                "embodiment_epoch": 1,
                "last_body_ref": "body-prev",
            }
        ),
        encoding="utf-8",
    )

    bundle_path = org_dir / "organism.symbiont"
    payload = {
        "organism_id": "symbiont:testsync",
        "saved_at_tick": 4000,
        "embodiment_lifecycle": {
            "epoch": 4,
            "state": "active",
            "current": {
                "body_id": "body.fresh4000",
                "body_kind": "anthropomorphic-v6",
                "embodiment_id": "embodiment.fresh4000",
            },
        },
        "living_body": {"age_ticks": 2000, "vital_state": "active"},
        "private_model_registry": {"records": [{"model_id": "m1", "state": "shadow"}]},
        "experience_ledger": {"records": [{"tick": 1}]},
    }

    models = tmp_path / "models"
    models.mkdir()
    for suffix in (".json", ".pt", ".tokenizer.json"):
        (models / f"m1{suffix}").write_bytes(b"artifact")
    save_symbiont_bundle(payload, models, bundle_path)

    updated_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = read_symbiont_bundle_manifest(bundle_path)

    # Invariants: external metadata matches internal bundle manifest exactly
    assert updated_meta["tick"] == 4000
    assert updated_meta["saved_at_tick"] == 4000
    assert updated_meta["embodiment_epoch"] == 4
    assert updated_meta["body_id"] == "body.fresh4000"
    assert updated_meta["embodiment_id"] == "embodiment.fresh4000"
    assert updated_meta["body_age_ticks"] == 2000
    assert updated_meta["models"] == 1
    assert updated_meta["experiences"] == 1
    assert updated_meta["ref"] == "org-testsync"
    assert updated_meta["last_body_ref"] == "body-prev"  # Preserved
    assert updated_meta["checkpoint_hash"] == manifest["checkpoint_hash"]


def test_portable_bundle_rejects_export_invariant_violations():
    import pytest

    from lab.physics3d.persistence import validate_bundle_export_invariants

    payload = {
        "saved_at_tick": 500,
        "embodiment_lifecycle": {
            "current": {
                "embodiment_id": "emb.1",
                "body_id": "body.1",
            }
        },
    }
    fake_sha = "abc123"

    # Mismatched tick
    bad_manifest = {
        "saved_at_tick": 999,
        "symbiont_tick": 999,
        "checkpoint_hash": f"sha256:{fake_sha}",
        "manifest_generated_from_checkpoint_hash": f"sha256:{fake_sha}",
        "embodiment_id": "emb.1",
        "body_id": "body.1",
    }
    with pytest.raises(ValueError, match="Export invariant violated: manifest.saved_at_tick"):
        validate_bundle_export_invariants(bad_manifest, payload, fake_sha)

    # Mismatched embodiment_id
    bad_manifest2 = {
        "saved_at_tick": 500,
        "symbiont_tick": 500,
        "checkpoint_hash": f"sha256:{fake_sha}",
        "manifest_generated_from_checkpoint_hash": f"sha256:{fake_sha}",
        "embodiment_id": "emb.wrong",
        "body_id": "body.1",
    }
    with pytest.raises(ValueError, match="Export invariant violated: manifest.embodiment_id"):
        validate_bundle_export_invariants(bad_manifest2, payload, fake_sha)

    # Mismatched hash
    bad_manifest3 = {
        "saved_at_tick": 500,
        "symbiont_tick": 500,
        "checkpoint_hash": "sha256:corrupted_hash",
        "manifest_generated_from_checkpoint_hash": f"sha256:{fake_sha}",
        "embodiment_id": "emb.1",
        "body_id": "body.1",
    }
    with pytest.raises(ValueError, match="Export invariant violated: manifest.checkpoint_hash"):
        validate_bundle_export_invariants(bad_manifest3, payload, fake_sha)


def test_runtime_checkpoint_references_artifacts_that_only_the_bundle_carries(tmp_path):
    """Longitudinal Integrity v1 §10: two persistence products, two contracts.

    The runtime checkpoint is organism state and names its private model; the
    weights live outside it. Only the portable bundle is a complete organism,
    and its byte integrity is independent of the checkpoint's state identity.
    """
    import pytest

    from symbiont.host.checkpoint import CheckpointError, verify_checkpoint_identity
    from symbiont.modeling import (
        ArchitectureId,
        ModelArtifactManifest,
        ModeledOrganismRuntime,
        ModelObjective,
        TrainingRequest,
    )

    runtime = ModeledOrganismRuntime(organism_id="portable-subject")
    request = TrainingRequest(
        organism_id=runtime.organism_id,
        corpus_hash="a" * 64,
        tokenizer_hash="b" * 64,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=7,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=100,
        created_tick_class=0,
    )
    artifact = ModelArtifactManifest.build(
        request=request, parameter_count=100_000, weights_hash="c" * 64, artifact_bytes=7
    )
    model_id = runtime.adopt_private_model(artifact, evaluation_summary=(0, 1)).model_id
    checkpoint = json.loads(json.dumps(runtime.checkpoint()))

    # Runtime checkpoint: names the model, carries no weights.
    serialized = json.dumps(checkpoint)
    assert model_id in serialized
    assert "weights" not in {key for key in checkpoint}
    assert b"model-weights".decode() not in serialized

    models = tmp_path / "models"
    models.mkdir()
    (models / f"{model_id}.json").write_text('{"manifest":true}', encoding="utf-8")
    (models / f"{model_id}.pt").write_bytes(b"model-weights")
    (models / f"{model_id}.tokenizer.json").write_text(
        json.dumps({"vocabulary": ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>"]}),
        encoding="utf-8",
    )
    bundle = save_symbiont_bundle(checkpoint, models, tmp_path / "subject.symbiont")

    # Portable bundle: the same checkpoint plus the artifacts it references.
    restored_models = tmp_path / "restored-models"
    restored = load_symbiont_bundle(bundle, restored_models)
    assert restored == checkpoint
    assert (restored_models / f"{model_id}.pt").read_bytes() == b"model-weights"

    # State identity is checked by restore, independently of the bundle hashes.
    verify_checkpoint_identity(restored)
    ModeledOrganismRuntime.from_checkpoint(restored)
    restored["generation"] += 1
    with pytest.raises(CheckpointError, match="does not match its recorded checkpoint_id"):
        ModeledOrganismRuntime.from_checkpoint(restored)

    # A bundle that lacks a referenced artifact is not a portable organism.
    (models / f"{model_id}.pt").unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        save_symbiont_bundle(checkpoint, models, tmp_path / "incomplete.symbiont")
