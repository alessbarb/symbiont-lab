"""Repair relative markdown links broken by the move to the five-domain layout.

For every broken local link it reconstructs the target as it was in the old
layout (resolving the link from the file's old location), maps that old path to
its new location, and rewrites the link relative to the file's new location.
Links whose target no longer exists anywhere are reported, not touched.
Files inside completed experiments (a ``results.json`` ancestor) are never edited.

Usage: python migration/tools/fix_markdown_links.py [--check] [--delink-missing]
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# old repo-relative prefix -> new repo-relative prefix (longest first)
MOVES = [
    # documentation owned by the organism (longest new prefix first)
    ("docs/explanation", "symbiont/docs/explanation"),
    ("docs/symbiont", "symbiont/docs"),
    # original layout
    ("src/symbiont_lab/physics3d/humanoid.py", "embodiment/src/embodiment/physics3d/humanoid.py"),
    ("src/symbiont_lab/physics3d/vision.py", "embodiment/src/embodiment/physics3d/vision.py"),
    ("src/symbiont_lab", "lab/src/lab"),
    ("src/symbiont_world", "environment/src/environment"),
    ("src/symbiont", "symbiont/src/symbiont"),
    ("observatory", "lab/src/lab/observatory"),
    ("experiments", "lab/experiments"),
    ("research", "lab/research"),
    ("examples", "lab/examples"),
    # intermediate layout (before the packages took their domain names)
    (
        "lab/src/symbiont_lab/physics3d/humanoid.py",
        "embodiment/src/embodiment/physics3d/humanoid.py",
    ),
    ("lab/src/symbiont_lab/physics3d/vision.py", "embodiment/src/embodiment/physics3d/vision.py"),
    ("lab/src/symbiont_lab", "lab/src/lab"),
    ("environment/src/symbiont_world", "environment/src/environment"),
]
SKIP_DIRS = {".git", ".venv", "node_modules", "graphify-out", ".remember", ".claude", ".agents"}
LINK = re.compile(r"(\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
FENCE = re.compile(r"^\s*```")


def to_new(old: str) -> str:
    for before, after in MOVES:
        if old == before or old.startswith(before + "/"):
            return after + old[len(before) :]
    return old


def to_old(new: str) -> str:
    for before, after in MOVES:
        if new == after or new.startswith(after + "/"):
            return before + new[len(after) :]
    return new


def frozen(path: Path) -> bool:
    return any((parent / "results.json").is_file() for parent in path.parents if parent != ROOT)


def markdown_files() -> list[Path]:
    found = []
    for directory, names, files in os.walk(ROOT):
        names[:] = [name for name in names if name not in SKIP_DIRS]
        found += [Path(directory) / name for name in files if name.endswith(".md")]
    return sorted(found)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    delink = "--delink-missing" in argv
    fixed = unresolved = skipped_frozen = 0
    for path in markdown_files():
        relative = path.relative_to(ROOT).as_posix()
        old_dir = (ROOT / to_old(relative)).parent
        in_fence = False
        lines = path.read_text(encoding="utf-8").split("\n")
        changed = False
        for index, line in enumerate(lines):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            def repair(match: re.Match[str]) -> str:
                nonlocal fixed, unresolved, skipped_frozen, changed
                target, _, anchor = match.group(2).partition("#")
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                    return match.group(0)
                if (path.parent / target).exists():
                    return match.group(0)
                old_target = Path(os.path.normpath(old_dir / target))
                if not old_target.is_relative_to(ROOT):
                    unresolved += 1
                    return match.group(0)
                new_target = ROOT / to_new(old_target.relative_to(ROOT).as_posix())
                if not new_target.exists():
                    unresolved += 1
                    print(f"UNRESOLVED {relative}:{index + 1}: {match.group(2)}")
                    if delink and not frozen(path):
                        changed = True
                        return "]\x00"  # marker, cleaned below
                    return match.group(0)
                if frozen(path):
                    skipped_frozen += 1
                    return match.group(0)
                fixed += 1
                changed = True
                link = os.path.relpath(new_target, path.parent)
                return f"{match.group(1)}{link}{'#' + anchor if anchor else ''}{match.group(3)}"

            repaired = LINK.sub(repair, line)
            # a link whose target was deleted becomes plain text
            lines[index] = re.sub(r"\[([^\]]*)\]\x00", r"\1", repaired) if delink else repaired
        if changed and not check:
            path.write_text("\n".join(lines), encoding="utf-8")
    verb = "would fix" if check else "fixed"
    print(
        f"{verb}: {fixed}  unresolved: {unresolved}  left in frozen experiments: {skipped_frozen}"
    )
    return 1 if check and (fixed or unresolved) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
