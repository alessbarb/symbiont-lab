"""Delete tests by pytest node id (``file::test`` or ``file::Class::test``), read from stdin.

Removes a class left without tests and a file left without tests.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    wanted: dict[Path, set[tuple[str, ...]]] = defaultdict(set)
    for line in sys.stdin:
        parts = line.strip().split("::")
        if len(parts) >= 2:
            wanted[Path(parts[0])].add(tuple(part.split("[")[0] for part in parts[1:]))
    for path, targets in wanted.items():
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        kill: set[int] = set()

        def span(node: ast.AST) -> set[int]:
            start = min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])
            return set(range(start - 1, node.end_lineno))

        remaining = 0
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("test"):
                    if (node.name,) in targets:
                        kill |= span(node)
                    else:
                        remaining += 1
            elif isinstance(node, ast.ClassDef):
                tests = [
                    child
                    for child in node.body
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                    and child.name.startswith("test")
                ]
                dropped = [child for child in tests if (node.name, child.name) in targets]
                if tests and len(dropped) == len(tests):
                    kill |= span(node)
                else:
                    remaining += len(tests) - len(dropped)
                    for child in dropped:
                        kill |= span(child)
        if remaining == 0:
            path.unlink()
            print(f"deleted {path}")
        else:
            kept = [line for index, line in enumerate(lines) if index not in kill]
            path.write_text("\n".join(kept), encoding="utf-8")
            print(f"{path}: dropped {len(targets)} tests, {remaining} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
