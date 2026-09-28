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
    event = json.loads(consumer.get_nowait().data)
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


def test_last_provider_call_cannot_establish_complete_sampling():
    rich = rich_state()
    rich["pre"]["sensory_input"] = {"values": {"rec.0": 0.7}}
    evidence = project_world_scene(rich)["evidence"]["rec.0"]
    assert evidence["sampled"] is None
    assert evidence["sample"] is None


def test_sampling_union_covers_multiple_calls_and_resets_between_ticks():
    from types import SimpleNamespace

    from symbiont_lab.physics3d.apparatus import PhysicsReadingProvider

    apparatus = SimpleNamespace(
        receptor_ids=("rec.0", "rec.1"), sample_receptors=lambda: {"rec.0": 0.3, "rec.1": 0.0}
    )
    provider = PhysicsReadingProvider(apparatus)
    provider.sample((SimpleNamespace(capability_id="rec.0"),))
    provider.sample((SimpleNamespace(capability_id="rec.1"),))
    assert provider.observed_tick_values == {"rec.0": 0.3, "rec.1": 0.0}
    assert provider.last_values == {"rec.1": 0.0}
    provider.observed_tick_values.clear()
    provider.sample(())
    assert provider.observed_tick_values == {}


def test_recovery_endpoint_returns_materialized_state_without_mutating_bus():
    from pathlib import Path

    from symbiont_lab.server.api import make_handler

    bus = ObservationBus()
    pub = WorldScenePublisher()
    scene = project_world_scene(rich_state())
    bus.push(pub.event(scene))
    scene["entities"]["e"]["position"] = [9, 0, 0]
    bus.push(pub.event(scene))
    handler_type = make_handler(None, None, None, None, bus, None, Path("."))
    handler = object.__new__(handler_type)
    handler.path = "/api/world-scene"
    responses = []
    handler._json = lambda status, payload: responses.append((status, payload))
    handler.do_GET()
    assert responses[0][0] == 200
    recovered = responses[0][1]["scene"]
    assert recovered["kind"] == "snapshot"
    assert recovered["revision"] == 2
    assert recovered["entities"]["e"]["position"] == [9, 0, 0]
    recovered["entities"].clear()
    assert bus.world_scene()["entities"]


def test_signal_claims_require_an_exported_percept_reference():
    rich = rich_state()
    sensor = next(iter(rich["observer_semantics"]["sensory"]))
    rich["runtime"]["signal_references"] = {sensor: "signal.acquired"}
    claim = {
        "claim_id": "claim.1",
        "kind": "coupling",
        "status": "insufficient",
        "related_signal_id": "signal.other",
        "evidence_count": 2,
        "revision": 1,
    }
    rich["runtime"]["signal_knowledge"] = [{"signal_id": "signal.acquired", "claims": [claim]}]
    scene = project_world_scene(rich)
    signal = next(s for e in scene["evidence"].values() for s in e["signals"] if s["id"] == sensor)
    assert signal["signal_id"] == "signal.acquired"
    assert signal["knowledge"]["claims"][0]["status"] == "insufficient"
    signal["knowledge"]["claims"].clear()
    assert rich["runtime"]["signal_knowledge"][0]["claims"] == [claim]
    rich["runtime"]["signal_references"] = {}
    scene = project_world_scene(rich)
    signal = next(s for e in scene["evidence"].values() for s in e["signals"] if s["id"] == sensor)
    assert signal["knowledge"] is None
    assert signal["reference_status"] == "unavailable"


def test_bus_overflow_rebases_world_channel_on_next_scene_event():
    bus = ObservationBus(queue_size=2)
    consumer = bus.subscribe()
    publisher = WorldScenePublisher()
    scene = project_world_scene(rich_state())
    bus.push(publisher.event(scene))
    observed = apply_world_event(None, json.loads(consumer.get_nowait().data))

    scene["tick"] += 1
    scene["entities"]["e"]["position"][0] = 10
    bus.push(publisher.event(scene))
    bus.push({"type": "vitals", "tick": 1})
    bus.push({"type": "vitals", "tick": 2})
    while not consumer.empty():
        consumer.get_nowait()

    scene["tick"] += 1
    scene["entities"]["e"]["position"][0] = 20
    bus.push(publisher.event(scene))
    observed = apply_world_event(observed, json.loads(consumer.get_nowait().data))
    assert observed == bus.world_scene()
