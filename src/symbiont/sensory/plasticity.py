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
        if not isinstance(self.mutation_id, str) or not self.mutation_id:
            raise ValueError("mutation_id must be a non-empty string")
        if not isinstance(self.sensor_id, str) or not self.sensor_id:
            raise ValueError("sensor_id must be a non-empty string")
        if not isinstance(self.kind, SensoryMutationKind):
            raise ValueError("kind must be a SensoryMutationKind")
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("mutation tick must be a non-negative integer")
        if len(set(self.parent_ids)) != len(self.parent_ids):
            raise ValueError("mutation parent ids must be unique")
        if any(not isinstance(item, str) or not item for item in self.parent_ids):
            raise ValueError("mutation parent ids must be non-empty strings")
        for digest in (self.pre_digest, self.post_digest):
            if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("mutation digests must be SHA-256 hex")
        if isinstance(self.cost, bool) or not isinstance(self.cost, (int, float)) or not math.isfinite(float(self.cost)) or self.cost < 0.0:
            raise ValueError("mutation cost must be finite and non-negative")

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> "SensoryMutation":
        if not isinstance(payload, dict):
            raise ValueError("sensory mutation checkpoint entry must be an object")
        required = ("mutation_id", "tick", "sensor_id", "kind", "pre_digest", "post_digest", "cost")
        if any(key not in payload for key in required):
            raise ValueError("sensory mutation checkpoint is missing required fields")
        parents = payload.get("parent_ids", ())
        if not isinstance(parents, (list, tuple)):
            raise ValueError("mutation parent_ids must be an array")
        if any(not isinstance(item, str) or not item for item in parents):
            raise ValueError("mutation parent ids must be non-empty strings")
        return cls(
            mutation_id=payload["mutation_id"],
            tick=payload["tick"],
            sensor_id=payload["sensor_id"],
            parent_ids=tuple(parents),
            kind=SensoryMutationKind(payload["kind"]),
            pre_digest=payload["pre_digest"],
            post_digest=payload["post_digest"],
            cost=payload["cost"],
        )
