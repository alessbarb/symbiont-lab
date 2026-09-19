"""Observer snapshot projection for the Pygame habitat.

No runtime imports are permitted here. All visual state comes from Observatory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisualCell:
    q: int
    r: int
    elevation: float
    moisture: float
    temperature: float
    fertility: float
    traces: float
    disturbance: float
    density: float
    resource_level: float
    hazard_level: float
    effective_fertility: float = 0.5
    surface_water: float = 0.0
    detritus: float = 0.0
    ecological_pressure: float = 0.0


@dataclass(frozen=True)
class VisualOrganism:
    organism_id: str
    q: int
    r: int
    alive: bool
    integrity: float | None
    reserve: float | None
    senses_count: int
    generation: int
    age: int
    recent_damage: float


@dataclass(frozen=True)
class VisualSnapshot:
    world_id: str
    tick: int
    width: int
    height: int
    cells: tuple[VisualCell, ...]
    organisms: tuple[VisualOrganism, ...]


def bounded(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def project_snapshot(snapshot: dict[str, Any]) -> VisualSnapshot:
    cells: list[VisualCell] = []
    raw_cells = snapshot.get("cells", {})
    if isinstance(raw_cells, dict):
        for payload in raw_cells.values():
            if not isinstance(payload, dict):
                continue
            resources = payload.get("resources", {})
            capacities = payload.get("resource_capacities", {})
            fractions: list[float] = []
            if isinstance(resources, dict) and isinstance(capacities, dict):
                for key, quantity in resources.items():
                    try:
                        capacity = float(capacities.get(key, 0.0))
                        amount = float(quantity)
                    except (TypeError, ValueError):
                        continue
                    if capacity > 0 and math.isfinite(capacity) and math.isfinite(amount):
                        fractions.append(max(0.0, min(1.0, amount / capacity)))
            hazards = payload.get("hazards", {})
            hazard_values = [bounded(v) for v in hazards.values()] if isinstance(hazards, dict) else []
            cells.append(
                VisualCell(
                    q=int(payload.get("q", 0)),
                    r=int(payload.get("r", 0)),
                    elevation=bounded(payload.get("elevation"), 0.5),
                    moisture=bounded(payload.get("moisture"), 0.5),
                    temperature=bounded(payload.get("temperature"), 0.5),
                    fertility=bounded(payload.get("fertility"), 0.5),
                    traces=bounded(payload.get("traces")),
                    disturbance=bounded(payload.get("disturbance")),
                    density=bounded(payload.get("density")),
                    resource_level=sum(fractions) / len(fractions) if fractions else 0.0,
                    hazard_level=max(hazard_values) if hazard_values else 0.0,
                    effective_fertility=bounded(
                        payload.get("effective_fertility"),
                        bounded(payload.get("fertility"), 0.5),
                    ),
                    surface_water=bounded(payload.get("surface_water")),
                    detritus=bounded(payload.get("detritus")),
                    ecological_pressure=bounded(payload.get("ecological_pressure")),
                )
            )

    organisms: list[VisualOrganism] = []
    raw_organisms = snapshot.get("organisms", [])
    if isinstance(raw_organisms, list):
        for payload in raw_organisms:
            if not isinstance(payload, dict):
                continue
            recent_damage = payload.get("recent_damage", 0.0)
            try:
                damage = max(0.0, float(recent_damage))
            except (TypeError, ValueError):
                damage = 0.0
            organisms.append(
                VisualOrganism(
                    organism_id=str(payload.get("id", "?")),
                    q=int(payload.get("q", 0)),
                    r=int(payload.get("r", 0)),
                    alive=bool(payload.get("alive", True)),
                    integrity=None if payload.get("integrity") is None else bounded(payload.get("integrity")),
                    reserve=None if payload.get("metabolic_reserve") is None else bounded(payload.get("metabolic_reserve")),
                    senses_count=max(0, int(payload.get("senses_count", 0) or 0)),
                    generation=max(0, int(payload.get("generation", 0) or 0)),
                    age=max(0, int(payload.get("age", 0) or 0)),
                    recent_damage=damage,
                )
            )

    return VisualSnapshot(
        world_id=str(snapshot.get("world_id", "world")),
        tick=max(0, int(snapshot.get("tick", 0) or 0)),
        width=max(1, int(snapshot.get("width", 1) or 1)),
        height=max(1, int(snapshot.get("height", 1) or 1)),
        cells=tuple(cells),
        organisms=tuple(organisms),
    )
