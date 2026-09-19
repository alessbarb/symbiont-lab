"""Dynamic Geography & Rich Terrain for Symbiont World v4 (docs/design/symbiont-world-v4.md §2).

Provides continuous terrain topography (elevation, permeability, moisture,
temperature, fertility) and dynamic ecological state (disturbance, decaying organism traces).

Ground truth belongs exclusively to the apparatus/evaluator and is never
leaked to organism cognition.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from symbiont_world.topology import HexCoord, HexTopology


@dataclass(slots=True)
class CellPhenotype:
    """Rich evaluator-side ecological state of an individual cell."""

    q: int
    r: int
    region_id: str
    elevation: float
    permeability: float
    moisture: float
    temperature: float
    fertility: float
    disturbance: float
    traces: float
    effective_fertility: float = 0.5
    surface_water: float = 0.0
    detritus: float = 0.0
    ecological_pressure: float = 0.0
    resources: dict[str, float] = field(default_factory=dict)
    resource_capacities: dict[str, float] = field(default_factory=dict)
    hazards: dict[str, float] = field(default_factory=dict)
    occupant: str | None = None
    density: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "q": self.q,
            "r": self.r,
            "region": self.region_id,
            "elevation": round(self.elevation, 4),
            "permeability": round(self.permeability, 4),
            "moisture": round(self.moisture, 4),
            "temperature": round(self.temperature, 4),
            "fertility": round(self.fertility, 4),
            "disturbance": round(self.disturbance, 4),
            "traces": round(self.traces, 4),
            "effective_fertility": round(self.effective_fertility, 4),
            "surface_water": round(self.surface_water, 4),
            "detritus": round(self.detritus, 4),
            "ecological_pressure": round(self.ecological_pressure, 4),
            "resources": {k: round(v, 3) for k, v in self.resources.items()},
            "resource_capacities": {k: round(v, 3) for k, v in self.resource_capacities.items()},
            "hazards": {k: round(v, 4) for k, v in self.hazards.items()},
            "occupant": self.occupant,
            "density": round(self.density, 3),
        }


class DynamicGeography:
    """Topographical substrate and dynamic ecological field for a HexTopology.

    Deterministic: Given (world_seed, topology), generates identical landscape
    patterns across runs.
    """

    def __init__(
        self,
        topology: HexTopology,
        world_seed: int,
        *,
        elevation: Mapping[HexCoord, float] | None = None,
        permeability: Mapping[HexCoord, float] | None = None,
        moisture: Mapping[HexCoord, float] | None = None,
        temperature: Mapping[HexCoord, float] | None = None,
        fertility: Mapping[HexCoord, float] | None = None,
        traces: Mapping[HexCoord, float] | None = None,
        disturbance: Mapping[HexCoord, float] | None = None,
        surface_water: Mapping[HexCoord, float] | None = None,
        detritus: Mapping[HexCoord, float] | None = None,
        ecological_pressure: Mapping[HexCoord, float] | None = None,
    ) -> None:
        self.topology = topology
        self.world_seed = world_seed

        self._elevation: dict[HexCoord, float] = (
            dict(elevation) if elevation is not None else {}
        )
        self._permeability: dict[HexCoord, float] = (
            dict(permeability) if permeability is not None else {}
        )
        self._moisture: dict[HexCoord, float] = (
            dict(moisture) if moisture is not None else {}
        )
        self._temperature: dict[HexCoord, float] = (
            dict(temperature) if temperature is not None else {}
        )
        self._fertility: dict[HexCoord, float] = (
            dict(fertility) if fertility is not None else {}
        )

        # Dynamic state
        self._traces: dict[HexCoord, float] = (
            dict(traces) if traces is not None else {}
        )
        self._disturbance: dict[HexCoord, float] = (
            dict(disturbance) if disturbance is not None else {}
        )
        self._surface_water: dict[HexCoord, float] = (
            dict(surface_water) if surface_water is not None else {}
        )
        self._detritus: dict[HexCoord, float] = (
            dict(detritus) if detritus is not None else {}
        )
        self._ecological_pressure: dict[HexCoord, float] = (
            dict(ecological_pressure) if ecological_pressure is not None else {}
        )

        if not self._elevation:
            self._generate_topography()
        if not self._surface_water:
            self._initialize_surface_water()

    def _generate_topography(self) -> None:
        w = max(self.topology.width, 1)
        h = max(self.topology.height, 1)
        s = float(self.world_seed % 1000)

        for q in range(self.topology.width):
            for r in range(self.topology.height):
                coord = HexCoord(q, r)
                # Harmonic multi-frequency noise
                nx = (q / w) * math.pi * 2.0
                ny = (r / h) * math.pi * 2.0

                # Elevation: valleys, ridges, and hills
                v1 = math.sin(nx * 1.5 + s * 0.1) * math.cos(ny * 1.5 + s * 0.2)
                v2 = math.sin(nx * 3.0 + s * 0.5) * 0.35 + math.cos(ny * 3.0 + s * 0.3) * 0.35
                elev = (v1 * 0.65 + v2 * 0.35 + 1.0) * 0.5
                elev = max(0.0, min(1.0, elev))
                self._elevation[coord] = round(elev, 4)

                # Temperature: latitudinal gradient (colder north/top, warmer south/bottom) + elevation cooling
                lat_temp = (r / h) * 0.7 + 0.15
                temp = lat_temp - (elev * 0.35) + 0.1
                temp = max(0.0, min(1.0, temp))
                self._temperature[coord] = round(temp, 4)

                # Moisture: river basins in valleys + sinusoidal rainfall
                rain = (math.cos(nx * 2.0 + s * 0.7) * 0.5 + 0.5) * 0.6
                basin = (1.0 - elev) * 0.4
                moist = rain + basin
                moist = max(0.0, min(1.0, moist))
                self._moisture[coord] = round(moist, 4)

                # Fertility: combination of moisture, moderate temperature, and valley soil
                temp_opt = 1.0 - abs(temp - 0.55) * 1.5
                fert = moist * 0.55 + max(0.0, temp_opt) * 0.45
                fert = max(0.05, min(1.0, fert))
                self._fertility[coord] = round(fert, 4)

                # Permeability: high in valleys and flatlands, low on steep cliffs/peaks
                slope_penalty = elev * 0.65
                perm = max(0.12, min(1.0, 1.0 - slope_penalty))
                self._permeability[coord] = round(perm, 4)

    def _initialize_surface_water(self) -> None:
        for q in range(self.topology.width):
            for r in range(self.topology.height):
                cell = HexCoord(q, r)
                value = max(
                    0.0,
                    (self.moisture(cell) - 0.58)
                    * (1.0 - 0.55 * self.elevation(cell))
                    * self.permeability(cell),
                )
                if value >= 0.002:
                    self._surface_water[cell] = round(min(1.0, value), 4)

    def elevation(self, cell: HexCoord) -> float:
        return self._elevation.get(cell, 0.5)

    def permeability(self, cell: HexCoord) -> float:
        return self._permeability.get(cell, 0.8)

    def moisture(self, cell: HexCoord) -> float:
        return self._moisture.get(cell, 0.5)

    def temperature(self, cell: HexCoord) -> float:
        return self._temperature.get(cell, 0.5)

    def fertility(self, cell: HexCoord) -> float:
        return self._fertility.get(cell, 0.5)

    def traces(self, cell: HexCoord) -> float:
        return self._traces.get(cell, 0.0)

    def disturbance(self, cell: HexCoord) -> float:
        return self._disturbance.get(cell, 0.0)

    def surface_water(self, cell: HexCoord) -> float:
        return self._surface_water.get(cell, 0.0)

    def detritus(self, cell: HexCoord) -> float:
        return self._detritus.get(cell, 0.0)

    def ecological_pressure(self, cell: HexCoord) -> float:
        return self._ecological_pressure.get(cell, 0.0)

    def effective_fertility(self, cell: HexCoord) -> float:
        base = self.fertility(cell)
        value = (
            base
            + self.detritus(cell) * 0.24
            + self.surface_water(cell) * 0.10
            - self.ecological_pressure(cell) * 0.22
            - self.disturbance(cell) * 0.12
        )
        return max(0.0, min(1.0, value))

    def resource_renewal_factor(self, cell: HexCoord) -> float:
        # Even poor cells retain a small renewal floor; richer cells recover faster.
        return 0.20 + 0.80 * self.effective_fertility(cell)

    def can_traverse(self, from_cell: HexCoord, to_cell: HexCoord) -> bool:
        """Determines if an organism can physically move between adjacent cells."""
        if not self.topology.in_bounds(to_cell):
            return False
        # Barriers / cliffs check
        target_perm = self.permeability(to_cell)
        if target_perm < 0.15:
            return False
        elev_delta = abs(self.elevation(to_cell) - self.elevation(from_cell))
        if elev_delta > 0.65:
            return False
        return True

    def deposit_trace(self, cell: HexCoord, amount: float = 0.35) -> None:
        current = self._traces.get(cell, 0.0)
        self._traces[cell] = min(1.0, current + amount)

    def deposit_disturbance(self, cell: HexCoord, amount: float = 0.25) -> None:
        current = self._disturbance.get(cell, 0.0)
        self._disturbance[cell] = min(1.0, current + amount)

    def deposit_detritus(self, cell: HexCoord, amount: float = 0.75) -> None:
        current = self._detritus.get(cell, 0.0)
        self._detritus[cell] = min(1.0, current + amount)

    def step(
        self,
        occupied_cells: Iterable[HexCoord],
        *,
        death_cells: Iterable[HexCoord] = (),
    ) -> None:
        """Advance physical ecology by one tick.

        Presence creates traces and pressure. Death deposits material. Surface
        water relaxes toward a terrain/moisture equilibrium and can spread to
        lower neighboring cells. All dynamics are deterministic.
        """
        occupied = tuple(occupied_cells)
        deaths = tuple(death_cells)

        for cell in occupied:
            self.deposit_trace(cell, 0.25)
            self._ecological_pressure[cell] = min(
                1.0, self._ecological_pressure.get(cell, 0.0) + 0.10
            )
        for cell in deaths:
            self.deposit_detritus(cell, 0.80)
            self.deposit_disturbance(cell, 0.35)

        # Surface water is a real dynamic state. Only active/wet/debris cells
        # and their neighbors need updating; static dry terrain remains sparse.
        active: set[HexCoord] = set(occupied) | set(deaths) | set(self._surface_water)
        active |= set(self._detritus) | set(self._disturbance)
        for cell in tuple(active):
            for direction in range(6):
                neighbor = cell.neighbor(direction)
                if self.topology.in_bounds(neighbor):
                    active.add(neighbor)

        next_water: dict[HexCoord, float] = {}
        for cell in active:
            current = self._surface_water.get(cell, 0.0)
            equilibrium = max(
                0.0,
                (self.moisture(cell) - 0.58)
                * (1.0 - 0.55 * self.elevation(cell))
                * self.permeability(cell),
            )
            value = current + (equilibrium - current) * 0.08
            value *= 1.0 - 0.025 * self.temperature(cell)
            # modest downhill inflow from wetter/higher neighbors
            inflow = 0.0
            for direction in range(6):
                neighbor = cell.neighbor(direction)
                if not self.topology.in_bounds(neighbor):
                    continue
                neighbor_water = self._surface_water.get(neighbor, 0.0)
                drop = self.elevation(neighbor) - self.elevation(cell)
                if drop > 0.0 and neighbor_water > value:
                    inflow += min(0.015, drop * neighbor_water * 0.02)
            value = max(0.0, min(1.0, value + inflow))
            if value >= 0.002:
                next_water[cell] = round(value, 4)
        self._surface_water = next_water

        # Decay traces
        decayed_traces = {}
        for cell, val in self._traces.items():
            new_val = val * 0.94
            if new_val >= 0.005:
                decayed_traces[cell] = round(new_val, 4)
        self._traces = decayed_traces

        # Decay disturbances
        decayed_dist = {}
        for cell, val in self._disturbance.items():
            new_val = val * 0.88
            if new_val >= 0.005:
                decayed_dist[cell] = round(new_val, 4)
        self._disturbance = decayed_dist

        decayed_detritus = {}
        for cell, val in self._detritus.items():
            new_val = val * 0.985
            if new_val >= 0.002:
                decayed_detritus[cell] = round(new_val, 4)
        self._detritus = decayed_detritus

        decayed_pressure = {}
        for cell, val in self._ecological_pressure.items():
            new_val = val * 0.92
            if new_val >= 0.002:
                decayed_pressure[cell] = round(new_val, 4)
        self._ecological_pressure = decayed_pressure

    def snapshot(self) -> dict[str, Any]:
        """Snapshot dynamic state for transaction rollback or checkpointing."""
        return {
            "traces": {f"{c.q},{c.r}": v for c, v in self._traces.items()},
            "disturbance": {f"{c.q},{c.r}": v for c, v in self._disturbance.items()},
            "surface_water": {f"{c.q},{c.r}": v for c, v in self._surface_water.items()},
            "detritus": {f"{c.q},{c.r}": v for c, v in self._detritus.items()},
            "ecological_pressure": {
                f"{c.q},{c.r}": v for c, v in self._ecological_pressure.items()
            },
        }

    def restore(self, snap: Mapping[str, Any]) -> None:
        """Restore dynamic state from a snapshot."""
        self._traces = {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
            for k, v in snap.get("traces", {}).items()
        }
        self._disturbance = {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
            for k, v in snap.get("disturbance", {}).items()
        }
        self._surface_water = {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
            for k, v in snap.get("surface_water", {}).items()
        }
        self._detritus = {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
            for k, v in snap.get("detritus", {}).items()
        }
        self._ecological_pressure = {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
            for k, v in snap.get("ecological_pressure", {}).items()
        }

    def to_dict(self) -> dict[str, Any]:
        """Full representation for persistent checkpointing."""
        return {
            "world_seed": self.world_seed,
            "width": self.topology.width,
            "height": self.topology.height,
            "elevation": {f"{c.q},{c.r}": v for c, v in self._elevation.items()},
            "permeability": {f"{c.q},{c.r}": v for c, v in self._permeability.items()},
            "moisture": {f"{c.q},{c.r}": v for c, v in self._moisture.items()},
            "temperature": {f"{c.q},{c.r}": v for c, v in self._temperature.items()},
            "fertility": {f"{c.q},{c.r}": v for c, v in self._fertility.items()},
            "traces": {f"{c.q},{c.r}": v for c, v in self._traces.items()},
            "disturbance": {f"{c.q},{c.r}": v for c, v in self._disturbance.items()},
            "surface_water": {f"{c.q},{c.r}": v for c, v in self._surface_water.items()},
            "detritus": {f"{c.q},{c.r}": v for c, v in self._detritus.items()},
            "ecological_pressure": {
                f"{c.q},{c.r}": v for c, v in self._ecological_pressure.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DynamicGeography:
        topo = HexTopology(width=int(data["width"]), height=int(data["height"]))
        def _parse_map(raw: Mapping[str, Any]) -> dict[HexCoord, float]:
            return {
                HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): float(v)
                for k, v in raw.items()
            }
        return cls(
            topology=topo,
            world_seed=int(data["world_seed"]),
            elevation=_parse_map(data.get("elevation", {})),
            permeability=_parse_map(data.get("permeability", {})),
            moisture=_parse_map(data.get("moisture", {})),
            temperature=_parse_map(data.get("temperature", {})),
            fertility=_parse_map(data.get("fertility", {})),
            traces=_parse_map(data.get("traces", {})),
            disturbance=_parse_map(data.get("disturbance", {})),
            surface_water=_parse_map(data.get("surface_water", {})),
            detritus=_parse_map(data.get("detritus", {})),
            ecological_pressure=_parse_map(data.get("ecological_pressure", {})),
        )
