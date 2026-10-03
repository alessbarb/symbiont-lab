"""Environment alone: no other first-party library installed or loaded.

    uv venv /tmp/environment-alone && \\
    uv pip install --python /tmp/environment-alone/bin/python ./environment pytest && \\
    /tmp/environment-alone/bin/python -m pytest environment/tests -p no:cacheprovider
"""

from __future__ import annotations

import importlib.util
import sys

from environment.physics3d.environments import ENVIRONMENT_NAMES, environment_recipe
from environment.rng import derive_world_rng

FOREIGN = ("symbiont", "embodiment", "modality", "lab")


def test_no_other_domain_is_installed_or_loaded() -> None:
    assert [name for name in FOREIGN if importlib.util.find_spec(name)] == []
    assert [name for name in sys.modules if name.split(".")[0] in FOREIGN] == []


def test_every_fixture_recipe_resolves() -> None:
    for name in ENVIRONMENT_NAMES:
        assert isinstance(environment_recipe(name), dict)


def test_world_randomness_is_a_function_of_seed_and_stream() -> None:
    assert derive_world_rng(7, "laws").random() == derive_world_rng(7, "laws").random()
    assert derive_world_rng(7, "laws").random() != derive_world_rng(8, "laws").random()
