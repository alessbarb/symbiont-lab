from __future__ import annotations

import ast
from pathlib import Path

from symbiont.actuation.proposer import ActuatorEvidenceModel, ActuatorProposer


def test_legacy_proposer_is_only_a_compatibility_subclass() -> None:
    assert issubclass(ActuatorProposer, ActuatorEvidenceModel)
    assert ActuatorProposer.__dict__.keys() <= {
        "__module__",
        "__doc__",
    }


def test_action_domain_does_not_reference_legacy_proposer_name() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "symbiont" / "core" / "domains" / "action.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "ActuatorProposer" not in imported
    assert "_legacy_proposer" not in source
    assert "ActuatorEvidenceModel" in imported
