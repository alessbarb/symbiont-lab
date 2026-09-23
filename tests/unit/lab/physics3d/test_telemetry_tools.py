from __future__ import annotations

from symbiont_lab.physics3d.telemetry_tools import (
    benchmark_run,
    compare_runs,
    convert_run,
    evaluate_acceptance_gates,
)
from symbiont_lab.physics3d.telemetry_v4 import TelemetryV4Writer
from symbiont_lab.physics3d.telemetry_v41 import TelemetryV41Reader


def _state(tick: int):
    return {
        "schema_version": 3,
        "tick": tick,
        "pre": {"physical": {"x": tick * 0.1}},
        "runtime": {
            "knowledge_events": [],
            "runtime_events": [],
            "experience_records_created": [],
            "signal_knowledge": [],
            "sensory_phenotype": {},
        },
        "cognition": {"mutations": [], "recycling_events": []},
        "sensorimotor": {"episodes": []},
        "observer_semantics": {"provenance": {"feeds_back": False}},
        "future_unknown": tick,
    }


def test_converter_proves_exact_v4_to_v41_equivalence(tmp_path):
    source_writer = TelemetryV4Writer(
        tmp_path / "source",
        organism_id="test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        snapshot_interval=2,
        run_id="old",
    )
    for tick in range(1, 6):
        source_writer.append({"tick": tick}, rich_state=_state(tick))
    source_writer.close()

    report = convert_run(
        source_writer.root,
        tmp_path / "converted",
        run_id="new",
    )

    assert report.verified is True
    assert report.ticks == 5
    reader = TelemetryV41Reader(report.destination_run)
    assert reader.state_at(5) == _state(5)


def test_benchmark_reports_v41_stream_breakdown(tmp_path):
    source_writer = TelemetryV4Writer(
        tmp_path / "source",
        organism_id="test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="old",
    )
    for tick in range(1, 5):
        source_writer.append({"tick": tick}, rich_state=_state(tick))
    source_writer.close()
    report = convert_run(source_writer.root, tmp_path / "converted", run_id="new")

    benchmark = benchmark_run(report.destination_run)

    assert benchmark["version"] == "v4.1"
    assert benchmark["ticks"] == 4
    assert benchmark["breakdown"]["ticks"] > 0
    assert benchmark["breakdown"]["dense"] > 0
    assert benchmark["bytes_per_tick"] > 0
    assert benchmark["state_at_ms"]["max"] is not None


def test_compare_runs_returns_storage_delta(tmp_path):
    a = TelemetryV4Writer(
        tmp_path / "a",
        organism_id="test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="run",
    )
    for tick in range(1, 4):
        a.append({"tick": tick}, rich_state=_state(tick))
    a.close()
    converted = convert_run(a.root, tmp_path / "b", run_id="run")

    comparison = compare_runs(a.root, converted.destination_run)

    assert "saved_bytes" in comparison
    assert comparison["left"]["ticks"] == comparison["right"]["ticks"] == 3


def test_acceptance_gate_passes_for_valid_small_v41_run(tmp_path):
    source_writer = TelemetryV4Writer(
        tmp_path / "source",
        organism_id="test",
        start_tick=0,
        seed=1,
        physics_hz=240,
        cognition_hz=24,
        embodiment_mode="test",
        run_id="old",
    )
    for tick in range(1, 5):
        source_writer.append({"tick": tick}, rich_state=_state(tick))
    source_writer.close()
    report = convert_run(source_writer.root, tmp_path / "converted", run_id="new")
    benchmark = benchmark_run(report.destination_run)

    gate = evaluate_acceptance_gates(
        benchmark,
        expected_ticks=4,
        max_evidence_bytes=10 * 1024 * 1024,
        max_fallback_fraction=1.0,
        max_state_at_p95_ms=10_000.0,
    )

    assert gate["passed"] is True
    assert all(gate["checks"].values())


def test_acceptance_gate_reports_each_failed_constraint():
    report = {
        "version": "v4.1",
        "ticks": 3,
        "evidence_bytes_excluding_checkpoints": 500,
        "fallback_fraction": 0.25,
        "integrity": {"complete": False},
        "state_at_ms": {"p95": 250.0},
    }

    gate = evaluate_acceptance_gates(
        report,
        expected_ticks=4,
        max_evidence_bytes=100,
        max_fallback_fraction=0.05,
        max_state_at_p95_ms=100.0,
    )

    assert gate["passed"] is False
    assert gate["checks"] == {
        "version_is_v41": True,
        "integrity_complete": False,
        "evidence_bytes": False,
        "fallback_fraction": False,
        "state_at_p95_ms": False,
        "expected_ticks": False,
    }
