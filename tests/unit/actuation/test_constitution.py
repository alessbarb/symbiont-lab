from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from symbiont.actuation.constitution import (
    ActuatorConstitution,
    MotorSlot,
    derive_actuator_constitution,
)


def test_derive_actuator_constitution_produces_body_owned_slots():
    constitution = derive_actuator_constitution(4)
    assert len(constitution.slots) == 4
    assert all(isinstance(slot, MotorSlot) for slot in constitution.slots)


def test_actuator_ids_are_unique_and_stable_for_same_body_cardinality():
    first = derive_actuator_constitution(6, physical_contract="body-a")
    second = derive_actuator_constitution(6, physical_contract="body-a")
    assert first.actuator_ids == second.actuator_ids
    assert first.contract_fingerprint == second.contract_fingerprint
    assert len(set(first.actuator_ids)) == 6


def test_body_contract_metadata_changes_fingerprint_not_opaque_channel_ids():
    first = derive_actuator_constitution(6, physical_contract="body-a")
    second = derive_actuator_constitution(6, physical_contract="body-b")
    assert first.actuator_ids == second.actuator_ids
    assert first.contract_fingerprint != second.contract_fingerprint


def test_surface_exposes_only_legal_command_contract():
    surface = derive_actuator_constitution(2)
    channel = surface.slots[0]
    assert (channel.command_min, channel.neutral, channel.command_max) == (0.0, 0.0, 1.0)
    assert channel.available is True
    assert not hasattr(channel, "initial_health")
    assert not hasattr(channel, "basal_cost")


def test_constitution_slots_are_immutable_tuple_not_dict():
    constitution = derive_actuator_constitution(2)
    assert isinstance(constitution.slots, tuple)
    with pytest.raises(FrozenInstanceError):
        constitution.channels = ()  # type: ignore[misc]


def test_slot_for_looks_up_by_actuator_id():
    constitution = derive_actuator_constitution(2)
    actuator_id = constitution.actuator_ids[0]
    slot = constitution.slot_for(actuator_id)
    assert slot.actuator_id == actuator_id


def test_slot_for_raises_for_unknown_actuator_id():
    constitution = derive_actuator_constitution(2)
    with pytest.raises(KeyError):
        constitution.slot_for("actuator.does-not-exist")
