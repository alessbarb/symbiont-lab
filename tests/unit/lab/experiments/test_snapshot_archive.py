from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont_lab.experiments.snapshot_archive import archive_snapshot, verify_snapshot


def test_archive_snapshot_is_hashed_and_not_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "models").mkdir(parents=True)
    (source / "organism.symbiont").write_bytes(b"organism")
    (source / "body.json").write_text('{"x":1}', encoding="utf-8")
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
    assert json.loads((destination / "manifest.json").read_text())["scenario"] == "unit"

    with pytest.raises(FileExistsError):
        archive_snapshot(
            source=source,
            destination=destination,
            source_commit="b" * 40,
        )
