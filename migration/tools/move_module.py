"""Move a module or package to a new dotted path and rewrite every import of it.

No compatibility shim is left at the old path: importers are rewritten.

    python migration/tools/move_module.py OLD.DOTTED.PATH NEW.DOTTED.PATH [TARGET_SRC_ROOT]
        [--imports-only]

What it rewrites, in all first-party source and tests:

- absolute references to the old dotted path (imports and string literals);
- relative imports of the moved module from its former siblings;
- relative imports inside the moved module, made absolute against the old
  location so they keep pointing at the same modules;
- ``from <old parent> import <name>`` when every imported name is the moved one.

Anything it cannot rewrite safely is printed as ``MANUAL``.
"""

from __future__ import annotations

import ast
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = [
    ROOT / domain / "src" for domain in ("symbiont", "environment", "modality", "embodiment", "lab")
]
SCAN = [*SOURCE_ROOTS, ROOT / "tests", ROOT / "observatory", ROOT / "scripts"]
TEXT_SCAN = [ROOT / "docs" / "governance", ROOT / "pyproject.toml", ROOT / ".github"]


def locate(dotted: str) -> tuple[Path, Path] | None:
    """(source root, path) of an existing module or package."""
    relative = Path(*dotted.split("."))
    for root in [*SOURCE_ROOTS, ROOT]:
        if (root / relative).with_suffix(".py").is_file():
            return root, (root / relative).with_suffix(".py")
        if (root / relative / "__init__.py").is_file():
            return root, root / relative
    return None


def root_for(dotted: str) -> Path:
    top = dotted.split(".")[0]
    for root in SOURCE_ROOTS:
        if (root / top).is_dir():
            return root
    raise SystemExit(f"no source root holds top-level package {top!r}")


def module_name(path: Path) -> tuple[str, bool] | None:
    for root in [*SOURCE_ROOTS, ROOT]:
        if path.is_relative_to(root):
            parts = list(path.relative_to(root).with_suffix("").parts)
            is_package = parts[-1] == "__init__"
            return ".".join(parts[:-1] if is_package else parts), is_package
    return None


def absolute(module: str, is_package: bool, node: ast.ImportFrom) -> str:
    base = module.split(".") if is_package else module.split(".")[:-1]
    base = base[: len(base) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def under(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + ".")


def rewrite_file(
    path: Path, old: str, new: str, moved_files: set[Path], imports_only: bool = False
) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    import_lines: set[int] = set()
    if path.suffix == ".py":
        info = module_name(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if info and tree:
            module, is_package = info
            lines = text.split("\n")
            inside_moved = path in moved_files
            old_parent, _, old_leaf = old.rpartition(".")
            new_parent, _, new_leaf = new.rpartition(".")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    import_lines |= set(range(node.lineno - 1, node.end_lineno))
                if not isinstance(node, ast.ImportFrom):
                    continue
                line = lines[node.lineno - 1]
                target = absolute(module, is_package, node) if node.level else node.module or ""
                names = [alias.name for alias in node.names]
                replacement = None
                if node.level and (under(target, old) != inside_moved):
                    # relative import crossing the boundary of the move: make it absolute
                    replacement = target
                if target == old_parent and old_leaf in names:
                    if names == [old_leaf] and (new_leaf == old_leaf or node.names[0].asname):
                        replacement = new_parent
                        if new_leaf != old_leaf:
                            line = re.sub(rf"\bimport {old_leaf}\b", f"import {new_leaf}", line)
                    else:
                        print(f"MANUAL {path.relative_to(ROOT)}:{node.lineno}: {line.strip()}")
                if replacement is not None:
                    lines[node.lineno - 1] = re.sub(
                        r"^(\s*from\s+)[.\w]+(\s+import\b)",
                        lambda m: f"{m.group(1)}{replacement}{m.group(2)}",
                        line,
                    )
            text = "\n".join(lines)
    pattern = re.compile(rf"(?<![\w.]){re.escape(old)}(?![\w])")
    if imports_only:
        # a common word as module name: touch only import statements and quoted dotted paths
        quoted = re.compile(rf"(?<=[\"'])(?:{re.escape(old)})(?=\.[A-Za-z_])")
        text = "\n".join(
            pattern.sub(new, line) if index in import_lines else quoted.sub(new, line)
            for index, line in enumerate(text.split("\n"))
        )
    else:
        text = pattern.sub(new, text)
        old_file, new_file = old.replace(".", "/"), new.replace(".", "/")
        text = text.replace(old_file + ".py", new_file + ".py").replace(
            old_file + "/", new_file + "/"
        )
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main(argv: list[str]) -> int:
    imports_only = "--imports-only" in argv
    argv = [arg for arg in argv if arg != "--imports-only"]
    if len(argv) not in (2, 3):
        raise SystemExit(__doc__)
    old, new = argv[:2]
    new_root = (ROOT / argv[2]).resolve() if len(argv) == 3 else None
    found = locate(old)
    if found is None:
        raise SystemExit(f"{old} not found")
    old_root, source = found
    is_package = source.is_dir()
    target = (new_root or root_for(new)) / Path(*new.split("."))
    target = target if is_package else target.with_suffix(".py")
    if target.exists():
        raise SystemExit(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    base = new_root or root_for(new)
    package_dir = target.parent
    while package_dir != base:
        (package_dir / "__init__.py").touch(exist_ok=True)
        package_dir = package_dir.parent

    # 1. rewrite relative imports inside the module while it still sits at the old path
    moved_before = set(source.rglob("*.py")) if is_package else {source}
    for path in sorted(moved_before):
        rewrite_file(path, old, old, moved_before, imports_only)
    shutil.move(str(source), str(target))

    # 2. rewrite every importer
    changed = 0
    moved_after = set(target.rglob("*.py")) if is_package else {target}
    files = {p for base in SCAN if base.exists() for p in base.rglob("*.py")}
    files |= {
        p
        for base in TEXT_SCAN
        if base.exists()
        for p in ([base] if base.is_file() else base.rglob("*"))
        if p.is_file() and p.suffix in {".toml", ".yml", ".yaml"}
    }
    for path in sorted(files):
        if "__pycache__" in path.parts:
            continue
        changed += rewrite_file(path, old, new, moved_after, imports_only)
    print(
        f"moved {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}; rewrote {changed} files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
