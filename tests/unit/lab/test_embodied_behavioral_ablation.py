from __future__ import annotations

from copy import deepcopy

from symbiont_lab.studies.learning.embodied_behavioral_ablation import (
    _freeze_cognitive_learning,
    _lesion_cognitive_motor_outputs,
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
                    },
                    {
                        "source_id": "concept_a",
                        "target_id": "readout_primitive:p",
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

    assert removed == 2
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
