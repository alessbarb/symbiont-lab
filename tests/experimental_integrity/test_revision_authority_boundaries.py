"""Revision Coherence v1 §3.3-§3.4: one executability, owned by one projection;
the executive never revises bindings."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def _calls(attribute: str):
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == attribute
            ):
                yield path.relative_to(SRC).as_posix()


def test_binding_executability_is_read_only_through_the_projection():
    assert sorted(set(_calls("is_executable"))) == []


def test_only_the_action_domain_revises_binding_status():
    writers = set(_calls("set_status")) | set(_calls("drain_transitions"))
    assert writers <= {"symbiont/core/domains/action.py"}
    executive = (SRC / "symbiont/agency/executive_outcome.py").read_text(encoding="utf-8")
    assert "binding import" not in executive and "set_status" not in executive
