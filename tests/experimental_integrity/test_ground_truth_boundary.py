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
                if node.module and (
                    node.module == "symbiont_lab" or node.module.startswith("symbiont_lab.")
                ):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_cognition_never_imports_symbiont_lab():
    """Narrower, package-specific instance of the general AST boundary
    (roadmap v0.55) — the cognitive-graph package must never depend on
    the evaluation apparatus that will eventually score it."""
    repo_root = Path(__file__).resolve().parents[2]
    cognition_src = repo_root / "src" / "symbiont" / "cognition"
    assert cognition_src.is_dir(), f"Not found: {cognition_src}"

    violations: list[str] = []
    for py_file in cognition_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "symbiont_lab" or alias.name.startswith("symbiont_lab."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module == "symbiont_lab" or node.module.startswith("symbiont_lab.")
                ):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_symbiont_never_imports_symbiont_world():
    """docs/design/symbiont-world-v1.md §2: the organism keeps receiving
    only normalized readings via source -> sensor -> percept; it never
    imports symbiont_world directly."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    violations: list[str] = []
    for py_file in symbiont_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "symbiont_world" or alias.name.startswith("symbiont_world."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module == "symbiont_world" or node.module.startswith("symbiont_world.")
                ):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_symbiont_world_imports_nothing_from_this_repo():
    """docs/design/symbiont-world-v1.md §2: symbiont_world imports neither
    symbiont nor symbiont_lab. symbiont_lab is the only adapter that
    crosses the boundary in both directions."""
    repo_root = Path(__file__).resolve().parents[2]
    world_src = repo_root / "src" / "symbiont_world"
    assert world_src.is_dir(), f"Not found: {world_src}"

    forbidden = {"symbiont", "symbiont_lab"}
    violations: list[str] = []
    for py_file in world_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden:
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden:
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_symbiont_never_contains_evolution_code():
    """Evolution belongs entirely to symbiont_lab, never the resident
    organism (master doc §8: "un individuo no se reproduce ni se
    despliega a sí mismo") -- a structural check, not just a style
    preference."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    forbidden_names = {"mutation.py", "evolution.py", "selection.py", "lineage.py"}
    hits = [
        str(path.relative_to(repo_root))
        for path in symbiont_src.rglob("*.py")
        if path.name in forbidden_names
    ]
    assert not hits, f"symbiont/ must never contain evolution code: {hits}"


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


def test_symbiont_never_reintroduces_typed_action_semantics():
    """P3 core extraction (docs/design decontamination series): canonical
    ``symbiont`` must never again ship an innate action->meaning vocabulary
    or a weighted utility/reward function selecting among local actions.

    ``symbiont/core/behavior.py`` (deleted) used to define ``ActionKind``
    (REST/INTAKE/REPAIR/... — an imposed semantic vocabulary) and
    ``select_action``, which computed a scalar
    ``viability + integrity + resource_change + reproductive_feasibility
    + social_expectation - cost`` utility. Both are forbidden by CLAUDE.md:
    symbiont must not be born knowing what an action means, and must not
    rank actions with a project-wide reward. This is a structural check,
    not a style preference: it fails on the file's return, not merely on
    a name collision, so a re-introduction under a new module name is
    still caught by the symbol/AST scan below.
    """
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    assert not (symbiont_src / "core" / "behavior.py").exists(), (
        "src/symbiont/core/behavior.py must not be reintroduced"
    )

    forbidden_names = {
        "ActionKind",
        "ExpectedOutcome",
        "ActionOpportunity",
        "SelectionResult",
        "ActionEvidence",
        "LocalActionModel",
        "InteroceptiveActionModel",
        "select_action",
    }
    violations: list[str] = []
    for py_file in symbiont_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            name = None
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
            elif isinstance(node, ast.Name):
                name = node.id
            if name in forbidden_names:
                violations.append(f"{py_file.relative_to(repo_root)} defines/references {name}")

    assert not violations, "Reintroduced typed action-selection contamination:\n" + "\n".join(
        violations
    )


def test_symbiont_contains_only_subject_modules():
    """Allowlist invariant: src/symbiont/ contains only organism/subject packages.

    `modeling/` is organism-owned state and contracts (experience, corpus,
    tokenizer, model registry/gateway). Training frameworks, held-out scoring and
    promotion evidence remain exclusively in `symbiont_lab`, enforced separately
    by the AST dependency boundary above.
    """
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    allowed = {
        "__init__.py",
        "__pycache__",
        "actuation",
        "agency",
        "cognition",
        "core",
        "environment",
        "host",
        "modeling",
        "simulation",
        "sensory",
    }
    actual = {p.name for p in symbiont_src.iterdir()}
    unexpected = actual - allowed
    assert not unexpected, (
        f"Subject package violation: src/symbiont contains non-subject or legacy files: {unexpected}"
    )
