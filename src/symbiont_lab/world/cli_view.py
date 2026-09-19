"""Read-only CLI visualization for a human operator (docs/design/
symbiont-world-v2.md §8). render_world is a pure function: it never
prints, never reads stdin, and has no code path that calls WorldAction or
mutates WorldState -- same discipline as every other Observatory surface
(CLAUDE.md: "the display does not control cognition").

Observatory is evaluator-side and already allowed to know what a
field/resource/hazard means (v1 §7's opacity invariant only binds what
reaches the organism) -- this is what GENESIS_V1_METADATA is for.
"""
from __future__ import annotations

from typing import Any, Mapping

from symbiont_world.events import EventJournal
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord, HexTopology, OccupancyGrid


def _label(metadata: Mapping[str, str], opaque_id: str) -> str:
    for name, mapped_id in metadata.items():
        if mapped_id == opaque_id:
            return name
    return opaque_id


def _calculate_density(topology: HexTopology, occupancy: OccupancyGrid, cell: HexCoord, radius: int = 1) -> float:
    visited = {cell}
    frontier = {cell}
    occupied_neighbors = 0
    total_neighbors = 0
    for _ in range(radius):
        next_frontier = set()
        for c in frontier:
            for direction in range(6):
                neighbor = c.neighbor(direction)
                if neighbor in visited or not topology.in_bounds(neighbor):
                    continue
                visited.add(neighbor)
                next_frontier.add(neighbor)
                total_neighbors += 1
                if occupancy.is_occupied(neighbor):
                    occupied_neighbors += 1
        frontier = next_frontier
    return occupied_neighbors / total_neighbors if total_neighbors else 0.0


def world_snapshot(
    state: WorldState,
    environment: WorldEnvironment,
    ground_truth: GroundTruth,
    metadata: Mapping[str, str],
    topology: HexTopology,
    *,
    population: Any | None = None,
    all_cells: bool = True,
) -> dict:
    """Structured, JSON-serializable read of the world state for Observatory.
    Includes geography of all cells, real local hazard exposures, and rich organism
    telemetry without breaking read-only discipline (docs/design/symbiont-world-v3.md §16-26)."""
    occupied = state.occupancy.snapshot()

    organisms = []
    for cell in sorted(occupied, key=lambda c: (c.q, c.r)):
        organism_id = occupied[cell]
        org_data: dict[str, Any] = {
            "id": organism_id,
            "q": cell.q,
            "r": cell.r,
            "region": ground_truth.region_of_cell(cell),
        }
        if population is not None and hasattr(population, "_rigs") and organism_id in population._rigs:
            rig = population._rigs[organism_id]
            phys = rig.runtime._physiology
            metab = rig.runtime.metabolism
            is_alive = population.is_alive(organism_id)

            last_action_str = None
            recent_hits: tuple[str, ...] = ()
            if getattr(population, "history", None):
                last_rec = population.history[-1].per_organism.get(organism_id)
                if last_rec is not None:
                    last_action_str = last_rec.action.action_id if last_rec.action else None
                    recent_hits = last_rec.hazard_hits

            # PERCEPTION must preserve the organism-facing opaque identity.
            # Human semantic labels belong only to Reality/GroundTruth.
            percept_readings: dict[str, float] = {}
            if hasattr(rig.reading_provider, "_observation") and rig.reading_provider._observation is not None:
                for sig_id, sig_val in sorted(rig.reading_provider._observation.signals.items()):
                    percept_readings[sig_id] = round(float(sig_val), 4)

            bridge = rig.runtime.cognitive_bridge
            concept_count = None
            if bridge is not None and getattr(bridge, "graph", None) is not None:
                concept_count = sum(
                    1 for node in bridge.graph.nodes
                    if getattr(getattr(node, "kind", None), "value", None) == "concept"
                )
            cognition_summary = {
                "concept_count": concept_count,
                # No authoritative scalar prediction-confidence surface exists
                # on the runtime. Observatory must report unknown, not invent 0.5.
                "prediction_confidence": None,
                "private_model_bridge_active": getattr(rig.runtime, "_private_model_bridge", None) is not None,
                "interoception_mode": getattr(rig.runtime, "_interoception_mode", None),
            }

            reserve_val = None
            metabolic_pressure = None
            if metab is not None:
                metabolic_snapshot = metab.snapshot()
                ratios = [
                    metabolic_snapshot.reserve[k] / max(metabolic_snapshot.capacity[k], 1e-12)
                    for k in metabolic_snapshot.capacity
                ]
                reserve_val = round(float(sum(ratios) / len(ratios)), 4) if ratios else None
                metabolic_pressure = metabolic_snapshot.pressure.value

            integ_val = round(float(rig.runtime.homeostasis.integrity), 4)

            recent_damage = 0.0
            if getattr(population, "history", None):
                last_tick = population.history[-1].tick
                recent_damage = round(sum(
                    float(event.payload.get("damage", 0.0))
                    for event in population.journal.replay()
                    if event.tick == last_tick
                    and event.actor == organism_id
                    and event.kind == "PHYSIOLOGICAL_DAMAGE"
                ), 4)

            org_data.update({
                "alive": is_alive,
                "vital_state": phys.state.name.lower(),
                "integrity": integ_val,
                "metabolic_reserve": reserve_val,
                "metabolic_pressure": metabolic_pressure,
                "generation": int(rig.runtime.generation),
                "age": int(rig.runtime.tick_count),
                "last_action": last_action_str,
                "recent_damage": recent_damage,
                "recent_hazard_hits": list(recent_hits),
                "perception": percept_readings,
                "cognition": cognition_summary,
            })
        organisms.append(org_data)

    fields = {_label(metadata, fid): value for fid, value in sorted(environment.field_values().items())}

    cells = {}
    cell_range = (
        [(q, r) for q in range(topology.width) for r in range(topology.height)]
        if all_cells
        else [(c.q, c.r) for c in sorted(occupied, key=lambda c: (c.q, c.r))]
    )
    for q, r in cell_range:
        cell = HexCoord(q, r)
        key = f"{q},{r}"
        region = ground_truth.region_of_cell(cell)
        occupant = state.occupancy.occupant(cell)
        density = _calculate_density(topology, state.occupancy, cell)

        resources = {}
        resource_capacities = {}
        for rid in sorted(ground_truth.resources):
            law = ground_truth.resource_law(cell, rid)
            r_label = _label(metadata, rid)
            resource_capacities[r_label] = round(float(law.capacity), 3)
            if environment.is_materialized(cell):
                resources[r_label] = round(float(environment.resource_pool(cell).get(rid, 0.0)), 3)
            else:
                resources[r_label] = round(float(law.initial_quantity), 3)

        hazards = {
            _label(metadata, hid): round(float(exposure), 4)
            for hid, exposure in sorted(environment.hazard_exposures_at(cell, local_density=density).items())
        }
        cells[key] = {
            "q": q,
            "r": r,
            "region": region,
            "occupant": occupant,
            "resources": resources,
            "resource_capacities": resource_capacities,
            "hazards": hazards,
            "density": round(density, 3),
        }

    return {
        "world_id": state.world_id,
        "tick": state.tick,
        "width": topology.width,
        "height": topology.height,
        "organisms": organisms,
        "fields": fields,
        "cells": cells,
    }



