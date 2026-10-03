"""Static import graph for the migration (stdlib only).

Resolves absolute and relative imports with ``ast`` and aggregates them into
unit -> unit edges, where a unit is a first-party package prefix such as
``symbiont.core`` or ``symbiont_lab.physics3d``.

Usage:
    python migration/tools/depgraph.py --root src --root . [--json out.json]
        [--edges-from symbiont.core] [--forbid 'symbiont -> symbiont_lab'] ...

Edge kinds: ``top`` (module import time), ``lazy`` (inside a function/method),
``typing`` (under ``if TYPE_CHECKING``).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

FIRST_PARTY = ("symbiont", "environment", "modality", "embodiment", "lab")
# Packages whose direct children are architectural units of their own.
SPLIT = ("symbiont", "lab", "symbiont.core", "lab.studies")
EXTERNAL_HEAVY = ("pybullet", "torch", "numpy", "PIL")


def discover(roots: list[Path]) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for root in roots:
        for top in FIRST_PARTY:
            base = root / top
            if not (base / "__init__.py").exists():
                continue
            for path in sorted(base.rglob("*.py")):
                rel = path.relative_to(root).with_suffix("")
                parts = list(rel.parts)
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                modules.setdefault(".".join(parts), path)
    return modules


def unit_of(module: str) -> str:
    parts = module.split(".")
    unit = parts[0]
    for depth in range(1, len(parts)):
        if unit in SPLIT:
            unit = ".".join(parts[: depth + 1])
        else:
            break
    return unit


class Visitor(ast.NodeVisitor):
    def __init__(self, module: str, is_package: bool, modules: dict[str, Path]):
        self.module = module
        self.package = module if is_package else module.rpartition(".")[0]
        self.modules = modules
        self.depth = 0
        self.typing = 0
        self.found: list[tuple[str, str, int]] = []

    def _kind(self) -> str:
        if self.typing:
            return "typing"
        return "lazy" if self.depth else "top"

    def _add(self, target: str, lineno: int) -> None:
        # Longest known first-party module prefix, else the external top-level name.
        probe = target
        while probe and probe not in self.modules:
            probe = probe.rpartition(".")[0]
        if probe:
            self.found.append((probe, self._kind(), lineno))
        elif target.split(".")[0] in EXTERNAL_HEAVY:
            self.found.append((f"<{target.split('.')[0]}>", self._kind(), lineno))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(alias.name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            base = self.package.split(".")
            base = base[: len(base) - (node.level - 1)]
            prefix = ".".join(base + ([node.module] if node.module else []))
        else:
            prefix = node.module or ""
        for alias in node.names:
            self._add(f"{prefix}.{alias.name}" if prefix else alias.name, node.lineno)

    def _scoped(self, node: ast.AST) -> None:
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    visit_FunctionDef = _scoped
    visit_AsyncFunctionDef = _scoped

    def visit_If(self, node: ast.If) -> None:
        test = ast.unparse(node.test)
        if test in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
            self.typing += 1
            for child in node.body:
                self.visit(child)
            self.typing -= 1
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)


def build(roots: list[Path]) -> tuple[dict[str, Path], list[dict]]:
    modules = discover(roots)
    edges: list[dict] = []
    for module, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = Visitor(module, path.name == "__init__.py", modules)
        visitor.visit(tree)
        for target, kind, lineno in visitor.found:
            edges.append(
                {
                    "src": module,
                    "dst": target,
                    "src_unit": unit_of(module),
                    "dst_unit": target if target.startswith("<") else unit_of(target),
                    "kind": kind,
                    "file": str(path),
                    "line": lineno,
                }
            )
    return modules, edges


def matches(unit: str, pattern: str) -> bool:
    return unit == pattern or unit.startswith(pattern + ".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--edges-from", action="append", default=[])
    parser.add_argument("--edges-to", action="append", default=[])
    parser.add_argument(
        "--forbid", action="append", default=[], help="'A -> B': fail on any A* -> B* edge"
    )
    parser.add_argument("--include-typing", action="store_true")
    args = parser.parse_args(argv)

    modules, edges = build(args.root)
    if args.json:
        args.json.write_text(json.dumps(edges, indent=1) + "\n", encoding="utf-8")

    unit_edges: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for edge in edges:
        if edge["src_unit"] != edge["dst_unit"]:
            unit_edges[(edge["src_unit"], edge["dst_unit"])][edge["kind"]] += 1

    def show(pair: tuple[str, str]) -> bool:
        if not args.edges_from and not args.edges_to:
            return True
        return any(matches(pair[0], p) for p in args.edges_from) or any(
            matches(pair[1], p) for p in args.edges_to
        )

    print(f"modules: {len(modules)}  import edges: {len(edges)}")
    for pair in sorted(unit_edges):
        if show(pair):
            kinds = " ".join(f"{k}={v}" for k, v in sorted(unit_edges[pair].items()))
            print(f"{pair[0]} -> {pair[1]}  [{kinds}]")

    violations = []
    for rule in args.forbid:
        left, _, right = (part.strip() for part in rule.partition("->"))
        for edge in edges:
            if edge["kind"] == "typing" and not args.include_typing:
                continue
            if matches(edge["src_unit"], left) and (
                matches(edge["dst_unit"], right) or edge["dst_unit"] == right
            ):
                violations.append((rule, edge))
    for rule, edge in violations:
        print(
            f"VIOLATION [{rule}] {edge['file']}:{edge['line']} "
            f"{edge['src']} -> {edge['dst']} ({edge['kind']})"
        )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
