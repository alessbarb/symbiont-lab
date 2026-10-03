"""Embodiment alone: no other first-party library installed or loaded.

    uv venv /tmp/embodiment-alone && \\
    uv pip install --python /tmp/embodiment-alone/bin/python ./embodiment pytest && \\
    /tmp/embodiment-alone/bin/python -m pytest embodiment/tests -p no:cacheprovider
"""

from __future__ import annotations

import importlib.util
import sys

from embodiment.physics3d.bodies import (
    ANTHROPOMORPHIC_V6,
    ASYMMETRIC_V1,
    CRAWLER_V1,
    BodyRegistry,
    vision_body_descriptor,
)
from embodiment.physics3d.vision import VISUAL_RECEPTOR_COUNT, visual_receptor_contract_ids

FOREIGN = ("symbiont", "modality", "environment", "lab")


def test_no_other_domain_is_installed_or_loaded() -> None:
    assert [name for name in FOREIGN if importlib.util.find_spec(name)] == []
    assert [name for name in sys.modules if name.split(".")[0] in FOREIGN] == []


def test_body_contracts_are_complete_without_any_other_domain() -> None:
    registry = BodyRegistry((ANTHROPOMORPHIC_V6, CRAWLER_V1, ASYMMETRIC_V1))
    for descriptor in registry.list():
        assert len(descriptor.receptor_ids) == descriptor.receptor_count
        assert len(set(descriptor.receptor_ids)) == descriptor.receptor_count
        assert len(descriptor.effector_ids) == descriptor.effector_count


def test_vision_body_extends_the_v6_contract_and_leaves_the_array_to_the_caller() -> None:
    descriptor = vision_body_descriptor(lambda _pybullet, _client: None)
    visual = visual_receptor_contract_ids()
    assert len(visual) == len(set(visual)) == VISUAL_RECEPTOR_COUNT
    assert not set(visual) & set(ANTHROPOMORPHIC_V6.receptor_ids)
    assert descriptor.receptor_count == ANTHROPOMORPHIC_V6.receptor_count + VISUAL_RECEPTOR_COUNT
