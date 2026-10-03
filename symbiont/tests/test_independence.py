"""The organism alone: installable, importable and persistable with nothing else.

Run in an environment that contains only the ``symbiont`` distribution:

    uv venv /tmp/symbiont-alone && \\
    uv pip install --python /tmp/symbiont-alone/bin/python ./symbiont pytest && \\
    /tmp/symbiont-alone/bin/python -m pytest symbiont/tests -p no:cacheprovider
"""

from __future__ import annotations

import importlib.util
import sys

from symbiont import api

FOREIGN = ("symbiont_lab", "symbiont_world", "observatory", "pybullet", "torch", "numpy", "PIL")


def test_nothing_outside_the_organism_is_installed_or_loaded() -> None:
    assert [name for name in FOREIGN if importlib.util.find_spec(name)] == []
    assert [name for name in sys.modules if name.split(".")[0] in FOREIGN] == []


def test_create_run_save_load_preserves_identity(tmp_path) -> None:
    organism = api.OrganismRuntime(min_samples=1, investigate_ticks=0)
    organism.run(3)
    path = tmp_path / "organism.json"
    organism.save(path)

    payload = api.load_checkpoint_file(path)
    api.verify_checkpoint_identity(payload)
    restored = api.OrganismRuntime.load_or_create(path, min_samples=1, investigate_ticks=0)

    assert restored.state_hash() == organism.state_hash()
    assert api.checkpoint_state_hash(payload) == organism.state_hash()
    restored.run(1)
    assert [name for name in sys.modules if name.split(".")[0] in FOREIGN] == []
