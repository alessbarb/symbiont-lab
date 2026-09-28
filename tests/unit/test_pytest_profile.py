"""Small boundary checks must remain selectable in the default profile."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("relative_path", "slow"),
    [
        ("integration/test_boundary.py", False),
        ("experimental_integrity/test_boundary.py", False),
        ("integration/studies/test_campaign.py", True),
        ("integration/dashboard/test_server.py", True),
        ("unit/test_private_model_training.py", True),
    ],
)
def test_profile_classifies_cost_not_entire_boundary_layer(relative_path, slow):
    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location("repo_profile", root / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    markers = []
    item = SimpleNamespace(path=root / relative_path, add_marker=markers.append)
    module.pytest_collection_modifyitems([item])
    assert any(marker.name == "slow" for marker in markers) is slow
