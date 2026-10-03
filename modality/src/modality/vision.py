"""Receptor-array vision channel (ADR-0011).

A square array of receptors rigidly mounted on a body link: physics world →
receptor array → bounded luminance per opaque receptor. The channel reads only
simulation state through the deterministic CPU renderer. It never reads
observer geometry, world_scene entities, the presentation camera or wall-clock
time, and it never emits depth, segmentation, entity identity or colour-channel
names. Which link carries the array, where on it, and under which receptor ids
is supplied by whoever mounts it; this module knows no body.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

VISUAL_ARRAY_SIDE = 12
VISUAL_RECEPTOR_COUNT = VISUAL_ARRAY_SIDE * VISUAL_ARRAY_SIDE


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

    def __init__(
        self,
        client_id: int,
        *,
        body_id: int,
        link_index: int,
        receptor_ids: tuple[str, ...],
        mount_offset: tuple[float, float, float],
        gaze_offset: tuple[float, float, float],
        side: int = VISUAL_ARRAY_SIDE,
    ) -> None:
        if len(receptor_ids) != side * side:
            raise ValueError("visual receptor ids must cover the complete array")
        import pybullet

        self.p = pybullet
        self.client_id = client_id
        self.body_id = body_id
        self.link_index = link_index
        self.side = side
        # Mount point and gaze target in the carrying link's frame (metres).
        self.mount_offset = mount_offset
        self.gaze_offset = gaze_offset
        self.receptor_ids = receptor_ids
        self.topology = PerceptualTopology.grid(receptor_ids, side)
        self._projection = pybullet.computeProjectionMatrixFOV(
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
        eye = self._world_point(position, orientation, self.mount_offset)
        target = self._world_point(position, orientation, self.gaze_offset)
        up = self.p.rotateVector(orientation, (0.0, 0.0, 1.0))
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


__all__ = [
    "VISUAL_ARRAY_SIDE",
    "VISUAL_RECEPTOR_COUNT",
    "PerceptualTopology",
    "VisualApparatus",
]
