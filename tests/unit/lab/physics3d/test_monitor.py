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
