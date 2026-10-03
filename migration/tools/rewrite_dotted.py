"""Rewrite references to dotted module paths without moving files.

Used to retire import aliases: every importer of ``OLD`` is pointed at ``NEW``.

    python migration/tools/rewrite_dotted.py mapping.json   # {"old.path": "new.path", ...}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import move_module  # noqa: E402


def main(argv: list[str]) -> int:
    mapping: dict[str, str] = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    files = sorted(
        path
        for base in move_module.SCAN
        if base.exists()
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    touched: set[Path] = set()
    # longest old path first, so a prefix alias never pre-empts a longer one
    for old, new in sorted(mapping.items(), key=lambda item: -len(item[0])):
        for path in files:
            if move_module.rewrite_file(path, old, new, set()):
                touched.add(path)
    print(f"rewrote {len(touched)} files for {len(mapping)} paths")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
