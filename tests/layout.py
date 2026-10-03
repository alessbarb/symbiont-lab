"""Where first-party source lives in the five-domain layout.

The organism, the environment and the lab are separate source roots. Tests that
scan or locate source by package-relative path go through here rather than
assuming one ``src/`` directory.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = tuple(
    ROOT / domain / "src" for domain in ("symbiont", "environment", "modality", "embodiment", "lab")
)
PYTHONPATH = os.pathsep.join(str(root) for root in SOURCE_ROOTS)


def source_files() -> list[Path]:
    """First-party source modules; tests packaged beside the source are not source."""
    return sorted(
        path
        for root in SOURCE_ROOTS
        for path in root.rglob("*.py")
        if "tests" not in path.relative_to(root).parts
    )


def package_relative(path: Path) -> Path:
    """``symbiont/src/symbiont/core/x.py`` -> ``symbiont/core/x.py``."""
    for root in SOURCE_ROOTS:
        if path.is_relative_to(root):
            return path.relative_to(root)
    raise ValueError(f"{path} is not under a source root")


def package_path(relative: str | Path) -> Path:
    """``symbiont/core/x.py`` -> its location under the owning source root."""
    relative = Path(relative)
    for root in SOURCE_ROOTS:
        if (root / relative.parts[0]).is_dir():
            return root / relative
    raise ValueError(f"no source root owns {relative}")
