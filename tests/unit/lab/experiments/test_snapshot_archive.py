from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont_lab.experiments.snapshot_archive import archive_snapshot, verify_snapshot


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
