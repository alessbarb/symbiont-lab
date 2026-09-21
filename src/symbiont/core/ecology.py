"""Finite shared physical resources with independent population capacity."""
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
    """External resource surface with membership independent of physical stock."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        habitat_id: str,
        capacity: int,
        resources: float,
        renewal_rate: float = 0.0,
        acquisition_cost: float = 1.0,
        physiological_usefulness: float = 1.0,
        information_content: float = 0.0,
    ) -> None:
        if not habitat_id or capacity < 1 or resources < 0:
            raise ValueError("invalid habitat bounds")
        values = (
            renewal_rate,
            acquisition_cost,
            physiological_usefulness,
            information_content,
        )
        if (
            any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in values
            )
            or renewal_rate < 0.0
            or not 0.1 <= acquisition_cost <= 16.0
            or not 0.0 <= physiological_usefulness <= 16.0
            or not 0.0 <= information_content <= 1.0
        ):
            raise ValueError("invalid habitat dynamics")
        self.habitat_id = habitat_id
        self.capacity = capacity
        self._resources = float(resources)
        self.renewal_rate = float(renewal_rate)
        self.acquisition_cost = float(acquisition_cost)
        self.physiological_usefulness = float(physiological_usefulness)
        self.information_content = float(information_content)
        self._members: set[str] = set()

    def has_allocation(self, organism_id: str) -> bool:
        """Compatibility-neutral name for membership presence."""
        return organism_id in self._members

    def admit(self, organism_id: str) -> bool:
        """Reserve one population slot without consuming physical resource."""
        if not organism_id or organism_id in self._members:
            return False
        if len(self._members) >= self.capacity:
            return False
        self._members.add(organism_id)
        return True

    def release(self, organism_id: str) -> bool:
        """Release one population slot without creating physical resource."""
        if organism_id not in self._members:
            return False
        self._members.remove(organism_id)
        return True

    def consume(self, organism_id: str, amount: float) -> float:
        """Consume physical resource units for one admitted resident."""
        if organism_id not in self._members or amount <= 0:
            raise ValueError("organism must be admitted and amount positive")
        granted = min(float(amount) * self.acquisition_cost, self._resources)
        self._resources -= granted
        return granted / self.acquisition_cost * self.physiological_usefulness

    def renew(self) -> float:
        """Apply one explicit world-side source term."""
        if self.renewal_rate <= 0.0:
            return 0.0
        self._resources += self.renewal_rate
        return self.renewal_rate

    def set_environment_resources(self, resources: float) -> None:
        if (
            isinstance(resources, bool)
            or not isinstance(resources, (int, float))
            or not math.isfinite(resources)
            or resources < 0.0
        ):
            raise ValueError("environment resources must be finite and non-negative")
        self._resources = float(resources)

    def snapshot(self) -> HabitatSnapshot:
        return HabitatSnapshot(
            self.habitat_id,
            len(self._members),
            self.capacity,
            self._resources,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "habitat_id": self.habitat_id,
            "capacity": self.capacity,
            "resources": self._resources,
            "renewal_rate": self.renewal_rate,
            "acquisition_cost": self.acquisition_cost,
            "physiological_usefulness": self.physiological_usefulness,
            "information_content": self.information_content,
            "members": sorted(self._members),
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "SharedHabitat":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid habitat checkpoint")
        habitat = cls(
            habitat_id=str(payload["habitat_id"]),
            capacity=int(payload["capacity"]),
            resources=float(payload["resources"]),
            renewal_rate=float(payload.get("renewal_rate", 0.0)),
            acquisition_cost=float(payload.get("acquisition_cost", 1.0)),
            physiological_usefulness=float(payload.get("physiological_usefulness", 1.0)),
            information_content=float(payload.get("information_content", 0.0)),
        )
        raw_members = payload.get("members", [])
        if (
            not isinstance(raw_members, list)
            or len(raw_members) > habitat.capacity
            or any(not isinstance(item, str) or not item for item in raw_members)
            or len(set(raw_members)) != len(raw_members)
        ):
            raise ValueError("invalid habitat members")
        habitat._members = set(raw_members)
        return habitat

    def restore_checkpoint(self, payload: dict[str, object]) -> None:
        restored = type(self).from_checkpoint(payload)
        if restored.habitat_id != self.habitat_id or restored.capacity != self.capacity:
            raise ValueError("habitat checkpoint identity or capacity mismatch")
        self._resources = restored._resources
        self.renewal_rate = restored.renewal_rate
        self.acquisition_cost = restored.acquisition_cost
        self.physiological_usefulness = restored.physiological_usefulness
        self.information_content = restored.information_content
        self._members = restored._members


__all__ = ["HabitatSnapshot", "SharedHabitat"]
