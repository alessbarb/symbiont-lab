from __future__ import annotations

from symbiont_lab.physics3d.telemetry_compaction import canonical_json_bytes
from symbiont_lab.physics3d.telemetry_numeric import (
    FrameSchemaRegistryReader,
    FrameSchemaRegistryWriter,
)
from symbiont_lab.physics3d.telemetry_schema import (
    TemporalClass,
    event_mode,
    partition_state,
    reassemble_state,
)
from symbiont_lab.physics3d.telemetry_structural import (
    LegacyStructuralStreamReader,
    LegacyStructuralStreamWriter,
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


def test_reassembly_materializes_parents_before_extracted_children():
    state = {
        "runtime": {
            "narrative": [{"capability_id": "cpu", "summary": "current"}],
            "signal_knowledge": [{"signal_id": "signal.a", "confidence": 0.5}],
            "knowledge_events": [{"kind": "learned"}],
            "homeostatic_deviation": 0.2,
        },
        "pre": {
            "physical": {"base_position": [1.0, 2.0, 3.0]},
            "sensory_input": {"values": {"signal.a": 0.4}},
        },
        "post": {
            "physical": {"base_position": [1.1, 2.0, 3.0]},
            "metabolism": {"energy": 0.8},
        },
        "physics": {
            "raw_substeps": [{"substep": 1, "x": 0.1}],
            "mechanical_work_joules": 0.3,
        },
    }
    split = partition_state(state, layout_revision=2)
    restored = reassemble_state(
        dense=split.dense,
        structural=split.structural,
        events=split.events,
        static=split.static,
        fallback=split.fallback,
    )
    assert canonical_json_bytes(restored) == canonical_json_bytes(state)


def test_layout_revision_one_preserves_early_v41_partition_contract():
    state = {
        "runtime": {
            "narrative": [{"capability_id": "cpu"}],
            "signal_references": {"signal.a": "sense.a"},
            "signal_knowledge": [{"signal_id": "signal.a"}],
        },
        "pre": {
            "physical": {"base_position": [1.0, 2.0, 3.0]},
            "sensory_input": {"values": {"signal.a": 0.1}},
        },
        "post": {"physical": {"base_position": [1.1, 2.0, 3.0]}},
    }

    legacy = partition_state(state, layout_revision=1)
    current = partition_state(state, layout_revision=2)

    assert "pre" in legacy.dense
    assert "pre.physical" not in legacy.dense
    assert "runtime.narrative" not in legacy.structural

    assert "pre.physical" in current.dense
    assert "runtime.narrative" in current.structural
    assert "runtime.signal_references" in current.structural

    assert canonical_json_bytes(
        reassemble_state(
            dense=legacy.dense,
            structural=legacy.structural,
            events=legacy.events,
            static=legacy.static,
            fallback=legacy.fallback,
        )
    ) == canonical_json_bytes(state)


def test_composite_edge_identity_is_order_independent_in_storage():
    first = [
        {
            "source_id": "a",
            "target_id": "b",
            "kind": "excitatory",
            "delay_ticks": 0,
            "weight": 0.1,
        },
        {
            "source_id": "b",
            "target_id": "c",
            "kind": "predictive",
            "delay_ticks": 1,
            "weight": 0.2,
        },
    ]
    second = list(reversed(first))

    first_view = structural_view(first)
    second_view = structural_view(second)
    first_payload = next(iter(first_view.values()))
    second_payload = next(iter(second_view.values()))

    assert first_payload["i"] == second_payload["i"]
    assert first_payload["o"] == list(reversed(second_payload["o"]))
    assert logical_view(first_view) == first
    assert logical_view(second_view) == second


def test_signal_knowledge_claims_are_keyed_by_claim_id():
    value = [
        {
            "signal_id": "signal.a",
            "claims": [
                {"claim_id": "claim.1", "status": "candidate"},
                {"claim_id": "claim.2", "status": "supported"},
            ],
        }
    ]
    stored = structural_view(value)
    profile_payload = stored["@k"]["i"]["s:signal.a"]
    claims_payload = profile_payload["@m"]["claims"]["@k"]

    assert claims_payload["n"] == "claim_id"
    assert set(claims_payload["i"]) == {"s:claim.1", "s:claim.2"}
    assert logical_view(stored) == value


def test_legacy_structural_codec_does_not_reinterpret_claim_id(tmp_path):
    schema_path = tmp_path / "frames.ndjson"
    stream_path = tmp_path / "structural.ndjson"
    value = [
        {
            "signal_id": "signal.a",
            "claims": [
                {"claim_id": "claim.1", "status": "candidate"},
                {"claim_id": "claim.2", "status": "supported"},
            ],
        }
    ]

    with (
        schema_path.open("w+", encoding="utf-8") as schemas,
        stream_path.open("w+", encoding="utf-8") as stream,
    ):
        registry = FrameSchemaRegistryWriter(schemas)
        writer = LegacyStructuralStreamWriter(stream, registry)
        writer.append(1, "runtime.signal_knowledge", value)
        schemas.flush()
        stream.flush()

    registry = FrameSchemaRegistryReader(schema_path)
    reader = LegacyStructuralStreamReader(registry)
    import json

    record = json.loads(stream_path.read_text(encoding="utf-8"))
    channel, restored = reader.apply(record)

    assert channel == "runtime.signal_knowledge"
    assert restored == value
