"""Governance covers every path of the five domains.

Reads the policy files of the working tree directly (the classifier itself reads
them from the trusted baseline commit), so a gap is caught before it is merged.
"""

from __future__ import annotations

import fnmatch
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = ("symbiont", "embodiment", "modality", "environment", "lab")
SURFACES = tomllib.loads((ROOT / "docs/governance/change-surfaces.toml").read_text("utf-8"))
MATRIX = tomllib.loads((ROOT / "docs/governance/validation-matrix.toml").read_text("utf-8"))
RANK = {"ORDINARY": 0, "SCIENTIFIC": 1, "CONSTITUTIONAL": 2}


def classification(path: str) -> str | None:
    """Highest classification of the surfaces whose paths match, ignoring content filters."""
    found = [
        surface["classification"]
        for surface in SURFACES["surface"]
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in surface["paths"])
        and not surface.get("symbols")
        and not surface.get("diff_regex")
    ]
    return max(found, key=RANK.__getitem__) if found else None


def lanes(path: str) -> set[str]:
    return {
        lane
        for name, section in MATRIX.items()
        if isinstance(section, dict)
        and any(fnmatch.fnmatchcase(path, pattern) for pattern in section.get("paths", []))
        for lane in section.get("ci_lanes", [])
    }


def tracked(prefix: str) -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", prefix],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return sorted(path for path in listed if path.endswith(".py") and (ROOT / path).is_file())


@pytest.mark.parametrize("domain", DOMAINS)
def test_declared_dependencies_of_a_domain_are_constitutional(domain: str) -> None:
    assert classification(f"{domain}/pyproject.toml") == "CONSTITUTIONAL"
    assert {"architecture_integrity", "canonical_full"} <= lanes(f"{domain}/pyproject.toml")


@pytest.mark.parametrize("domain", ("symbiont", "embodiment", "modality", "environment"))
def test_library_source_is_scientific_and_selects_validation(domain: str) -> None:
    for path in tracked(f"{domain}/src"):
        assert RANK[classification(path) or "ORDINARY"] >= RANK["SCIENTIFIC"], path
        assert {"software_core", "architecture_integrity"} & lanes(path), path


@pytest.mark.parametrize("domain", DOMAINS)
def test_every_source_and_test_path_is_classified_and_selects_a_lane(domain: str) -> None:
    unclassified = [path for path in tracked(domain) if classification(path) is None]
    assert unclassified == []
    without_lane = [path for path in tracked(domain) if not lanes(path)]
    assert without_lane == []


def test_boundary_checks_are_constitutional() -> None:
    for path in (
        "scripts/check_isolation.py",
        "scripts/run_tests.py",
        "tests/experimental_integrity/test_five_domain_architecture.py",
        "symbiont/tests/test_independence.py",
        "embodiment/tests/test_self_contained.py",
        "modality/tests/test_self_contained.py",
        "environment/tests/test_self_contained.py",
        "uv.lock",
        "conftest.py",
    ):
        assert classification(path) == "CONSTITUTIONAL", path


def test_no_policy_path_points_at_nothing() -> None:
    patterns = [p for surface in SURFACES["surface"] for p in surface["paths"]] + [
        p for section in MATRIX.values() if isinstance(section, dict) for p in section["paths"]
    ]
    dead = [
        pattern
        for pattern in sorted(set(patterns))
        if not pattern.startswith((".agents", ".claude", ".codex"))
        and not list(
            ROOT.glob(pattern.replace("/**", "/*") if pattern.endswith("/**") else pattern)
        )
    ]
    assert dead == []
