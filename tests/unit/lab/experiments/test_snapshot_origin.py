"""Issue #276: snapshot manifests record the origin of their organism.

Kept with the other snapshot-archive tests: the archive path is POSIX-only
(directory fsync), like the governed launcher that uses it.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from tests.checkpoints import as_legacy

from lab.experiments.snapshot_archive import (
    archive_snapshot,
    inspect_snapshot_source,
    verify_snapshot,
)
from symbiont.core.orchestration.runtime import OrganismRuntime

KWARGS = dict(bootstrap_semantic_senses=False)


def _current() -> dict:
    return OrganismRuntime(**KWARGS).checkpoint()


def _legacy_then_saved() -> dict:
    restored = OrganismRuntime.from_checkpoint(as_legacy(_current()), **KWARGS)
    return restored.checkpoint()


def _source(tmp_path: Path, runtime_payload: object | None) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    with zipfile.ZipFile(source / "organism.symbiont", "w") as bundle:
        if runtime_payload is not None:
            bundle.writestr("runtime.json", json.dumps(runtime_payload))
    (source / "body.json").write_text("{}", encoding="utf-8")
    return source


@pytest.mark.parametrize(
    ("runtime_payload", "expected"),
    [
        pytest.param(_current(), False, id="verified"),
        pytest.param(_legacy_then_saved(), True, id="legacy"),
        pytest.param(None, None, id="no-runtime-state"),
        pytest.param([1, 2], None, id="malformed-runtime-state"),
    ],
)
def test_snapshot_manifests_record_the_origin_of_their_subject(
    tmp_path: Path, runtime_payload: object | None, expected: bool | None
) -> None:
    source = _source(tmp_path, runtime_payload)

    assert inspect_snapshot_source(source)["unverified_legacy_origin"] is expected
    manifest = archive_snapshot(
        source=source, destination=tmp_path / "snapshot", source_commit="a" * 40
    )
    assert manifest["unverified_legacy_origin"] is expected
    assert verify_snapshot(tmp_path / "snapshot")["unverified_legacy_origin"] is expected


@pytest.mark.parametrize(
    ("build", "expected"),
    [
        pytest.param(_current, False, id="current"),
        pytest.param(_legacy_then_saved, True, id="legacy"),
    ],
)
def test_the_origin_is_read_from_a_bundle_written_by_the_real_bundle_writer(
    tmp_path: Path, build, expected: bool
) -> None:
    # Not a hand-built zip: the layout the launcher will actually meet.
    from lab.physics3d.persistence import save_symbiont_bundle

    source = tmp_path / "source"
    (source / "models").mkdir(parents=True)
    save_symbiont_bundle(build(), source / "models", source / "organism.symbiont")
    (source / "body.json").write_text("{}", encoding="utf-8")

    assert inspect_snapshot_source(source)["unverified_legacy_origin"] is expected
