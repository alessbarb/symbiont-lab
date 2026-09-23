from __future__ import annotations

from symbiont_lab.physics3d.telemetry_compaction import canonical_json_bytes
from symbiont_lab.physics3d.telemetry_schema import (
    TemporalClass,
    event_mode,
    partition_state,
    reassemble_state,
)
from symbiont_lab.physics3d.telemetry_structural import (
    logical_view,
    structural_view,
)


def test_partition_reassembles_exact_state():
    state = {
        "schema_version": 3,
        "tick": 4,
        "observer_semantics": {"sensory": {"a": 1}},
        "pre": {"physical": {"x": 1.0}},
        "runtime": {
            "signal_knowledge": [{"signal_id": "a", "confidence": 0.5}],
            "sensory_phenotype": {"sensors": []},
            "knowledge_events": [{"kind": "new"}],
            "runtime_events": [],
            "experience_records_created": [{"record_id": "r1"}],
            "narrative": ["opaque"],
        },
        "cognition": {
            "mutations": [{"kind": "edge"}],
            "recycling_events": [],
            "activations": {"a": 0.2},
        },
        "sensorimotor": {
            "episodes": [{"primitive_id": "p", "sample_index": 1}],
            "motor_primitives": [{"primitive_id": "p", "weight": 0.4}],
        },
        "cognitive_topology": {"nodes": [], "edges": []},
        "future_unknown": {"keep": [-0.0, None]},
    }

    split = partition_state(state)
    restored = reassemble_state(
        dense=split.dense,
        structural=split.structural,
        events=split.events,
        static=split.static,
        fallback=split.fallback,
    )

    assert canonical_json_bytes(restored) == canonical_json_bytes(state)
    assert "future_unknown" in split.fallback
    assert event_mode("runtime.knowledge_events") is TemporalClass.EVENT_EPHEMERAL
    assert event_mode("sensorimotor.episodes") is TemporalClass.EVENT_CUMULATIVE


def test_structural_ast_is_collision_free_and_reversible():
    value = {
        "@m": {"@l": [{"@v": 1}]},
        "items": [
            {"node_id": "a", "weight": -0.0},
            {"node_id": "b", "weight": 1.0},
        ],
        "ordinary": [{"x": 1}, {"x": 2}],
    }

    restored = logical_view(structural_view(value))

    assert canonical_json_bytes(restored) == canonical_json_bytes(value)


def test_keyed_structural_view_preserves_original_order():
    value = [
        {"node_id": "b", "weight": 2.0},
        {"node_id": "a", "weight": 1.0},
    ]

    restored = logical_view(structural_view(value))

    assert [item["node_id"] for item in restored] == ["b", "a"]
