from __future__ import annotations

import json
import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "simulate" in result.stdout
    assert "experiment" in result.stdout
    assert "audit" in result.stdout
    assert "archive" in result.stdout
    assert "host" in result.stdout
    assert "reproduce" in result.stdout


def test_cli_audit():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "audit", "verify"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "All experimental invariants verified successfully." in result.stdout


def test_cli_simulate():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "simulate", "--hosts", "10", "--steps", "20", "--seed", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "=== Symbiont Simulation Result ===" in result.stdout


def test_cli_host_discover():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "discover"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    capability_ids = {item["capability_id"] for item in payload["capabilities"]}
    assert "runtime.python" in capability_ids
    assert "clock.monotonic" in capability_ids
    forbidden = {"hostname", "username", "user", "home", "cwd", "ip", "mac"}
    detail_keys = {
        key.lower()
        for capability in payload["capabilities"]
        for key in capability["detail"]
    }
    assert not forbidden.intersection(detail_keys)


def test_cli_host_sample():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "sample"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert not payload["failures"]
    capability_ids = {item["capability_id"] for item in payload["readings"]}
    assert "compute.logical_cpu" in capability_ids
    assert "storage.disk_usage" in capability_ids
    for reading in payload["readings"]:
        assert reading["privacy_class"] in ("aggregate", "non_identifying")
        if reading["quality"] == "unavailable":
            assert reading["value"] is None
        else:
            assert isinstance(reading["value"], (int, float))


def test_cli_host_monitor():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "monitor", "--ticks", "3"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["snapshots"]) == 3
    assert [snapshot["tick"] for snapshot in payload["snapshots"]] == [1, 2, 3]
    assert isinstance(payload["capability_changes"], list)


def test_cli_study_run_prints_its_result():
    """A study's computed result must reach the user, not just a success banner."""
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "study", "run", "attention.replicated", "--seeds", "1,2"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Study completed successfully." in result.stdout
    banner_index = result.stdout.index("Study completed successfully.")
    payload = json.loads(result.stdout[banner_index + len("Study completed successfully.") :])
    assert payload["seeds"] == [1, 2]
    assert "summaries" in payload
