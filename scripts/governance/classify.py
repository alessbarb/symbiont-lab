"""Final-diff classifier for governed publication."""

from __future__ import annotations

import fnmatch
import re
import subprocess
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ChangeClass(StrEnum):
    ORDINARY = "ORDINARY"
    SCIENTIFIC = "SCIENTIFIC"
    FROZEN = "FROZEN"
    CONSTITUTIONAL = "CONSTITUTIONAL"


@dataclass(frozen=True)
class Assessment:
    classification: ChangeClass
    paths: tuple[str, ...]
    reasons: tuple[str, ...]
    equivalence_scenarios: tuple[str, ...]


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern)


def _frozen(repo: Path, base: str, path: str) -> bool:
    parts = Path(path).parts
    if not parts or parts[0] != "experiments":
        return False
    parent = Path(path).parent
    while len(parent.parts) > 1:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{base}:{parent.as_posix()}/results.json"],
            cwd=repo,
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            return True
        parent = parent.parent
    return False


def assess(repo: Path, base: str, paths: list[str], diff_text: str) -> Assessment:
    config = tomllib.loads(
        (repo / "docs/governance/change-surfaces.toml").read_text(encoding="utf-8")
    )
    classification = ChangeClass.ORDINARY
    rank = {
        ChangeClass.ORDINARY: 0,
        ChangeClass.SCIENTIFIC: 1,
        ChangeClass.CONSTITUTIONAL: 2,
        ChangeClass.FROZEN: 3,
    }
    reasons: list[str] = []
    scenarios: list[str] = []

    for path in paths:
        if _frozen(repo, base, path):
            classification = ChangeClass.FROZEN
            reasons.append(f"{path}: completed experiment evidence")
            continue

        for surface in config.get("surface", []):
            if not any(_matches(path, pattern) for pattern in surface.get("paths", [])):
                continue
            target = ChangeClass(surface["classification"])
            regexes = surface.get("diff_regex", [])
            if regexes and not any(re.search(rx, diff_text, re.IGNORECASE) for rx in regexes):
                continue
            if rank[target] > rank[classification]:
                classification = target
            reasons.append(f"{path}: {surface['id']}")
            for scenario in surface.get("equivalence", []):
                if scenario not in scenarios:
                    scenarios.append(scenario)

    return Assessment(
        classification,
        tuple(paths),
        tuple(dict.fromkeys(reasons)),
        tuple(scenarios),
    )
