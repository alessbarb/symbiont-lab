import queue

from symbiont_lab.physics3d.monitor import (
    CameraState,
    MonitorSnapshot,
    _put_latest,
    strongest_outputs,
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
