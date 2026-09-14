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
    assert "capsule" in result.stdout
    assert "organism" in result.stdout
    assert "evaluate" in result.stdout


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


def test_cli_host_perceive():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "perceive"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    names = {percept["name"] for percept in payload["percepts"]}
    assert "system_load" in names
    assert "storage_pressure" in names
    for percept in payload["percepts"]:
        assert set(percept) == {"name", "value", "unit", "quality", "privacy_class"}


def test_cli_host_rhythms():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "rhythms", "--ticks", "5"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["time_bucket"] in ("night", "morning", "afternoon", "evening")
    assert set(payload["co_occurring_percepts"]) >= {"system_load", "storage_pressure"}
    for name in payload["co_occurring_percepts"]:
        baseline = payload["baselines"][name]
        assert baseline["count"] == 5


def test_cli_host_acclimate():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "acclimate", "--ticks", "5"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["acclimated_capabilities"]
    for capability_id in payload["acclimated_capabilities"]:
        baseline = payload["baselines"][capability_id]
        assert baseline["count"] == 5
        assert "mean" in baseline and "stdev" in baseline
        assert set(baseline) == {"count", "mean", "variance", "stdev"}


def test_cli_host_drift():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "drift", "--ticks", "5"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["ticks"]) == 5
    assert payload["baselines"]
    for name, baseline in payload["baselines"].items():
        assert set(baseline) == {"is_established", "mean", "stdev"}
    for tick in payload["ticks"]:
        for name, obs in tick.items():
            assert obs["kind"] in ("none", "isolated", "gradual", "regime_shift")


def test_cli_host_checkpoint_round_trips():
    export_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "checkpoint", "export", "--ticks", "5"],
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0
    checkpoint = json.loads(export_result.stdout)
    assert checkpoint["schema_version"] == 3

    import_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "checkpoint", "import"],
        input=export_result.stdout,
        capture_output=True,
        text=True,
    )
    assert import_result.returncode == 0
    summary = json.loads(import_result.stdout)
    assert summary["restored_acclimation_capabilities"]
    assert summary["restored_drift_percepts"]


def test_cli_host_checkpoint_import_rejects_bad_schema_version():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "checkpoint", "import"],
        input=json.dumps({"schema_version": 999}),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "invalid checkpoint" in result.stderr


def test_cli_host_attend():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "attend", "--ticks", "5", "--budget", "1.5"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["known_capabilities"]
    assert payload["allocations"]
    for allocation in payload["allocations"]:
        assert set(allocation) == {"name", "uncertainty", "cost"}


def test_cli_host_attend_rejects_non_positive_budget():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "attend", "--budget", "0"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "--budget must be positive" in result.stderr


def test_cli_host_second_look():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main",
            "host", "second-look", "--capability-id", "compute.logical_cpu", "--ticks", "3",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["capability_id"] == "compute.logical_cpu"
    assert payload["cancelled"] is False
    assert len(payload["readings"]) == 3
    for reading in payload["readings"]:
        assert reading["capability_id"] == "compute.logical_cpu"


def test_cli_host_second_look_rejects_unauthorized_capability():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main",
            "host", "second-look", "--capability-id", "nonexistent.thing",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "not available in this host's manifest" in result.stderr


def test_cli_host_revise():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main",
            "host", "revise", "--capability-id", "compute.logical_cpu",
            "--acclimate-ticks", "5", "--evidence-ticks", "3",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["capability_id"] == "compute.logical_cpu"
    assert payload["baseline"]["count"] == 8
    assert set(payload["baseline"]) == {"count", "mean", "variance", "stdev"}


def test_cli_host_revise_rejects_unauthorized_capability():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "host", "revise", "--capability-id", "nonexistent.thing"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "not available in this host's manifest" in result.stderr


def test_cli_host_narrate():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main",
            "host", "narrate", "--ticks", "5", "--budget", "1.5", "--evidence-ticks", "3",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["entries"]
    for entry in payload["entries"]:
        assert set(entry) == {
            "capability_id", "familiarity", "uncertainty", "attended",
            "attention_cost", "evidence_gathered", "contested", "dissent", "summary",
        }
        assert entry["familiarity"] in ("familiar", "unfamiliar")
    attended = [entry for entry in payload["entries"] if entry["attended"]]
    assert attended
    assert attended[0]["evidence_gathered"] > 0


def test_cli_capsule_create_and_verify_round_trip(tmp_path):
    keyfile = tmp_path / "key.json"
    create_result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main",
            "capsule", "create", "--ticks", "5", "--keyfile", str(keyfile),
        ],
        capture_output=True,
        text=True,
    )
    assert create_result.returncode == 0
    assert keyfile.is_file()
    capsule = json.loads(create_result.stdout)
    assert capsule["schema_version"] == 1
    assert "payload" in capsule

    verify_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "verify"],
        input=create_result.stdout,
        capture_output=True,
        text=True,
    )
    assert verify_result.returncode == 0
    summary = json.loads(verify_result.stdout)
    assert summary["valid"] is True
    assert summary["signer_public_key"] == capsule["signer_public_key"]


def test_cli_capsule_reuses_signer_identity_across_invocations(tmp_path):
    keyfile = tmp_path / "key.json"
    first = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "create", "--keyfile", str(keyfile)],
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "create", "--keyfile", str(keyfile)],
        capture_output=True,
        text=True,
    )
    assert json.loads(first.stdout)["signer_public_key"] == json.loads(second.stdout)["signer_public_key"]


