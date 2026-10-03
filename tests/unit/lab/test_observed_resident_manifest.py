"""The observed resident launcher: published contract and manifest failures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab.cli import observed_resident
from lab.observatory.schema_validate import validate

OBSERVATORY = Path(__file__).resolve().parents[3] / "lab" / "src" / "lab" / "observatory"


def _run(tmp_path: Path) -> int:
    return observed_resident.main(
        [
            "--state-file",
            str(tmp_path / "organism.json"),
            "--observatory-dir",
            str(tmp_path / "observatory"),
            "--max-ticks",
            "2",
            "--interval",
            "0.001",
            "--checkpoint-every",
            "1",
            "--no-stdout",
        ]
    )


def test_manifest_is_written_on_a_healthy_run(tmp_path: Path) -> None:
    assert _run(tmp_path) == 0
    assert list((tmp_path / "observatory" / "manifests").glob("*.manifest.json"))


def test_manifest_failure_is_visible_and_the_organism_is_still_saved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(observed_resident, "write_capture_manifest", broken)

    assert _run(tmp_path) == 1

    assert "capture manifest not written" in capsys.readouterr().err
    assert (tmp_path / "organism.json").is_file()
    assert not list((tmp_path / "observatory" / "manifests").glob("*.manifest.json"))


def test_launcher_output_validates_against_the_closed_snapshot_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The subprocess contract suite lives under observatory/tests and runs on
    # Observatory changes; this keeps the launcher itself under the Lab's lane.
    code = observed_resident.main(
        [
            "--state-file",
            str(tmp_path / "organism.json"),
            "--observatory-dir",
            str(tmp_path / "observatory"),
            "--max-ticks",
            "1",
            "--interval",
            "0.001",
            "--checkpoint-every",
            "1",
        ]
    )
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    schema = json.loads((OBSERVATORY / "snapshot.schema.json").read_text(encoding="utf-8"))

    assert code == 0
    assert len(lines) == 1
    envelope = json.loads(lines[0])
    assert envelope["type"] == "symbiont-observatory-snapshot"
    validate(envelope["snapshot"], schema, schema_root=OBSERVATORY)


def test_slm_service_status_is_part_of_the_closed_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = observed_resident.main(
        [
            "--state-file",
            str(tmp_path / "organism.json"),
            "--observatory-dir",
            str(tmp_path / "observatory"),
            "--max-ticks",
            "1",
            "--interval",
            "0.001",
            "--checkpoint-every",
            "1",
            "--enable-slm",
        ]
    )
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    schema = json.loads((OBSERVATORY / "snapshot.schema.json").read_text(encoding="utf-8"))
    snapshot = json.loads(lines[0])["snapshot"]

    assert code == 0
    assert snapshot["apparatus"]["slm_service"]["enabled"] is True
    validate(snapshot, schema, schema_root=OBSERVATORY)
