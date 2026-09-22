from __future__ import annotations

from symbiont_lab.server.organism_stream import (
    OrganismStream,
    Physics3DStreamBridge,
    stream_runtime_tick,
)


def test_stream_runtime_tick_emits_compatible_body_cognition_vitals() -> None:
    stream = OrganismStream()
    stream_runtime_tick(
        stream,
        {
            "tick": 12,
            "instance_id": "0123456789abcdef",
            "run_id": "run-12",
            "sequence": 7,
            "alive": True,
            "base_position": [0.2, 1.1, 0.4],
            "base_orientation": [0.0, 0.0, 0.2, 0.98],
            "schema_confidence": 0.81,
            "schema_parts": 33,
            "schema_sensory_parts": 12,
            "schema_cognitive_regions": 8,
            "predictor_count": 17,
            "prediction_error": 0.11,
            "joint_motion": 0.18,
            "contact_count": 2,
            "mechanical_work_joules": 1.2,
            "metabolic_work_cost": 0.02,
            "slm_active": True,
            "motor_origin": "cognition",
            "resource_progress": 0.64,
            "metabolic_reserve_ratio": 0.72,
            "prospective_selected": True,
            "prospective_expected_value": 0.88,
            "joints": [
                {"name": "left_shoulder_pitch", "position": 0.5},
                {"name": "right_shoulder_pitch", "position": -0.5},
            ],
        },
    )

    events = []
    queue = stream.subscribe()
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) >= 3
    joined = "\n".join(events)
    assert '"type":"body"' in joined
    assert '"type":"cognition"' in joined
    assert '"type":"vitals"' in joined
    assert '"motor_origin":"cognition"' in joined
    assert '"prospective_expected_value":0.88' in joined
    assert '"instance_id":"0123456789abcdef"' in joined
    assert '"run_id":"run-12"' in joined
    assert '"sequence":7' in joined


def test_stream_drops_stale_backlog_for_slow_consumers() -> None:
    stream = OrganismStream(queue_size=2)
    queue = stream.subscribe()

    stream.push({"type": "vitals", "tick": 1})
    stream.push({"type": "vitals", "tick": 2})
    stream.push({"type": "vitals", "tick": 3})

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) == 2
    assert '"tick":1' not in events
    assert '"tick":2' in events[0]
    assert '"tick":3' in events[1]



def test_physics3d_bridge_projects_passive_viewer_frames() -> None:
    stream = OrganismStream()
    bridge = Physics3DStreamBridge(stream)
    queue = stream.subscribe()

    bridge.publish(
        {
            "tick": 21,
            "symbiont_id": "symbiont:3d:test",
            "schema_confidence": 0.73,
            "schema_parts": 9,
            "schema_sensory_parts": 4,
            "schema_cognitive_regions": 3,
            "predictor_count": 5,
            "prediction_error": 0.2,
            "joint_motion": 0.4,
            "contact_count": 2,
            "mechanical_work_joules": 1.5,
            "metabolic_work_cost": 0.1,
            "metabolic_reserve_ratio": 0.8,
            "resource_progress": 0.3,
            "displacement_from_origin": 0.2,
            "motor_origin": "cognition",
            "slm_active": False,
        },
        physical_state={
            "base_position": [1.0, 2.0, 0.9],
            "base_orientation": [0.0, 0.0, 0.0, 1.0],
            "joints": [
                {"joint_index": 7, "position": 0.42},
            ],
        },
    )

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    joined = "\n".join(events)

    assert '"source":"physics3d"' in joined
    assert '"base_position":[1.0,2.0,0.9]' in joined
    assert '"name":"left_shoulder_pitch"' in joined
    assert '"position":0.42' in joined
