from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from symbiont_lab.physics3d.telemetry_binary import (
    BinaryDeltaReader,
    BinaryDenseReader,
    BinaryEventReader,
    BinaryFrameSchemaReader,
    BinaryPathRegistryReader,
    BinaryRecordIterator,
    BinaryStringTableReader,
)
from symbiont_lab.physics3d.telemetry_compaction import canonical_json_bytes
from symbiont_lab.physics3d.telemetry_reader import open_telemetry
from symbiont_lab.physics3d.telemetry_v41 import (
    AsyncTelemetryV41Writer,
    TelemetryV41Reader,
    TelemetryV41Writer,
    verify_v41_run,
)


@dataclass
class DummyTick:
    tick: int
    alive: bool = True
    metabolic_work_cost: float = 0.0
    signed_zero: float = 0.0


def _episode(sample: int):
    return {
        "primitive_id": "primitive.example",
        "start_tick": max(0, sample - 1),
        "end_tick": sample,
        "source": "natural",
        "evidence_blocks": [sample],
        "sample_index": sample,
        "materialized": sample >= 2,
        "competence": False,
    }


def _state(tick: int) -> dict:
    episodes = []
    if tick >= 2:
        episodes.append(_episode(2))
    if tick >= 5:
        episodes.append(_episode(5))
    semantics_note = "v2" if tick >= 5 else "v1"
    return {
        "schema_version": 3,
        "tick": tick,
        "organism_id": "symbiont:test",
        "observer_semantics": {
            "sensory": {"signal.a": {"kind": "opaque", "note": semantics_note}},
            "motor": {},
            "provenance": {"owner": "observer", "feeds_back": False},
        },
        "pre": {
            "physical": {
                "base_position": [tick * 0.01, 0.0, 1.0],
                "base_orientation": [0.0, 0.0, 0.0, 1.0],
                "joints": [
                    {"joint_index": 0, "position": tick * 0.1, "velocity": 0.2},
                    {"joint_index": 1, "position": 0.0, "velocity": 0.0},
                ],
            },
            "sensory_input": {
                "monotonic_timestamp_ns": 1000 + tick,
                "values": {"signal.a": tick * 0.1},
            },
        },
        "runtime": {
            "signal_knowledge": [
                {"signal_id": "signal.a", "samples": tick, "confidence": tick / 10}
            ],
            "sensory_phenotype": {
                "sensors": [
                    {"sensor_id": "signal.a", "health": 1.0, "cost": 0.1}
                ]
            },
            "knowledge_events": (
                [{"kind": "knowledge", "value": tick}] if tick % 2 == 0 else []
            ),
            "runtime_events": [],
            "experience_records_created": (
                [{"record_id": f"r{tick}", "context_tokens": ["a", "b"]}]
                if tick in (2, 5)
                else []
            ),
            "narrative": [f"tick-{tick}"],
            "homeostatic_deviation": tick * 0.001,
        },
        "cognition": {
            "activations": {"sense.a": tick * 0.2},
            "readouts": {"readout_core": tick * 0.3},
            "motor_readouts": {},
            "primitive_readouts": {},
            "prediction_errors": [],
            "mutations": (
                [{"kind": "edge", "payload": {"tick": tick}}]
                if tick == 3
                else []
            ),
            "recycling_events": [],
            "predictive_gain": tick * 0.01,
        },
        "cognitive_topology": {
            "nodes": [
                {
                    "node_id": "sense.a",
                    "kind": "sense",
                    "predicts_node_id": None,
                    "bias": 0.1,
                    "tau": 1.0,
                },
                {
                    "node_id": "concept.a",
                    "kind": "concept",
                    "predicts_node_id": None,
                    "bias": 0.2,
                    "tau": 1.0,
                },
            ],
            "edges": [
                {
                    "source_id": "sense.a",
                    "target_id": "concept.a",
                    "kind": "excitatory",
                    "weight": tick * 0.01,
                    "plasticity": 0.1,
                    "delay_ticks": 0,
                    "support": tick,
                    "age_ticks": tick,
                    "stable_ticks": tick,
                    "last_use_tick": tick,
                }
            ],
        },
        "action": {
            "origin": "none",
            "origin_detail": "none",
            "actuations": [],
        },
        "physics": {
            "substeps": 10,
            "mechanical_work_joules": tick * 0.01,
            "resource_contacted": False,
            "contact_count": 0,
            "base_path_length": 0.01,
            "max_contact_normal_force": 0.0,
            "contact_normal_impulse": 0.0,
            "final_contacts": [],
            "raw_substeps": None,
        },
        "post": {
            "physical": {
                "base_position": [(tick + 1) * 0.01, 0.0, 1.0],
                "base_orientation": [0.0, 0.0, 0.0, 1.0],
                "joints": [
                    {"joint_index": 0, "position": tick * 0.1 + 0.01, "velocity": 0.2},
                    {"joint_index": 1, "position": 0.0, "velocity": 0.0},
                ],
            },
            "resource": {"distance": 1.0, "remaining": 1.0, "absorbed_energy": 0.0},
            "metabolism": {"energy": 1.0},
            "physiology": None,
        },
        "self_model": {"confidence": tick * 0.01},
        "body_schema": {
            "parts": [
                {"id": "joint.0", "confidence": 1.0},
                {"id": "joint.1", "confidence": 1.0},
            ]
        },
        "outcome": {
            "current_resource_distance": 1.0,
            "resource_progress": 0.0,
        },
        "sensorimotor": {
            "episodes": episodes,
            "motor_primitives": [
                {"primitive_id": "primitive.example", "samples": tick}
            ],
            "active_motor_repertoire": ["primitive.example"] if tick >= 2 else [],
            "actuator_evidence": [
                {"actuator_id": "motor.0", "activations": tick, "relations": []}
            ],
        },
        "timing_ms": {"organism": tick * 0.1, "physics": tick * 0.2},
        "future_unknown": {
            "signed": -0.0 if tick >= 4 else 0.0,
            "payload": [tick, None],
        },
    }


