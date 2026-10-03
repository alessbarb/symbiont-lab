"""Modality alone: no other first-party library installed or loaded.

    uv venv /tmp/modality-alone && \\
    uv pip install --python /tmp/modality-alone/bin/python ./modality pytest && \\
    /tmp/modality-alone/bin/python -m pytest modality/tests -p no:cacheprovider
"""

from __future__ import annotations

import importlib.util
import sys

from modality.vision import VISUAL_ARRAY_SIDE, PerceptualTopology

FOREIGN = ("symbiont", "embodiment", "environment", "lab")


def test_no_other_domain_is_installed_or_loaded() -> None:
    assert [name for name in FOREIGN if importlib.util.find_spec(name)] == []
    assert [name for name in sys.modules if name.split(".")[0] in FOREIGN] == []


def test_receptor_adjacency_is_over_opaque_ids_only() -> None:
    ids = tuple(f"r{index}" for index in range(VISUAL_ARRAY_SIDE * VISUAL_ARRAY_SIDE))
    topology = PerceptualTopology.grid(ids, VISUAL_ARRAY_SIDE)
    assert set(topology.neighbours) == set(ids)
    assert topology.neighbours["r0"] == ("r1", f"r{VISUAL_ARRAY_SIDE}")
    assert all(2 <= len(adjacent) <= 4 for adjacent in topology.neighbours.values())
