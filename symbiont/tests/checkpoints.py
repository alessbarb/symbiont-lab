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


# Written only by schema 11 and later; a schema-10 runtime never produced them.
_SCHEMA_11_PROVENANCE = ("session_controls", "changed_since_restore")


def as_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    """The same state shaped as a schema-10 runtime saved it.

    For tests of migration paths, where a field is absent because the schema
    that wrote the checkpoint predates it. Schema-11-only provenance is removed
    and the lineage carries no verifiable identity, as in a real schema-10 file;
    tests/compatibility/checkpoint_v10 holds payloads written by that code.
    """
    legacy = dict(payload)
    legacy["schema_version"] = 10
    provenance = payload.get("runtime_provenance")
    if isinstance(provenance, dict):
        legacy["runtime_provenance"] = {
            **{k: v for k, v in provenance.items() if k not in _SCHEMA_11_PROVENANCE},
            "checkpoint_schema_version": 10,
        }
    lineage = payload.get("checkpoint_lineage")
    if isinstance(lineage, dict):
        legacy["checkpoint_lineage"] = {
            key: value
            for key, value in lineage.items()
            if key in ("checkpoint_id", "parent_checkpoint_hash")
        }
    return legacy
