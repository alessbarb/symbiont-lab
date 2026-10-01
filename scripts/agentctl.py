#!/usr/bin/env python3
"""Repository governance enforcement for human and intelligent-agent workflows."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (_BOOTSTRAP_ROOT / "scripts", _BOOTSTRAP_ROOT / "src"):
    bootstrap = str(_bootstrap_path)
    if bootstrap not in sys.path:
        sys.path.insert(0, bootstrap)

from governance.classify import ChangeClass
from governance.classify import assess as assess_change
from governance.publish import publish as publish_changes

from symbiont_lab.experiments.execution_workspace import pinned_worktree
from symbiont_lab.experiments.resource_guard import ResourceRequest, assess_resources
from symbiont_lab.experiments.snapshot_archive import (
    archive_snapshot,
    inspect_snapshot_source,
    verify_snapshot,
)
from symbiont_lab.physics3d.equivalence_suite import (
    load_suite as load_equivalence_suite,
)
from symbiont_lab.physics3d.equivalence_suite import (
    run_once as run_equivalence_once,
)
from symbiont_lab.physics3d.equivalence_suite import (
    suite_status as equivalence_suite_status,
)

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "docs" / "governance"
CONTROL_PLANE = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/governance/**",
    "scripts/agentctl.py",
    "tests/governance/**",
    ".github/workflows/**",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".pre-commit-config.yaml",
    ".gitignore",
    ".agents/**",
    ".claude/**",
    ".codex/**",
    "pyproject.toml",
    "pyrightconfig.json",
)

ALLOWED_PROGRAMME_STATES = {
    "running",
    "active",
    "next",
    "frozen",
    "paused",
    "unscheduled",
    "p0-open",
    "maintenance-only",
    "closed-bounded",
    "blocked",
    "design-data-complete",
    "blocked-by-P0",
    "blocked-by-P1",
    "blocked-by-P2",
}
SCIENTIFIC_SCOPES = {"development", "held-out", "confirmation", "replication", "mechanical"}


def load(name: str) -> dict[str, Any]:
    with (GOV / name).open("rb") as handle:
        return tomllib.load(handle)


def git_result(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git(*args: str, check: bool = True) -> str:
    result = git_result(*args)
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def commit_exists(ref: str) -> bool:
    return git_result("cat-file", "-e", f"{ref}^{{commit}}").returncode == 0


def git_show(ref: str, path: str) -> str | None:
    result = git_result("show", f"{ref}:{path}")
    return result.stdout if result.returncode == 0 else None


def load_at(ref: str, name: str) -> dict[str, Any]:
    raw = git_show(ref, f"docs/governance/{name}")
    return tomllib.loads(raw) if raw is not None else {}


def _trusted_origin_ref() -> str:
    fetch = git_result("fetch", "origin", "main")
    if fetch.returncode != 0:
        raise RuntimeError(
            "cannot refresh trusted origin/main governance state: "
            + (fetch.stderr.strip() or "git fetch failed")
        )
    ref = git("rev-parse", "origin/main")
    if not commit_exists(ref):
        raise RuntimeError("trusted origin/main did not resolve to a commit")
    return ref


def _trusted_governance_at(ref: str, name: str) -> dict[str, Any]:
    raw = git_show(ref, f"docs/governance/{name}")
    if raw is None:
        raise RuntimeError(f"trusted governance ref {ref[:12]} is missing docs/governance/{name}")
    return tomllib.loads(raw)


def _trusted_origin_governance(name: str) -> dict[str, Any]:
    """Compatibility helper for callers that need one document only."""
    ref = _trusted_origin_ref()
    return _trusted_governance_at(ref, name)


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern)


def parent_of(ref: str) -> str | None:
    result = git_result("rev-parse", f"{ref}^")
    return result.stdout.strip() if result.returncode == 0 else None


def git_common_dir() -> Path:
    raw = git("rev-parse", "--git-common-dir")
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / path).resolve()


def runtime_dir() -> Path:
    return git_common_dir() / "symbiont-agent"


def changed_paths(staged_only: bool = False) -> list[str]:
    paths: set[str] = set()
    staged = git("diff", "--cached", "--name-only", "--diff-filter=ACMRD")
    paths.update(line for line in staged.splitlines() if line)
    if not staged_only:
        unstaged = git("diff", "--name-only", "--diff-filter=ACMRD")
        paths.update(line for line in unstaged.splitlines() if line)
        untracked = git("ls-files", "--others", "--exclude-standard")
        paths.update(line for line in untracked.splitlines() if line)
    return sorted(paths)


def changed_paths_between(base: str, head: str) -> list[str]:
    raw = git("diff", "--name-only", "--diff-filter=ACMRD", base, head)
    return [line for line in raw.splitlines() if line]


def _active_work_at(base_ref: str) -> list[dict[str, Any]]:
    return load_at(base_ref, "active-work.toml").get("work", [])


def _path_blocked_by_active(path: str, base_ref: str) -> str | None:
    for work in _active_work_at(base_ref):
        if work.get("state") != "RUNNING":
            continue
        if any(matches(path, pattern) for pattern in work.get("protected_paths", [])):
            return str(work["id"])
    return None


def _validation_sections(paths: list[str]) -> list[tuple[str, dict[str, Any]]]:
    matrix = load("validation-matrix.toml")
    selected: list[tuple[str, dict[str, Any]]] = []
    for name, section in matrix.items():
        if name == "schema_version" or not isinstance(section, dict):
            continue
        patterns = section.get("paths", [])
        if any(any(matches(path, pattern) for pattern in patterns) for path in paths):
            selected.append((name, section))
    return selected


def validate(staged_only: bool = True) -> int:
    """Optional local reproduction of validation commands; never a publication gate."""
    paths = changed_paths(staged_only=staged_only)
    if not paths:
        print("validation: no changed paths")
        return 0
    sections = _validation_sections(paths)
    if not sections:
        print("validation: no matrix section covers changed paths", file=sys.stderr)
        return 1

    commands: list[str] = []
    for _, section in sections:
        for command in section.get("commands", []):
            if command not in commands:
                commands.append(command)

    if not commands:
        print("validation: no local commands; CI owns technical validation")
        return 0

    for command in commands:
        print(f"VALIDATE: {command}")
        result = subprocess.run(command, cwd=ROOT, shell=True)
        if result.returncode != 0:
            print(f"validation failed: {command}", file=sys.stderr)
            return result.returncode
    print("validation: PASS (manual local reproduction)")
    return 0


def _canonical_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    i = text.find(start)
    j = text.find(end)
    return "" if i < 0 or j < 0 else text[i : j + len(end)]


def _verify_contract() -> list[str]:
    errors: list[str] = []
    agents = _canonical_block(ROOT / "AGENTS.md")
    claude = _canonical_block(ROOT / "CLAUDE.md")
    if not agents:
        errors.append("canonical agent contract markers are missing")
    elif agents != claude:
        errors.append("AGENTS.md and CLAUDE.md canonical agent contracts differ")
    if "## Architectural invariants" not in (GOV / "constitution.md").read_text(encoding="utf-8"):
        errors.append("Constitution is missing canonical architectural invariants")
    return errors


def _verify_toml() -> list[str]:
    errors: list[str] = []
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
        "resource-policy.toml",
        "owner-root.toml",
        "bootstrap-exceptions.toml",
        "change-surfaces.toml",
        "publication-policy.toml",
    ):
        try:
            load(name)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{name}: {exc}")
    return errors


def _verify_semantics() -> list[str]:
    errors: list[str] = []
    state = load("project-state.toml")
    programmes = state.get("programmes", {})
    gate = state.get("current_gate")
    if gate not in programmes:
        errors.append(f"current_gate {gate!r} is not a declared programme")
    for name, item in programmes.items():
        if item.get("state") not in ALLOWED_PROGRAMME_STATES:
            errors.append(f"programme {name}: unknown state {item.get('state')!r}")

    running = [w for w in load("active-work.toml").get("work", []) if w.get("state") == "RUNNING"]
    max_runs = int(load("resource-policy.toml").get("scientific_runs", {}).get("max_concurrent", 1))
    if len(running) > max_runs:
        errors.append(f"{len(running)} tracked RUNNING campaigns exceed max_concurrent={max_runs}")
    for work in running:
        if work.get("id") not in programmes:
            errors.append(f"active work {work.get('id')!r} has no programme-state entry")

    for entry in load("bootstrap-exceptions.toml").get("commit", []):
        sha = str(entry.get("sha", ""))
        if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
            errors.append("bootstrap exception has invalid commit SHA")
        if entry.get("status") != "accepted" or not entry.get("reason"):
            errors.append(f"bootstrap exception {sha[:12]} lacks accepted status/reason")

    frozen_patterns = {a["path_glob"] for a in load("frozen-artifacts.toml").get("artifact", [])}
    for pattern in CONTROL_PLANE:
        if pattern not in frozen_patterns:
            errors.append(f"control-plane path is not frozen: {pattern}")
    return errors


def verify() -> int:
    errors = _verify_contract() + _verify_toml() + _verify_semantics()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("governance verification: PASS")
    return 0


def _trailer(message: str, name: str) -> str | None:
    prefix = name.lower() + ":"
    for line in reversed(message.splitlines()):
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _governance_adr_valid(ref: str, path: str) -> bool:
    candidate = PurePosixPath(path)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or len(candidate.parts) < 3
        or candidate.parts[0:2] != ("docs", "adr")
        or not candidate.name.startswith("ADR-")
        or candidate.suffix.lower() != ".md"
    ):
        return False
    raw = git_show(ref, candidate.as_posix())
    if raw is None:
        return False
    return bool(
        re.search(
            r"(?im)^-\s*\*\*Status:\*\*\s*Accepted\s*$|^Status:\s*Accepted\s*$",
            raw,
        )
    )


def _equivalence_evidence_errors(
    parent: str,
    commit: str,
    assessment: Any,
    raw: str | None,
) -> list[str]:
    required = tuple(str(item) for item in assessment.equivalence_scenarios)
    if not required:
        return ["scientific-sensitive diff has no covering equivalence scenario"]
    if not raw:
        return ["scientific-sensitive diff downgraded without equivalence evidence"]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ["equivalence evidence trailer is not valid JSON"]
    if not isinstance(payload, dict):
        return ["equivalence evidence trailer must be a JSON object"]

    meta = payload.get("_meta")
    if not isinstance(meta, dict) or meta.get("baseline_commit") != parent:
        return ["equivalence evidence baseline does not match commit parent"]
    candidate_tree = git("show", "-s", "--format=%T", commit)
    if meta.get("candidate_tree") != candidate_tree:
        return ["equivalence evidence candidate tree does not match commit tree"]

    errors: list[str] = []
    for scenario in required:
        evidence = payload.get(scenario)
        if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
            errors.append(f"equivalence scenario {scenario!r} is missing or not PASS")
    return errors


def _bootstrap_exception(commit: str) -> dict[str, Any] | None:
    try:
        entries = load("bootstrap-exceptions.toml").get("commit", [])
    except (OSError, tomllib.TOMLDecodeError):
        return None
    for entry in entries:
        if entry.get("sha") == commit and entry.get("status") == "accepted":
            return entry
    return None


def _audit_commit(commit: str) -> list[str]:
    parent = parent_of(commit)
    if not parent:
        return []
    if _bootstrap_exception(commit):
        return []

    paths = changed_paths_between(parent, commit)
    message = git("show", "-s", "--format=%B", commit)
    governance_class = _trailer(message, "Governance-Class")
    if governance_class not in {"ORDINARY", "SCIENTIFIC", "CONSTITUTIONAL"}:
        return [f"{commit[:12]}: missing or invalid Governance-Class trailer"]

    active_errors: list[str] = []
    for path in paths:
        blocked = _path_blocked_by_active(path, parent)
        if blocked:
            active_errors.append(f"{commit[:12]}: {path} modifies active run {blocked}")
    if active_errors:
        return active_errors

    diff_text = git("diff", parent, commit)
    assessment = assess_change(ROOT, parent, paths, diff_text)
    expected = str(assessment.classification)
    if expected == ChangeClass.FROZEN:
        return [f"{commit[:12]}: modifies frozen evidence; create a new version instead"]
    if expected == ChangeClass.CONSTITUTIONAL and governance_class != "CONSTITUTIONAL":
        return [f"{commit[:12]}: constitutional diff mislabeled as {governance_class}"]
    if expected == ChangeClass.SCIENTIFIC and governance_class == "ORDINARY":
        evidence_errors = _equivalence_evidence_errors(
            parent, commit, assessment, _trailer(message, "Equivalence-Evidence")
        )
        if evidence_errors:
            return [f"{commit[:12]}: {error}" for error in evidence_errors]
    if expected == ChangeClass.ORDINARY and governance_class != "ORDINARY":
        return [f"{commit[:12]}: ordinary diff mislabeled as {governance_class}"]
    if governance_class == "CONSTITUTIONAL":
        adr = _trailer(message, "Governance-ADR")
        if not adr:
            return [f"{commit[:12]}: constitutional change lacks Governance-ADR"]
        if not _governance_adr_valid(commit, adr):
            return [f"{commit[:12]}: Governance-ADR is missing, outside docs/adr, or not Accepted"]
    return []


def _publication_cutoff(ref: str = "HEAD") -> str | None:
    raw = git_show(ref, "docs/governance/publication-policy.toml")
    if raw is None:
        return None
    try:
        payload = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return None
    value = payload.get("legacy_cutoff_commit")
    return str(value) if value else None


def _is_legacy_commit(commit: str, cutoff: str | None) -> bool:
    if not cutoff or not commit_exists(cutoff):
        return False
    return git_result("merge-base", "--is-ancestor", commit, cutoff).returncode == 0


def _is_redundant_merge_commit(commit: str) -> bool:
    """Return whether a merge adds no tree content beyond one of its parents."""
    parents = git("show", "-s", "--format=%P", commit).split()
    if len(parents) < 2:
        return False
    tree = git("show", "-s", "--format=%T", commit)
    return any(git("show", "-s", "--format=%T", parent) == tree for parent in parents)


def ci_check(base: str, head: str) -> int:
    if not commit_exists(head):
        print(f"HEAD commit is unavailable: {head}", file=sys.stderr)
        return 2
    if not base or set(base) == {"0"}:
        parent = parent_of(head)
        if not parent:
            print("cannot determine audit base", file=sys.stderr)
            return 2
        base = parent
    if not commit_exists(base):
        print(f"audit base commit is unavailable: {base}", file=sys.stderr)
        return 2
    if git_result("merge-base", "--is-ancestor", base, head).returncode != 0:
        print(
            "audit base is not an ancestor of head; non-linear/force push rejected", file=sys.stderr
        )
        return 2

    commits = [c for c in git("rev-list", "--reverse", f"{base}..{head}").splitlines() if c]
    errors: list[str] = []
    cutoff = _publication_cutoff(head)
    audited = 0
    redundant_merges = 0
    for commit in commits:
        if _is_redundant_merge_commit(commit):
            redundant_merges += 1
            continue
        if _is_legacy_commit(commit, cutoff):
            continue
        audited += 1
        errors.extend(_audit_commit(commit))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    skipped = f"; {redundant_merges} redundant merge commits skipped" if redundant_merges else ""
    print(f"commit governance audit: PASS ({audited} commits audited{skipped})")
    return 0


def _run_lock_path() -> Path:
    return runtime_dir() / "scientific-run.json"


def _equivalence_lock_path() -> Path:
    return runtime_dir() / "equivalence-run.json"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True


def _tracked_running_at(ref: str) -> list[str]:
    data = _trusted_governance_at(ref, "active-work.toml")
    return [str(work["id"]) for work in data.get("work", []) if work.get("state") == "RUNNING"]


def _tracked_running() -> list[str]:
    """Compatibility helper: fetch origin/main once and evaluate that exact ref."""
    return _tracked_running_at(_trusted_origin_ref())


def _reserve_run_lock(payload: dict[str, Any]) -> int:
    directory = runtime_dir()
    directory.mkdir(parents=True, exist_ok=True)
    lock = _run_lock_path()
    if lock.exists():
        try:
            existing = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("scientific run lock is corrupt; owner inspection required", file=sys.stderr)
            return 1
        pid = int(existing.get("child_pid") or existing.get("owner_pid") or -1)
        if _pid_alive(pid):
            print(f"scientific run lock held by {existing.get('id')}", file=sys.stderr)
            return 1
        print("stale scientific run lock exists; run 'agentctl run clear-stale'", file=sys.stderr)
        return 1
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return 0


def _scientific_preexec(memory_gb: float, wall_minutes: int, cpu: int):
    if os.name != "posix":
        return None

    def apply_limits() -> None:
        import resource

        memory_bytes = int(memory_gb * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        cpu_seconds = max(1, wall_minutes * 60)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))
        if hasattr(os, "sched_setaffinity"):
            available = sorted(os.sched_getaffinity(0))
            os.sched_setaffinity(0, set(available[: max(1, min(cpu, len(available)))]))

    return apply_limits


def run_pinned(
    *,
    commit: str,
    run_id: str,
    scope: str,
    snapshot_source: Path,
    snapshot_source_commit: str | None,
    command: list[str],
    wall_minutes: int,
    memory_gb: float,
    cpu: int,
    disk_gb: float,
) -> int:
    """Run one pinned scientific command from an immutable archived starting state."""

    if scope not in SCIENTIFIC_SCOPES:
        print(f"invalid scientific scope: {scope}", file=sys.stderr)
        return 2
    if not commit_exists(commit):
        print(f"unknown commit: {commit}", file=sys.stderr)
        return 2
    commit = git("rev-parse", f"{commit}^{{commit}}")
    if _equivalence_lock_path().exists():
        print("BLOCKED — causal-equivalence run already active", file=sys.stderr)
        return 3
    try:
        governance_ref = _trusted_origin_ref()
        policy = _trusted_governance_at(governance_ref, "resource-policy.toml").get(
            "scientific_runs", {}
        )
        others = _tracked_running_at(governance_ref)
    except RuntimeError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 3
    if others:
        print(f"BLOCKED — long scientific run already active: {', '.join(others)}", file=sys.stderr)
        return 3

    if _run_lock_path().exists():
        print("BLOCKED — local scientific run lock already exists", file=sys.stderr)
        return 3

    if wall_minutes > int(policy.get("max_wall_minutes", 360)):
        print("BLOCKED — requested wall time exceeds trusted policy", file=sys.stderr)
        return 3
    if memory_gb > float(policy.get("max_memory_gb", 12)):
        print("BLOCKED — requested memory exceeds trusted policy", file=sys.stderr)
        return 3
    if cpu > int(policy.get("max_cpu_threads", 4)):
        print("BLOCKED — requested CPU threads exceed trusted policy", file=sys.stderr)
        return 3
    if policy.get("require_posix_hard_memory_limit", True) and os.name != "posix":
        print("BLOCKED — trusted policy requires POSIX hard memory limits", file=sys.stderr)
        return 3

    assessment = assess_resources(
        ResourceRequest(
            peak_memory_gb=memory_gb,
            disk_gb=disk_gb,
            cpu_threads=cpu,
            safety_memory_gb=1.0,
        ),
        disk_path=ROOT,
    )
    if not assessment.allowed:
        print("BLOCKED — resource preflight failed:", file=sys.stderr)
        for reason in assessment.reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 3

    existing_manifest: dict[str, Any] | None = None
    if (snapshot_source / "manifest.json").is_file():
        try:
            existing_manifest = verify_snapshot(snapshot_source)
        except ValueError as exc:
            print(f"BLOCKED — invalid archived snapshot: {exc}", file=sys.stderr)
            return 3

    input_source_commit = snapshot_source_commit
    if existing_manifest is not None:
        archived_commit = str(existing_manifest.get("source_commit") or "")
        if input_source_commit and input_source_commit != archived_commit:
            print(
                "BLOCKED — --snapshot-source-commit conflicts with archived snapshot provenance",
                file=sys.stderr,
            )
            return 3
        input_source_commit = archived_commit
    if input_source_commit is None:
        input_source_commit = commit
    if not commit_exists(input_source_commit):
        print(
            f"BLOCKED — snapshot source commit is unavailable: {input_source_commit}",
            file=sys.stderr,
        )
        return 3
    input_source_commit = git("rev-parse", f"{input_source_commit}^{{commit}}")

    run_root = runtime_dir() / "runs" / run_id
    if run_root.exists():
        print(f"run id already exists: {run_id}", file=sys.stderr)
        return 3
    run_root.mkdir(parents=True, exist_ok=False)
    input_dir = run_root / "input"
    try:
        manifest = archive_snapshot(
            source=snapshot_source,
            destination=input_dir,
            source_commit=input_source_commit,
            body_kind=(
                str(existing_manifest.get("body_kind"))
                if existing_manifest and existing_manifest.get("body_kind")
                else None
            ),
            scenario=scope,
        )
    except Exception:
        shutil.rmtree(run_root, ignore_errors=True)
        raise
    work_dir = run_root / "work"
    shutil.copytree(input_dir, work_dir, copy_function=shutil.copy2)
    for path in work_dir.rglob("*"):
        if path.is_file():
            try:
                path.chmod(0o644)
            except OSError:
                pass

    payload = {
        "id": run_id,
        "scope": scope,
        "commit": commit,
        "input_source_commit": input_source_commit,
        "governance_ref": governance_ref,
        "authorization_model": "external-operator-policy",
        "owner_pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "wall_minutes": wall_minutes,
        "memory_gb": memory_gb,
        "cpu_threads": cpu,
        "disk_gb": disk_gb,
        "input_manifest": manifest,
        "resource_preflight": {
            "available_memory_gb": assessment.available_memory_gb,
            "free_disk_gb": assessment.free_disk_gb,
            "available_cpu_threads": assessment.available_cpu_threads,
        },
        "state": "launching",
    }
    if _reserve_run_lock(payload):
        return 1

    argv = [
        str(input_dir) if token == "{input}" else str(work_dir) if token == "{work}" else token
        for token in command
    ]
    env = os.environ.copy()
    env["SYMBIONT_RUN_INPUT"] = str(input_dir)
    env["SYMBIONT_RUN_WORK"] = str(work_dir)
    env["SYMBIONT_RUN_ID"] = run_id
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env[key] = str(cpu)

    started = time.time()
    returncode = 1
    try:
        with pinned_worktree(ROOT, commit) as worktree:
            env["PYTHONPATH"] = str(worktree / "src")
            proc = subprocess.Popen(
                argv,
                cwd=worktree,
                env=env,
                start_new_session=True,
                preexec_fn=_scientific_preexec(memory_gb, wall_minutes, cpu),
            )
            payload["child_pid"] = proc.pid
            payload["worktree_commit"] = commit
            payload["command"] = argv
            payload["state"] = "running"
            _run_lock_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            try:
                returncode = proc.wait(timeout=wall_minutes * 60)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                else:
                    proc.terminate()
                    proc.wait(timeout=10)
                returncode = 124
    finally:
        receipt = {
            **payload,
            "state": "complete",
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.time() - started,
            "returncode": returncode,
        }
        (run_root / "execution.json").write_text(
            json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8"
        )
        _run_lock_path().unlink(missing_ok=True)
    return returncode


def run_status() -> int:
    lock = _run_lock_path()
    print(lock.read_text(encoding="utf-8") if lock.exists() else "no local scientific run lock")
    return 0


def clear_stale() -> int:
    lock = _run_lock_path()
    if not lock.exists():
        return 0
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("corrupt lock requires manual owner inspection", file=sys.stderr)
        return 1
    pid = int(payload.get("child_pid") or payload.get("owner_pid") or -1)
    if _pid_alive(pid):
        print("lock owner/child is still alive", file=sys.stderr)
        return 1
    lock.unlink()
    print("stale scientific run lock cleared")
    return 0


def equivalence_status_command(suite: Path) -> int:
    payload = equivalence_suite_status(suite)
    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload.get("ready") else 2


def equivalence_run_command(suite: Path, scenario_ids: list[str]) -> int:
    try:
        governance_ref = _trusted_origin_ref()
        running = _tracked_running_at(governance_ref)
        trusted_policy = _trusted_governance_at(governance_ref, "resource-policy.toml").get(
            "scientific_runs", {}
        )
    except RuntimeError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 3
    if running:
        print(
            "BLOCKED — long scientific work already RUNNING at "
            + governance_ref[:12]
            + ": "
            + ", ".join(running),
            file=sys.stderr,
        )
        return 3
    if _run_lock_path().exists() or _equivalence_lock_path().exists():
        print("BLOCKED — another heavy run is already active", file=sys.stderr)
        return 3

    _, scenarios = load_equivalence_suite(suite)
    by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    selected = list(by_id) if not scenario_ids else scenario_ids
    unknown = [scenario_id for scenario_id in selected if scenario_id not in by_id]
    if unknown:
        print("unknown equivalence scenario(s): " + ", ".join(unknown), file=sys.stderr)
        return 2

    readiness = equivalence_suite_status(suite)
    if not readiness.get("ready"):
        print(json.dumps(readiness, indent=2, default=str))
        return 2

    lock = _equivalence_lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print("BLOCKED — another equivalence run is already active", file=sys.stderr)
        return 3
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(
            {"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat()}, handle
        )
        handle.write("\n")

    exit_code = 0
    try:
        for scenario_id in selected:
            scenario = by_id[scenario_id]
            if scenario.memory_gb > float(trusted_policy.get("max_memory_gb", 12)):
                print(
                    json.dumps(
                        {
                            "scenario": scenario_id,
                            "status": "NOT_ASSESSABLE_RESOURCES",
                            "governance_ref": governance_ref,
                            "reasons": ["scenario memory exceeds trusted policy"],
                        },
                        indent=2,
                    )
                )
                exit_code = 2
                continue
            if scenario.cpu_threads > int(trusted_policy.get("max_cpu_threads", 4)):
                print(
                    json.dumps(
                        {
                            "scenario": scenario_id,
                            "status": "NOT_ASSESSABLE_RESOURCES",
                            "governance_ref": governance_ref,
                            "reasons": ["scenario CPU exceeds trusted policy"],
                        },
                        indent=2,
                    )
                )
                exit_code = 2
                continue
            resources = assess_resources(
                ResourceRequest(
                    peak_memory_gb=scenario.memory_gb,
                    disk_gb=scenario.disk_gb,
                    cpu_threads=scenario.cpu_threads,
                    safety_memory_gb=1.0,
                ),
                disk_path=ROOT,
            )
            if not resources.allowed:
                print(
                    json.dumps(
                        {
                            "scenario": scenario_id,
                            "status": "NOT_ASSESSABLE_RESOURCES",
                            "reasons": list(resources.reasons),
                        },
                        indent=2,
                    )
                )
                exit_code = 2
                continue
            result = run_equivalence_once(scenario)
            print(json.dumps({"scenario": scenario_id, **result}, indent=2, default=str))
            if result.get("status") != "PASS":
                exit_code = 2
    finally:
        lock.unlink(missing_ok=True)
    return exit_code


def context(*, as_json: bool = False) -> int:
    """Print the minimum trusted state needed to start one task."""
    try:
        base = _trusted_origin_ref()
        state = _trusted_governance_at(base, "project-state.toml")
        active = _trusted_governance_at(base, "active-work.toml").get("work", [])
    except RuntimeError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 3

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    head = git("rev-parse", "HEAD")
    paths = changed_paths(staged_only=False)
    running = [
        str(work["id"])
        for work in active
        if work.get("state") == "RUNNING"
    ]
    conflicts = sorted(
        {
            f"{work['id']}:{path}"
            for work in active
            if work.get("state") == "RUNNING"
            for path in paths
            if any(
                matches(path, pattern)
                for pattern in work.get("protected_paths", [])
            )
        }
    )
    payload = {
        "base": base,
        "branch": branch,
        "head": head,
        "worktree": "clean" if not paths else "dirty",
        "changed_paths": len(paths),
        "current_gate": state.get("current_gate"),
        "running_work": running,
        "protected_conflicts": conflicts,
        "publication": 'python scripts/agentctl.py publish --message "..."',
        "classification": "deferred-to-publish",
        "policy_read": (
            "context-once; read deeper governance only for scientific protocol, "
            "FROZEN, RUNNING or constitutional boundaries"
        ),
    }

    if as_json:
        print(json.dumps(payload, sort_keys=True))
        return 0

    running_text = ",".join(running) if running else "none"
    conflict_text = ",".join(conflicts) if conflicts else "none"
    print(f"base: {base[:12]}")
    print(f"branch: {branch}")
    print(f"head: {head[:12]}")
    print(f"worktree: {payload['worktree']} ({len(paths)} changed paths)")
    print(f"gate: {payload['current_gate']}")
    print(f"running: {running_text}")
    print(f"conflicts: {conflict_text}")
    print("classification: deferred-to-publish")
    print('next: work within task; publish once with agentctl publish --message "..."')
    print(
        "read-more: only if crossing scientific protocol, FROZEN, RUNNING "
        "or constitutional boundaries"
    )
    return 0


def status() -> int:
    state = load("project-state.toml")
    print(f"current gate: {state['current_gate']}")
    for name, item in state.get("programmes", {}).items():
        print(f"  {name}: {item.get('state', 'unknown')}")
    for work in load("active-work.toml").get("work", []):
        print(f"  work {work['id']}: {work['state']} ({work.get('owner', 'unowned')})")
    if _run_lock_path().exists():
        print(f"  local scientific lock: {_run_lock_path()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    p_context = sub.add_parser("context")
    p_context.add_argument("--json", action="store_true")
    sub.add_parser("verify")
    p_validate = sub.add_parser("validate", help=argparse.SUPPRESS)
    p_validate.add_argument("--staged", action="store_true", default=True)
    p_ci = sub.add_parser("ci-check")
    p_ci.add_argument("--base", required=True)
    p_ci.add_argument("--head", required=True)
    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--message", required=True)
    p_publish.add_argument(
        "--adr",
        help="Accepted ADR path/id for CONSTITUTIONAL publication; auto-detected when exactly one Accepted ADR is changed",
    )

    p_equivalence = sub.add_parser("equivalence")
    equivalence_sub = p_equivalence.add_subparsers(dest="equivalence_command", required=True)
    p_eq_status = equivalence_sub.add_parser("status")
    p_eq_status.add_argument(
        "--suite", type=Path, default=ROOT / "experiments/equivalence/suite-v1/suite.toml"
    )
    p_eq_run = equivalence_sub.add_parser("run")
    p_eq_run.add_argument(
        "--suite", type=Path, default=ROOT / "experiments/equivalence/suite-v1/suite.toml"
    )
    p_eq_run.add_argument("--scenario", action="append", default=[])

    p_snapshot = sub.add_parser("snapshot")
    snapshot_sub = p_snapshot.add_subparsers(dest="snapshot_command", required=True)
    p_inspect = snapshot_sub.add_parser("inspect")
    p_inspect.add_argument("--source", type=Path, required=True)
    p_capture = snapshot_sub.add_parser("capture")
    p_capture.add_argument("--source", type=Path, required=True)
    p_capture.add_argument("--destination", type=Path, required=True)
    p_capture.add_argument("--body-kind")
    p_capture.add_argument("--scenario")
    p_capture.add_argument("--source-commit")
    p_verify_snapshot = snapshot_sub.add_parser("verify")
    p_verify_snapshot.add_argument("--path", type=Path, required=True)

    p_run = sub.add_parser("run")
    run_sub = p_run.add_subparsers(dest="run_command", required=True)
    p_start = run_sub.add_parser("start")
    p_start.add_argument("--commit", required=True)
    p_start.add_argument("--id", required=True)
    p_start.add_argument("--scope", choices=sorted(SCIENTIFIC_SCOPES), required=True)
    p_start.add_argument("--snapshot-source", type=Path, required=True)
    p_start.add_argument(
        "--snapshot-source-commit",
        help="commit that produced the input state; archived snapshots preserve their own source_commit",
    )
    p_start.add_argument("--wall-minutes", type=int, default=180)
    p_start.add_argument("--memory-gb", type=float, default=8.0)
    p_start.add_argument("--disk-gb", type=float, default=2.0)
    p_start.add_argument("--cpu", type=int, default=2)
    p_start.add_argument("argv", nargs=argparse.REMAINDER)

    run_sub.add_parser("status")
    run_sub.add_parser("clear-stale")

    args = parser.parse_args()
    if args.command == "status":
        return status()
    if args.command == "context":
        return context(as_json=args.json)
    if args.command == "verify":
        return verify()
    if args.command == "publish":
        return publish_changes(
            message=args.message,
            adr_ref=args.adr,
        )
    if args.command == "equivalence":
        if args.equivalence_command == "status":
            return equivalence_status_command(args.suite)
        return equivalence_run_command(args.suite, args.scenario)
    if args.command == "snapshot":
        if args.snapshot_command == "inspect":
            payload = inspect_snapshot_source(args.source)
            print(json.dumps(payload, indent=2, sort_keys=True, default=str))
            return 0 if payload.get("capturable") else 2
        if args.snapshot_command == "verify":
            print(json.dumps(verify_snapshot(args.path), indent=2, sort_keys=True))
            return 0
        source_commit = args.source_commit or git("rev-parse", "HEAD")
        if not commit_exists(source_commit):
            print(f"unknown source commit: {source_commit}", file=sys.stderr)
            return 2
        source_commit = git("rev-parse", f"{source_commit}^{{commit}}")
        manifest = archive_snapshot(
            source=args.source,
            destination=args.destination,
            source_commit=source_commit,
            body_kind=args.body_kind,
            scenario=args.scenario,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    if args.command == "validate":
        return validate(staged_only=args.staged)
    if args.command == "ci-check":
        return ci_check(args.base, args.head)
    if args.run_command == "status":
        return run_status()
    if args.run_command == "start":
        argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
        if not argv:
            print("missing command after --", file=sys.stderr)
            return 2
        return run_pinned(
            commit=args.commit,
            run_id=args.id,
            scope=args.scope,
            snapshot_source=args.snapshot_source,
            snapshot_source_commit=args.snapshot_source_commit,
            command=argv,
            wall_minutes=args.wall_minutes,
            memory_gb=args.memory_gb,
            cpu=args.cpu,
            disk_gb=args.disk_gb,
        )
    if args.run_command == "clear-stale":
        return clear_stale()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
