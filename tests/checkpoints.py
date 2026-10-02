"""Helpers for tests that deliberately change a saved checkpoint."""

from __future__ import annotations

from typing import Any

from symbiont.host.checkpoint import stamp_checkpoint_identity


def edited(payload: dict[str, Any]) -> dict[str, Any]:
    """Declare a hand-made change so restore reaches the validator under test.

    Without it, restore rejects the payload for not matching its recorded
    checkpoint_id before the field-specific validation is ever exercised.
    """
    return stamp_checkpoint_identity(payload, transform="test-edit")


def as_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    """The same state as a schema-10 runtime saved it: no verifiable identity.

    For tests of migration paths, where a field is absent because the schema
    that wrote the checkpoint predates it.
    """
    legacy = dict(payload)
    legacy["schema_version"] = 10
    provenance = payload.get("runtime_provenance")
    if isinstance(provenance, dict):
        legacy["runtime_provenance"] = {**provenance, "checkpoint_schema_version": 10}
    lineage = payload.get("checkpoint_lineage")
    if isinstance(lineage, dict):
        legacy["checkpoint_lineage"] = {
            key: value for key, value in lineage.items() if key != "identity_scope"
        }
    return legacy
