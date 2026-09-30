from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
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
