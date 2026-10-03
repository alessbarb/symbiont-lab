"""One-shot rewrite of legacy root-level path references to the five-domain layout.

Applied once during the migration to tests, scripts, observatory, CI config and
governance policy files;
kept as the executable record of the old-path -> new-path mapping. It is
idempotent: already-rewritten references are not matched again.

Usage: python migration/tools/rewrite_legacy_paths.py [--check] PATH...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# import package -> domain directory that now owns it
DOMAIN = {"symbiont_lab": "lab", "symbiont_world": "environment", "symbiont": "symbiont"}
_PKG = "(symbiont_lab|symbiont_world|symbiont)"

RULES = [
    # Path joins: / "src" / "symbiont_lab"  (possibly split across lines)
    (
        re.compile(r'(?<!"lab" )(?<!"environment" )(?<!"symbiont" )/ "src"(\s*)/ "' + _PKG + r'"'),
        lambda m: f'/ "{DOMAIN[m.group(2)]}" / "src"{m.group(1)}/ "{m.group(2)}"',
    ),
    # String literals and globs: src/symbiont_lab/...
    (
        re.compile(r"(?<![\w/])src/" + _PKG + r"(?![\w])"),
        lambda m: f"{DOMAIN[m.group(1)]}/src/{m.group(1)}",
    ),
]

# experiments/, research/ and examples/ now live under lab/.
_DATA = "(experiments|research|examples)"
RULES += [
    # Path joins off a variable: ROOT / "experiments"  (not "tests" / "experiments")
    (re.compile(r'(?<!" )/ "' + _DATA + r'"'), lambda m: f'/ "lab" / "{m.group(1)}"'),
    # String literals and globs starting a path: "experiments/..."
    (re.compile(r"(?<![\w/.-])" + _DATA + r"/(?=[\w*{$.-])"), lambda m: f"lab/{m.group(1)}/"),
]

SUFFIXES = {".py", ".yml", ".yaml", ".json", ".toml", ".mjs", ".js", ".sh"}


def rewrite(text: str) -> str:
    for pattern, replacement in RULES:
        text = pattern.sub(replacement, text)
    return text


def main(argv: list[str]) -> int:
    check = "--check" in argv
    changed = 0
    for arg in (a for a in argv if a != "--check"):
        root = Path(arg)
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            if path.suffix not in SUFFIXES or "__pycache__" in path.parts:
                continue
            old = path.read_text(encoding="utf-8")
            new = rewrite(old)
            if new != old:
                changed += 1
                print(path)
                if not check:
                    path.write_text(new, encoding="utf-8")
    print(f"{'would change' if check else 'changed'}: {changed} files")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
