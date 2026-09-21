from __future__ import annotations

from copy import deepcopy

from symbiont_lab.studies.learning.embodied_behavioral_ablation import (
    _delay_cognitive_motor_outputs,
    _freeze_cognitive_learning,
    _lesion_cognitive_motor_outputs,
    _shuffle_cognitive_motor_outputs,
)


def _checkpoint():
    return {
        "cognitive_bridge": {
            "safety_state": {
                "consecutive_failures": 0,
                "frozen": False,
            },
            "graph": {
                "nodes": [
                    {"node_id": "concept_a", "kind": "concept"},
                    {"node_id": "readout_core", "kind": "readout"},
                    {"node_id": "readout_motor:a", "kind": "readout"},
                    {"node_id": "readout_primitive:p", "kind": "readout"},
                ],
                "edges": [
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_core",
                    },
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_motor:a",
                        "delay_ticks": 1,
                    },
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_motor:b",
                        "delay_ticks": 1,
                    },
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_primitive:p",
                        "delay_ticks": 1,
                    },
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_primitive:q",
                        "delay_ticks": 1,
                    },
                ],
            },
            "structural_candidates": [
                {"family": "motor_readout", "candidate_id": "motor:a"},
                {"family": "primitive_readout", "candidate_id": "primitive:p"},
                {"family": "concept", "candidate_id": "concept:x"},
            ],
        },
        "actuation": {
            "sensorimotor": {"opaque": "preserved"},
        },
        "physiology": {"opaque": "preserved"},
    }


def test_behavioral_ablation_lesions_only_cognitive_motor_output_edges():
    original = _checkpoint()
    lesion = deepcopy(original)

    removed = _lesion_cognitive_motor_outputs(lesion)

    assert removed == 4
    edges = lesion["cognitive_bridge"]["graph"]["edges"]
    assert edges == [
        {
            "source_id": "concept_a",
            "target_id": "readout_core",
        }
    ]
    assert lesion["actuation"] == original["actuation"]
    assert lesion["physiology"] == original["physiology"]


def test_behavioral_ablation_drops_pending_motor_reconstruction_only():
    checkpoint = _checkpoint()

    _lesion_cognitive_motor_outputs(checkpoint)

    families = [
        candidate["family"]
        for candidate in checkpoint["cognitive_bridge"]["structural_candidates"]
    ]
    assert families == ["concept"]


def test_behavioral_ablation_freezes_learning_without_changing_failure_history():
    checkpoint = _checkpoint()

    _freeze_cognitive_learning(checkpoint)

    safety = checkpoint["cognitive_bridge"]["safety_state"]
    assert safety["frozen"] is True
    assert safety["consecutive_failures"] == 0



def test_behavioral_ablation_shuffles_only_within_output_family():
    checkpoint = _checkpoint()

    changed = _shuffle_cognitive_motor_outputs(checkpoint)

    assert changed == 4
    edges = checkpoint["cognitive_bridge"]["graph"]["edges"]
    motor_targets = [
        edge["target_id"]
        for edge in edges
        if edge["target_id"].startswith("readout_motor:")
    ]
    primitive_targets = [
        edge["target_id"]
        for edge in edges
        if edge["target_id"].startswith("readout_primitive:")
    ]
    assert set(motor_targets) == {"readout_motor:a", "readout_motor:b"}
    assert set(primitive_targets) == {
        "readout_primitive:p",
        "readout_primitive:q",
    }
    assert edges[0]["target_id"] == "readout_core"


def test_behavioral_ablation_delay_touches_only_motor_output_edges():
    checkpoint = _checkpoint()

    changed = _delay_cognitive_motor_outputs(checkpoint)

    assert changed == 4
    edges = checkpoint["cognitive_bridge"]["graph"]["edges"]
    core = next(edge for edge in edges if edge["target_id"] == "readout_core")
    assert "delay_ticks" not in core
    for edge in edges:
        if edge["target_id"].startswith(("readout_motor:", "readout_primitive:")):
            assert edge["delay_ticks"] == 2
