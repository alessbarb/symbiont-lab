"""Schema 10 -> 11: verified checkpoint identity (Longitudinal Integrity v1 §4-§5).

A schema-10 checkpoint carried an identifier that covered only base runtime
fields and was never checked on restore. It must keep restoring, migrate
deterministically, and start a verifiable lineage from its next save.
"""

from __future__ import annotations

import json

import pytest
from tests.checkpoints import as_legacy, edited

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    IDENTITY_SCOPE,
    CheckpointError,
    normalize_checkpoint,
    verify_checkpoint_identity,
)
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

RUNTIME_KWARGS = dict(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)


def _v10(runtime_type=OrganismRuntime) -> dict:
    runtime = runtime_type(**RUNTIME_KWARGS)
    runtime.run(3)
    return as_legacy(json.loads(json.dumps(runtime.checkpoint())))


def test_v10_checkpoint_migrates_deterministically_without_mutating_its_input() -> None:
    legacy = _v10()
    before = json.dumps(legacy, sort_keys=True)

    first = normalize_checkpoint(legacy)
    second = normalize_checkpoint(legacy)

    assert first == second
    assert first["schema_version"] == CHECKPOINT_SCHEMA_VERSION == 11
    assert json.dumps(legacy, sort_keys=True) == before
    assert {key: value for key, value in first.items() if key != "schema_version"} == {
        key: value for key, value in legacy.items() if key != "schema_version"
    }


@pytest.mark.parametrize("runtime_type", [OrganismRuntime, PrivateModelOrganismRuntime])
def test_v10_checkpoint_restores_and_starts_a_verifiable_lineage(runtime_type) -> None:
    legacy = _v10(runtime_type)
    verify_checkpoint_identity(legacy)  # legacy identifiers are accepted unverified

    restored = runtime_type.from_checkpoint(legacy, **RUNTIME_KWARGS)
    saved = json.loads(json.dumps(restored.checkpoint()))

    lineage = saved["checkpoint_lineage"]
    assert saved["schema_version"] == 11
    assert lineage["identity_scope"] == IDENTITY_SCOPE
    assert lineage["parent_checkpoint_hash"] == legacy["checkpoint_lineage"]["checkpoint_id"]
    verify_checkpoint_identity(saved)
    runtime_type.from_checkpoint(saved, **RUNTIME_KWARGS)


@pytest.mark.parametrize("field", ["social_ledger", "signal_knowledge", "exchange_guard"])
def test_the_same_absence_migrates_from_v10_but_is_loss_in_v11(field: str) -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.run(3)
    current = json.loads(json.dumps(runtime.checkpoint()))

    historical = as_legacy(current)
    del historical[field]
    OrganismRuntime.from_checkpoint(historical, **RUNTIME_KWARGS)

    del current[field]
    with pytest.raises(CheckpointError, match=f"missing required field {field!r}"):
        OrganismRuntime.from_checkpoint(edited(current), **RUNTIME_KWARGS)
