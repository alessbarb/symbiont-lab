"""One-command publication workflow for ordinary agent work."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from governance.classify import ChangeClass, assess  # noqa: E402
from symbiont_lab.experiments.execution_workspace import pinned_worktree  # noqa: E402
from symbiont_lab.physics3d.equivalence_suite import compare, load_suite  # noqa: E402


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _changed_against(base: str) -> tuple[list[str], str]:
    paths = set(filter(None, _git("diff", "--name-only", base).splitlines()))
    paths.update(filter(None, _git("ls-files", "--others", "--exclude-standard").splitlines()))
    diff = _git("diff", "--no-ext-diff", base, check=False)
    return sorted(paths), diff


def _run_scenario(code_root: Path, suite: Path, scenario: str, output: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(code_root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.physics3d.equivalence_suite",
            str(suite),
            scenario,
            str(output),
        ],
        cwd=code_root,
        env=env,
        check=False,
    )
    if not output.exists():
        return {"status": "ERROR", "reason": f"runner exit {result.returncode} without output"}
    return json.loads(output.read_text(encoding="utf-8"))


def run_equivalence(base: str, scenarios: tuple[str, ...]) -> tuple[bool, dict]:
    if not scenarios:
        return True, {}
    suite = ROOT / "experiments/equivalence/suite-v1/suite.toml"
    if not suite.is_file():
        return False, {"reason": "equivalence suite is not installed"}

    _, definitions = load_suite(suite)
    by_id = {item.scenario_id: item for item in definitions}
    evidence: dict[str, dict] = {}
    with pinned_worktree(ROOT, base) as baseline_tree:
        for scenario_id in scenarios:
            definition = by_id.get(scenario_id)
            if definition is None:
                evidence[scenario_id] = {"status": "ERROR", "reason": "unknown scenario"}
                return False, evidence
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                baseline = _run_scenario(
                    baseline_tree, suite, scenario_id, td_path / "baseline.json"
                )
                candidate = _run_scenario(
                    ROOT, suite, scenario_id, td_path / "candidate.json"
                )
                result = compare(definition, baseline, candidate)
                evidence[scenario_id] = result
                if result.get("status") != "PASS":
                    return False, evidence
    return True, evidence


def _classify(base: str):
    paths, diff = _changed_against(base)
    return paths, assess(ROOT, base, paths, diff)


def _validate_and_commit(message: str, classification: str, owner_approved: bool, evidence: dict) -> str:
    _git("add", "-A")
    subprocess.run(
        [sys.executable, "scripts/agentctl.py", "validate", "--staged"],
        cwd=ROOT,
        check=True,
    )
    trailers = [
        f"Governance-Class: {classification}",
        f"Owner-Approval: {'explicit' if owner_approved else 'not-required'}",
    ]
    if evidence:
        digest = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        trailers.append(f"Equivalence-Evidence: {digest}")
    _git("commit", "-m", message.rstrip() + "\n\n" + "\n".join(trailers))
    return _git("rev-parse", "HEAD")


def publish(*, message: str, owner_approved: bool = False, retries: int = 3) -> int:
    """Fetch/rebase, classify the final diff, validate, commit and push to main."""
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        print("BLOCKED — publish requires a branch checkout", file=sys.stderr)
        return 2

    _git("fetch", "origin", "main")
    remote = _git("rev-parse", "origin/main")
    if _git("rev-parse", "HEAD") != remote:
        result = subprocess.run(
            ["git", "rebase", "--autostash", "origin/main"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            print("BLOCKED — concurrent semantic conflict during rebase", file=sys.stderr)
            return 2
        remote = _git("rev-parse", "origin/main")

    paths, assessment = _classify(remote)
    if not paths:
        print("nothing to publish")
        return 0

    print(f"classification: {assessment.classification}")
    for reason in assessment.reasons:
        print(f"  - {reason}")

    if assessment.classification == ChangeClass.FROZEN:
        print("BLOCKED — frozen scientific evidence must be versioned", file=sys.stderr)
        return 3
    if assessment.classification == ChangeClass.CONSTITUTIONAL and not owner_approved:
        print("BLOCKED — constitutional approval required", file=sys.stderr)
        return 3

    eq_pass, evidence = run_equivalence(remote, assessment.equivalence_scenarios)
    effective = assessment.classification
    if effective == ChangeClass.SCIENTIFIC and assessment.equivalence_scenarios and eq_pass:
        effective = ChangeClass.ORDINARY
        print("equivalence: PASS — causally transparent within declared scenario coverage")
    elif effective == ChangeClass.SCIENTIFIC and not owner_approved:
        print("BLOCKED — scientific decision required", file=sys.stderr)
        if evidence:
            print(json.dumps(evidence, indent=2))
        return 3

    local_commit = _validate_and_commit(message, str(effective), owner_approved, evidence)

    for attempt in range(1, retries + 1):
        _git("fetch", "origin", "main")
        latest = _git("rev-parse", "origin/main")
        if latest != remote:
            result = subprocess.run(["git", "rebase", "origin/main"], cwd=ROOT, check=False)
            if result.returncode:
                print("BLOCKED — main changed and rebase conflicts", file=sys.stderr)
                return 2
            remote = latest

            _, reassessed = _classify(remote)
            if reassessed.classification == ChangeClass.FROZEN:
                print("BLOCKED — rebase now touches frozen evidence", file=sys.stderr)
                return 3
            if reassessed.classification == ChangeClass.CONSTITUTIONAL and not owner_approved:
                print("BLOCKED — rebase now requires constitutional approval", file=sys.stderr)
                return 3
            eq_pass, new_evidence = run_equivalence(remote, reassessed.equivalence_scenarios)
            if reassessed.classification == ChangeClass.SCIENTIFIC and not (
                eq_pass and reassessed.equivalence_scenarios
            ) and not owner_approved:
                print("BLOCKED — rebase invalidated ordinary/equivalence classification", file=sys.stderr)
                return 3
            subprocess.run(
                [sys.executable, "scripts/agentctl.py", "verify"],
                cwd=ROOT,
                check=True,
            )

        before_push = _git("rev-parse", "origin/main")
        result = subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode == 0:
            print(f"published: {_git('rev-parse', 'HEAD')}")
            return 0
        _git("fetch", "origin", "main")
        if _git("rev-parse", "origin/main") == before_push:
            print(f"push failed for non-concurrency reason; local commit {local_commit}", file=sys.stderr)
            return result.returncode
        if attempt == retries:
            break

    print("BLOCKED — main kept changing; rerun agentctl publish", file=sys.stderr)
    return 4
