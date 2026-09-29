"""Repository-wide pytest classification for expensive scientific checks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"


@pytest.fixture(autouse=True, scope="session")
def _ensure_hermetic_checkout_pythonpath() -> None:
    """Ensure all subprocess invocations resolve to this checkout's src/ directory (INF-05)."""
    src_str = str(_SRC_DIR)
    existing = os.environ.get("PYTHONPATH", "")
    if not existing.startswith(src_str):
        os.environ["PYTHONPATH"] = f"{src_str}:{existing}" if existing else src_str


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep campaign-scale checks out of the everyday test profile."""
    for item in items:
        path = Path(str(item.path)).as_posix()
        slow = (
            "/tests/integration/studies/" in path
            or "/tests/integration/dashboard/" in path
            or path.endswith("test_physics3d_existing_reuse.py")
            or path.endswith("test_private_model_training.py")
        )
        if slow:
            item.add_marker(pytest.mark.slow)
