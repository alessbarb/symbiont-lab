from __future__ import annotations

import ast
from pathlib import Path

_ALLOWED_COGNITION_GENOME_COMPATIBILITY = {
    "src/symbiont/cognition/genome.py",
}


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_production_genome_access_does_not_route_through_cognition() -> None:
    root = Path(__file__).resolve().parents[2]
    production_roots = (
        root / "src" / "symbiont",
        root / "src" / "symbiont_lab",
        root / "observatory",
    )
    violations: list[str] = []
    for production_root in production_roots:
        for path in production_root.rglob("*.py"):
            rel_path = path.relative_to(root)
            rel = rel_path.as_posix()
            if "tests" in rel_path.parts:
                continue
            if rel in _ALLOWED_COGNITION_GENOME_COMPATIBILITY:
                continue
            for module in _imports(path):
                if module == "symbiont.cognition.genome" or module.endswith(".cognition.genome"):
                    violations.append(f"{rel}:{module}")
    assert violations == []


def test_runtime_imports_domains_not_extracted_algorithm_helpers() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    source = runtime.read_text(encoding="utf-8")
    forbidden = (
        "SecondLookSession",
        "attend_to_host",
        "AttentionCandidate",
        "RegulatorySignals",
        "SignalObservationBatch",
        "project_cognitive_self_observation",
        "ConsolidationSignal",
        "narrate_host",
    )
    for symbol in forbidden:
        assert symbol not in source
