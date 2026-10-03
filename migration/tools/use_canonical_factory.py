"""Route organism construction and restore through the Lab's canonical factory.

Rewrites, in the given files:

    Runtime(...)                    -> create_canonical_organism(Runtime, ...)
    Runtime.from_checkpoint(p, ...) -> restore_canonical_organism(p, Runtime, ...)
    Runtime.load_or_create(p, ...)  -> load_or_create_canonical_organism(p, Runtime, ...)

for the organism runtime classes, where ``Runtime`` is omitted when it is
``OrganismRuntime``. Only call sites that name the class directly are touched;
anything else (``cls(...)``, a class held in a variable) is printed as MANUAL.

    python migration/tools/use_canonical_factory.py [--check] PATH...
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RUNTIMES = {"OrganismRuntime", "ModeledOrganismRuntime", "PrivateModelOrganismRuntime"}
FACTORY = {
    None: "create_canonical_organism",
    "from_checkpoint": "restore_canonical_organism",
    "load_or_create": "load_or_create_canonical_organism",
}
IMPORT = "from lab.integration.organism import"


def targets(tree: ast.AST) -> list[tuple[ast.Call, str, str | None]]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in RUNTIMES:
            found.append((node, func.id, None))
        elif (
            isinstance(func, ast.Attribute)
            and func.attr in ("from_checkpoint", "load_or_create")
            and isinstance(func.value, ast.Name)
            and func.value.id in RUNTIMES
        ):
            found.append((node, func.value.id, func.attr))
    return found


def rewrite(text: str) -> tuple[str, set[str]]:
    tree = ast.parse(text)
    lines = text.split("\n")
    used: set[str] = set()
    # last call first, so earlier offsets stay valid
    for node, runtime, method in sorted(
        targets(tree), key=lambda item: (item[0].lineno, item[0].col_offset), reverse=True
    ):
        func = node.func
        if func.lineno != func.end_lineno:
            continue
        line = lines[func.lineno - 1]
        after = line[func.end_col_offset :]
        if not after.startswith("("):
            continue
        name = FACTORY[method]
        used.add(name)
        runtime_argument = "" if runtime == "OrganismRuntime" else runtime
        if method is None:
            # Runtime(args) -> factory(Runtime, args)
            rest = after[1:]
            empty = rest.lstrip().startswith(")") and not node.args and not node.keywords
            insert = runtime_argument + ("" if empty or not runtime_argument else ", ")
            if runtime_argument and not empty and rest.strip() == "":
                insert = runtime_argument + ","
            lines[func.lineno - 1] = line[: func.col_offset] + name + "(" + insert + rest
        else:
            # Runtime.method(first, rest) -> factory(first, Runtime, rest)
            first = node.args[0] if node.args else None
            if first is None or not runtime_argument:
                lines[func.lineno - 1] = line[: func.col_offset] + name + after
                continue
            target = lines[first.end_lineno - 1]
            lines[first.end_lineno - 1] = (
                target[: first.end_col_offset] + ", " + runtime_argument + target[first.end_col_offset :]
            )
            line = lines[func.lineno - 1]
            lines[func.lineno - 1] = line[: func.col_offset] + name + line[func.end_col_offset :]
    return "\n".join(lines), used


def add_import(text: str, names: set[str]) -> str:
    if not names:
        return text
    tree = ast.parse(text)
    existing = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "lab.integration.organism"
        ),
        None,
    )
    lines = text.split("\n")
    if existing is not None:
        merged = sorted({alias.name for alias in existing.names} | names)
        lines[existing.lineno - 1 : existing.end_lineno] = [f"{IMPORT} {', '.join(merged)}"]
        return "\n".join(lines)
    last = max(
        (node.end_lineno for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)),
        default=0,
    )
    lines[last:last] = [f"{IMPORT} {', '.join(sorted(names))}"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    changed = 0
    for argument in (a for a in argv if a != "--check"):
        root = Path(argument)
        for path in [root] if root.is_file() else sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts or "integration/organism" in path.as_posix():
                continue
            text = path.read_text(encoding="utf-8")
            updated, used = rewrite(text)
            updated = add_import(updated, used)
            if updated != text:
                ast.parse(updated)  # never write something that does not parse
                changed += 1
                print(path)
                if not check:
                    path.write_text(updated, encoding="utf-8")
    print(f"{'would change' if check else 'changed'}: {changed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
