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
from typing import Callable, Mapping

from .laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from .topology import HexCoord

FieldId = str
ResourceId = str
HazardId = str
RegionId = str


def _freeze_nested(mapping: Mapping) -> Mapping:
    return MappingProxyType({key: MappingProxyType(dict(value)) for key, value in mapping.items()})


@dataclass(frozen=True, slots=True)
class GroundTruth:
    """Fields stay global (uniform temporal signal). Resources/hazards have
    a base law (fallback) plus optional per-region overrides
    (docs/design/symbiont-world-v2.md §3) -- additive: a GroundTruth built
    without region_of/regional_* behaves exactly as it did in v1."""

    fields: Mapping[FieldId, PeriodicFieldLaw] = field(default_factory=dict)
    resources: Mapping[ResourceId, ResourceLaw] = field(default_factory=dict)
    hazards: Mapping[HazardId, HazardLaw] = field(default_factory=dict)
    region_of: Callable[[HexCoord], RegionId] | None = None
    regional_resources: Mapping[RegionId, Mapping[ResourceId, ResourceLaw]] = field(default_factory=dict)
    regional_hazards: Mapping[RegionId, Mapping[HazardId, HazardLaw]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "resources", MappingProxyType(dict(self.resources)))
        object.__setattr__(self, "hazards", MappingProxyType(dict(self.hazards)))
        object.__setattr__(self, "regional_resources", _freeze_nested(self.regional_resources))
        object.__setattr__(self, "regional_hazards", _freeze_nested(self.regional_hazards))

    def region_of_cell(self, cell: HexCoord) -> RegionId | None:
        return self.region_of(cell) if self.region_of is not None else None

    def resource_law(self, cell: HexCoord, resource_id: ResourceId) -> ResourceLaw:
        region = self.region_of_cell(cell)
        if region is not None:
            override = self.regional_resources.get(region, {}).get(resource_id)
            if override is not None:
                return override
        return self.resources[resource_id]

    def hazard_law(self, cell: HexCoord, hazard_id: HazardId) -> HazardLaw:
        region = self.region_of_cell(cell)
        if region is not None:
            override = self.regional_hazards.get(region, {}).get(hazard_id)
            if override is not None:
                return override
        return self.hazards[hazard_id]


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
                resource_id: self.ground_truth.resource_law(cell, resource_id).initial_quantity
                for resource_id in self.ground_truth.resources
            }
        return self._resource_pools[cell]

    def resource_pool(self, cell: HexCoord) -> Mapping[ResourceId, float]:
        return MappingProxyType(dict(self._pool(cell)))

    def renew_resources(self, cell: HexCoord) -> None:
        pool = self._pool(cell)
        for resource_id in self.ground_truth.resources:
            law = self.ground_truth.resource_law(cell, resource_id)
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
        """Base-law exposures, ignoring any regional override. Kept for
        backward compatibility with v1 callers/tests (gate V02-08)."""
        return {
            hazard_id: law.exposure(local_density)
            for hazard_id, law in self.ground_truth.hazards.items()
        }

    def hazard_exposures_at(self, cell: HexCoord, local_density: float) -> Mapping[HazardId, float]:
        """Region-aware exposures (docs/design/symbiont-world-v2.md §3)."""
        return {
            hazard_id: self.ground_truth.hazard_law(cell, hazard_id).exposure(local_density)
            for hazard_id in self.ground_truth.hazards
        }
