from __future__ import annotations

import ast
from pathlib import Path


def test_ast_symbiont_never_imports_symbiont_lab():
    """Epistemological invariant: symbiont must never depend on lab."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "symbiont" / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    violations: list[str] = []
    for py_file in symbiont_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "lab" or alias.name.startswith("lab."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "lab" or node.module.startswith("lab.")):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_cognition_never_imports_symbiont_lab():
    """Narrower, package-specific instance of the general AST boundary
    (roadmap v0.55) — the cognitive-graph package must never depend on
    the evaluation apparatus that will eventually score it."""
    repo_root = Path(__file__).resolve().parents[2]
    cognition_src = repo_root / "symbiont" / "src" / "symbiont" / "cognition"
    assert cognition_src.is_dir(), f"Not found: {cognition_src}"

    violations: list[str] = []
    for py_file in cognition_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "lab" or alias.name.startswith("lab."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "lab" or node.module.startswith("lab.")):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_symbiont_never_imports_symbiont_world():
    """docs/design/archive/symbiont-world-v1.md §2: the organism keeps receiving
    only normalized readings via source -> sensor -> percept; it never
    imports environment directly."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "symbiont" / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    violations: list[str] = []
    for py_file in symbiont_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "environment" or alias.name.startswith("environment."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module == "environment" or node.module.startswith("environment.")
                ):
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)


def test_symbiont_world_imports_nothing_from_this_repo():
    """docs/design/archive/symbiont-world-v1.md §2: environment imports neither
    symbiont nor lab. lab is the only adapter that
    crosses the boundary in both directions."""
    repo_root = Path(__file__).resolve().parents[2]
    world_src = repo_root / "environment" / "src" / "environment"
    assert world_src.is_dir(), f"Not found: {world_src}"

    forbidden = {"symbiont", "lab"}
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
    """Evolution belongs entirely to lab, never the resident
    organism (master doc §8: "un individuo no se reproduce ni se
    despliega a sí mismo") -- a structural check, not just a style
    preference."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "symbiont" / "src" / "symbiont"
    forbidden_names = {
        "mutation.py",
        "evolution.py",
        "selection.py",
        "lineage.py",
        "reproduction.py",
    }
    hits = [
        str(path.relative_to(repo_root))
        for path in symbiont_src.rglob("*.py")
        if path.name in forbidden_names
        or (path.name == "recombination.py" and "genetics" in path.parts)
    ]
    assert not hits, f"symbiont/ must never contain evolution code: {hits}"


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
    symbiont_src = repo_root / "symbiont" / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    assert not (symbiont_src / "core" / "behavior.py").exists(), (
        "symbiont/src/symbiont/core/behavior.py must not be reintroduced"
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
    """Allowlist invariant: symbiont/src/symbiont/ contains only organism/subject packages.

    `modeling/` is organism-owned state and contracts (experience, corpus,
    tokenizer, model registry/gateway). Training frameworks, held-out scoring and
    promotion evidence remain exclusively in `lab`, enforced separately
    by the AST dependency boundary above.
    """
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "symbiont" / "src" / "symbiont"
    assert symbiont_src.is_dir(), f"Not found: {symbiont_src}"

    allowed = {
        "__init__.py",
        "__pycache__",
        "actuation",
        "agency",
        "api.py",
        "capacity.py",
        "cognition",
        "core",
        "genetics",
        "host",
        "modeling",
        "provenance.py",
        "sensory",
    }
    actual = {p.name for p in symbiont_src.iterdir()}
    unexpected = actual - allowed
    assert not unexpected, (
        f"Subject package violation: symbiont/src/symbiont contains non-subject or legacy files: {unexpected}"
    )
