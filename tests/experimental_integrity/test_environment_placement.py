"""ADR-0060 §5: the organism package gains no new environment-side class.

The habitats and the synthetic host-event package already live under
``src/symbiont`` and are tolerated as a closed list. Anything new that models
the external side of the boundary belongs in the World kernel or in the Lab.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORGANISM = ROOT / "src" / "symbiont"
ENVIRONMENT_NAME = re.compile(r"World|Habitat|Environment")
TOLERATED = {
    ("core/host/local_habitat.py", "LocalHabitat"),
    ("core/social/ecology.py", "HabitatSnapshot"),
    ("core/social/ecology.py", "SharedHabitat"),
    ("core/social/relations.py", "SocialHabitat"),
}
TOLERATED_PACKAGE = "environment"


def _environment_classes() -> set[tuple[str, str]]:
    found = set()
    for path in ORGANISM.rglob("*.py"):
        relative = path.relative_to(ORGANISM).as_posix()
        if relative.startswith(f"{TOLERATED_PACKAGE}/"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and ENVIRONMENT_NAME.search(node.name):
                found.add((relative, node.name))
    return found


def test_environment_side_classes_in_the_organism_package_are_a_closed_list() -> None:
    assert _environment_classes() == TOLERATED


def test_the_tolerated_legacy_environment_package_has_not_grown() -> None:
    modules = {path.name for path in (ORGANISM / TOLERATED_PACKAGE).glob("*.py")}
    assert modules == {"__init__.py", "regimes.py", "rng.py", "world.py"}
