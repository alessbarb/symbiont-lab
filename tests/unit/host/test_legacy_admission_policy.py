"""Issue #276: the boundary for checkpoints of unverified legacy origin.

Policy (owner, 2026-10-02): schema 10 and earlier stay admissible and marked;
uses that need a verified origin refuse them; and the admission must be decided
again before the checkpoint schema reaches the review version.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    IDENTITY_VERIFIED_SINCE_SCHEMA,
    LEGACY_ADMISSION_REVIEW_AT_SCHEMA,
    CheckpointError,
    has_unverified_legacy_origin,
    require_verified_origin,
    stamp_checkpoint_identity,
)
from symbiont_lab.experiments.snapshot_archive import (
    archive_snapshot,
    inspect_snapshot_source,
    verify_snapshot,
)
from tests.checkpoints import as_legacy

KWARGS = dict(bootstrap_semantic_senses=False)


def _current() -> dict:
    return OrganismRuntime(**KWARGS).checkpoint()


def _legacy_then_saved() -> dict:
    restored = OrganismRuntime.from_checkpoint(as_legacy(_current()), **KWARGS)
    return restored.checkpoint()


def test_legacy_admission_is_reviewed_before_the_schema_reaches_the_review_version() -> None:
    assert IDENTITY_VERIFIED_SINCE_SCHEMA < LEGACY_ADMISSION_REVIEW_AT_SCHEMA
    assert CHECKPOINT_SCHEMA_VERSION < LEGACY_ADMISSION_REVIEW_AT_SCHEMA, (
        "the checkpoint schema reached the legacy-admission review version: decide "
        "issue #276 again (retire the legacy path or move the review version)"
    )


def test_a_subject_born_under_the_current_schema_has_a_verified_origin() -> None:
    payload = _current()

    assert has_unverified_legacy_origin(payload) is False
    require_verified_origin(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(as_legacy(_current()), id="legacy-as-loaded"),
        pytest.param(_legacy_then_saved(), id="legacy-then-saved-by-current-runtime"),
        pytest.param(
            stamp_checkpoint_identity(as_legacy(_current()), transform="test-transform"),
            id="legacy-then-transformed",
        ),
    ],
)
def test_a_subject_of_legacy_origin_is_still_restorable_but_refused_where_origin_matters(
    payload: dict,
) -> None:
    OrganismRuntime.from_checkpoint(json.loads(json.dumps(payload)), **KWARGS)

    assert has_unverified_legacy_origin(payload) is True
    with pytest.raises(CheckpointError, match="unverified legacy origin"):
        require_verified_origin(payload)


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
    from symbiont_lab.physics3d.persistence import save_symbiont_bundle

    source = tmp_path / "source"
    (source / "models").mkdir(parents=True)
    save_symbiont_bundle(build(), source / "models", source / "organism.symbiont")
    (source / "body.json").write_text("{}", encoding="utf-8")

    assert inspect_snapshot_source(source)["unverified_legacy_origin"] is expected
