#!/usr/bin/env python3
"""Deterministic version synchronization for five-domain workspace packages.

The root pyproject.toml defines the authoritative workspace version.
Every workspace member maintains an exact static PEP 621 copy so it remains
independently buildable without a parent workspace, but member versions must
never be edited manually.

Usage:
    python scripts/governance/version.py check
    python scripts/governance/version.py sync
    python scripts/governance/version.py bump [patch|minor|major]
    python scripts/governance/version.py set <VERSION>
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = ("symbiont", "embodiment", "modality", "environment", "lab")
SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")


def get_root_version(root: Path = ROOT) -> str:
    pyproject = root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def get_member_version(domain: str, root: Path = ROOT) -> str:
    pyproject = root / domain / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def get_package_init_version(domain: str, root: Path = ROOT) -> str | None:
    init_file = root / domain / "src" / domain / "__init__.py"
    if not init_file.is_file():
        return None
    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def check_versions(root: Path = ROOT) -> list[str]:
    """Return a list of mismatch descriptions across all domain files.

    An empty list indicates all domain pyproject.toml files and package
    __version__ declarations exactly match the root authoritative version.
    """
    root_version = get_root_version(root)
    mismatches: list[str] = []

    if not SEMVER_REGEX.match(root_version):
        mismatches.append(f"Root version '{root_version}' is not valid semantic versioning")

    for domain in DOMAINS:
        member_version = get_member_version(domain, root)
        if member_version != root_version:
            mismatches.append(
                f"{domain}/pyproject.toml version ({member_version}) != root ({root_version})"
            )

        init_version = get_package_init_version(domain, root)
        if init_version is None:
            mismatches.append(
                f"{domain}/src/{domain}/__init__.py is missing __version__ declaration"
            )
        elif init_version != root_version:
            mismatches.append(
                f"{domain}/src/{domain}/__init__.py __version__ ({init_version}) != root ({root_version})"
            )

    return mismatches


def parse_semver(version: str) -> tuple[int, int, int, str]:
    match = SEMVER_REGEX.match(version)
    if not match:
        raise ValueError(f"Invalid semver version: {version!r}")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4) or ""
    return major, minor, patch, prerelease


def bump_semver(current: str, part: str) -> str:
    major, minor, patch, _ = parse_semver(current)
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "major":
        return f"{major + 1}.0.0"
    raise ValueError(f"Unknown semver bump part: {part!r}, expected 'patch', 'minor', or 'major'")


def _update_pyproject_version(path: Path, new_version: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^(\s*version\s*=\s*)["\'][^"\']+["\']',
        rf'\g<1>"{new_version}"',
        content,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Failed to find and update version in {path}")
    path.write_text(updated, encoding="utf-8")


def _update_init_version(path: Path, new_version: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^(\s*__version__\s*=\s*)["\'][^"\']+["\']',
        rf'\g<1>"{new_version}"',
        content,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Failed to find and update __version__ in {path}")
    path.write_text(updated, encoding="utf-8")


def sync_versions(
    target_version: str | None = None,
    *,
    root: Path = ROOT,
    run_lock: bool = True,
) -> str:
    """Synchronize all workspace member pyproject.toml and __init__.py files.

    If target_version is provided, root pyproject.toml is updated first.
    Then every member is updated to match.
    """
    if target_version is not None:
        if not SEMVER_REGEX.match(target_version):
            raise ValueError(f"Invalid semver version: {target_version!r}")
        _update_pyproject_version(root / "pyproject.toml", target_version)
        version = target_version
    else:
        version = get_root_version(root)

    for domain in DOMAINS:
        _update_pyproject_version(root / domain / "pyproject.toml", version)
        init_file = root / domain / "src" / domain / "__init__.py"
        if init_file.is_file():
            _update_init_version(init_file, version)

    if run_lock:
        cmd = ["uv", "lock"]
        res = subprocess.run(cmd, cwd=root, check=False, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"uv lock failed after version sync:\n{res.stderr}")

    return version


def bump_version(part: str, *, root: Path = ROOT, run_lock: bool = True) -> str:
    current = get_root_version(root)
    next_version = bump_semver(current, part)
    return sync_versions(next_version, root=root, run_lock=run_lock)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check that all workspace members match root version")
    subparsers.add_parser(
        "sync", help="Synchronize all member versions to match root pyproject.toml"
    )

    bump_p = subparsers.add_parser("bump", help="Bump semver and synchronize all members")
    bump_p.add_argument("part", choices=["patch", "minor", "major"], help="Part of semver to bump")
    bump_p.add_argument("--no-lock", action="store_true", help="Do not run uv lock")

    set_p = subparsers.add_parser("set", help="Set explicit version and synchronize all members")
    set_p.add_argument("version", help="Explicit version string (e.g. 0.91.0)")
    set_p.add_argument("--no-lock", action="store_true", help="Do not run uv lock")

    args = parser.parse_args(argv)

    if args.command == "check":
        root_v = get_root_version()
        mismatches = check_versions()
        if mismatches:
            print(f"FAILED: Version mismatches against root ({root_v}):", file=sys.stderr)
            for m in mismatches:
                print(f"  - {m}", file=sys.stderr)
            return 1
        print(f"OK: All 5 domain packages match authoritative root version {root_v}")
        return 0

    if args.command == "sync":
        v = sync_versions()
        print(f"Synchronized all domain packages to version {v}")
        return 0

    if args.command == "bump":
        v = bump_version(args.part, run_lock=not args.no_lock)
        print(f"Bumped version ({args.part}) to {v} across all domain packages and lockfile")
        return 0

    if args.command == "set":
        v = sync_versions(args.version, run_lock=not args.no_lock)
        print(f"Set version to {v} across all domain packages and lockfile")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
