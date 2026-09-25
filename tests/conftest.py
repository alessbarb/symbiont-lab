"""Repository-wide pytest classification for expensive scientific checks."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep campaign-scale checks out of the everyday test profile."""
    for item in items:
        path = Path(str(item.path)).as_posix()
        slow = (
            "/tests/integration/" in path
            or "/tests/experimental_integrity/" in path
            or "/tests/integration/studies/" in path
            or "/tests/integration/dashboard/" in path
            or path.endswith("test_physics3d_existing_reuse.py")
            or path.endswith("test_private_model_training.py")
        )
        if slow:
            item.add_marker(pytest.mark.slow)
