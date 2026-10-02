"""Longitudinal Integrity v1 LI-P0: no runtime state may remain unclassified."""

from __future__ import annotations

import inspect

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.continuity import (
    APPARATUS_FIELDS,
    CONDITIONAL_FIELDS,
    ENVELOPE_FIELDS,
    LAYERS,
    REGISTER,
    ContinuityClass,
    Reembodiment,
    entries_for,
)
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont.modeling.runtime import ModeledOrganismRuntime

RUNTIMES = dict(zip(LAYERS, (OrganismRuntime, ModeledOrganismRuntime, PrivateModelOrganismRuntime)))
# Audit findings whose contract the code does not meet yet. None remain; a new
# gap must be named here and in the register entry that carries it.
OPEN_GAPS: set[str] = set()


def _runtime(layer: str, **kwargs: object) -> OrganismRuntime:
    runtime = RUNTIMES[layer](
        bootstrap_semantic_senses=True, discover_senses=False, min_samples=1, **kwargs
    )
    runtime.tick()
    return runtime


def test_register_has_one_entry_per_attribute() -> None:
    names = [entry.attribute for entry in REGISTER]
    assert sorted(names) == sorted(set(names))


@pytest.mark.parametrize("layer", LAYERS)
def test_every_runtime_attribute_is_classified(layer: str) -> None:
    registered = {entry.attribute for entry in entries_for(layer)}
    assert registered == set(vars(_runtime(layer)))


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("persist_replay_state", [False, True])
def test_every_checkpoint_field_is_owned(layer: str, persist_replay_state: bool) -> None:
    owned = {field for entry in entries_for(layer) for field in entry.checkpoint_fields}
    owned |= {field.checkpoint_field for field in ENVELOPE_FIELDS}
    runtime = _runtime(layer, persist_replay_state=persist_replay_state)
    written = set(runtime.checkpoint())
    assert written <= owned
    assert owned - written <= CONDITIONAL_FIELDS


def test_state_identity_flag_matches_the_hashed_payload() -> None:
    runtime = _runtime(LAYERS[-1])
    hashed = set(runtime._build_checkpoint_payload()) - {"runtime_provenance"}
    declared = {
        field for entry in REGISTER if entry.in_state_identity for field in entry.checkpoint_fields
    }
    declared |= {field.checkpoint_field for field in ENVELOPE_FIELDS if field.in_state_identity}
    assert declared - CONDITIONAL_FIELDS == hashed


def test_entries_are_internally_consistent() -> None:
    for entry in REGISTER:
        assert entry.owner and entry.restore_path and entry.migration, entry.attribute
        if entry.continuity is ContinuityClass.MUST_PRESERVE and entry.checkpoint_field is None:
            assert entry.known_gap is not None, entry.attribute
        if entry.continuity is ContinuityClass.MUST_RESET:
            assert entry.reembodiment is not Reembodiment.INVALIDATED, entry.attribute
        if entry.continuity is ContinuityClass.MUST_INVALIDATE_AUTHORITY:
            assert entry.reembodiment is Reembodiment.INVALIDATED, entry.attribute
        if entry.continuity is ContinuityClass.MUST_REAPPLY_CONFIG:
            assert entry.checkpoint_field is not None, entry.attribute


def test_open_gaps_are_exactly_the_audit_findings() -> None:
    assert {entry.known_gap for entry in REGISTER} - {None} == OPEN_GAPS


def test_apparatus_fields_name_real_physics3d_state() -> None:
    pytest.importorskip("pybullet")
    from symbiont_lab.physics3d import reembodiment
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    source = inspect.getsource(PyBulletEmbodimentRuntime) + inspect.getsource(reembodiment)
    for field in APPARATUS_FIELDS:
        assert f"self.{field.attribute}" in source, field.attribute
        assert f'"{field.checkpoint_field}"' in source, field.checkpoint_field
