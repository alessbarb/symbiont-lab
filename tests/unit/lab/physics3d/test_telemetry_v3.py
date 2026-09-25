import json
from contextlib import suppress
from dataclasses import dataclass

import pytest

from symbiont_lab.physics3d.persistence import load_telemetry_records
from symbiont_lab.physics3d.telemetry import (
    AsyncTelemetryV3Writer,
    TelemetryV3Writer,
    load_v3_deltas,
    load_v3_tick_records,
    load_v3_transitions,
    verify_v3_run,
)
from symbiont_lab.physics3d.telemetry_reader import open_telemetry


@dataclass
class DummyTick:
    tick: int
    alive: bool = True
    joint_motion: float = 0.0


def _rich(tick: int) -> dict:
    return {
        "schema_version": 3,
        "tick": tick,
        "pre": {
            "sensory_input": {
                "monotonic_timestamp_ns": 1000 + tick,
                "values": {"signal.a": 0.1 * tick},
            }
        },
        "cognition": {
            "topology_revision": tick // 2,
            "topology_health": "developing",
            "recovering": False,
            "mutations": [],
            "recycling_events": [],
            "stranded_concepts": [],
            "retiring_predictors": [],
            "retirement_edges": 0,
            "structural_candidates": 0,
            "structural_producers": 0,
            "oldest_structural_wait_ticks": 0,
            "representation_maturity": {"nascent": 1},
            "max_contention_losses": 0,
            "activations": {"sense.a": 0.2 * tick},
            "readouts": {"readout_core": 0.3 * tick},
            "prediction_errors": [],
        },
        "action": {"origin": "babbling", "actuations": []},
        "physics": {"substeps": 20},
        "post": {"physical": {"base_position": [0.0, 0.0, 1.0]}},
        "body_schema": {
            "schema_version": 2,
            "state": "partial",
            "parts": [],
            "dependencies": [],
            "global_state": {},
        },
        "sensorimotor": {
            "known_patterns": tick,
            "primitives": 0,
            "hypotheses": 0,
            "cognitive_primitives": 0,
            "investigation_active": False,
            "investigation_primitive_id": None,
            "replay_active": False,
            "active_motor_repertoire": [],
            "best_controllability": 0.1 * tick,
        },
    }


def test_v3_writer_creates_run_manifest_chain_deltas_and_snapshots(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path / "telemetry-v3",
        organism_id="symbiont:test",
        start_tick=0,
        seed=42,
        physics_hz=240,
        cognition_hz=12,
        embodiment_mode="new",
        effective_configuration={"mode": "test"},
        snapshot_interval=2,
        flush_every=1,
        run_id="run-test",
    )
    try:
        for tick in (1, 2, 3):
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
    finally:
        writer.close()

    run = tmp_path / "telemetry-v3" / "run-test"
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 3
    assert manifest["tick_records"] == 3
    assert manifest["snapshots"] == 2
    assert manifest["final_record_hash"]

    records = load_v3_tick_records(run)
    assert [record["tick"] for record in records] == [1, 2, 3]
    assert records[2]["joint_motion"] == 3.0

    transitions = load_v3_transitions(run)
    assert transitions[0]["pre"]["sensory_input"]["values"]["signal.a"] == 0.1
    assert transitions[2]["cognition"]["readouts"]["readout_core"] == pytest.approx(0.9)

    deltas = load_v3_deltas(run)
    assert {item["component"] for item in deltas} == {
        "cognition",
        "body_schema",
        "sensorimotor",
    }

    assert (run / "snapshots" / "tick-000000000001.json").is_file()
    assert (run / "snapshots" / "tick-000000000002.json").is_file()

    verification = verify_v3_run(run)
    assert verification["complete"] is True
    assert verification["records"] == 3


def test_v3_loader_detects_hash_chain_tampering(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=12,
        embodiment_mode="new",
        run_id="run-tamper",
    )
    writer.append(DummyTick(tick=1), rich_state=_rich(1))
    writer.close()

    ticks = writer.root / "ticks.ndjson"
    line = json.loads(ticks.read_text(encoding="utf-8"))
    line["payload"]["summary"]["joint_motion"] = 999.0
    ticks.write_text(json.dumps(line) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="record hash mismatch"):
        load_v3_tick_records(writer.root, verify=True)


