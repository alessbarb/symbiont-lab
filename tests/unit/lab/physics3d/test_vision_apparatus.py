"""ADR-0011 visual apparatus substrate: contracts that need no physics engine."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from embodiment.physics3d import vision
from embodiment.physics3d.humanoid import receptor_contract_ids
from embodiment.physics3d.vision import (
    vision_receptor_contract_ids,
    visual_receptor_contract_ids,
)
from lab.integration.physics3d.bodies import (
    ANTHROPOMORPHIC_V6,
    ANTHROPOMORPHIC_V6_VISION,
)
from modality import vision as vision_channel
from modality.vision import VISUAL_ARRAY_SIDE, PerceptualTopology


def test_v6_receptor_contract_is_byte_identical() -> None:
    expected = tuple(f"rec.{i}" for i in range(107))
    assert receptor_contract_ids() == expected
    assert ANTHROPOMORPHIC_V6.receptor_ids == expected
    assert ANTHROPOMORPHIC_V6.receptor_count == 107
    assert ANTHROPOMORPHIC_V6.sensory_capacity == 256


def test_visual_ids_are_opaque_new_ordinals_without_layout() -> None:
    ids = visual_receptor_contract_ids()
    assert len(ids) == len(set(ids)) == VISUAL_ARRAY_SIDE**2 == 144
    assert {int(item.removeprefix("rec.")) for item in ids} == set(range(107, 251))
    assert not set(ids) & set(receptor_contract_ids())
    # Position order must not be recoverable from ordinals.
    assert list(ids) != sorted(ids, key=lambda item: int(item.removeprefix("rec.")))
    assert visual_receptor_contract_ids() == ids  # versioned, deterministic


def test_vision_body_contract_matches_reading_provider_order() -> None:
    ids = vision_receptor_contract_ids()
    assert ANTHROPOMORPHIC_V6_VISION.receptor_ids == ids
    assert ANTHROPOMORPHIC_V6_VISION.receptor_count == len(ids) == 251
    assert ids[-4:] == ANTHROPOMORPHIC_V6_VISION.interoceptive_receptor_ids
    # Enough capacity that visual receptors never displace body senses.
    assert ANTHROPOMORPHIC_V6_VISION.sensory_capacity >= 2 * len(ids)


def test_topology_is_symmetric_adjacency_over_opaque_ids_only() -> None:
    ids = visual_receptor_contract_ids()
    topology = PerceptualTopology.grid(ids, VISUAL_ARRAY_SIDE)
    assert set(topology.neighbours) == set(ids)
    degrees = sorted(len(value) for value in topology.neighbours.values())
    assert degrees.count(2) == 4 and degrees[-1] == 4
    for receptor, neighbours in topology.neighbours.items():
        assert receptor not in neighbours
        for other in neighbours:
            assert receptor in topology.neighbours[other]
    flat = repr(topology.as_dict())
    for forbidden in ("row", "col", "depth", "left", "right", "red", "x", "y"):
        assert f"'{forbidden}" not in flat


@pytest.mark.parametrize("module", [vision, vision_channel], ids=["body", "channel"])
def test_visual_apparatus_never_imports_observer_truth(module) -> None:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    modules = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)] + [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    forbidden = ("observation", "world_scene", "world_observation", "observer_semantics", "time")
    for module in modules:
        assert not any(part in module.split(".") for part in forbidden), module
