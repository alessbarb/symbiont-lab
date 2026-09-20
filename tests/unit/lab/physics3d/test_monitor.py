import queue

from symbiont_lab.physics3d.monitor import (
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
    assert snapshot.mechanical_work_joules == 1.25
    assert snapshot.metabolic_work_cost == 0.00125
