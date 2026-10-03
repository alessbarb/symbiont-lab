"""Vision body kind: the anthropomorphic body with a head-mounted receptor array (ADR-0011).

Binds the modality's receptor-array channel to a body link and assigns it
opaque receptor ids that extend, without reordering, the v6 receptor contract.
"""

from __future__ import annotations

import random
from collections.abc import Mapping

from embodiment.physics3d.humanoid import (
    INTEROCEPTIVE_RECEPTOR_COUNT,
    PHYSICAL_RECEPTOR_COUNT,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
    interoceptive_receptor_contract_ids,
    physical_receptor_contract_ids,
)
from modality.vision import VISUAL_RECEPTOR_COUNT, VisualApparatus

VISION_BODY_KIND = "anthropomorphic-v6-vision"
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

__all__ = [
    "VISION_BODY_KIND",
    "VISION_TOTAL_RECEPTOR_COUNT",
    "VisionHumanoidPhysics",
    "vision_receptor_contract_ids",
    "visual_receptor_contract_ids",
]
