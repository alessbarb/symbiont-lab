"""Portable bundle validation and non-destructive artifact installation."""

import json
import zipfile

import pytest

from symbiont_lab.physics3d import persistence


def _bundle(tmp_path, *, state="shadow"):
    models = tmp_path / "source"
    models.mkdir()
    for suffix in (".json", ".pt", ".tokenizer.json"):
        (models / f"model{suffix}").write_bytes(b"artifact")
    payload = {
        "saved_at_tick": 2,
        "private_model_registry": {"records": [{"model_id": "model", "state": state}]},
    }
    path = persistence.save_symbiont_bundle(payload, models, tmp_path / "bundle")
    return path, payload


def _rewrite(path, edit):
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    edit(entries)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


@pytest.mark.parametrize(
    "field,value", [("saved_at_tick", 99), ("checkpoint_hash", "wrong"), ("symbiont_tick", 99)]
)
def test_load_verifies_manifest_before_creating_destination(tmp_path, field, value):
    path, _ = _bundle(tmp_path)

    def edit(entries):
        manifest = json.loads(entries["manifest.json"])
        manifest[field] = value
        entries["manifest.json"] = json.dumps(manifest)

    _rewrite(path, edit)
    destination = tmp_path / "restored"
    with pytest.raises(ValueError):
        persistence.load_symbiont_bundle(path, destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    "bad_name", ["models/z/nested.pt", "models/../escape.pt", "models/z\\escape.pt"]
)
def test_late_unsafe_entry_never_overwrites_existing_model(tmp_path, bad_name):
    path, _ = _bundle(tmp_path)
    _rewrite(path, lambda entries: entries.update({bad_name: b"bad"}))
    destination = tmp_path / "restored"
    destination.mkdir()
    existing = destination / "model.json"
    existing.write_bytes(b"previous")
    with pytest.raises(ValueError, match="unsafe model path"):
        persistence.load_symbiont_bundle(path, destination)
    assert existing.read_bytes() == b"previous"
    assert list(destination.iterdir()) == [existing]


def test_artifact_hash_is_verified(tmp_path):
    path, _ = _bundle(tmp_path)
    _rewrite(path, lambda entries: entries.update({"models/model.pt": b"tampered"}))
    with pytest.raises(ValueError, match="inventory mismatch"):
        persistence.load_symbiont_bundle(path, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("state", ["active", "shadow"])
@pytest.mark.parametrize("suffix", [".json", ".pt", ".tokenizer.json"])
def test_save_requires_all_live_model_artifacts_and_preserves_previous_bundle(
    tmp_path, state, suffix
):
    path, payload = _bundle(tmp_path, state=state)
    previous = path.read_bytes()
    (tmp_path / "source" / f"model{suffix}").unlink()
    with pytest.raises(ValueError, match="missing required model artifact"):
        persistence.save_symbiont_bundle(payload, tmp_path / "source", path)
    assert path.read_bytes() == previous


def test_publication_failure_removes_only_new_files(tmp_path, monkeypatch):
    path, _ = _bundle(tmp_path)
    destination = tmp_path / "restored"
    destination.mkdir()
    existing = destination / "model.json"
    existing.write_bytes(b"artifact")
    unrelated = destination / "unrelated"
    unrelated.write_bytes(b"preserve")
    link = persistence.os.link
    calls = 0

    def fail_second(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publication failure")
        link(source, target)

    monkeypatch.setattr(persistence.os, "link", fail_second)
    with pytest.raises(OSError, match="injected"):
        persistence.load_symbiont_bundle(path, destination)
    assert sorted(p.name for p in destination.iterdir()) == ["model.json", "unrelated"]
    assert existing.read_bytes() == b"artifact"
    assert unrelated.read_bytes() == b"preserve"


def test_conflicting_local_artifacts_are_not_replaced(tmp_path):
    path, _ = _bundle(tmp_path)
    destination = tmp_path / "restored"
    destination.mkdir()
    (destination / "model.pt").write_bytes(b"local")
    with pytest.raises(ValueError, match="conflicting local"):
        persistence.load_symbiont_bundle(path, destination)
    assert (destination / "model.pt").read_bytes() == b"local"
    assert len(list(destination.iterdir())) == 1


def test_duplicate_members_rejected(tmp_path):
    path, _ = _bundle(tmp_path)
    with zipfile.ZipFile(path, "a") as archive, pytest.warns(UserWarning):
        archive.writestr("models/model.pt", b"other")
    with pytest.raises(ValueError, match="duplicate members"):
        persistence.load_symbiont_bundle(path, tmp_path / "restored")


@pytest.mark.parametrize("manifest_free", [False, True])
def test_complete_legacy_bundle_remains_loadable(tmp_path, manifest_free):
    path, payload = _bundle(tmp_path)

    def edit(entries):
        manifest = json.loads(entries.pop("manifest.json"))
        if not manifest_free:
            manifest["bundle_schema_version"] = "1.0"
            del manifest["model_artifacts"]
            entries["manifest.json"] = json.dumps(manifest)

    _rewrite(path, edit)
    assert persistence.load_symbiont_bundle(path, tmp_path / "restored") == payload


@pytest.mark.parametrize("model_id", ["../escape", "nested/model", "x\\y", ""])
def test_export_rejects_unsafe_model_id(tmp_path, model_id):
    with pytest.raises(ValueError, match="unsafe model identity"):
        persistence.save_symbiont_bundle(
            {"private_model_registry": {"records": [{"model_id": model_id, "state": "shadow"}]}},
            tmp_path,
            tmp_path / "bundle",
        )


def test_legacy_missing_required_artifact_rejected_even_if_locally_available(tmp_path):
    path, _ = _bundle(tmp_path)

    def edit(entries):
        del entries["manifest.json"]
        del entries["models/model.pt"]

    _rewrite(path, edit)
    destination = tmp_path / "restored"
    destination.mkdir()
    (destination / "model.pt").write_bytes(b"artifact")
    with pytest.raises(ValueError, match="missing required model artifact"):
        persistence.load_symbiont_bundle(path, destination)
    assert list(p.name for p in destination.iterdir()) == ["model.pt"]


def test_restore_rejects_symlink_without_touching_referent(tmp_path):
    path, _ = _bundle(tmp_path)
    destination = tmp_path / "restored"
    destination.mkdir()
    referent = tmp_path / "unrelated"
    referent.write_bytes(b"original")
    (destination / "model.json").symlink_to(referent)
    with pytest.raises(ValueError, match="symlink"):
        persistence.load_symbiont_bundle(path, destination)
    assert referent.read_bytes() == b"original"
    assert (destination / "model.json").is_symlink()


def test_repeated_restore_reuses_identical_artifacts(tmp_path):
    path, payload = _bundle(tmp_path)
    destination = tmp_path / "restored"
    persistence.load_symbiont_bundle(path, destination)
    assert persistence.load_symbiont_bundle(path, destination) == payload
    assert len(list(destination.iterdir())) == 3
