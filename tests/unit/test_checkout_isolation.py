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
