"""Vision body kind: the anthropomorphic body with a head mount for a receptor array (ADR-0011).

The body owns the mount: which link carries the array, where on it, how many
receptor slots it has and their opaque ids, which extend the v6 receptor
contract without reordering it. What fills the mount and produces the values is
supplied from outside as ``receptor_array_factory``.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from typing import Any

from embodiment.physics3d.humanoid import (
    INTEROCEPTIVE_RECEPTOR_COUNT,
    PHYSICAL_RECEPTOR_COUNT,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
    interoceptive_receptor_contract_ids,
    physical_receptor_contract_ids,
)

VISION_BODY_KIND = "anthropomorphic-v6-vision"
# The head mount: a square of receptor slots, just outside the head surface,
# looking along the head link's +x axis, slightly downward (link frame, metres).
VISUAL_ARRAY_SIDE = 12
VISUAL_RECEPTOR_COUNT = VISUAL_ARRAY_SIDE * VISUAL_ARRAY_SIDE
HEAD_MOUNT_LINK = "head"
HEAD_MOUNT_OFFSET = (0.12, 0.0, 0.14)
HEAD_MOUNT_GAZE_OFFSET = (1.0, 0.0, -0.1)
VISION_TOTAL_RECEPTOR_COUNT = TOTAL_RECEPTOR_COUNT + VISUAL_RECEPTOR_COUNT
# Versioned constitution of the position → opaque ordinal permutation.
_VISUAL_PERMUTATION_SEED = 0x5EE1


def _visual_permutation() -> tuple[int, ...]:
    order = list(range(VISUAL_RECEPTOR_COUNT))
    random.Random(_VISUAL_PERMUTATION_SEED).shuffle(order)
    return tuple(order)


def visual_receptor_contract_ids() -> tuple[str, ...]:
    """Opaque ids in array-position order; ordinals do not reveal layout."""
    return tuple(f"rec.{TOTAL_RECEPTOR_COUNT + ordinal}" for ordinal in _visual_permutation())


def vision_receptor_contract_ids() -> tuple[str, ...]:
    """Reading-provider order: apparatus receptors, then interoception."""
    return (
        physical_receptor_contract_ids()
        + visual_receptor_contract_ids()
        + interoceptive_receptor_contract_ids()
    )


class VisionHumanoidPhysics(HumanoidPhysics):
    """anthropomorphic-v6 plus one head-mounted receptor array.

    ``receptor_array_factory(client_id, *, body_id, link_index,
    receptor_ids, mount_offset, gaze_offset, side)`` must return an object with
    ``receptor_ids`` and ``sample() -> Mapping[str, float]``.
    """

    def __init__(
        self,
        client_id: int,
        *,
        receptor_array_factory: Callable[..., Any],
        **kwargs,
    ) -> None:
        super().__init__(client_id, **kwargs)
        self.visual_apparatus = receptor_array_factory(
            client_id,
            body_id=self.body_id,
            link_index=self._link_index_by_name[HEAD_MOUNT_LINK],
            receptor_ids=visual_receptor_contract_ids(),
            mount_offset=HEAD_MOUNT_OFFSET,
            gaze_offset=HEAD_MOUNT_GAZE_OFFSET,
            side=VISUAL_ARRAY_SIDE,
        )
        self.receptor_ids = self.physical_receptor_ids + self.visual_apparatus.receptor_ids

    def sample_receptors(self) -> Mapping[str, float]:
        values = dict(super().sample_receptors())
        values.update(self.visual_apparatus.sample())
        self._sensor_values = values
        return dict(values)


assert PHYSICAL_RECEPTOR_COUNT + INTEROCEPTIVE_RECEPTOR_COUNT == TOTAL_RECEPTOR_COUNT

__all__ = [
    "HEAD_MOUNT_GAZE_OFFSET",
    "HEAD_MOUNT_LINK",
    "HEAD_MOUNT_OFFSET",
    "VISION_BODY_KIND",
    "VISUAL_ARRAY_SIDE",
    "VISUAL_RECEPTOR_COUNT",
    "VISION_TOTAL_RECEPTOR_COUNT",
    "VisionHumanoidPhysics",
    "vision_receptor_contract_ids",
    "visual_receptor_contract_ids",
]
