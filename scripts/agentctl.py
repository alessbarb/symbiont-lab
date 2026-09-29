#!/usr/bin/env python3
"""Repository governance helper for human and intelligent-agent workflows."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "docs" / "governance"
LEVEL = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load(name: str) -> dict:
    with (GOV / name).open("rb") as handle:
        return tomllib.load(handle)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def current_paths(staged: bool) -> list[str]:
    args = ["diff", "--name-only"]
    if staged:
        args.append("--cached")
    output = git(*args)
    return [line for line in output.splitlines() if line]


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
        path, pattern.replace("**/", "*")
    )


def status() -> int:
    state = load("project-state.toml")
    active = load("active-work.toml")
    print(f"current gate: {state['current_gate']}")
    print("programmes:")
    for name, item in state.get("programmes", {}).items():
        print(f"  {name}: {item.get('state', 'unknown')}")
    print("active work:")
    for work in active.get("work", []):
        print(f"  {work['id']}: {work['state']} ({work.get('owner', 'unowned')})")
    return 0


def _canonical_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    i = text.find(start)
    j = text.find(end)
    if i < 0 or j < 0:
        return ""
    return text[i : j + len(end)]


def verify_contract_sync() -> list[str]:
    errors: list[str] = []
    if _canonical_block(ROOT / "AGENTS.md") != _canonical_block(ROOT / "CLAUDE.md"):
        errors.append("AGENTS.md and CLAUDE.md canonical agent contracts differ")
    if not _canonical_block(ROOT / "AGENTS.md"):
        errors.append("canonical agent contract markers are missing")
    return errors


def verify_metadata() -> list[str]:
    errors: list[str] = []
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
    ):
        try:
            load(name)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{name}: {exc}")
    return errors


def verify() -> int:
    errors = verify_contract_sync() + verify_metadata()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("governance verification: PASS")
    return 0


def manifest_allowed(path: str, manifest: dict | None) -> bool:
    if manifest is None:
        return True
    allowed = manifest.get("allowed_paths", [])
    return any(matches(path, pattern) for pattern in allowed)


def check(authority: str, staged: bool, manifest_path: str | None) -> int:
    if authority not in LEVEL:
        print(f"unknown authority level: {authority}", file=sys.stderr)
        return 2

    manifest = None
    if manifest_path:
        with Path(manifest_path).open("rb") as handle:
            manifest = tomllib.load(handle)
        declared = manifest.get("authority")
        if declared and LEVEL[authority] > LEVEL.get(declared, -1):
            print("requested authority exceeds session manifest", file=sys.stderr)
            return 2

    paths = current_paths(staged=staged)
    frozen = load("frozen-artifacts.toml").get("artifact", [])
    active = load("active-work.toml").get("work", [])
    errors: list[str] = []

    for path in paths:
        if not manifest_allowed(path, manifest):
            errors.append(f"{path}: outside session allowed_paths")

        for artifact in frozen:
            if matches(path, artifact["path_glob"]):
                need = artifact.get("minimum_authority", "L4")
                if LEVEL[authority] < LEVEL[need]:
                    errors.append(f"{path}: requires {need} ({artifact['class']})")

        for work in active:
            if work.get("state") != "RUNNING":
                continue
            if any(matches(path, pattern) for pattern in work.get("protected_paths", [])):
                errors.append(f"{path}: protected by active run {work['id']}")

    if errors:
        for error in errors:
            print(f"BLOCK: {error}", file=sys.stderr)
        return 1

    print(f"agent check: PASS ({authority}, {len(paths)} changed paths)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("verify")

    p_check = sub.add_parser("check")
    p_check.add_argument("--authority", required=True, choices=tuple(LEVEL))
    p_check.add_argument("--staged", action="store_true")
    p_check.add_argument("--manifest")

    args = parser.parse_args()
    if args.command == "status":
        return status()
    if args.command == "verify":
        return verify()
    return check(args.authority, args.staged, args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
