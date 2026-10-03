"""The Lab's body catalogue: self-contained bodies plus those the Lab composes.

The vision body is composed here: the embodiment's head mount is filled with
the modality's receptor array.
"""

from __future__ import annotations

from functools import partial

from embodiment.physics3d.bodies import (
    ANTHROPOMORPHIC_V6,
    ASYMMETRIC_V1,
    CRAWLER_V1,
    BodyDescriptor,
    BodyRegistry,
    vision_body_descriptor,
)
from embodiment.physics3d.vision import VisionHumanoidPhysics
from modality.vision import VisualApparatus

ANTHROPOMORPHIC_V6_VISION = vision_body_descriptor(
    partial(VisionHumanoidPhysics, receptor_array_factory=VisualApparatus)
)

DEFAULT_BODY_REGISTRY = BodyRegistry(
    (
        ANTHROPOMORPHIC_V6,
        ANTHROPOMORPHIC_V6_VISION,
        CRAWLER_V1,
        ASYMMETRIC_V1,
    )
)

__all__ = [
    "ANTHROPOMORPHIC_V6",
    "ANTHROPOMORPHIC_V6_VISION",
    "ASYMMETRIC_V1",
    "CRAWLER_V1",
    "BodyDescriptor",
    "BodyRegistry",
    "DEFAULT_BODY_REGISTRY",
]
