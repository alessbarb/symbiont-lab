"""Declared ecological resource interactions (v0.71)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Allocation:
    organism_id: str
    resource: str
    requested: float
    granted: float


class EcologicalResourcePool:
    """Finite typed resources with deterministic proportional allocation."""

    def __init__(self, resources: dict[str, float]) -> None:
        if not resources or any(
            not isinstance(k, str)
            or not k
            or len(k) > 64
            or isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or v < 0
            for k, v in resources.items()
        ):
            raise ValueError("invalid ecological resources")
        self._resources = {str(k): float(v) for k, v in resources.items()}

    def allocate(self, requests: list[tuple[str, str, float]]) -> tuple[Allocation, ...]:
        grouped: dict[str, list[tuple[str, float]]] = {}
        for organism_id, resource, amount in requests:
            if (
                not isinstance(organism_id, str)
                or not organism_id
                or len(organism_id) > 128
                or not isinstance(resource, str)
                or not resource
                or resource not in self._resources
                or isinstance(amount, bool)
                or not isinstance(amount, (int, float))
                or not math.isfinite(amount)
                or amount <= 0
            ):
                raise ValueError("invalid resource request")
            grouped.setdefault(resource, []).append((organism_id, float(amount)))
        result: list[Allocation] = []
        for resource, entries in grouped.items():
            total = sum(amount for _, amount in entries)
            available = self._resources[resource]
            factor = min(1.0, available / total) if total else 0.0
            for organism_id, requested in entries:
                result.append(Allocation(organism_id, resource, requested, requested * factor))
            self._resources[resource] = max(0.0, available - min(available, total))
        return tuple(result)

    def replenish(self, resource: str, amount: float) -> None:
        if (
            not isinstance(resource, str)
            or resource not in self._resources
            or isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
            or amount < 0
        ):
            raise ValueError("invalid replenishment")
        self._resources[resource] += amount

    def snapshot(self) -> dict[str, float]:
        return dict(self._resources)

    def checkpoint(self) -> dict[str, object]:
        """Serialize the finite pool without introducing hidden state."""
        return {"schema_version": 1, "resources": self.snapshot()}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "EcologicalResourcePool":
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("invalid resource checkpoint")
        resources = payload.get("resources")
        if not isinstance(resources, dict):
            raise ValueError("invalid resource checkpoint")
        return cls({str(k): float(v) for k, v in resources.items()})


__all__ = ["Allocation", "EcologicalResourcePool"]
