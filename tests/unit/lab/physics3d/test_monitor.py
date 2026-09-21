import queue

from symbiont_lab.physics3d.monitor import (
    CameraState,
    MonitorSnapshot,
    _put_latest,
    strongest_outputs,
    _event_transition,
    _event_context,
)


def test_monitor_ranks_opaque_outputs_only():
    assert strongest_outputs(
        {"out.3": 0.2, "out.1": 0.9, "out.2": 0.5, "out.0": 0.1},
        limit=3,
    ) == (
        ("out.1", 0.9),
        ("out.2", 0.5),
        ("out.3", 0.2),
    )


def test_monitor_queue_drops_stale_frames_instead_of_blocking():
    q = queue.Queue(maxsize=1)
    _put_latest(q, {"type": "snapshot", "payload": {"tick": 1}})
    _put_latest(q, {"type": "snapshot", "payload": {"tick": 2}})

    assert q.get_nowait()["payload"]["tick"] == 2


def test_monitor_snapshot_contains_only_evaluator_fields():
    snapshot = MonitorSnapshot(
        tick=10,
        symbiont_id="subject",
        embodiment_mode="resume",
        schema_confidence=0.4,
        schema_parts=5,
        schema_sensory_parts=3,
        schema_cognitive_regions=2,
        schema_dependency_evidence=4,
        schema_dependencies=2,
        predictor_count=1,
        shadow_prediction_count=4,
        promotable_shadow_count=1,
        prediction_error=0.1,
        active_effectors=2,
        joint_motion=1.2,
        contact_count=3,
        mechanical_work_joules=1.25,
        metabolic_work_cost=0.00125,
        height=0.5,
        checkpoint_age=7,
        symbiont_file="/tmp/subject.symbiont.json",
        strongest_outputs=(("motor.0", 0.8),),
        slm_records=128,
        slm_transition_records=96,
        slm_models=1,
        slm_active=True,
        slm_training=False,
        slm_error=None,
        slm_gate_reason="held_out_outcome_gain",
        slm_gate_gain=0.12,
        slm_best_baseline="persistence",
        slm_candidate_loss=0.8,
        slm_best_baseline_loss=0.92,
        cycle_ms=12.5,
        realtime_ratio=2.0,
        organism_ms=7.0,
        physics_ms=4.0,
        diagnostics_ms=1.5,
        resource_distance=1.8,
        resource_field=0.30,
        resource_remaining=198.0,
        absorbed_energy=2.0,
        metabolic_reserve_ratio=0.75,
        displacement_from_origin=0.4,
        motor_origin="cognition",
        initial_resource_distance=3.05,
        minimum_resource_distance=2.10,
        resource_progress=0.95,
        motor_origin_cognition=12,
        motor_origin_babbling=80,
        motor_origin_primitive=3,
        motor_origin_mixed=7,
        motor_origin_spontaneous=34,
        motor_origin_probe=5,
        motor_origin_none=49,
        motor_repertoire_size=6,
        sensorimotor_coverage=1.0,
        sensorimotor_patterns=23,
        motor_primitives=4,
        cognitive_motor_primitives=2,
        best_motor_controllability=0.42,
        best_motor_directional_consistency=0.81,
        primitive_replay_active=True,
        sensorimotor_h1_samples=100,
        sensorimotor_h4_samples=90,
        sensorimotor_h16_samples=70,
        sensorimotor_h64_samples=20,
        passive_baseline_samples=6,
    )

    assert not hasattr(snapshot, "body_id")
    assert not hasattr(snapshot, "joint_names")
    assert snapshot.strongest_outputs == (("motor.0", 0.8),)
    assert snapshot.schema_parts == 5
    assert snapshot.schema_cognitive_regions == 2
    assert snapshot.predictor_count == 1
    assert snapshot.shadow_prediction_count == 4
    assert snapshot.promotable_shadow_count == 1
    assert snapshot.slm_transition_records == 96
    assert snapshot.slm_active is True
    assert snapshot.cycle_ms == 12.5
    assert snapshot.realtime_ratio == 2.0
    assert snapshot.organism_ms == 7.0
    assert snapshot.physics_ms == 4.0
    assert snapshot.diagnostics_ms == 1.5
    assert snapshot.mechanical_work_joules == 1.25
    assert snapshot.metabolic_work_cost == 0.00125
    assert snapshot.resource_distance == 1.8
    assert snapshot.resource_field == 0.30
    assert snapshot.resource_remaining == 198.0
    assert snapshot.absorbed_energy == 2.0
    assert snapshot.metabolic_reserve_ratio == 0.75
    assert snapshot.displacement_from_origin == 0.4
    assert snapshot.motor_origin == "cognition"
    assert snapshot.initial_resource_distance == 3.05
    assert snapshot.minimum_resource_distance == 2.10
    assert snapshot.resource_progress == 0.95
    assert snapshot.motor_origin_cognition == 12
    assert snapshot.motor_origin_babbling == 80
    assert snapshot.motor_origin_primitive == 3
    assert snapshot.motor_origin_mixed == 7
    assert snapshot.motor_origin_spontaneous == 34
    assert snapshot.motor_origin_probe == 5
    assert snapshot.motor_origin_none == 49
    assert snapshot.motor_repertoire_size == 6
    assert snapshot.sensorimotor_coverage == 1.0
    assert snapshot.sensorimotor_patterns == 23
    assert snapshot.motor_primitives == 4
    assert snapshot.cognitive_motor_primitives == 2
    assert snapshot.best_motor_controllability == 0.42
    assert snapshot.best_motor_directional_consistency == 0.81
    assert snapshot.primitive_replay_active is True
    assert snapshot.sensorimotor_h64_samples == 20
    assert snapshot.passive_baseline_samples == 6



