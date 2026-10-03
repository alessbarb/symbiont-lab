"""Revision Coherence v1 §3.3-§3.4: one executability, owned by one projection;
the executive never revises bindings."""

from __future__ import annotations

import ast

from tests.layout import package_path, package_relative, source_files


def _calls(attribute: str):
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == attribute
            ):
                yield package_relative(path).as_posix()


def test_binding_executability_is_read_only_through_the_projection():
    assert sorted(set(_calls("is_executable"))) == []


def test_only_the_action_domain_revises_binding_status():
    writers = set(_calls("set_status")) | set(_calls("drain_transitions"))
    assert writers <= {"symbiont/core/domains/action.py"}
    executive = package_path("symbiont/agency/executive_outcome.py").read_text(encoding="utf-8")
    assert "binding import" not in executive and "set_status" not in executive