def _write(writer):
    originals = []
    summaries = []
    for tick in range(1, 8):
        state = _state(tick)
        summary = DummyTick(
            tick=tick,
            metabolic_work_cost=tick * 0.001,
            signed_zero=-0.0 if tick >= 4 else 0.0,
        )
        full = (
            {
                "organism": {
                    "saved_at_tick": tick,
                    "large": "x" * 5000,
                },
                "physical": {"tick": tick},
            }
            if writer.needs_snapshot(tick)
            else None
        )
        writer.append(summary, rich_state=state, full_snapshot=full)
        originals.append(state)
        summaries.append(summary)
    writer.close()
    return originals, summaries


def test_v41_round_trip_is_exact_for_every_tick(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=42,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=3,
        flush_every=1,
        run_id="run",
    )
    originals, summaries = _write(writer)
    reader = TelemetryV41Reader(writer.root)

    reconstructed = list(reader.iter_states())
    reconstructed_summaries = list(reader.iter_summaries())
    assert len(reconstructed) == len(originals)
    for left, right in zip(originals, reconstructed, strict=True):
        assert canonical_json_bytes(left) == canonical_json_bytes(right)
    for left, right in zip(summaries, reconstructed_summaries, strict=True):
        assert canonical_json_bytes(left.__dict__) == canonical_json_bytes(right)

    assert canonical_json_bytes(reader.state_at(4)) == canonical_json_bytes(_state(4))
    assert reader.summary_at(7)["tick"] == 7
    assert verify_v41_run(writer.root)["complete"] is True


def test_v41_separates_checkpoints_from_anchors(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="split",
    )
    _write(writer)

    anchors = sorted((writer.root / "anchors").glob("*.json"))
    organism_checkpoints = sorted(
        (writer.root / "checkpoints" / "organism").glob("*.json")
    )
    physical_checkpoints = sorted(
        (writer.root / "checkpoints" / "physical").glob("*.json")
    )
    assert anchors
    assert organism_checkpoints
    assert physical_checkpoints
    assert all(
        '"snapshot"' not in path.read_text(encoding="utf-8")
        for path in anchors
    )
    organism_payload = json.loads(
        organism_checkpoints[0].read_text(encoding="utf-8")
    )
    physical_payload = json.loads(
        physical_checkpoints[0].read_text(encoding="utf-8")
    )
    assert organism_payload["component"] == "organism"
    assert physical_payload["component"] == "physical"
    assert "state" in organism_payload
    assert "state" in physical_payload



def test_v41_events_are_not_repeated_as_accumulated_snapshots(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=20,
        run_id="events",
    )
    _write(writer)

    events = list(
        TelemetryV41Reader(writer.root).iter_events(
            event_type="sensorimotor.episodes"
        )
    )
    assert len(events) == 2
    assert [item["payload"][0]["sample_index"] for item in events] == [2, 5]

