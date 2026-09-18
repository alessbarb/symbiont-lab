from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any


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

    def __post_init__(self) -> None:
        if not self.mutation_id or not self.sensor_id:
            raise ValueError("mutation_id and sensor_id are required")
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("mutation tick must be a non-negative integer")
        if len(set(self.parent_ids)) != len(self.parent_ids):
            raise ValueError("mutation parent ids must be unique")
        for digest in (self.pre_digest, self.post_digest):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("mutation digests must be SHA-256 hex")
        if isinstance(self.cost, bool) or not isinstance(self.cost, (int, float)) or not math.isfinite(float(self.cost)) or self.cost < 0.0:
            raise ValueError("mutation cost must be finite and non-negative")

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> "SensoryMutation":
        if not isinstance(payload, dict):
            raise ValueError("sensory mutation checkpoint entry must be an object")
        return cls(
            mutation_id=str(payload["mutation_id"]),
            tick=int(payload["tick"]),
            sensor_id=str(payload["sensor_id"]),
            parent_ids=tuple(str(item) for item in payload.get("parent_ids", ())),
            kind=SensoryMutationKind(payload["kind"]),
            pre_digest=str(payload["pre_digest"]),
            post_digest=str(payload["post_digest"]),
            cost=float(payload["cost"]),
        )