def test_persistence_loader_resolves_latest_v3_run(tmp_path):
    root = tmp_path / "telemetry-v3"
    for run_id, tick in (("20260921T010000Z-a", 1), ("20260921T020000Z-b", 2)):
        writer = TelemetryV3Writer(
            root,
            organism_id="symbiont:test",
            start_tick=0,
            seed=1,
            physics_hz=240,
            cognition_hz=12,
            embodiment_mode="new",
            run_id=run_id,
        )
        writer.append(DummyTick(tick=tick), rich_state=_rich(tick))
        writer.close()

    records = load_telemetry_records(root)
    assert [record["tick"] for record in records] == [2]


def test_structural_delta_projection_ignores_dynamic_activation_churn(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=12,
        embodiment_mode="new",
        run_id="run-deltas",
    )
    first = _rich(1)
    second = _rich(1)
    second["tick"] = 2
    second["cognition"]["activations"] = {"sense.a": 0.99}
    second["cognition"]["readouts"] = {"readout_core": 0.77}

    writer.append(DummyTick(tick=1), rich_state=first)
    writer.append(DummyTick(tick=2), rich_state=second)
    writer.close()

    deltas = [
        json.loads(line)
        for line in (writer.root / "deltas.ndjson").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cognition_deltas = [item for item in deltas if item["component"] == "cognition"]
    assert len(cognition_deltas) == 1


def test_writer_rejects_rich_tick_mismatch(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=12,
        embodiment_mode="new",
        run_id="run-tick-mismatch",
    )
    try:
        with pytest.raises(ValueError, match="rich telemetry tick mismatch"):
            writer.append(DummyTick(tick=2), rich_state=_rich(1))
    finally:
        writer.close()


def _write_three_ticks(writer) -> None:
    for tick in (1, 2, 3):
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


def test_async_writer_is_byte_equivalent_to_synchronous_writer(tmp_path):
    common = dict(
        organism_id="symbiont:test",
        start_tick=0,
        seed=42,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="new",
        effective_configuration={"mode": "test"},
        snapshot_interval=2,
        flush_every=1,
        run_id="run-equivalent",
    )
    sync = TelemetryV3Writer(tmp_path / "sync", **common)
    async_writer = AsyncTelemetryV3Writer(tmp_path / "async", **common)
    _write_three_ticks(sync)
    _write_three_ticks(async_writer)

    for relative in (
        "ticks.ndjson",
        "deltas.ndjson",
        "snapshots/tick-000000000001.json",
        "snapshots/tick-000000000002.json",
    ):
        assert (sync.root / relative).read_bytes() == (async_writer.root / relative).read_bytes()

    assert verify_v3_run(async_writer.root)["complete"] is True


def test_async_writer_close_drains_queue_without_dropping_ticks(tmp_path):
    writer = AsyncTelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="new",
        snapshot_interval=1000,
        queue_size=8,
        run_id="run-drain",
    )
    for tick in range(1, 101):
        writer.append(DummyTick(tick=tick), rich_state=_rich(tick))
    writer.close()

    records = load_v3_tick_records(writer.root)
    assert [record["tick"] for record in records] == list(range(1, 101))
    manifest = json.loads((writer.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tick_records"] == 100


def test_async_writer_propagates_worker_failure(tmp_path):
    writer = AsyncTelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="new",
        run_id="run-worker-error",
    )
    try:
        with pytest.raises(RuntimeError, match="async telemetry worker failed"):
            writer.append(DummyTick(tick=2), rich_state=_rich(1))
            writer.flush()
    finally:
        with suppress(RuntimeError):
            writer.close()


def test_version_neutral_v3_reader_streams_state_and_summary_together(tmp_path):
    writer = TelemetryV3Writer(
        tmp_path,
        organism_id="symbiont:test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="new",
        run_id="run-neutral",
    )
    _write_three_ticks(writer)

    reader = open_telemetry(writer.root)
    records = list(reader.iter_records())

    assert [state["tick"] for state, _summary in records] == [1, 2, 3]
    assert [summary["tick"] for _state, summary in records] == [1, 2, 3]
    assert records[-1][0] == _rich(3)