def test_camera_state_is_bounded_for_safe_passive_rendering():
    bounded = CameraState(
        yaw=725.0,
        pitch=-200.0,
        distance=0.1,
        target_z=9.0,
    ).bounded()

    assert bounded.yaw == 5.0
    assert bounded.pitch == -85.0
    assert bounded.distance == 1.1
    assert bounded.target_z == 2.5


def test_viewer_process_poll_commands_and_stop():
    import time
    from multiprocessing import get_context
    from symbiont_lab.physics3d.monitor import UnifiedViewerProcess

    ctx = get_context("spawn")
    viewer = UnifiedViewerProcess(ctx)
    viewer._commands.put({"type": "pause", "paused": True})
    viewer._commands.put({"type": "speed", "speed": 2.0})
    viewer._commands.put({"type": "step"})
    time.sleep(0.05)

    cmds = viewer.poll_commands()
    assert len(cmds) == 3
    assert cmds[0] == {"type": "pause", "paused": True}
    assert cmds[1] == {"type": "speed", "speed": 2.0}
    assert cmds[2] == {"type": "step"}

    # Test that poll_stop preserves non-stop commands in buffer
    viewer._commands.put({"type": "speed", "speed": 0.5})
    viewer._commands.put({"type": "stop"})
    time.sleep(0.05)
    assert viewer.poll_stop() is True
    # The non-stop command should still be retrievable
    remaining = viewer.poll_commands()
    assert any(c.get("type") == "speed" and c.get("speed") == 0.5 for c in remaining)


def test_record_to_snapshot_conversion():
    from symbiont_lab.physics3d.monitor import record_to_snapshot

    record = {
        "tick": 42,
        "organism_id": "test:organism",
        "schema_confidence": 0.88,
        "schema_parts": 6,
        "schema_sensory_parts": 3,
        "schema_cognitive_regions": 2,
        "schema_dependency_evidence": 5,
        "schema_dependencies": 4,
        "predictor_count": 2,
        "shadow_prediction_count": 5,
        "promotable_shadow_count": 1,
        "prediction_error": 0.05,
        "active_effectors": 3,
        "joint_motion": 0.45,
        "contact_count": 2,
        "mechanical_work_joules": 0.12,
        "metabolic_work_cost": 0.00012,
        "base_position": [0.1, 0.2, 0.85],
        "motor_origin": "primitive",
        "resource_distance": 1.25,
        "resource_progress": 0.75,
    }

    snap = record_to_snapshot(record, fallback_id="fallback")
    assert snap["tick"] == 42
    assert snap["symbiont_id"] == "test:organism"
    assert snap["schema_confidence"] == 0.88
    assert snap["height"] == 0.85
    assert snap["motor_origin"] == "primitive"
    assert snap["resource_distance"] == 1.25
    assert snap["resource_progress"] == 0.75


def test_snapshot_to_physical_state_with_full_and_fallback_data():
    from symbiont_lab.physics3d.monitor import snapshot_to_physical_state

    # 1. Full data with joints and contact links
    record_full = {
        "tick": 10,
        "base_position": [1.0, 2.0, 0.9],
        "base_orientation": [0.0, 0.0, 0.0, 1.0],
        "base_linear_velocity": [0.1, 0.0, 0.0],
        "base_angular_velocity": [0.0, 0.1, 0.0],
        "contact_links": [2, 4],
        "joints": [
            {"joint_index": 0, "joint_name": "hip", "position": 0.1, "applied_torque": 5.0},
        ],
        "locomotion_resource": {
            "position": [2.0, 3.0, 0.0],
            "remaining": 150.0,
        },
    }
    state = snapshot_to_physical_state(record_full)
    assert state["base_position"] == [1.0, 2.0, 0.9]
    assert state["contact_links"] == [2, 4]
    assert len(state["joints"]) == 1
    assert state["joints"][0]["applied_torque"] == 5.0
    assert state["locomotion_resource"]["remaining"] == 150.0
    assert state["_reconstructed_fields"] == []

    # 2. Historical data missing joints, contact_links, and locomotion_resource
    record_minimal = {
        "tick": 5,
        "base_position": [0.0, 0.0, 0.8],
        "resource_distance": 2.5,
    }
    state_min = snapshot_to_physical_state(record_minimal)
    assert state_min["base_position"] == [0.0, 0.0, 0.8]
    assert state_min["contact_links"] == []
    assert len(state_min["joints"]) == 14  # one neutral fallback for each v1 motor DOF
    assert state_min["locomotion_resource"]["position"] == [2.5, 0.0, 0.15]
    assert set(state_min["_reconstructed_fields"]) == {"joints", "resource_position"}




