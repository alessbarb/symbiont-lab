"""Remove imports of deleted modules from a file, and the names they provided from ``__all__``.

    python migration/tools/drop_imports.py FILE DEAD.MODULE [DEAD.MODULE ...]

Prints every other use of a dropped name left in the file as ``MANUAL``.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import move_module  # noqa: E402


def main(argv: list[str]) -> int:
    path, dead = Path(argv[0]).resolve(), argv[1:]
    module, is_package = move_module.module_name(path)
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    dropped: set[str] = set()
    kill: set[int] = set()
    for node in ast.parse(text).body:
        targets: list[str] = []
        if isinstance(node, ast.ImportFrom):
            base = move_module.absolute(module, is_package, node) if node.level else node.module
            targets = [base or ""] + [f"{base}.{alias.name}" for alias in node.names]
            hit = any(move_module.under(target, d) for d in dead for target in targets[:1])
            partial = [
                alias
                for alias in node.names
                if any(move_module.under(f"{base}.{alias.name}", d) for d in dead)
            ]
            if hit or (partial and len(partial) == len(node.names)):
                dropped |= {alias.asname or alias.name for alias in node.names}
                kill |= set(range(node.lineno - 1, node.end_lineno))
            elif partial:
                print(f"MANUAL {path}:{node.lineno}: partial import of deleted names")
        elif isinstance(node, ast.Import):
            if any(move_module.under(alias.name, d) for d in dead for alias in node.names):
                dropped |= {(alias.asname or alias.name).split(".")[0] for alias in node.names}
                kill |= set(range(node.lineno - 1, node.end_lineno))
    kept = [line for index, line in enumerate(lines) if index not in kill]
    kept = [
        line
        for line in kept
        if not re.fullmatch(r'\s*"(\w+)",', line) or line.strip()[1:-2] not in dropped
    ]
    for number, line in enumerate(kept, 1):
        for name in dropped:
            if re.search(rf"\b{re.escape(name)}\b", line):
                print(f"MANUAL {path.name}:{number}: {line.strip()[:110]}")
    path.write_text("\n".join(kept), encoding="utf-8")
    print(f"{path.name}: dropped {len(kill)} import lines, {len(dropped)} names")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
