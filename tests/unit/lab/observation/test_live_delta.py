import json

import pytest

from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.observation.delta import (
    DELTA_CONTRACT,
    ObservationDeltaDecoder,
    ObservationDeltaEncoder,
)


def test_anchor_and_deltas_reconstruct_exact_live_event():
    encoder = ObservationDeltaEncoder(anchor_interval=8)
    decoder = ObservationDeltaDecoder()

    states = [
        {"type": "vitals", "tick": 1, "alive": True, "reserve": 0.9},
        {"type": "vitals", "tick": 2, "alive": True, "reserve": 0.8},
        {"type": "vitals", "tick": 3, "alive": True, "reserve": 0.8, "state": "active"},
        {"type": "vitals", "tick": 4, "alive": True, "state": "active"},
    ]

    encoded = [encoder.encode(item) for item in states]
    assert encoded[0]["kind"] == "anchor"
    assert all(item["contract"] == DELTA_CONTRACT for item in encoded)
    assert all(item["type"] == "observation_delta" for item in encoded)
    assert [decoder.decode(item) for item in encoded] == states


def test_periodic_anchor_breaks_dependency_chain():
    encoder = ObservationDeltaEncoder(anchor_interval=2)

    first = encoder.encode({"type": "body", "tick": 1, "x": 1})
    second = encoder.encode({"type": "body", "tick": 2, "x": 2})
    third = encoder.encode({"type": "body", "tick": 3, "x": 3})
    fourth = encoder.encode({"type": "body", "tick": 4, "x": 4})

    assert first["kind"] == "anchor"
    assert second["kind"] == "delta"
    assert third["kind"] == "delta"
    assert fourth["kind"] == "anchor"
    assert fourth["revision"] == 4


def test_decoder_rejects_revision_gap_until_fresh_anchor():
    encoder = ObservationDeltaEncoder(anchor_interval=3)
    decoder = ObservationDeltaDecoder()

    anchor = encoder.encode({"type": "cognition", "tick": 1, "value": 1})
    skipped = encoder.encode({"type": "cognition", "tick": 2, "value": 2})
    gap = encoder.encode({"type": "cognition", "tick": 3, "value": 3})
    recovery = encoder.encode({"type": "cognition", "tick": 4, "value": 4})

    assert decoder.decode(anchor)["tick"] == 1
    assert skipped["kind"] == "delta"
    assert decoder.decode(gap) is None
    assert recovery["kind"] == "anchor"
    assert decoder.decode(recovery) == {"type": "cognition", "tick": 4, "value": 4}


def test_decoder_detects_tampered_anchor_state_commitment():
    encoder = ObservationDeltaEncoder(anchor_interval=8)
    decoder = ObservationDeltaDecoder()

    anchor = encoder.encode({"type": "vitals", "tick": 1, "reserve": 1.0})
    anchor["state_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="hash mismatch"):
        decoder.decode(anchor)


def test_non_compressible_pose_remains_plain_event():
    encoder = ObservationDeltaEncoder()
    event = {"type": "body_pose", "tick": 1, "base_position": [0.0, 0.0, 1.0]}

    assert encoder.encode(event) == event


def test_bus_new_subscriber_receives_materialized_anchor_not_orphan_delta():
    bus = ObservationBus(queue_size=8, history_size=8, anchor_interval=64)
    bus.push({"type": "vitals", "tick": 1, "reserve": 1.0})
    bus.push({"type": "vitals", "tick": 2, "reserve": 0.9})
    bus.push({"type": "vitals", "tick": 3, "reserve": 0.8})

    consumer = bus.subscribe()
    payload = json.loads(consumer.get_nowait())
    decoded = ObservationDeltaDecoder().decode(payload)

    assert payload["kind"] == "anchor"
    assert payload["revision"] == 3
    assert decoded == {"type": "vitals", "tick": 3, "reserve": 0.8}


def test_bus_history_overflow_recovers_resume_request_with_current_anchor():
    bus = ObservationBus(queue_size=8, history_size=2, anchor_interval=64)
    first_id = bus.push({"type": "vitals", "tick": 1})
    for tick in range(2, 7):
        bus.push({"type": "vitals", "tick": tick})

    consumer = bus.subscribe(after_sequence=first_id)
    payloads = []
    while not consumer.empty():
        payloads.append(json.loads(consumer.get_nowait()))

    vitals = next(item for item in payloads if item.get("channel") == "vitals")
    assert vitals["kind"] == "anchor"
    assert ObservationDeltaDecoder().decode(vitals)["tick"] == 6


def test_bus_slow_consumer_gets_immediate_anchor_after_drop():
    bus = ObservationBus(queue_size=2, history_size=8, anchor_interval=64)
    consumer = bus.subscribe()

    bus.push({"type": "vitals", "tick": 1})
    bus.push({"type": "vitals", "tick": 2})
    bus.push({"type": "vitals", "tick": 3})

    decoder = ObservationDeltaDecoder()
    decoded = []
    while not consumer.empty():
        item = decoder.decode(json.loads(consumer.get_nowait()))
        if item is not None:
            decoded.append(item)

    assert decoded == [{"type": "vitals", "tick": 3}]



def test_delta_is_materially_smaller_for_stable_large_structure():
    encoder = ObservationDeltaEncoder(anchor_interval=64)
    topology = {
        f"node.{index}": {
            "kind": "concept",
            "bias": index / 1000.0,
            "tau": 1.0,
        }
        for index in range(200)
    }
    first = {
        "type": "cognition",
        "tick": 1,
        "topology": topology,
        "activation": {"node.1": 0.1},
    }
    second = {
        "type": "cognition",
        "tick": 2,
        "topology": topology,
        "activation": {"node.1": 0.2},
    }

    anchor = encoder.encode(first)
    delta = encoder.encode(second)

    full_bytes = len(json.dumps(second, separators=(",", ":")).encode())
    delta_bytes = len(json.dumps(delta, separators=(",", ":")).encode())

    assert anchor["kind"] == "anchor"
    assert delta["kind"] == "delta"
    assert delta_bytes < full_bytes * 0.25
