"""Causal visual apparatus (ADR-0011).

Physics world → head-mounted receptor array → bounded luminance per opaque
receptor. The apparatus reads only simulation state through the deterministic
CPU renderer. It never reads observer geometry, world_scene entities, the
presentation camera or wall-clock time, and it never emits depth,
segmentation, entity identity or colour-channel names.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass

from .humanoid import (
    INTEROCEPTIVE_RECEPTOR_COUNT,
    PHYSICAL_RECEPTOR_COUNT,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
    interoceptive_receptor_contract_ids,
    physical_receptor_contract_ids,
)

VISION_BODY_KIND = "anthropomorphic-v6-vision"
VISUAL_ARRAY_SIDE = 12
VISUAL_RECEPTOR_COUNT = VISUAL_ARRAY_SIDE * VISUAL_ARRAY_SIDE
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


@dataclass(frozen=True, slots=True)
class PerceptualTopology:
    """Physical receptor adjacency as neighbour lists over opaque ids only."""

    neighbours: Mapping[str, tuple[str, ...]]

    @classmethod
    def grid(cls, ids_by_position: tuple[str, ...], side: int) -> PerceptualTopology:
        neighbours: dict[str, tuple[str, ...]] = {}
        for index, receptor_id in enumerate(ids_by_position):
            row, col = divmod(index, side)
            adjacent = [
                ids_by_position[r * side + c]
                for r, c in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
                if 0 <= r < side and 0 <= c < side
            ]
            neighbours[receptor_id] = tuple(sorted(adjacent))
        return cls(neighbours=dict(sorted(neighbours.items())))

    def as_dict(self) -> dict[str, list[str]]:
        return {key: list(value) for key, value in self.neighbours.items()}


class VisualApparatus:
    """One receptor array rigidly mounted on a body link."""

    FIELD_OF_VIEW_DEG = 70.0
    NEAR = 0.02
    FAR = 8.0
    # Mount point and gaze in the link frame (metres): just outside the head
    # surface, looking along the link's +x axis, slightly downward.
    MOUNT_OFFSET = (0.12, 0.0, 0.14)
    GAZE_OFFSET = (1.0, 0.0, -0.1)

    def __init__(
        self,
        pybullet_module,
        client_id: int,
        *,
        body_id: int,
        link_index: int,
        receptor_ids: tuple[str, ...],
        side: int = VISUAL_ARRAY_SIDE,
    ) -> None:
        if len(receptor_ids) != side * side:
            raise ValueError("visual receptor ids must cover the complete array")
        self.p = pybullet_module
        self.client_id = client_id
        self.body_id = body_id
        self.link_index = link_index
        self.side = side
        self.receptor_ids = receptor_ids
        self.topology = PerceptualTopology.grid(receptor_ids, side)
        self._projection = pybullet_module.computeProjectionMatrixFOV(
            self.FIELD_OF_VIEW_DEG, 1.0, self.NEAR, self.FAR
        )
        # Observer correlation key (gap §25); never an organism signal.
        self.sample_index = 0

    def _link_pose(self):
        state = self.p.getLinkState(
            self.body_id,
            self.link_index,
            computeForwardKinematics=True,
            physicsClientId=self.client_id,
        )
        return state[4], state[5]

    def _world_point(self, position, orientation, offset):
        point, _ = self.p.multiplyTransforms(
            position, orientation, offset, (0.0, 0.0, 0.0, 1.0), physicsClientId=self.client_id
        )
        return point

    def sample(self) -> dict[str, float]:
        position, orientation = self._link_pose()
        eye = self._world_point(position, orientation, self.MOUNT_OFFSET)
        target = self._world_point(position, orientation, self.GAZE_OFFSET)
        up = (
            self.p.rotateVector(orientation, (0.0, 0.0, 1.0))
            if hasattr(self.p, "rotateVector")
            else _rotate(orientation, (0.0, 0.0, 1.0))
        )
        view = self.p.computeViewMatrix(eye, target, up)
        _w, _h, rgba, _depth, _seg = self.p.getCameraImage(
            self.side,
            self.side,
            viewMatrix=view,
            projectionMatrix=self._projection,
            renderer=self.p.ER_TINY_RENDERER,
            flags=self.p.ER_NO_SEGMENTATION_MASK,
            physicsClientId=self.client_id,
        )
        flat = [int(value) for value in _flatten(rgba)]
        values = {}
        for index, receptor_id in enumerate(self.receptor_ids):
            r, g, b = flat[index * 4], flat[index * 4 + 1], flat[index * 4 + 2]
            values[receptor_id] = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        self.sample_index += 1
        return values


def _flatten(values):
    try:
        return values.reshape(-1).tolist()  # numpy build of pybullet
    except AttributeError:
        return list(values)


def _rotate(quaternion, vector):
    x, y, z, w = quaternion
    vx, vy, vz = vector
    # v' = v + 2w(q×v) + 2q×(q×v)
    cx, cy, cz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
    cx2, cy2, cz2 = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (vx + 2 * (w * cx + cx2), vy + 2 * (w * cy + cy2), vz + 2 * (w * cz + cz2))


class VisionHumanoidPhysics(HumanoidPhysics):
    """anthropomorphic-v6 plus one head-mounted visual receptor array."""

    def __init__(self, pybullet_module, client_id: int, **kwargs) -> None:
        super().__init__(pybullet_module, client_id, **kwargs)
        self.visual_apparatus = VisualApparatus(
            pybullet_module,
            client_id,
            body_id=self.body_id,
            link_index=self._link_index_by_name["head"],
            receptor_ids=visual_receptor_contract_ids(),
        )
        self.receptor_ids = self.physical_receptor_ids + self.visual_apparatus.receptor_ids

    def sample_receptors(self) -> Mapping[str, float]:
        values = dict(super().sample_receptors())
        values.update(self.visual_apparatus.sample())
        self._sensor_values = values
        return dict(values)


assert PHYSICAL_RECEPTOR_COUNT + INTEROCEPTIVE_RECEPTOR_COUNT == TOTAL_RECEPTOR_COUNT
assert not math.isnan(VisualApparatus.FIELD_OF_VIEW_DEG)

__all__ = [
    "VISION_BODY_KIND",
    "VISION_TOTAL_RECEPTOR_COUNT",
    "VISUAL_ARRAY_SIDE",
    "VISUAL_RECEPTOR_COUNT",
    "PerceptualTopology",
    "VisionHumanoidPhysics",
    "VisualApparatus",
    "vision_receptor_contract_ids",
    "visual_receptor_contract_ids",
]
