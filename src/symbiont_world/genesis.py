"""GroundTruth container and WorldEnvironment: real field/resource dynamics
(docs/design/symbiont-world-v1.md §13).

symbiont_world never loads TOML or knows about `experiments/`; a caller
(symbiont_lab, in a later increment) constructs GroundTruth from
world-ground-truth.toml and injects it here. Only opaque FieldId/ResourceId
strings and generic numeric laws ever reach this module -- no domain names.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from .topology import HexCoord

FieldId = str
ResourceId = str
HazardId = str


@dataclass(frozen=True, slots=True)
class GroundTruth:
    fields: Mapping[FieldId, PeriodicFieldLaw] = field(default_factory=dict)
    resources: Mapping[ResourceId, ResourceLaw] = field(default_factory=dict)
    hazards: Mapping[HazardId, HazardLaw] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "resources", MappingProxyType(dict(self.resources)))
        object.__setattr__(self, "hazards", MappingProxyType(dict(self.hazards)))


class WorldEnvironment:
    """Mutable runtime state derived from a frozen GroundTruth: current
    field values (spatially uniform in W2) and per-cell resource pools,
    materialized lazily on first access."""

    def __init__(self, ground_truth: GroundTruth) -> None:
        self.ground_truth = ground_truth
        self._field_values: dict[FieldId, float] = {}
        self._resource_pools: dict[HexCoord, dict[ResourceId, float]] = {}

    def propagate_fields(self, tick: int) -> None:
        self._field_values = {
            field_id: law.value_at(tick) for field_id, law in self.ground_truth.fields.items()
        }

    def field_values(self) -> Mapping[FieldId, float]:
        return MappingProxyType(dict(self._field_values))

    def is_materialized(self, cell: HexCoord) -> bool:
        return cell in self._resource_pools

    def _pool(self, cell: HexCoord) -> dict[ResourceId, float]:
        if cell not in self._resource_pools:
            self._resource_pools[cell] = {
                resource_id: law.initial_quantity
                for resource_id, law in self.ground_truth.resources.items()
            }
        return self._resource_pools[cell]

    def resource_pool(self, cell: HexCoord) -> Mapping[ResourceId, float]:
        return MappingProxyType(dict(self._pool(cell)))

    def renew_resources(self, cell: HexCoord) -> None:
        pool = self._pool(cell)
        for resource_id, law in self.ground_truth.resources.items():
            pool[resource_id] = law.step(pool.get(resource_id, law.initial_quantity))

    def acquire(self, cell: HexCoord, resource_id: ResourceId, requested: float) -> float:
        if requested < 0:
            raise ValueError("requested quantity must be non-negative")
        pool = self._pool(cell)
        available = pool.get(resource_id, 0.0)
        granted = min(requested, available)
        pool[resource_id] = available - granted
        return granted

    def hazard_exposures(self, local_density: float) -> Mapping[HazardId, float]:
        return {
            hazard_id: law.exposure(local_density)
            for hazard_id, law in self.ground_truth.hazards.items()
        }
