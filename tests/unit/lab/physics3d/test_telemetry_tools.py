from __future__ import annotations

from symbiont_lab.physics3d.telemetry_tools import (
    benchmark_run,
    compare_runs,
    convert_run,
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
