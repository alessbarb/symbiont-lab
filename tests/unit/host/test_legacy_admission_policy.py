"""Issue #276: the boundary for checkpoints of unverified legacy origin.

Policy (owner, 2026-10-02): schema 10 and earlier stay admissible and marked;
uses that need a verified origin refuse them; and the admission must be decided
again before the checkpoint schema reaches the review version.
"""

from __future__ import annotations

import json

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
