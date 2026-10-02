"""Longitudinal Integrity v1 §4-§5: checkpoint identity and strict current-schema restore."""

from __future__ import annotations

import json

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointError,
    stamp_checkpoint_identity,
)
from symbiont.host.continuity import LAYERS, required_checkpoint_fields
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont.modeling.runtime import ModeledOrganismRuntime
from tests.checkpoints import as_legacy

RUNTIME_KWARGS = dict(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)
RUNTIMES = dict(zip(LAYERS, (OrganismRuntime, ModeledOrganismRuntime, PrivateModelOrganismRuntime)))
# checkpoint_lineage is the identity itself; its absence is covered separately.
CASES = [
    (layer, field)
    for layer in LAYERS
    for field in sorted(required_checkpoint_fields(layer) - {"checkpoint_lineage"})
]


def _saved(layer: str) -> dict:
    runtime = RUNTIMES[layer](**RUNTIME_KWARGS)
    runtime.tick()
    return json.loads(json.dumps(runtime.checkpoint()))


@pytest.mark.parametrize("layer", LAYERS)
def test_saved_checkpoint_restores_and_keeps_its_identity(layer: str) -> None:
    saved = _saved(layer)
    assert saved["schema_version"] == CHECKPOINT_SCHEMA_VERSION

    restored = RUNTIMES[layer].from_checkpoint(saved, **RUNTIME_KWARGS)

    assert restored.state_hash() == saved["checkpoint_lineage"]["checkpoint_id"]


@pytest.mark.parametrize("layer", LAYERS)
def test_checkpoint_id_covers_every_field_of_the_saving_runtime(layer: str) -> None:
    saved = _saved(layer)
    covered = set(saved) - {"checkpoint_lineage", "runtime_provenance"}

    for field in sorted(covered):
        tampered = dict(saved)
        tampered[field] = {"tampered": True}
        with pytest.raises(CheckpointError, match="does not match its recorded checkpoint_id"):
            RUNTIMES[layer].from_checkpoint(tampered, **RUNTIME_KWARGS)


def test_identity_cannot_be_dropped_from_a_current_save() -> None:
    saved = _saved(LAYERS[0])
    del saved["checkpoint_lineage"]["identity_scope"]

    with pytest.raises(CheckpointError, match="no verifiable checkpoint_lineage"):
        OrganismRuntime.from_checkpoint(saved, **RUNTIME_KWARGS)


def test_authorized_transform_is_accepted_and_recorded() -> None:
    saved = _saved(LAYERS[0])
    transformed = dict(saved)
    transformed["resting_requested"] = True
    transformed = stamp_checkpoint_identity(transformed, transform="test-transform")

    restored = OrganismRuntime.from_checkpoint(transformed, **RUNTIME_KWARGS)

    lineage = transformed["checkpoint_lineage"]
    assert lineage["parent_checkpoint_hash"] == saved["checkpoint_lineage"]["checkpoint_id"]
    assert lineage["transforms"] == ["test-transform"]
    assert (
        restored.checkpoint()["checkpoint_lineage"]["parent_checkpoint_hash"]
        == (lineage["checkpoint_id"])
    )


@pytest.mark.parametrize(("layer", "field"), CASES)
def test_current_schema_cannot_lose_a_required_field(layer: str, field: str) -> None:
    saved = _saved(layer)
    del saved[field]
    saved = stamp_checkpoint_identity(saved, transform="drop-field")

    with pytest.raises(CheckpointError, match=f"missing required field {field!r}"):
        RUNTIMES[layer].from_checkpoint(saved, **RUNTIME_KWARGS)


@pytest.mark.parametrize(
    ("layer", "field"),
    [
        (LAYERS[0], "exchange_guard"),
        (LAYERS[0], "exchange_sequence"),
        (LAYERS[0], "social_ledger"),
        (LAYERS[0], "signal_knowledge"),
        (LAYERS[0], "memory"),
        (LAYERS[1], "episodic_memory"),
        (LAYERS[1], "social_evidence_ledger"),
        (LAYERS[1], "private_learning_state"),
        (LAYERS[2], "prospective_agency"),
    ],
)
def test_legacy_schema_may_still_predate_a_field(layer: str, field: str) -> None:
    legacy = as_legacy(_saved(layer))
    del legacy[field]

    restored = RUNTIMES[layer].from_checkpoint(legacy, **RUNTIME_KWARGS)

    assert restored.organism_id == legacy["organism_id"]


def test_legacy_lineage_is_accepted_without_verification() -> None:
    legacy = as_legacy(_saved(LAYERS[0]))
    legacy["resting_requested"] = True

    restored = OrganismRuntime.from_checkpoint(legacy, **RUNTIME_KWARGS)

    assert (
        restored.checkpoint()["checkpoint_lineage"]["parent_checkpoint_hash"]
        == (legacy["checkpoint_lineage"]["checkpoint_id"])
    )


def test_non_canonical_state_is_rejected_as_a_checkpoint_error() -> None:
    saved = _saved(LAYERS[0])
    saved["epigenetic_decay"] = float("nan")

    with pytest.raises(CheckpointError, match="not canonical JSON"):
        OrganismRuntime.from_checkpoint(saved, **RUNTIME_KWARGS)
