from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

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
    checkpoints = sorted((writer.root / "checkpoints").glob("*.json"))
    assert anchors
    assert checkpoints
    assert all('"snapshot"' not in path.read_text(encoding="utf-8") for path in anchors)
    assert any('"snapshot"' in path.read_text(encoding="utf-8") for path in checkpoints)


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

    event_lines = [
        json.loads(line)
        for line in (writer.root / "events" / "events.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    episode_appends = [
        item
        for item in event_lines
        if item["c"] == "sensorimotor.episodes" and item["o"] == "append"
    ]
    assert len(episode_appends) == 2
    assert [item["v"]["sample_index"] for item in episode_appends] == [2, 5]


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

    path = writer.root / "frames" / "dense.ndjson"
    lines = path.read_text(encoding="utf-8").splitlines()
    item = json.loads(lines[-1])
    if item["m"] == "f":
        item["v"][0] = "tampered"
    else:
        item["v"][0][1] = "tampered"
    lines[-1] = json.dumps(item, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="dense record commitment mismatch"):
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

    checkpoint = sorted((writer.root / "checkpoints").glob("*.json"))[-1]
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["snapshot"]["organism"]["large"] = "tampered"
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