def test_v41_unknown_paths_use_exact_fallback(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=20,
        run_id="fallback",
    )
    _write(writer)

    manifest = json.loads((writer.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["compaction"]["fallback_records"] > 0
    assert manifest["compaction"]["fallback_bytes"] > 0
    assert canonical_json_bytes(TelemetryV41Reader(writer.root).state_at(6)) == canonical_json_bytes(_state(6))



def test_v41_detects_frame_tampering(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=20,
        run_id="tamper",
    )
    _write(writer)

    path = writer.root / "frames" / "dense.bin"
    raw = bytearray(path.read_bytes())
    assert raw
    raw[-1] ^= 0x01
    path.write_bytes(raw)

    with pytest.raises(ValueError):
        list(TelemetryV41Reader(writer.root).iter_states())

def test_v41_detects_commit_tampering(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="commit-tamper",
    )
    _write(writer)

    path = writer.root / "ticks.ndjson"
    lines = path.read_text(encoding="utf-8").splitlines()
    item = json.loads(lines[-1])
    item["state_sha256"] = "0" * 64
    lines[-1] = json.dumps(item, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="commit hash mismatch"):
        list(TelemetryV41Reader(writer.root).iter_states())


def test_v41_async_writer_is_semantically_equivalent(tmp_path):
    common = dict(
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=3,
        run_id="run",
    )
    sync = TelemetryV41Writer(tmp_path / "sync", **common)
    async_writer = AsyncTelemetryV41Writer(tmp_path / "async", **common)
    left, _ = _write(sync)
    right, _ = _write(async_writer)

    assert left == right
    sync_states = list(TelemetryV41Reader(sync.root).iter_states())
    async_states = list(TelemetryV41Reader(async_writer.root).iter_states())
    assert [
        canonical_json_bytes(item) for item in sync_states
    ] == [
        canonical_json_bytes(item) for item in async_states
    ]


def test_open_telemetry_detects_v41(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="generic",
    )
    _write(writer)

    reader = open_telemetry(writer.root)
    assert canonical_json_bytes(reader.state_at(3)) == canonical_json_bytes(_state(3))


def test_v41_verify_detects_checkpoint_tampering(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="checkpoint-tamper",
    )
    _write(writer)

    checkpoint = sorted(
        (writer.root / "checkpoints" / "organism").glob("*.json")
    )[-1]
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["state"]["large"] = "tampered"
    checkpoint.write_text(
        json.dumps(payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        verify_v41_run(writer.root)


def test_v41_state_at_rejects_self_consistent_but_divergent_anchor(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="anchor-commitment",
    )
    _write(writer)

    anchor = sorted((writer.root / "anchors").glob("*.json"))[1]
    payload = json.loads(anchor.read_text(encoding="utf-8"))
    payload.pop("anchor_sha256")
    payload["state"]["future_unknown"]["payload"][0] = 999999
    from symbiont_lab.physics3d.telemetry_compaction import payload_sha256
    payload["anchor_sha256"] = payload_sha256(payload)
    anchor.write_text(
        json.dumps(payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    tick = int(payload["tick"])
    with pytest.raises(ValueError, match="anchor state commitment mismatch"):
        TelemetryV41Reader(writer.root).state_at(tick)



def test_v41_channel_disappearance_resets_writer_and_reader_baselines(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="channel-lifecycle",
    )
    states = [
        {
            "schema_version": 3,
            "tick": 1,
            "observer_semantics": {"version": "same"},
            "slm": {"loss": 1.0},
            "self_model": {"confidence": 0.1},
            "sensorimotor": {
                "episodes": [{"primitive_id": "p", "sample_index": 1}],
                "motor_primitives": [{"primitive_id": "p", "samples": 1}],
            },
        },
        {"schema_version": 3, "tick": 2},
        {
            "schema_version": 3,
            "tick": 3,
            "observer_semantics": {"version": "same"},
            "slm": {"loss": 2.0},
            "self_model": {"confidence": 0.2},
            "sensorimotor": {
                "episodes": [{"primitive_id": "p", "sample_index": 1}],
                "motor_primitives": [{"primitive_id": "p", "samples": 2}],
            },
        },
    ]
    for state in states:
        writer.append({"tick": state["tick"]}, rich_state=state)
    writer.close()

    reconstructed = list(TelemetryV41Reader(writer.root).iter_states())
    assert [
        canonical_json_bytes(item) for item in reconstructed
    ] == [
        canonical_json_bytes(item) for item in states
    ]

    episode_records = list(
        TelemetryV41Reader(writer.root).iter_events(
            event_type="sensorimotor.episodes"
        )
    )
    assert len(episode_records) == 2
    assert [item["tick"] for item in episode_records] == [1, 3]


def test_v41_uses_exact_previous_post_copy_for_matching_pre_physical(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        run_id="physical-copy",
    )
    first_post = {
        "base_position": [1.0, 2.0, 3.0],
        "joints": [{"joint_index": 0, "position": 0.2}],
    }
    writer.append(
        {"tick": 1},
        rich_state={
            "tick": 1,
            "pre": {"physical": {"base_position": [0.0, 0.0, 0.0]}},
            "post": {"physical": first_post},
        },
    )
    writer.append(
        {"tick": 2},
        rich_state={
            "tick": 2,
            "pre": {"physical": first_post},
            "post": {
                "physical": {
                    "base_position": [1.1, 2.0, 3.0],
                    "joints": [{"joint_index": 0, "position": 0.3}],
                }
            },
        },
    )
    writer.close()

    strings = BinaryStringTableReader(writer.root / "schemas" / "strings.bin")
    schemas = BinaryFrameSchemaReader(
        writer.root / "schemas" / "frames.bin",
        strings,
    )
    decoder = BinaryDenseReader(schemas, strings)
    copies = []
    with (writer.root / "frames" / "dense.bin").open("rb") as handle:
        iterator = BinaryRecordIterator(handle, decoder.decode_record)
        while True:
            item = iterator.next()
            if item is None:
                break
            if (
                item["t"] == 2
                and item["c"] == "pre.physical"
                and item["m"] == 2
            ):
                copies.append(item)
    assert len(copies) == 1
    assert copies[0]["f"] == "post.physical"
    assert (
        TelemetryV41Reader(writer.root).state_at(2)["pre"]["physical"]
        == first_post
    )

def test_v41_writes_derivative_tick_event_and_structure_indexes(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=3,
        run_id="indexes",
    )
    _write(writer)

    tick_index = writer.root / "indexes" / "ticks.ndjson"
    event_index = writer.root / "indexes" / "events.ndjson"
    structure_index = writer.root / "indexes" / "structures.ndjson"
    assert tick_index.stat().st_size > 0
    assert event_index.stat().st_size > 0
    assert structure_index.stat().st_size > 0

    reader = TelemetryV41Reader(writer.root)
    events = list(
        reader.iter_events(
            event_type="runtime.knowledge_events",
            start_tick=4,
        )
    )
    assert all(item["tick"] >= 4 for item in events)



def test_v41_manifest_declares_layout_revision_four(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="layout-revision",
    )
    writer.append({"tick": 1}, rich_state={"tick": 1})
    writer.close()

    manifest = json.loads(
        (writer.root / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["layout_revision"] == 4
    assert manifest["storage_model"] == "typed-binary-temporal-streams"
    assert (writer.root / "schemas" / "strings.bin").is_file()
    assert (writer.root / "frames" / "dense.bin").is_file()

def test_v41_corrupt_event_index_falls_back_to_canonical_scan(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=3,
        run_id="corrupt-index",
    )
    _write(writer)

    index_path = writer.root / "indexes" / "events.ndjson"
    index_path.write_text("{not-json}\n", encoding="utf-8")

    reader = TelemetryV41Reader(writer.root)
    events = list(
        reader.iter_events(
            event_type="runtime.knowledge_events",
            start_tick=2,
        )
    )
    assert [item["tick"] for item in events] == [2, 4, 6]



def test_v41_structural_claim_growth_uses_path_deltas_not_frame_schemas(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        run_id="claim-deltas",
    )
    base_profile = {
        "signal_id": "signal.a",
        "observed_opportunities": 1,
        "claims": [
            {
                "claim_id": "claim.1",
                "kind": "association",
                "status": "candidate",
                "evidence_count": 1,
            }
        ],
    }
    grown_profile = {
        "signal_id": "signal.a",
        "observed_opportunities": 2,
        "claims": [
            {
                "claim_id": "claim.1",
                "kind": "association",
                "status": "supported",
                "evidence_count": 2,
            },
            {
                "claim_id": "claim.2",
                "kind": "association",
                "status": "candidate",
                "evidence_count": 1,
            },
        ],
    }
    for tick, profile in ((1, base_profile), (2, grown_profile)):
        writer.append(
            {"tick": tick},
            rich_state={
                "tick": tick,
                "runtime": {
                    "signal_knowledge": [profile],
                    "knowledge_events": [],
                    "runtime_events": [],
                    "experience_records_created": [],
                },
                "cognition": {"mutations": [], "recycling_events": []},
                "sensorimotor": {"episodes": []},
            },
        )
    writer.close()

    strings = BinaryStringTableReader(writer.root / "schemas" / "strings.bin")
    paths = BinaryPathRegistryReader(
        writer.root / "schemas" / "structural-paths.bin",
        strings,
    )
    decoder = BinaryDeltaReader(paths, strings)
    second = None
    with (writer.root / "structures" / "state.bin").open("rb") as handle:
        iterator = BinaryRecordIterator(handle, decoder.decode_record)
        while True:
            item = iterator.next()
            if item is None:
                break
            if item["t"] == 2 and item["c"] == "runtime.signal_knowledge":
                second = item
                break
    assert second is not None
    assert second["p"]

    schemas = BinaryFrameSchemaReader(
        writer.root / "schemas" / "frames.bin",
        strings,
    )
    assert all(
        channel != "runtime.signal_knowledge"
        for channel, _template in schemas.schemas.values()
    )

    rebuilt = TelemetryV41Reader(writer.root).state_at(2)
    assert rebuilt["runtime"]["signal_knowledge"] == [grown_profile]


def test_v41_batches_ephemeral_events_per_channel_and_tick(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="event-batches",
    )
    events = [
        {"kind": "one", "event_id": "e1"},
        {"kind": "two", "event_id": "e2"},
        {"kind": "three", "event_id": "e3"},
    ]
    writer.append(
        {"tick": 1},
        rich_state={
            "tick": 1,
            "runtime": {
                "knowledge_events": events,
                "runtime_events": [],
                "experience_records_created": [],
            },
            "cognition": {"mutations": [], "recycling_events": []},
            "sensorimotor": {"episodes": []},
        },
    )
    writer.close()

    strings = BinaryStringTableReader(writer.root / "schemas" / "strings.bin")
    decoder = BinaryEventReader(strings)
    knowledge = []
    with (writer.root / "events" / "events.bin").open("rb") as handle:
        iterator = BinaryRecordIterator(handle, decoder.decode_record)
        while True:
            item = iterator.next()
            if item is None:
                break
            if item["c"] == "runtime.knowledge_events":
                knowledge.append(item)
    assert len(knowledge) == 1
    assert knowledge[0]["v"] == events
    assert (
        TelemetryV41Reader(writer.root)
        .state_at(1)["runtime"]["knowledge_events"]
        == events
    )



def test_v41_random_access_uses_nearest_anchor_index_and_survives_corruption(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="anchor-index",
    )
    originals, _summaries = _write(writer)

    reader = TelemetryV41Reader(writer.root)
    assert canonical_json_bytes(reader.state_at(6)) == canonical_json_bytes(
        originals[5]
    )

    index_path = writer.root / "indexes" / "anchors.ndjson"
    index_path.write_text("{corrupt-index}\n", encoding="utf-8")

    reader = TelemetryV41Reader(writer.root)
    assert canonical_json_bytes(reader.state_at(6)) == canonical_json_bytes(
        originals[5]
    )


def test_v41_default_anchor_interval_is_256_and_checkpoint_interval_is_1024(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="anchor-default",
    )
    try:
        assert writer.manifest["anchor_interval"] == 256
        assert writer.manifest["checkpoint_interval"] == 1024
        assert writer.needs_anchor(256) is True
        assert writer.needs_snapshot(256) is False
        assert writer.needs_snapshot(1024) is True
    finally:
        writer.close()


def test_v41_anchor_and_checkpoint_cadence_are_independent(tmp_path):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=8,
        anchor_interval=2,
        run_id="independent-cadence",
    )
    try:
        assert writer.needs_anchor(2) is True
        assert writer.needs_snapshot(2) is False
        assert writer.needs_anchor(8) is True
        assert writer.needs_snapshot(8) is True
    finally:
        writer.close()


def test_v41_state_at_materializes_only_requested_tick(tmp_path, monkeypatch):
    writer = TelemetryV41Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        anchor_interval=100,
        run_id="single-materialization",
    )
    _write(writer)

    import symbiont_lab.physics3d.telemetry_v41 as module

    original = module.reassemble_state
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "reassemble_state", counted)
    reader = TelemetryV41Reader(writer.root)
    state = reader.state_at(7)

    assert state["tick"] == 7
    assert calls == 1
