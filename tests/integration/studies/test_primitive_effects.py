from __future__ import annotations

import math

from symbiont_lab.physics3d.telemetry import TelemetryV3Writer
from symbiont_lab.studies.physics3d.primitive_effects import (
    StateComparability,
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
    assert report.materialized is True
    assert report.independent_evidence_blocks == 2
    assert report.replication_target_met is False
    assert report.body_translation_mean[0] > 0.0
    assert report.translation_magnitude_median > 0.0
    assert report.directional_concentration > 0.99
    assert report.initial_contact_spread == 0.0


def test_assay_separates_within_state_from_between_state_effect_variation(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="study",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        run_id="conditioned",
    )
    states = {
        0: _physical(0.00),
        4: _physical(0.10),
        8: _physical(
            0.20,
            orientation=(0.0, 0.0, 1.0, 0.0),
            joint=1.0,
            contacts=(3,),
        ),
        12: _physical(
            0.22,
            orientation=(0.0, 0.0, 1.0, 0.0),
            joint=1.0,
            contacts=(3,),
        ),
    }
    last = states[0]
    for tick in range(13):
        if tick in states:
            last = states[tick]
        episodes = []
        if tick in (4, 8, 12):
            episodes = [{
                "primitive_id": "primitive.conditioned",
                "start_tick": tick - 4,
                "end_tick": tick,
                "source": "natural",
                "evidence_blocks": [tick // 4 - 1],
                "sample_index": tick // 4,
                "materialized": tick >= 8,
                "competence": False,
            }]
        writer.append(
            {"tick": tick, "metabolic_work_cost": 0.0},
            rich_state={
                "schema_version": 3,
                "tick": tick,
                "pre": {"physical": last},
                "physics": {
                    "base_path_length": 0.03,
                    "mechanical_work_joules": 0.1,
                },
                "sensorimotor": {"episodes": episodes},
            },
        )
    writer.close()

    report = analyze_primitive_effects(
        writer.root,
        comparability=StateComparability(
            orientation_angle_max=math.radians(10.0),
            linear_velocity_delta_max=0.1,
            angular_velocity_delta_max=0.1,
            joint_rms_delta_max=0.1,
            contact_jaccard_distance_max=0.1,
            com_height_delta_max=0.01,
        ),
        replication_target=3,
    )[0]

    assert report.replication_target_met is True
    assert report.comparable_state_pairs == 1
    assert report.noncomparable_state_pairs == 2
    assert report.within_state_translation_delta_mean is not None
    assert report.between_state_translation_delta_mean is not None
    assert (
        report.within_state_translation_delta_mean
        < report.between_state_translation_delta_mean
    )
