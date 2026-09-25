from __future__ import annotations

import ast
from pathlib import Path


def test_runtime_imports_domains_not_action_deliberation_internals() -> None:
    root = Path(__file__).resolve().parents[2]
    path = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        imported.update(alias.name for alias in node.names)

    forbidden = {
        "ActionEvaluation",
        "ActionJustification",
        "ActionProposal",
        "ActionSource",
        "ExplorationPolicy",
        "ExplorationSignals",
        "CompetenceEvidence",
        "PredictionError",
    }
    assert imported.isdisjoint(forbidden)
    assert "ActionDomain" in imported
    assert "PerceptionDomain" in imported
    assert "CognitionDomain" in imported
    assert "PhysiologyDomain" in imported
    assert "RegulationDomain" in imported
