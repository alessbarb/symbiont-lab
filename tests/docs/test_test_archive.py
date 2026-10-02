"""Archived tests name the canonical test that replaces them (tests/archive/README.md)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "tests" / "archive"


def _superseded_by(node: ast.FunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and ast.unparse(decorator.func).endswith("superseded"):
            arguments = {kw.arg: kw.value for kw in decorator.keywords}
            by, reason = arguments.get("by"), arguments.get("reason")
            if isinstance(by, ast.Constant) and isinstance(reason, ast.Constant) and reason.value:
                return str(by.value)
    return None


def test_every_archived_test_names_an_existing_replacement_and_is_indexed() -> None:
    index = (ARCHIVE / "README.md").read_text(encoding="utf-8")
    files = sorted(ARCHIVE.glob("test_*.py"))
    assert files
    for path in files:
        assert f"`{path.name}`" in index, f"{path.name} missing from the archive index"
        tests = [
            node
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        assert tests, path.name
        for node in tests:
            by = _superseded_by(node)
            assert by, f"{path.name}::{node.name} has no superseded(by=..., reason=...)"
            target, _, name = by.partition("::")
            assert not target.startswith("tests/archive/"), by
            replacement = ROOT / target
            assert replacement.is_file(), by
            assert f"def {name}(" in replacement.read_text(encoding="utf-8"), by


def test_archive_is_outside_the_canonical_collection() -> None:
    assert '"archive"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
