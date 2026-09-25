from __future__ import annotations

import ast
from pathlib import Path

import symbiont.actuation.proposer as proposer_module
from symbiont.actuation.proposer import ActuatorEvidenceModel


def test_legacy_actuator_proposer_symbol_is_removed() -> None:
    assert not hasattr(proposer_module, "ActuatorProposer")
    assert ActuatorEvidenceModel.__name__ == "ActuatorEvidenceModel"


def test_action_domain_imports_only_canonical_actuator_evidence() -> None:
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
    assert "ActuatorEvidenceModel" in imported
