#!/usr/bin/env python3
"""Repository governance enforcement for human and intelligent-agent workflows."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "docs" / "governance"
LEVEL = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
CONTROL_PLANE = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/governance/**",
    "scripts/agentctl.py",
    "tests/governance/**",
    ".github/workflows/**",
    ".github/CODEOWNERS",
    ".pre-commit-config.yaml",
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
RUNTIME_DIR = ROOT / ".git" / "symbiont-agent"
RUN_LOCK = RUNTIME_DIR / "scientific-run.json"


def load(name: str) -> dict[str, Any]:
    with (GOV / name).open("rb") as handle:
        return tomllib.load(handle)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def git_show(ref: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if result.returncode == 0 else None


def load_at(ref: str, name: str) -> dict[str, Any]:
    raw = git_show(ref, f"docs/governance/{name}")
    if raw is None:
        return {}
    return tomllib.loads(raw)


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern)


def parent_of(ref: str) -> str | None:
    value = git("rev-parse", f"{ref}^", check=False)
    return value or None


def file_exists_at(ref: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


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


def _canonical_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    i = text.find(start)
    j = text.find(end)
    if i < 0 or j < 0:
        return ""
    return text[i : j + len(end)]


def required_authority(path: str, base_ref: str = "HEAD") -> str:
    required = "L1"

    if path.startswith(("src/", "observatory/")):
        required = "L2"
    if path.startswith("experiments/") and path.endswith("/experiment.toml"):
        required = "L3"
        sibling = path.rsplit("/", 1)[0] + "/results.json"
        if file_exists_at(base_ref, sibling):
            required = "L4"

    frozen = load_at(base_ref, "frozen-artifacts.toml")
    for artifact in frozen.get("artifact", []):
        if matches(path, artifact["path_glob"]):
            candidate = artifact.get("minimum_authority", "L4")
            if LEVEL[candidate] > LEVEL[required]:
                required = candidate

    for pattern in CONTROL_PLANE:
        if matches(path, pattern) and LEVEL["L4"] > LEVEL[required]:
            required = "L4"

    return required


def _grant_from_base(base_ref: str, grant_id: str) -> dict[str, Any] | None:
    grants = load_at(base_ref, "authority-grants.toml").get("grant", [])
    for grant in grants:
        if grant.get("id") != grant_id or grant.get("status") != "open":
            continue
        issuer_parent = parent_of(base_ref)
        if not issuer_parent:
            continue
        if grant.get("single_use", True) and grant.get("base_commit") != issuer_parent:
            continue
        if grant.get("authority") not in LEVEL:
            continue
        return grant
    return None


def _grant_allows(grant: dict[str, Any], path: str, required: str) -> bool:
    if LEVEL[grant["authority"]] < LEVEL[required]:
        return False
    allowed = grant.get("allowed_paths", [])
    return any(matches(path, pattern) for pattern in allowed)


def _active_work_at(base_ref: str) -> list[dict[str, Any]]:
    return load_at(base_ref, "active-work.toml").get("work", [])


def _path_blocked_by_active(path: str, base_ref: str, grant: dict[str, Any] | None) -> str | None:
    allowed_active = set((grant or {}).get("allowed_active_work", []))
    for work in _active_work_at(base_ref):
        if work.get("state") != "RUNNING":
            continue
        if work.get("id") in allowed_active:
            continue
        if any(matches(path, pattern) for pattern in work.get("protected_paths", [])):
            return work["id"]
    return None


def _load_manifest(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(path)
    with manifest_path.open("rb") as handle:
        return tomllib.load(handle)


def check(base_ref: str, staged_only: bool, manifest_path: str | None) -> int:
    paths = changed_paths(staged_only=staged_only)
    manifest = _load_manifest(manifest_path)
    grant_id = manifest.get("grant_id")
    grant = _grant_from_base(base_ref, grant_id) if grant_id else None
    manifest_paths = manifest.get("allowed_paths", [])
    errors: list[str] = []

    for path in paths:
        required = required_authority(path, base_ref)
        blocked = _path_blocked_by_active(path, base_ref, grant)
        if blocked:
            errors.append(f"{path}: protected by active scientific run {blocked}")

        if manifest_paths and not any(matches(path, pattern) for pattern in manifest_paths):
            errors.append(f"{path}: outside session manifest allowed_paths")

        if LEVEL[required] > LEVEL["L1"]:
            if not grant_id:
                errors.append(f"{path}: requires {required} owner grant")
            elif grant is None:
                errors.append(f"{path}: grant {grant_id!r} is absent, stale, consumed or invalid")
            elif not _grant_allows(grant, path, required):
                errors.append(f"{path}: grant {grant_id!r} does not authorize {required}")

    if errors:
        for error in sorted(set(errors)):
            print(f"BLOCK: {error}", file=sys.stderr)
        return 1

    label = grant_id or "default-L1"
    print(f"agent check: PASS ({label}, {len(paths)} changed paths)")
    return 0


def _verify_contract() -> list[str]:
    errors: list[str] = []
    agents = _canonical_block(ROOT / "AGENTS.md")
    claude = _canonical_block(ROOT / "CLAUDE.md")
    if not agents:
        errors.append("canonical agent contract markers are missing")
    elif agents != claude:
        errors.append("AGENTS.md and CLAUDE.md canonical agent contracts differ")

    constitution = (GOV / "constitution.md").read_text(encoding="utf-8")
    if "## Architectural invariants" not in constitution:
        errors.append("Constitution is missing canonical architectural invariants")
    for name in ("AGENTS.md", "CLAUDE.md"):
        if "## Normative architectural invariants" in (ROOT / name).read_text(encoding="utf-8"):
            errors.append(f"{name} duplicates architectural invariants outside the Constitution")
    return errors


def _verify_toml() -> list[str]:
    errors: list[str] = []
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
        "authority-grants.toml",
        "resource-policy.toml",
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
        value = item.get("state")
        if value not in ALLOWED_PROGRAMME_STATES:
            errors.append(f"programme {name}: unknown state {value!r}")

    running = [w for w in load("active-work.toml").get("work", []) if w.get("state") == "RUNNING"]
    max_runs = int(load("resource-policy.toml").get("scientific_runs", {}).get("max_concurrent", 1))
    if len(running) > max_runs:
        errors.append(f"{len(running)} tracked RUNNING campaigns exceed max_concurrent={max_runs}")
    for work in running:
        if work.get("id") not in programmes:
            errors.append(f"active work {work.get('id')!r} has no programme-state entry")

    grants = load("authority-grants.toml").get("grant", [])
    ids: set[str] = set()
    for grant in grants:
        gid = grant.get("id")
        if not gid or gid in ids:
            errors.append(f"duplicate or empty authority grant id: {gid!r}")
        ids.add(gid)
        if grant.get("authority") not in LEVEL:
            errors.append(f"grant {gid}: invalid authority")
        if grant.get("status") not in {"open", "consumed", "revoked"}:
            errors.append(f"grant {gid}: invalid status")
        base = grant.get("base_commit", "")
        if len(base) != 40 or any(ch not in "0123456789abcdef" for ch in base.lower()):
            errors.append(f"grant {gid}: base_commit is not a full SHA")

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


def _grant_trailer(message: str) -> str | None:
    for line in reversed(message.splitlines()):
        if line.lower().startswith("authority-grant:"):
            return line.split(":", 1)[1].strip()
    return None


def _audit_commit(commit: str) -> list[str]:
    errors: list[str] = []
    parent = parent_of(commit)
    if not parent:
        return errors
    paths = changed_paths_between(parent, commit)
    required = "L1"
    for path in paths:
        level = required_authority(path, parent)
        if LEVEL[level] > LEVEL[required]:
            required = level

    if LEVEL[required] <= LEVEL["L1"]:
        return errors

    message = git("show", "-s", "--format=%B", commit)
    grant_id = _grant_trailer(message)
    if not grant_id:
        return [f"{commit[:12]}: requires {required} but has no Authority-Grant trailer"]
    grant = _grant_from_base(parent, grant_id)
    if grant is None:
        return [f"{commit[:12]}: grant {grant_id!r} is invalid for parent {parent[:12]}"]

    for path in paths:
        level = required_authority(path, parent)
        if LEVEL[level] > LEVEL["L1"] and not _grant_allows(grant, path, level):
            errors.append(f"{commit[:12]}: {path} requires {level} outside grant {grant_id}")
        blocked = _path_blocked_by_active(path, parent, grant)
        if blocked:
            errors.append(f"{commit[:12]}: {path} modifies active run {blocked}")
    return errors


def ci_check(base: str, head: str) -> int:
    zero = set(base) == {"0"} if base else True
    if zero or not git("cat-file", "-e", f"{base}^{{commit}}", check=False):
        base = parent_of(head) or head
    commits_raw = git("rev-list", "--reverse", f"{base}..{head}")
    commits = [c for c in commits_raw.splitlines() if c]
    errors: list[str] = []
    for commit in commits:
        errors.extend(_audit_commit(commit))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"commit authority audit: PASS ({len(commits)} commits)")
    return 0


def status() -> int:
    state = load("project-state.toml")
    print(f"current gate: {state['current_gate']}")
    for name, item in state.get("programmes", {}).items():
        print(f"  {name}: {item.get('state', 'unknown')}")
    for work in load("active-work.toml").get("work", []):
        print(f"  work {work['id']}: {work['state']} ({work.get('owner', 'unowned')})")
    if RUN_LOCK.exists():
        print(f"  local scientific lock: {RUN_LOCK.read_text(encoding='utf-8')}")
    return 0


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True


def _tracked_running_other_than(run_id: str) -> list[str]:
    return [
        w["id"]
        for w in load("active-work.toml").get("work", [])
        if w.get("state") == "RUNNING" and w.get("id") != run_id
    ]


def acquire_run(run_id: str, command: list[str], wall_minutes: int, memory_gb: float, cpu: int) -> int:
    policy = load("resource-policy.toml").get("scientific_runs", {})
    if wall_minutes > int(policy.get("max_wall_minutes", 360)):
        print("requested wall time exceeds policy", file=sys.stderr)
        return 1
    if memory_gb > float(policy.get("max_memory_gb", 12)):
        print("requested memory exceeds policy", file=sys.stderr)
        return 1
    if cpu > int(policy.get("max_cpu_threads", 4)):
        print("requested CPU threads exceed policy", file=sys.stderr)
        return 1

    others = _tracked_running_other_than(run_id)
    if others:
        print(f"tracked scientific run already active: {', '.join(others)}", file=sys.stderr)
        return 1

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if RUN_LOCK.exists():
        try:
            existing = json.loads(RUN_LOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("scientific run lock is corrupt; owner inspection required", file=sys.stderr)
            return 1
        if _pid_alive(int(existing.get("pid", -1))):
            print(f"scientific run lock held by {existing.get('id')}", file=sys.stderr)
            return 1
        print("stale scientific run lock exists; run 'agentctl run clear-stale'", file=sys.stderr)
        return 1

    payload = {
        "id": run_id,
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "wall_minutes": wall_minutes,
        "memory_gb": memory_gb,
        "cpu_threads": cpu,
        "head": git("rev-parse", "HEAD"),
    }
    fd = os.open(RUN_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return 0


def release_run() -> None:
    RUN_LOCK.unlink(missing_ok=True)


def run_exec(run_id: str, command: list[str], wall_minutes: int, memory_gb: float, cpu: int) -> int:
    if not command:
        print("missing command after --", file=sys.stderr)
        return 2
    rc = acquire_run(run_id, command, wall_minutes, memory_gb, cpu)
    if rc:
        return rc
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env[key] = str(cpu)
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, timeout=wall_minutes * 60)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("scientific run exceeded wall-time budget and was terminated", file=sys.stderr)
        return 124
    finally:
        release_run()


def run_status() -> int:
    if not RUN_LOCK.exists():
        print("no local scientific run lock")
        return 0
    print(RUN_LOCK.read_text(encoding="utf-8"))
    return 0


def clear_stale() -> int:
    if not RUN_LOCK.exists():
        return 0
    try:
        payload = json.loads(RUN_LOCK.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("corrupt lock requires manual owner inspection", file=sys.stderr)
        return 1
    if _pid_alive(int(payload.get("pid", -1))):
        print("lock owner is still alive", file=sys.stderr)
        return 1
    release_run()
    print("stale scientific run lock cleared")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("verify")

    p_check = sub.add_parser("check")
    p_check.add_argument("--base", default="HEAD")
    p_check.add_argument("--staged", action="store_true")
    p_check.add_argument("--manifest", default=".agent-session.toml")

    p_ci = sub.add_parser("ci-check")
    p_ci.add_argument("--base", required=True)
    p_ci.add_argument("--head", required=True)

    p_run = sub.add_parser("run")
    run_sub = p_run.add_subparsers(dest="run_command", required=True)
    p_exec = run_sub.add_parser("exec")
    p_exec.add_argument("--id", required=True)
    p_exec.add_argument("--wall-minutes", type=int, default=180)
    p_exec.add_argument("--memory-gb", type=float, default=8.0)
    p_exec.add_argument("--cpu", type=int, default=2)
    p_exec.add_argument("argv", nargs=argparse.REMAINDER)
    run_sub.add_parser("status")
    run_sub.add_parser("clear-stale")

    args = parser.parse_args()
    if args.command == "status":
        return status()
    if args.command == "verify":
        return verify()
    if args.command == "check":
        manifest = args.manifest if Path(args.manifest).exists() else None
        return check(args.base, args.staged, manifest)
    if args.command == "ci-check":
        return ci_check(args.base, args.head)
    if args.run_command == "status":
        return run_status()
    if args.run_command == "clear-stale":
        return clear_stale()
    argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
    return run_exec(args.id, argv, args.wall_minutes, args.memory_gb, args.cpu)


if __name__ == "__main__":
    raise SystemExit(main())
