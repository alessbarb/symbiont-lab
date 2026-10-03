from __future__ import annotations

from lab.physics3d.telemetry.v41 import TelemetryV41Writer
from lab.studies.physics3d.primitive_effects import (
    analyze_primitive_effects,
)


def _physical(
    x: float,
    *,
    orientation=(0.0, 0.0, 0.0, 1.0),
    joint: float = 0.0,
    contacts=(1, 2),
):
    return {
        "base_position": [x, 0.0, 1.0],
        "base_orientation": list(orientation),
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "center_of_mass": [x, 0.0, 1.0],
        "contact_links": list(contacts),
        "joints": [
            {"joint_index": 0, "position": joint, "velocity": 0.0},
        ],
    }


def test_assay_reads_v41_without_version_specific_code(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="study",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=4,
        run_id="v41",
    )
    for tick in range(9):
        episodes = []
        if tick in (4, 8):
            episodes = [
                {
                    "primitive_id": "primitive.v41",
                    "start_tick": tick - 4,
                    "end_tick": tick,
                    "source": "natural",
                    "evidence_blocks": [tick // 4 - 1],
                    "sample_index": tick // 4,
                    "materialized": tick == 8,
                    "competence": False,
                }
            ]
        writer.append(
            {"tick": tick, "metabolic_work_cost": 0.001},
            rich_state={
                "schema_version": 3,
                "tick": tick,
                "pre": {"physical": _physical(0.01 * tick)},
                "physics": {
                    "base_path_length": 0.011,
                    "mechanical_work_joules": 0.1,
                },
                "sensorimotor": {"episodes": episodes},
            },
        )
    writer.close()

    report = analyze_primitive_effects(writer.root, replication_target=2)[0]
    assert report.primitive_id == "primitive.v41"
    assert report.episodes == 2
    assert report.materialized is True
    assert report.replication_target_met is True
