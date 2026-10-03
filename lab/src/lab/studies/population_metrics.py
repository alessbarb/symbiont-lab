"""Bounded evaluator-side population measurements for ecological studies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PopulationSnapshot:
    tick: int
    population: int
    births: int
    deaths: int
    resource_use: float
    cooperation: int
    competition: int


class PopulationMetrics:
    """Records study labels outside ``symbiont`` cognition."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._snapshots: list[PopulationSnapshot] = []

    def record(
        self,
        *,
        tick: int,
        population: int,
        births: int = 0,
        deaths: int = 0,
        resource_use: float = 0.0,
        cooperation: int = 0,
        competition: int = 0,
    ) -> PopulationSnapshot:
        if (
            tick < 0
            or (self._snapshots and tick <= self._snapshots[-1].tick)
            or not 0 <= population <= self.capacity
            or min(births, deaths, cooperation, competition) < 0
            or resource_use < 0
        ):
            raise ValueError("invalid population observation")
        snapshot = PopulationSnapshot(
            tick, population, births, deaths, float(resource_use), cooperation, competition
        )
        self._snapshots.append(snapshot)
        return snapshot

    def snapshots(self) -> tuple[PopulationSnapshot, ...]:
        return tuple(self._snapshots)

    @property
    def extinct(self) -> bool:
        return bool(self._snapshots) and self._snapshots[-1].population == 0


__all__ = ["PopulationMetrics", "PopulationSnapshot"]
