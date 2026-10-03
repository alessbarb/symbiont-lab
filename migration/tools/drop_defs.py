"""Delete top-level functions/classes (with their decorators) from a Python file.

python migration/tools/drop_defs.py FILE NAME [NAME ...]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    path, names = Path(argv[0]), set(argv[1:])
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    kill: set[int] = set()
    found: set[str] = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if node.name in names:
                start = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 1
                kill |= set(range(start, node.end_lineno))
                found.add(node.name)
    path.write_text(
        "\n".join(line for i, line in enumerate(lines) if i not in kill), encoding="utf-8"
    )
    missing = names - found
    print(
        f"{path}: dropped {sorted(found)}" + (f"  NOT FOUND {sorted(missing)}" if missing else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
