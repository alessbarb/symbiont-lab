"""Finite shared habitat resources for bounded populations (v0.70)."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class HabitatSnapshot:
    habitat_id: str
    population: int
    capacity: int
    available_resources: float


class SharedHabitat:
    SCHEMA_VERSION = 1
    def __init__(self, *, habitat_id: str, capacity: int, resources: float,
                 renewal_rate: float = 0.0, acquisition_cost: float = 1.0,
                 physiological_usefulness: float = 1.0,
                 information_content: float = 0.0) -> None:
        if not habitat_id or capacity < 1 or resources < 0:
            raise ValueError("invalid habitat bounds")
        values = (renewal_rate, acquisition_cost, physiological_usefulness, information_content)
        if (any(isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(float(value)) for value in values)
                or renewal_rate < 0.0
                or not 0.1 <= acquisition_cost <= 16.0
                or not 0.0 <= physiological_usefulness <= 16.0
                or not 0.0 <= information_content <= 1.0):
            raise ValueError("invalid habitat dynamics")
        self.habitat_id, self.capacity = habitat_id, capacity
        self._resources = float(resources)
        # These are physical properties of the surface, not semantic labels.
        # The organism encounters their consequences through intake outcomes.
        self.renewal_rate = float(renewal_rate)
        self.acquisition_cost = float(acquisition_cost)
        self.physiological_usefulness = float(physiological_usefulness)
        self.information_content = float(information_content)
        self._allocations: dict[str, float] = {}

    def has_allocation(self, organism_id: str) -> bool:
        return organism_id in self._allocations

    def admit(self, organism_id: str, units: float) -> bool:
        if not organism_id or units <= 0 or organism_id in self._allocations:
            return False
        if len(self._allocations) >= self.capacity or units > self._resources:
            return False
        self._allocations[organism_id] = float(units); self._resources -= float(units); return True

    def release(self, organism_id: str) -> float:
        units = self._allocations.pop(organism_id, 0.0)
        self._resources += units
        return units

    def consume(self, organism_id: str, amount: float) -> float:
        """Consume physical resource units for an admitted resident.

        ``amount`` is the requested physiological quantum.  Surface-specific
        acquisition cost is applied at the boundary, so scarcity and cost are
        experienced as different granted outcomes rather than instructions.
        """
        if organism_id not in self._allocations or amount <= 0:
            raise ValueError("organism must be admitted and amount positive")
        granted = min(float(amount) * self.acquisition_cost, self._resources)
        self._resources -= granted
        return granted / self.acquisition_cost * self.physiological_usefulness

    def renew(self) -> float:
        """Apply one bounded apparatus-side renewal step and return its amount."""
        if self.renewal_rate <= 0.0:
            return 0.0
        self._resources += self.renewal_rate
        return self.renewal_rate

    def set_environment_resources(self, resources: float) -> None:
        """Replace free resources at an environment boundary.

        This is deliberately not part of the organism API.  A study harness
        may use it to apply a synthetic regime between biological ticks.
        Allocated residency units remain untouched.
        """
        if isinstance(resources, bool) or not isinstance(resources, (int, float)) or not math.isfinite(resources) or resources < 0.0:
            raise ValueError("environment resources must be finite and non-negative")
        self._resources = float(resources)

    def snapshot(self) -> HabitatSnapshot:
        return HabitatSnapshot(self.habitat_id, len(self._allocations), self.capacity, self._resources)

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": self.SCHEMA_VERSION, "habitat_id": self.habitat_id,
                "capacity": self.capacity, "resources": self._resources,
                "renewal_rate": self.renewal_rate,
                "acquisition_cost": self.acquisition_cost,
                "physiological_usefulness": self.physiological_usefulness,
                "information_content": self.information_content,
                "allocations": dict(self._allocations)}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "SharedHabitat":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid habitat checkpoint")
        h = cls(habitat_id=str(payload["habitat_id"]), capacity=int(payload["capacity"]),
                resources=float(payload["resources"]),
                renewal_rate=float(payload.get("renewal_rate", 0.0)),
                acquisition_cost=float(payload.get("acquisition_cost", 1.0)),
                physiological_usefulness=float(payload.get("physiological_usefulness", 1.0)),
                information_content=float(payload.get("information_content", 0.0)))
        h._allocations = {str(k): float(v) for k, v in dict(payload.get("allocations", {})).items()}
        if len(h._allocations) > h.capacity or any(v <= 0 for v in h._allocations.values()):
            raise ValueError("invalid habitat allocations")
        return h

    def restore_checkpoint(self, payload: dict[str, object]) -> None:
        """Restore this external surface in place for a coordinated study resume."""
        restored = type(self).from_checkpoint(payload)
        if restored.habitat_id != self.habitat_id or restored.capacity != self.capacity:
            raise ValueError("habitat checkpoint identity or capacity mismatch")
        self._resources = restored._resources
        self.renewal_rate = restored.renewal_rate
        self.acquisition_cost = restored.acquisition_cost
        self.physiological_usefulness = restored.physiological_usefulness
        self.information_content = restored.information_content
        self._allocations = restored._allocations


__all__ = ["HabitatSnapshot", "SharedHabitat"]
