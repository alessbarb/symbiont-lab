from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SensoryMutationKind(StrEnum):
    PARAMETER_ADJUST = "parameter_adjust"
    DUPLICATE = "duplicate"
    PARAMETER_DIVERGE = "parameter_diverge"
    SOURCE_REWIRE = "source_rewire"
    PRUNE = "prune"


@dataclass(slots=True, frozen=True)
class SensoryMutation:
    mutation_id: str
    tick: int
    sensor_id: str
    parent_ids: tuple[str, ...]
    kind: SensoryMutationKind
    pre_digest: str
    post_digest: str
    cost: float
