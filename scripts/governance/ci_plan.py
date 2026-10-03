#!/usr/bin/env python3
"""Build an explicit GitHub Actions validation plan from governed change surfaces."""

from __future__ import annotations

import argparse
import fnmatch
import importlib
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

classify = importlib.import_module("governance.classify")
ChangeClass = classify.ChangeClass
assess = classify.assess


_LEGACY_SECTION_LANES = {
    "docs": ("docs",),
    "governance": ("governance",),
    "subject": ("software_core", "architecture_integrity"),
    "lab": ("software_core", "architecture_integrity"),
    "world": ("world", "architecture_integrity"),
    "observatory": ("observatory", "architecture_integrity"),
    "experiment_protocol": ("experiment_mechanics", "architecture_integrity"),
    "tests": ("canonical_full",),
}


@dataclass(frozen=True)
class CIPlan:
    classification: str
    docs: bool
    governance: bool
    software_core: bool
    world: bool
    observatory: bool
    architecture_integrity: bool
    runtime_contracts: bool
    experiment_mechanics: bool
    canonical_full: bool
    physics3d: bool
    modeling: bool
    python_compat: bool
    host_portability: bool
    alpine: bool
    protocol_mechanics: bool
    performance: bool
    changed_paths: tuple[str, ...]
    matrix_sections: tuple[str, ...]
    reasons: tuple[str, ...]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _load_matrix_at(base: str) -> dict:
    raw = _git("show", f"{base}:docs/governance/validation-matrix.toml")
    return tomllib.loads(raw)


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern)


def _selected_matrix_sections(base: str, paths: tuple[str, ...]) -> tuple[str, ...]:
    matrix = _load_matrix_at(base)
    selected: list[str] = []
    for path in paths:
        matched = [
            name
            for name, section in matrix.items()
            if name != "schema_version"
            and isinstance(section, dict)
            and any(_matches(path, pattern) for pattern in section.get("paths", []))
        ]
        # [tests] is deliberately broad for local validation. In CI, prefer a
        # more specific governed section when one exists for the same path.
        if len(matched) > 1 and "tests" in matched:
            matched.remove("tests")
        for name in matched:
            if name not in selected:
                selected.append(name)
    return tuple(selected)


def _lanes_for_sections(base: str, sections: tuple[str, ...]) -> set[str]:
    matrix = _load_matrix_at(base)
    lanes: set[str] = set()
    for name in sections:
        section = matrix.get(name, {})
        declared = tuple(str(item) for item in section.get("ci_lanes", []))
        lanes.update(declared or _LEGACY_SECTION_LANES.get(name, ()))
    return lanes


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return path.startswith(prefixes)


def build_plan(base: str, head: str) -> CIPlan:
    paths = tuple(
        line
        for line in _git("diff", "--name-only", "--diff-filter=ACMRD", base, head).splitlines()
        if line
    )
    diff_text = _git("diff", base, head)
    assessment = assess(ROOT, base, list(paths), diff_text)
    classification = assessment.classification
    sections = _selected_matrix_sections(base, paths)
    lanes = _lanes_for_sections(base, sections)

    markdown_only = bool(paths) and all(path.endswith((".md", ".markdown")) for path in paths)

    constitutional = classification in {ChangeClass.CONSTITUTIONAL, ChangeClass.FROZEN}
    scientific = classification in {
        ChangeClass.SCIENTIFIC,
        ChangeClass.CONSTITUTIONAL,
        ChangeClass.FROZEN,
    }

    host_related = (
        any(
            _matches_prefix(
                path,
                (
                    "symbiont/src/symbiont/host/",
                    "symbiont/tests/unit/host/",
                    "lab/src/lab/physics3d/",
                    "embodiment/src/embodiment/",
                    "lab/src/lab/integration/",
                    "modality/src/modality/",
                    "environment/src/environment/physics3d/",
                ),
            )
            for path in paths
        )
        and not markdown_only
    )
    physics_related = (
        any(
            _matches_prefix(
                path,
                (
                    "lab/src/lab/physics3d/",
                    "embodiment/src/embodiment/",
                    "lab/src/lab/integration/",
                    "modality/src/modality/",
                    "environment/src/environment/physics3d/",
                    "lab/tests/unit/lab/physics3d/",
                    "embodiment/tests/",
                    "modality/tests/",
                    "lab/tests/integration/test_physics3d",
                ),
            )
            for path in paths
        )
        and not markdown_only
    )
    modeling_related = (
        any(
            _matches_prefix(
                path,
                (
                    "lab/src/lab/modeling/",
                    "symbiont/tests/unit/modeling/",
                    "lab/tests/unit/modeling/",
                    "lab/tests/unit/lab/modeling/",
                    "lab/tests/integration/test_private_model",
                    "lab/tests/integration/test_training_ancestry",
                ),
            )
            for path in paths
        )
        and not markdown_only
    )

    performance_related = (
        any(
            _matches_prefix(
                path,
                (
                    "symbiont/src/symbiont/",
                    "lab/src/lab/physics3d/",
                    "embodiment/src/embodiment/",
                    "lab/src/lab/integration/",
                    "modality/src/modality/",
                    "environment/src/environment/physics3d/",
                    "lab/src/lab/modeling/",
                    "lab/src/lab/observatory/",
                    "lab/src/lab/workbench/",
                ),
            )
            for path in paths
        )
        and not markdown_only
    )

    # Constitutional changes validate the CI/governance mechanism itself, so
    # keep broad behavioral sentinels during this rollout unless the diff is
    # strictly limited to Markdown documentation.
    if constitutional and not markdown_only:
        lanes.update(
            {
                "software_core",
                "observatory",
                "architecture_integrity",
                "runtime_contracts",
                "experiment_mechanics",
            }
        )

    return CIPlan(
        classification=str(classification),
        docs="docs" in lanes or markdown_only,
        governance="governance" in lanes,
        software_core="software_core" in lanes and not markdown_only,
        world="world" in lanes and "software_core" not in lanes and not markdown_only,
        observatory="observatory" in lanes and not markdown_only,
        architecture_integrity=(
            ("architecture_integrity" in lanes or scientific) and not markdown_only
        ),
        runtime_contracts=("runtime_contracts" in lanes or scientific) and not markdown_only,
        experiment_mechanics="experiment_mechanics" in lanes and not markdown_only,
        canonical_full="canonical_full" in lanes and not markdown_only,
        physics3d=(constitutional or physics_related) and not markdown_only,
        modeling=(constitutional or modeling_related) and not markdown_only,
        python_compat=scientific and not markdown_only,
        host_portability=(constitutional or host_related) and not markdown_only,
        alpine=(constitutional or host_related) and not markdown_only,
        protocol_mechanics=scientific and not markdown_only,
        performance=(constitutional or performance_related) and not markdown_only,
        changed_paths=paths,
        matrix_sections=sections,
        reasons=assessment.reasons,
    )


def _bool(value: bool) -> str:
    return "true" if value else "false"


def emit_github_output(plan: CIPlan, output_path: Path) -> None:
    payload = asdict(plan)
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in payload.items():
            if isinstance(value, bool):
                handle.write(f"{key}={_bool(value)}\n")
            elif isinstance(value, str):
                handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    plan = build_plan(args.base, args.head)
    print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    if args.github_output is not None:
        emit_github_output(plan, args.github_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
