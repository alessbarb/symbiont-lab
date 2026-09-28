from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_p8_local_runner_is_the_canonical_full_reprofile_entrypoint() -> None:
    root = _root()
    runner = (root / "scripts" / "reprofile_performance.py").read_text(encoding="utf-8")

    assert "scripts/reprofile_performance.py" in runner
    assert "--quick" in runner
    assert "report.json" in runner
    assert "report.md" in runner
    assert "observer_off.prof" in runner
    assert "observer_on.prof" in runner
    assert "test_performance_optimization_gate.py" in runner
    assert '"validity": validity' in runner
    assert '"matched_end_hash"' in runner
    assert '"addopts="' in runner


def test_p8_ci_report_is_non_blocking_and_quick_only() -> None:
    root = _root()
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    job = workflow[workflow.index("  performance-report:") :]
    assert "continue-on-error: true" in job
    assert "scripts/reprofile_performance.py --quick" in job
    assert "actions/upload-artifact@v4" in job


def test_p8_does_not_turn_wall_clock_timings_into_ci_thresholds() -> None:
    root = _root()
    runner = (root / "scripts" / "reprofile_performance.py").read_text(encoding="utf-8")

    forbidden = (
        "max_ms_per_tick",
        "min_ticks_per_second",
        "performance_threshold",
        "assert speedup",
        "assert tax",
    )
    for token in forbidden:
        assert token not in runner
