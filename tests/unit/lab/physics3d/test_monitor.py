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
        prediction_error=0.1,
        active_effectors=2,
        joint_motion=1.2,
        contact_count=3,
        height=0.5,
        checkpoint_age=7,
        symbiont_file="/tmp/subject.symbiont.json",
        strongest_outputs=(("out.0", 0.8),),
    )

    assert not hasattr(snapshot, "body_id")
    assert not hasattr(snapshot, "joint_names")
    assert snapshot.strongest_outputs == (("out.0", 0.8),)
