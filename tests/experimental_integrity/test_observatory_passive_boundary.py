"""The ``observatory`` package projects and serves; it never owns an organism.

Launchers that construct, restore or drive a runtime live in the Lab and hand
ticks to the projection. A package name is not evidence of passivity, so the
boundary is checked on the code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OBSERVATORY = ROOT / "lab" / "src" / "lab" / "observatory"
MODULES = sorted(OBSERVATORY.glob("*.py"))

# Organism construction, restore and training live behind these modules.
FORBIDDEN_IMPORTS = (
    "symbiont.core",
    "symbiont.modeling",
    "symbiont.host.checkpoint",
    "lab.cli",
    "lab.modeling",
    "lab.physics3d",
)
FORBIDDEN_CALLS = {
    "from_checkpoint",
    "load_or_create",
    "load_required",
    "load_or_create_for_first_boot",
    "restore_resident_with_canonical_cognition",
    "attach_private_model_bridge",
    "tick",
    "save",
}
LAUNCHERS = ("observed_resident.py", "observed_replay.py")


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_the_package_has_modules_to_check() -> None:
    assert len(MODULES) >= 8


@pytest.mark.parametrize("path", MODULES, ids=lambda path: path.name)
def test_observatory_module_cannot_construct_or_drive_an_organism(path: Path) -> None:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported = [node.module or ""]
        else:
            imported = []
        for module in imported:
            assert not module.startswith(FORBIDDEN_IMPORTS), f"{path.name} imports {module}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in FORBIDDEN_CALLS, f"{path.name} calls .{node.func.attr}()"


@pytest.mark.parametrize("name", LAUNCHERS)
def test_launchers_live_in_the_lab(name: str) -> None:
    assert (ROOT / "lab" / "src" / "lab" / "cli" / name).is_file()
    assert not (OBSERVATORY / name).exists()
    assert not (OBSERVATORY / "resident.py").exists()
