from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from symbiont_world.contracts import ContactEvidence, ReceivedEmission, WorldAction, WorldObservation
from symbiont_world.events import WorldEvent

FORBIDDEN_SUBSTRINGS = ("ground_truth", "semantic", "observer", "cell_id", "entity_type")


def test_world_observation_signals_are_not_mutable():
    obs = WorldObservation(signals={"a1b2": 0.5})
    assert isinstance(obs.signals, MappingProxyType)
    with pytest.raises(TypeError):
        obs.signals["a1b2"] = 1.0


def test_world_observation_fields_are_frozen():
    obs = WorldObservation()
    with pytest.raises(FrozenInstanceError):
        obs.signals = {}


def test_world_observation_has_no_ground_truth_field_names():
    field_names = {f for f in WorldObservation.__slots__}
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert not any(forbidden in name for name in field_names), field_names


def test_world_observation_contact_is_evidence_only_no_typed_identity():
    field_names = {f for f in ContactEvidence.__slots__}
    assert field_names == {"source_id", "intensity"}
    assert "entity_type" not in field_names


def test_world_action_has_no_high_level_semantic_verbs():
    field_names = {f for f in WorldAction.__slots__}
    for forbidden in (
        "eat", "attack", "mate", "trade",
        "dig", "build", "fertilize", "move_material", "irrigate",
    ):
        assert forbidden not in field_names
    assert field_names == {"move", "sample", "acquire", "emit", "rest"}


def test_world_action_is_frozen_and_normalizes_emit_to_tuple():
    action = WorldAction(emit=[1, 2, 3])
    assert action.emit == (1, 2, 3)
    with pytest.raises(FrozenInstanceError):
        action.rest = True


def test_received_emission_carries_no_sender_identity():
    field_names = {f for f in ReceivedEmission.__slots__}
    assert field_names == {"sequence", "intensity"}



@pytest.mark.parametrize("kind", ["SUBSTRATE_IMPULSE", "ECOLOGY_CHANGED"])
def test_physical_ecology_event_kinds_are_valid(kind):
    event = WorldEvent(
        event_id=f"evt-{kind}",
        world_id="world",
        tick=0,
        kind=kind,
        actor=None,
        position=None,
    )
    assert event.kind == kind