def test_event_transition_reports_only_evidence_backed_changes():
    previous = {
        "tick": 99,
        "motor_origin": "babbling",
        "minimum_resource_distance": 2.0,
        "absorbed_energy": 1.0,
        "motor_primitives": 1,
        "cognitive_motor_primitives": 0,
        "schema_parts": 3,
        "predictor_count": 1,
        "displacement_from_origin": 0.04,
    }
    current = {
        "tick": 100,
        "motor_origin": "primitive",
        "minimum_resource_distance": 1.85,
        "absorbed_energy": 1.25,
        "motor_primitives": 2,
        "cognitive_motor_primitives": 1,
        "schema_parts": 4,
        "predictor_count": 2,
        "displacement_from_origin": 0.06,
    }

    events = _event_transition(previous, current)
    kinds = {event["kind"] for event in events}
    categories = {event["kind"]: event["category"] for event in events}

    assert kinds == {
        "motor_origin",
        "resource_minimum",
        "energy_absorbed",
        "motor_primitive",
        "cognitive_primitive",
        "schema_part",
        "predictor",
        "displacement_milestone",
    }
    assert all(event["tick"] == 100 for event in events)
    assert categories["motor_origin"] == "behavior"
    assert categories["resource_minimum"] == "environment"
    assert categories["energy_absorbed"] == "survival"
    assert categories["motor_primitive"] == "learning"
    assert categories["cognitive_primitive"] == "learning"
    assert categories["predictor"] == "learning"
    assert categories["schema_part"] == "body"
    assert categories["displacement_milestone"] == "body"


def test_event_transition_is_quiet_without_change():
    snapshot = {
        "tick": 10,
        "motor_origin": "none",
        "minimum_resource_distance": 3.0,
        "absorbed_energy": 0.0,
        "motor_primitives": 0,
        "cognitive_motor_primitives": 0,
        "schema_parts": 0,
        "predictor_count": 0,
        "displacement_from_origin": 0.0,
    }

    assert _event_transition(snapshot, {**snapshot, "tick": 11}) == ()


def test_event_context_compares_before_and_after_windows():
    records = []
    for tick in range(10):
        records.append(
            {
                "tick": tick,
                "joint_motion": 1.0 if tick < 5 else 3.0,
                "best_motor_controllability": 0.25 if tick < 5 else 1.0,
                "best_motor_directional_consistency": 0.25 if tick < 5 else 1.0,
                "resource_distance": 3.0 if tick < 5 else 2.0,
                "metabolic_reserve_ratio": 0.8 if tick < 5 else 0.6,
                "prediction_error": 0.5 if tick < 5 else 0.2,
            }
        )

    context = _event_context(records, 5, radius=2)

    assert context["tick"] == 5
    assert context["before_samples"] == 2
    assert context["after_samples"] == 2
    metrics = context["metrics"]
    assert metrics["movement"] == (1.0, 3.0)
    assert metrics["control"] == (0.25, 1.0)
    assert metrics["resource"] == (3.0, 2.0)
    assert metrics["energy"] == (0.8, 0.6)
    assert metrics["prediction_error"] == (0.5, 0.2)


def test_event_context_handles_edges_and_missing_values():
    records = [
        {"tick": 1, "joint_motion": 1.0, "prediction_error": None},
        {"tick": 2, "joint_motion": 2.0, "prediction_error": 0.4},
    ]

    context = _event_context(records, 0, radius=12)

    assert context["before_samples"] == 0
    assert context["after_samples"] == 1
    assert context["metrics"]["movement"] == (None, 2.0)
    assert context["metrics"]["prediction_error"] == (None, 0.4)


def test_pill_frame_delegates_fg_and_bg():
    import pytest
    from symbiont_lab.physics3d.monitor import PillFrame

    if PillFrame is None:
        pytest.skip("Tkinter not available")

    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tkinter")

    try:
        var = tk.StringVar(value="DIRECTO")
        pill = PillFrame(root, var, "#8b949e", "#21262d")
        assert pill.cget("fg") == "#8b949e"

        # Configuring fg should delegate to inner label and not raise TclError
        pill.configure(fg="#facc15")
        assert pill.cget("fg") == "#facc15"
        assert pill.label.cget("fg") == "#facc15"

        # Configuring bg should update both frame and label
        pill.configure(bg="#374151")
        assert pill["bg"] == "#374151"
        assert pill.label.cget("bg") == "#374151"
    finally:
        root.destroy()
