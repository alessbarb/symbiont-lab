from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont_lab.experiments.snapshot_archive import (
    archive_snapshot,
    inspect_snapshot_source,
    verify_snapshot,
)


def test_archive_snapshot_is_hashed_and_not_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "models").mkdir(parents=True)
    (source / "organism.symbiont").write_bytes(b"organism")
    (source / "body.json").write_text(
        '{"body_kind":"crawler","embodiment_id":"emb-1","age_ticks":12}',
        encoding="utf-8",
    )
    (source / "models" / "a.bin").write_bytes(b"weights")
    destination = tmp_path / "archive" / "S01"

    manifest = archive_snapshot(
        source=source,
        destination=destination,
        source_commit="a" * 40,
        body_kind="test",
        scenario="unit",
    )
    assert manifest == verify_snapshot(destination)
    persisted = json.loads((destination / "manifest.json").read_text())
    assert persisted["scenario"] == "unit"
    assert persisted["captured_at"]
    assert persisted["embodiment_id"] == "emb-1"
    assert persisted["body_age_ticks"] == 12
    assert persisted["bundle_models_tree_sha256"]

    with pytest.raises(FileExistsError):
        archive_snapshot(
            source=source,
            destination=destination,
            source_commit="b" * 40,
        )


def test_verify_snapshot_detects_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "models").mkdir(parents=True)
    (source / "organism.symbiont").write_bytes(b"organism")
    (source / "body.json").write_text("{}", encoding="utf-8")
    destination = tmp_path / "archive" / "S01"
    archive_snapshot(source=source, destination=destination, source_commit="a" * 40)

    (destination / "body.json").chmod(0o644)
    (destination / "body.json").write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="body_sha256"):
        verify_snapshot(destination)



def test_archive_snapshot_extracts_embedded_models(tmp_path: Path) -> None:
    import zipfile

    source = tmp_path / "source"
    source.mkdir()
    with zipfile.ZipFile(source / "organism.symbiont", "w") as archive:
        archive.writestr(
            "runtime.json",
            '{"organism_id":"sym-1","saved_at_tick":2048,"schema_version":9}',
        )
        archive.writestr("models/model.json", "{}")
        archive.writestr("models/model.pt", b"weights")
    (source / "body.json").write_text(
        '{"body_kind":"anthropomorphic-v6-vision","embodiment_id":"emb-1"}',
        encoding="utf-8",
    )

    inspected = inspect_snapshot_source(source)
    assert inspected["capturable"] is True
    assert inspected["model_source"] == "bundle"
    assert inspected["embedded_model_count"] == 2
    assert inspected["organism_id"] == "sym-1"
    assert inspected["captured_tick"] == 2048

    destination = tmp_path / "archive" / "S02"
    manifest = archive_snapshot(
        source=source,
        destination=destination,
        source_commit="a" * 40,
        scenario="private-model-training",
    )
    assert manifest["models_source"] == "bundle"
    assert (destination / "models" / "model.json").is_file()
    assert (destination / "models" / "model.pt").is_file()
    assert verify_snapshot(destination)["models_tree_sha256"] == manifest["models_tree_sha256"]


def test_inspect_snapshot_source_requires_physical_body_state(tmp_path: Path) -> None:
    import zipfile

    source = tmp_path / "source"
    source.mkdir()
    with zipfile.ZipFile(source / "organism.symbiont", "w") as archive:
        archive.writestr("runtime.json", '{"organism_id":"sym-1","saved_at_tick":2048}')
        archive.writestr("models/model.pt", b"weights")

    inspected = inspect_snapshot_source(source)
    assert inspected["organism_present"] is True
    assert inspected["embedded_model_count"] == 1
    assert inspected["body_present"] is False
    assert inspected["capturable"] is False