def test_cli_capsule_verify_rejects_tampered_payload():
    create_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "create"],
        capture_output=True,
        text=True,
    )
    capsule = json.loads(create_result.stdout)
    capsule["payload"] = {"tampered": True}

    verify_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "verify"],
        input=json.dumps(capsule),
        capture_output=True,
        text=True,
    )
    assert verify_result.returncode == 1
    assert json.loads(verify_result.stdout)["valid"] is False


def test_cli_capsule_ingest():
    create_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "create", "--ticks", "5"],
        capture_output=True,
        text=True,
    )
    ingest_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "ingest", "--ticks", "5"],
        input=create_result.stdout,
        capture_output=True,
        text=True,
    )
    assert ingest_result.returncode == 0
    payload = json.loads(ingest_result.stdout)
    assert set(payload) == {"signer_public_key", "agreement_scores", "reliability"}


def test_cli_capsule_ingest_rejects_tampered_capsule():
    create_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "create"],
        capture_output=True,
        text=True,
    )
    capsule = json.loads(create_result.stdout)
    capsule["payload"] = {"acclimation": {"compute.logical_cpu": {"count": 5, "mean": 999.0, "variance": 0.0}}}

    ingest_result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "capsule", "ingest"],
        input=json.dumps(capsule),
        capture_output=True,
        text=True,
    )
    assert ingest_result.returncode == 1
    assert "signature verification" in ingest_result.stderr


def test_cli_organism_run():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "4", "--attention-budget", "1.5", "--investigate-ticks", "2", "--min-samples", "2",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["ticks"]) == 4
    assert [t["tick"] for t in payload["ticks"]] == [1, 2, 3, 4]
    assert payload["checkpoint"]["schema_version"] == 3
    assert payload["checkpoint"]["acclimation"]
    for tick in payload["ticks"]:
        assert isinstance(tick["narrative"], list) and tick["narrative"]


def test_cli_organism_run_investigate_ticks_zero_disables_investigation():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "2", "--investigate-ticks", "0", "--min-samples", "1",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    for tick in payload["ticks"]:
        assert tick["investigated_capability"] is None
        assert tick["evidence_gathered"] == 0


def test_cli_organism_run_reports_governor_state():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run", "--ticks", "3", "--min-samples", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["governor"]["ticks_run"] == 3
    assert payload["governor"]["stopped_early"] is None
    assert payload["governor"]["is_consented"] is True


def test_cli_organism_run_advisory_disabled_by_default():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run", "--ticks", "3", "--min-samples", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["advisories"] == []


def test_cli_organism_run_advisory_log_only_written_with_consent(tmp_path):
    log_path = tmp_path / "advisories.json"
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "3", "--min-samples", "1", "--advisory-log", str(log_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert not log_path.exists()  # no --advisory-consent given, so no advisories evaluated at all


def test_cli_organism_run_state_file_resumes_across_invocations(tmp_path):
    state_file = tmp_path / "state.json"

    first = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "3", "--min-samples", "1", "--state-file", str(state_file),
        ],
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0
    assert state_file.is_file()
    first_payload = json.loads(first.stdout)
    assert first_payload["checkpoint"]["saved_at_tick"] == 3

    second = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "2", "--min-samples", "1", "--state-file", str(state_file),
        ],
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0
    second_payload = json.loads(second.stdout)
    assert [t["tick"] for t in second_payload["ticks"]] == [4, 5]
    assert second_payload["checkpoint"]["saved_at_tick"] == 5


def test_cli_organism_run_stops_early_at_max_ticks():
    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "organism", "run",
            "--ticks", "5", "--max-ticks", "2", "--min-samples", "1",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["ticks"]) == 2
    assert payload["governor"]["ticks_remaining"] == 0
    assert "budget" in payload["governor"]["stopped_early"]


def test_cli_evaluate_advisories_label_and_summary(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"

    # Seed the advisory log directly for a deterministic CLI test, rather
    # than depending on a real regime shift actually occurring on this
    # machine's live CPU/disk readings.
    from symbiont.core.advisory import AdvisorySignal, DefensiveAdvisory, append_advisories_to_log

    append_advisories_to_log(
        (
            DefensiveAdvisory(
                tick=1,
                capability_id="compute.logical_cpu",
                signals=(AdvisorySignal(kind="persistent_deviation", detail="x"),),
                summary="compute.logical_cpu review",
            ),
        ),
        log_path,
    )

    label_result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "evaluate", "advisories", "label",
            "--advisory-log", str(log_path), "--labels-file", str(labels_path),
            "--tick", "1", "--capability-id", "compute.logical_cpu", "--judgment", "useful",
        ],
        capture_output=True,
        text=True,
    )
    assert label_result.returncode == 0

    summary_result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "evaluate", "advisories", "summary",
            "--advisory-log", str(log_path), "--labels-file", str(labels_path),
        ],
        capture_output=True,
        text=True,
    )
    assert summary_result.returncode == 0
    payload = json.loads(summary_result.stdout)
    assert payload["total_fired"] == 1
    assert payload["usefulness_rate"] == 1.0


def test_cli_evaluate_advisories_label_rejects_unfired_advisory(tmp_path):
    log_path = tmp_path / "advisories.json"
    labels_path = tmp_path / "labels.json"

    result = subprocess.run(
        [
            sys.executable, "-m", "symbiont_lab.cli.main", "evaluate", "advisories", "label",
            "--advisory-log", str(log_path), "--labels-file", str(labels_path),
            "--tick", "1", "--capability-id", "cpu", "--judgment", "useful",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "no fired advisory found" in result.stderr


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
