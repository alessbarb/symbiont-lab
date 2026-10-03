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
    CONSTITUTIONAL = "CONSTITUTIONAL"
    FROZEN = "FROZEN"


_PRIORITY = {
    ChangeClass.ORDINARY: 0,
    ChangeClass.SCIENTIFIC: 1,
    ChangeClass.CONSTITUTIONAL: 2,
    ChangeClass.FROZEN: 3,
}


@dataclass(frozen=True)
class Assessment:
    classification: ChangeClass
    paths: tuple[str, ...]
    reasons: tuple[str, ...]
    equivalence_scenarios: tuple[str, ...]


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern)


def _elevate(current: ChangeClass, candidate: ChangeClass) -> ChangeClass:
    return candidate if _PRIORITY[candidate] > _PRIORITY[current] else current


def _frozen(repo: Path, base: str, path: str) -> bool:
    parts = Path(path).parts
    if parts[:2] != ("lab", "experiments"):
        return False
    parent = Path(path).parent
    while len(parent.parts) > 2:
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


def _diff_by_path(diff_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        match = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if match:
            current = match.group(2)
            sections.setdefault(current, []).append(line)
            continue
        if current is not None:
            sections[current].append(line)
    return {path: "\n".join(lines) for path, lines in sections.items()}


def _surface_haystack(repo: Path, path: str, sections: dict[str, str]) -> str:
    segment = sections.get(path, "")
    if segment:
        return segment
    candidate = repo / path
    if candidate.is_file():
        try:
            return candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    return ""


def _load_surfaces(repo: Path, base: str) -> dict:
    """Load classification policy from the trusted baseline, never the candidate tree."""
    result = subprocess.run(
        ["git", "show", f"{base}:docs/governance/change-surfaces.toml"],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError("trusted baseline is missing docs/governance/change-surfaces.toml")
    return tomllib.loads(result.stdout)


def assess(repo: Path, base: str, paths: list[str], diff_text: str) -> Assessment:
    config = _load_surfaces(repo, base)
    sections = _diff_by_path(diff_text)
    classification = ChangeClass.ORDINARY
    reasons: list[str] = []
    scenarios: list[str] = []

    for path in paths:
        if _frozen(repo, base, path):
            classification = _elevate(classification, ChangeClass.FROZEN)
            reasons.append(f"{path}: completed experiment evidence")
            continue

        haystack = _surface_haystack(repo, path, sections)
        for surface in config.get("surface", []):
            if not any(_matches(path, pattern) for pattern in surface.get("paths", [])):
                continue
            regexes = [str(rx) for rx in surface.get("diff_regex", [])]
            symbols = [str(symbol) for symbol in surface.get("symbols", [])]
            if regexes and not any(re.search(rx, haystack, re.IGNORECASE) for rx in regexes):
                continue
            if symbols and not any(
                re.search(rf"\b{re.escape(symbol)}\b", haystack) for symbol in symbols
            ):
                continue

            target = ChangeClass(surface["classification"])
            classification = _elevate(classification, target)
            reasons.append(f"{path}: {surface['id']}")
            for scenario in surface.get("equivalence", []):
                if scenario not in scenarios:
                    scenarios.append(str(scenario))

    return Assessment(
        classification=classification,
        paths=tuple(paths),
        reasons=tuple(dict.fromkeys(reasons)),
        equivalence_scenarios=tuple(scenarios),
    )
