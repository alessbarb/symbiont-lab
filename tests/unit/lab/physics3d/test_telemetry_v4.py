from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from symbiont_lab.physics3d.persistence import (
    load_telemetry_records,
    load_telemetry_transitions,
)
from symbiont_lab.physics3d.telemetry_v4 import (
    AsyncTelemetryV4Writer,
    TelemetryV4Reader,
    TelemetryV4Writer,
    load_v4_tick_records,
    load_v4_transitions,
    verify_v4_run,
)


@dataclass
class DummyTick:
    tick: int
    alive: bool = True
    joint_motion: float = 0.0


def _rich(tick: int) -> dict:
    return {
        "schema_version": 4,
        "tick": tick,
        "observer_semantics": {
            "sensory": {"signal.a": {"kind": "opaque", "note": "x" * 128}},
            "motor": {},
        },
        "pre": {
            "physical": {
                "base_position": [tick * 0.001, 0.0, 1.0],
                "joints": [
                    {"joint_index": 0, "position": tick * 0.01, "velocity": 0.1},
                    {"joint_index": 1, "position": 0.0, "velocity": 0.0},
                ],
            },
            "sensory_input": {
                "monotonic_timestamp_ns": 1000 + tick,
                "values": {"signal.a": 0.1 * tick},
            },
        },
        "cognition": {
            "activations": {"sense.a": 0.2 * tick},
            "readouts": {"readout_core": 0.3 * tick},
            "prediction_errors": [],
        },
        "cognitive_topology": {
            "nodes": [{"node_id": "sense.a", "payload": "z" * 256}],
            "edges": [],
        },
        "sensorimotor": {"episodes": []},
    }


def _write(writer) -> None:
    for tick in range(1, 7):
        full = (
            {"organism": {"saved_at_tick": tick}, "physical": {"tick": tick}}
            if writer.needs_snapshot(tick)
            else None
        )
        writer.append(
            DummyTick(tick=tick, joint_motion=float(tick)),
            rich_state=_rich(tick),
            full_snapshot=full,
        )
    writer.close()


def test_v4_losslessly_reconstructs_every_tick_and_summary(tmp_path):
    writer = TelemetryV4Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=42,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        flush_every=1,
        run_id="run",
        minimum_reference_bytes=32,
    )
    _write(writer)

    states = load_v4_transitions(writer.root)
    summaries = load_v4_tick_records(writer.root)

    assert states == [_rich(tick) for tick in range(1, 7)]
    assert [item["tick"] for item in summaries] == list(range(1, 7))
    assert summaries[-1]["joint_motion"] == 6.0
    assert TelemetryV4Reader(writer.root).state_at(5) == _rich(5)

    verification = verify_v4_run(writer.root)
    assert verification["complete"] is True
    assert verification["records"] == 6
    assert verification["anchors"] == 4


def test_v4_transitions_are_sparse_instead_of_repeating_rich_state(tmp_path):
    writer = TelemetryV4Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=100,
        run_id="sparse",
        minimum_reference_bytes=32,
    )
    _write(writer)

    transition_bytes = (writer.root / "transitions.ndjson").stat().st_size
    naive_bytes = sum(
        len(json.dumps(_rich(tick), sort_keys=True, separators=(",", ":")).encode())
        + len(
            json.dumps(
                DummyTick(tick=tick, joint_motion=float(tick)).__dict__,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        for tick in range(1, 7)
    )
    assert transition_bytes < naive_bytes


def test_v4_detects_transition_tampering(tmp_path):
    writer = TelemetryV4Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="tamper",
    )
    writer.append(DummyTick(tick=1), rich_state=_rich(1))
    writer.append(DummyTick(tick=2), rich_state=_rich(2))
    writer.close()

    lines = (writer.root / "transitions.ndjson").read_text(
        encoding="utf-8"
    ).splitlines()
    second = json.loads(lines[1])
    second["state_patch"][0]["value"] = 999
    lines[1] = json.dumps(second, separators=(",", ":"))
    (writer.root / "transitions.ndjson").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="record hash mismatch"):
        load_v4_transitions(writer.root)


def test_async_v4_is_semantically_equivalent(tmp_path):
    common = dict(
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="run",
        minimum_reference_bytes=32,
    )
    sync = TelemetryV4Writer(tmp_path / "sync", **common)
    async_writer = AsyncTelemetryV4Writer(tmp_path / "async", **common)
    _write(sync)
    _write(async_writer)

    assert load_v4_transitions(sync.root) == load_v4_transitions(async_writer.root)
    assert load_v4_tick_records(sync.root) == load_v4_tick_records(async_writer.root)
    assert verify_v4_run(async_writer.root)["complete"] is True


def test_generic_persistence_api_auto_detects_v4(tmp_path):
    writer = TelemetryV4Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="generic",
    )
    for tick in range(1, 4):
        writer.append(
            DummyTick(tick=tick, joint_motion=float(tick)),
            rich_state=_rich(tick),
        )
    writer.close()

    assert load_telemetry_records(writer.root) == load_v4_tick_records(writer.root)
    assert load_telemetry_transitions(writer.root) == load_v4_transitions(writer.root)


def test_v4_reconstruction_streams_transition_records(tmp_path, monkeypatch):
    writer = TelemetryV4Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="streaming",
    )
    _write(writer)

    reader = TelemetryV4Reader(writer.root)
    monkeypatch.setattr(
        reader,
        "transitions",
        lambda: (_ for _ in ()).throw(
            AssertionError("materializing transitions is forbidden")
        ),
    )

    assert list(reader.iter_states()) == [_rich(tick) for tick in range(1, 7)]
    assert reader.state_at(5) == _rich(5)
