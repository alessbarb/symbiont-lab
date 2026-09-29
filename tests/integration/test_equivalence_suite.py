from __future__ import annotations

from pathlib import Path

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.equivalence import EquivalenceRunConfig, equivalent, run_digests
from symbiont_lab.physics3d.equivalence_suite import (
    EquivalenceStatus,
    Scenario,
    _coverage_failure,
)


def _snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "snapshot"
    (snapshot / "models").mkdir(parents=True)
    run(
        headless=True,
        ticks=2,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        body_kind="anthropomorphic-v6",
        symbiont_file=snapshot / "organism.symbiont",
        body_file=snapshot / "body.json",
        telemetry_file=tmp_path / "telemetry",
    )
    return snapshot


def test_equivalence_config_is_deterministic_without_training(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    config = EquivalenceRunConfig(ticks=4, body_kind="anthropomorphic-v6")
    first = run_digests(snapshot, config=config)
    second = run_digests(snapshot, config=config)
    assert equivalent(first, second)


def test_training_coverage_requires_observed_events(tmp_path: Path) -> None:
    scenario = Scenario(
        scenario_id="promotion",
        snapshot=tmp_path,
        body_kind="test",
        ticks=192,
        seed=42,
        training=True,
        train_interval=32,
        min_training_completions=4,
        require_promotion_event=True,
        coverage=("private-model-training", "model-promotion"),
        memory_gb=6.0,
        disk_gb=1.0,
        cpu_threads=1,
    )
    assert "completed private-model trainings" in (
        _coverage_failure(scenario, {"training_completions": 3, "promotion_events": []}) or ""
    )
    assert "promotion event" in (
        _coverage_failure(scenario, {"training_completions": 4, "promotion_events": []}) or ""
    )
    assert _coverage_failure(
        scenario,
        {"training_completions": 4, "promotion_events": [{"tick": 100}]},
    ) is None


def test_not_assessable_status_is_distinct_from_causal_fail() -> None:
    assert EquivalenceStatus.NOT_ASSESSABLE_NONDETERMINISM != (
        EquivalenceStatus.FAIL_CAUSAL_DIVERGENCE
    )



def test_suite_status_reports_missing_reference_snapshots(tmp_path: Path) -> None:
    from symbiont_lab.physics3d.equivalence_suite import suite_status

    suite = tmp_path / "suite.toml"
    suite.write_text(
        '''
schema_version = 1
suite_id = "test-suite"
status = "capture-required"

[[scenario]]
id = "missing"
snapshot = "snapshots/S01"
body_kind = "anthropomorphic-v6"
ticks = 10
training = false
coverage = ["organism-state"]
''',
        encoding="utf-8",
    )
    status = suite_status(suite)
    assert status["ready"] is False
    assert status["computed_status"] == "CAPTURE_REQUIRED"
    assert status["scenarios"][0]["state"] == "MISSING"



def test_snapshot_contract_rejects_wrong_body_kind() -> None:
    from symbiont_lab.physics3d.equivalence_suite import _snapshot_contract_failure

    scenario = Scenario(
        scenario_id="developed-cognition",
        snapshot=Path("."),
        body_kind="anthropomorphic-v6-vision",
        ticks=32,
        seed=42,
        training=False,
        train_interval=32,
        min_training_completions=0,
        require_promotion_event=False,
        coverage=("organism-state",),
        memory_gb=4.0,
        disk_gb=1.0,
        cpu_threads=1,
    )
    reason = _snapshot_contract_failure(
        scenario,
        {
            "scenario": "developed-cognition",
            "body_kind": "crawler-v1",
        },
    )
    assert reason and "body_kind mismatch" in reason


def test_snapshot_contract_rejects_wrong_scenario() -> None:
    from symbiont_lab.physics3d.equivalence_suite import _snapshot_contract_failure

    scenario = Scenario(
        scenario_id="promotion-eligible",
        snapshot=Path("."),
        body_kind="anthropomorphic-v6-vision",
        ticks=192,
        seed=42,
        training=True,
        train_interval=32,
        min_training_completions=4,
        require_promotion_event=True,
        coverage=("model-promotion",),
        memory_gb=6.0,
        disk_gb=1.0,
        cpu_threads=1,
    )
    reason = _snapshot_contract_failure(
        scenario,
        {
            "scenario": "private-model-training",
            "body_kind": "anthropomorphic-v6-vision",
        },
    )
    assert reason and "scenario mismatch" in reason


def test_snapshot_contract_rejects_missing_model_artifacts() -> None:
    from symbiont_lab.physics3d.equivalence_suite import _snapshot_contract_failure

    scenario = Scenario(
        scenario_id="developed-cognition",
        snapshot=Path("."),
        body_kind="anthropomorphic-v6-vision",
        ticks=32,
        seed=42,
        training=False,
        train_interval=32,
        min_training_completions=0,
        require_promotion_event=False,
        coverage=("organism-state",),
        memory_gb=4.0,
        disk_gb=1.0,
        cpu_threads=1,
    )
    reason = _snapshot_contract_failure(
        scenario,
        {
            "scenario": "developed-cognition",
            "body_kind": "anthropomorphic-v6-vision",
            "models_source": "none",
        },
    )
    assert reason and "model artifacts" in reason
