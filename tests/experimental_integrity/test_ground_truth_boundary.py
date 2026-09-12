from __future__ import annotations

import ast
import inspect
from pathlib import Path

from symbiont.core.agent import Agent
from symbiont.core.metacognition import MetacognitionEngine
from symbiont.core.reasoning import ReasoningEngine


def test_ast_symbiont_never_imports_symbiont_lab():
    """Epistemological invariant: symbiont must never depend on symbiont_lab."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    violations: list[str] = []
    for py_file in symbiont_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "symbiont_lab" or alias.name.startswith("symbiont_lab."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "symbiont_lab" or node.module.startswith("symbiont_lab.")):
                    violations.append(f"{py_file.relative_to(repo_root)} imports from {node.module}")

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_agent_cognition_has_no_ground_truth_parameters():
    """Agent and reasoning components must receive only observations and local/collective memory."""
    observe_sig = inspect.signature(Agent.observe)
    params = list(observe_sig.parameters.keys())
    assert "is_threat" not in params
    assert "truth_label" not in params
    assert "ground_truth" not in params

    reason_sig = inspect.signature(ReasoningEngine.analyze)
    params = list(reason_sig.parameters.keys())
    assert "is_threat" not in params
    assert "evaluator" not in params

    meta_sig = inspect.signature(MetacognitionEngine.assess)
    params = list(meta_sig.parameters.keys())
    assert "is_threat" not in params
    assert "ground_truth" not in params
