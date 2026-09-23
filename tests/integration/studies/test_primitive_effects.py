from __future__ import annotations

from symbiont_lab.physics3d.telemetry import TelemetryV3Writer
from symbiont_lab.studies.physics3d.primitive_effects import (
    analyze_primitive_effects,
)


def _physical(x: float):
    return {
        "base_position": [x, 0.0, 1.0],
        "base_orientation": [0.0, 0.0, 0.0, 1.0],
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "center_of_mass": [x, 0.0, 1.0],
        "contact_links": [1, 2],
        "joints": [
            {"joint_index": 0, "position": 0.0, "velocity": 0.0},
        ],
    }


def test_assay_recovers_recurrent_body_frame_translation(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="study",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        run_id="run",
    )
    for tick in range(13):
        episodes = []
        if tick in (4, 12):
            episodes = [{
                "primitive_id": "primitive.example",
                "start_tick": tick - 4,
                "end_tick": tick,
                "source": "natural",
                "evidence_blocks": [0 if tick == 4 else 1],
                "sample_index": 1 if tick == 4 else 2,
                "materialized": tick == 12,
                "competence": False,
            }]
        x = 0.01 * tick
        rich = {
            "schema_version": 3,
            "tick": tick,
            "pre": {"physical": _physical(x)},
            "physics": {
                "base_path_length": 0.011,
                "mechanical_work_joules": 0.1,
            },
            "sensorimotor": {"episodes": episodes},
        }
        summary = {
            "tick": tick,
            "metabolic_work_cost": 0.001,
        }
        writer.append(summary, rich_state=rich)
    writer.close()

    reports = analyze_primitive_effects(writer.root)
    assert len(reports) == 1
    report = reports[0]
    assert report.episodes == 2
    assert report.body_translation_mean[0] > 0.0
    assert report.directional_concentration > 0.99
    assert report.initial_contact_spread == 0.0