def render_world(
    state: WorldState,
    environment: WorldEnvironment,
    ground_truth: GroundTruth,
    metadata: Mapping[str, str],
    topology: HexTopology,
    *,
    journal: EventJournal | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"World {state.world_id!r} — tick {state.tick} — {topology.width}x{topology.height} hex")
    lines.append("")

    occupied = state.occupancy.snapshot()
    lines.append(f"Organisms ({len(occupied)}):")
    if not occupied:
        lines.append("  (none)")
    for cell in sorted(occupied, key=lambda c: (c.q, c.r)):
        organism_id = occupied[cell]
        region = ground_truth.region_of_cell(cell)
        region_note = f" region={region}" if region is not None else ""
        lines.append(f"  {organism_id:20s} @ ({cell.q:3d},{cell.r:3d}){region_note}")
    lines.append("")

    field_values = environment.field_values()
    lines.append("Fields (global):")
    if not field_values:
        lines.append("  (none)")
    for field_id, value in sorted(field_values.items()):
        lines.append(f"  {_label(metadata, field_id):28s} = {value:+.4f}")
    lines.append("")

    lines.append("Local resources/hazards per occupied cell:")
    for cell in sorted(occupied, key=lambda c: (c.q, c.r)):
        organism_id = occupied[cell]
        lines.append(f"  cell ({cell.q},{cell.r}) [{organism_id}]:")
        if environment.is_materialized(cell):
            pool = environment.resource_pool(cell)
            for resource_id, quantity in sorted(pool.items()):
                lines.append(f"    resource {_label(metadata, resource_id):24s} = {quantity:.3f}")
        else:
            lines.append("    resource pool not yet materialized")
        density = _calculate_density(topology, state.occupancy, cell)
        exposures = environment.hazard_exposures_at(cell, local_density=density)
        for hazard_id, exposure in sorted(exposures.items()):
            lines.append(
                f"    hazard   {_label(metadata, hazard_id):24s} "
                f"exposure(density={density:.3f}) = {exposure:.3f}"
            )
    lines.append("")

    lines.append("Event feed:")
    if journal is None or len(journal) == 0:
        lines.append("  (no journal attached / no events recorded)")
    else:
        for event in journal.replay()[-20:]:
            causal = f"causal={list(event.causal_parent_ids)}" if event.causal_parent_ids else ""
            contributing = f"contributing={list(event.contributing_event_ids)}" if event.contributing_event_ids else ""
            provenance = " ".join(part for part in (causal, contributing) if part)
            lines.append(f"  [{event.tick:5d}] {event.kind:24s} actor={event.actor} {provenance}".rstrip())

    return "\n".join(lines)
