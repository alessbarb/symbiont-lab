"""Spatial evidence must not promote sampled signals into known world objects."""

import json
from copy import deepcopy

import pytest

from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.observation.world_scene import (
    WorldScenePublisher,
    apply_world_event,
    project_world_scene,
)


def rich_state():
    return {
        "tick": 4,
        "embodiment": {"embodiment_id": "emb.1", "body_id": "body.1"},
        "world_observation": {
            "world_id": "world.1",
            "coordinates": {"up": "z"},
            "environment": "physics3d",
            "entities": {
                "e": {"id": "e", "position": [1, 2, 3], "orientation": [0, 0, 0, 1], "shapes": []}
            },
            "contacts": [],
            "receptors": {"rec.0": {"modality": "scalar_field", "source_entity_id": "e"}},
        },
        "pre": {"sensory_input": {"sampled_values": {"rec.0": 0.7}}, "physical": {}},
        "observer_semantics": {"sensory": {"opaque": {"source_ids": ["rec.0"]}}},
        "runtime": {"percepts": []},
        "self_model": {"opaque": {"confidence_class": 9}},
    }


def test_sampling_is_not_perception_or_object_recognition():
    rich = rich_state()
    before = deepcopy(rich)
    scene = project_world_scene(rich)
    e = scene["evidence"]["rec.0"]
    assert e["sampled"] and not e["percept_emitted"]
    assert e["signals"][0]["represented"]
    assert scene["availability"]["spatial_object_identity"] == "not-exported"
    assert "known" not in scene["entities"]["e"]
    assert rich == before
    rich["runtime"]["percepts"] = [{"name": "opaque", "value": 0.0}]
    assert project_world_scene(rich)["evidence"]["rec.0"]["percept_emitted"]
    rich["runtime"]["percepts"][0]["value"] = None
    assert not project_world_scene(rich)["evidence"]["rec.0"]["percept_emitted"]


def test_old_stream_does_not_fabricate_world():
    assert project_world_scene({"tick": 1, "body_schema": {}}) is None


def test_deltas_reconstruct_add_remove_and_transform_without_resending_shapes():
    publisher = WorldScenePublisher()
    scene = project_world_scene(rich_state())
    first = publisher.event(scene)
    scene["entities"]["e"]["position"] = [2, 2, 3]
    scene["tick"] = 5
    delta = publisher.event(scene)
    assert delta["upserts"] == {}
    assert delta["transforms"] == {"e": {"position": [2, 2, 3], "orientation": [0, 0, 0, 1]}}
    latest = apply_world_event(first, delta)
    assert latest["entities"] == scene["entities"]
    scene["entities"] = {"new": {"id": "new", "position": [0, 0, 0], "orientation": [0, 0, 0, 1]}}
    delta = publisher.event(scene)
    assert delta["removals"] == ["e"]
    assert apply_world_event(latest, delta)["entities"] == scene["entities"]
    with pytest.raises(ValueError, match="gap"):
        apply_world_event(first, delta)


def test_bus_reconnect_materializes_snapshot_after_history_overflow():
    bus = ObservationBus(queue_size=2, history_size=2)
    pub = WorldScenePublisher()
    scene = project_world_scene(rich_state())
    for tick in range(10):
        scene["tick"] = tick
        scene["entities"]["e"]["position"][0] = tick
        bus.push(pub.event(scene))
    consumer = bus.subscribe()
    event = json.loads(consumer.get_nowait())
    assert event["kind"] == "snapshot"
    assert event["revision"] == 10
    assert event["entities"]["e"]["position"][0] == 9
    recovered = bus.world_scene()
    recovered["entities"].clear()
    assert bus.world_scene()["entities"]
    bus.unsubscribe(consumer)


def test_session_change_is_full_reset_even_with_reused_native_entity_ids():
    pub = WorldScenePublisher()
    scene = project_world_scene(rich_state())
    first = pub.event(scene)
    scene["world_id"] = "world.2"
    scene["entities"] = {}
    event = pub.event(scene)
    assert event["kind"] == "snapshot"
    assert apply_world_event(first, event)["entities"] == {}
