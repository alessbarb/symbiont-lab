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

from typing import Mapping

from symbiont_world.events import EventJournal
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.state import WorldState
from symbiont_world.topology import HexTopology


def _label(metadata: Mapping[str, str], opaque_id: str) -> str:
    for name, mapped_id in metadata.items():
        if mapped_id == opaque_id:
            return name
    return opaque_id


def world_snapshot(
    state: WorldState,
    environment: WorldEnvironment,
    ground_truth: GroundTruth,
    metadata: Mapping[str, str],
    topology: HexTopology,
) -> dict:
    """Structured, JSON-serializable read of the same data render_world()
    prints -- for a graphical (SVG/canvas) client instead of a <pre>
    block. Same read-only discipline: this never mutates state."""
    occupied = state.occupancy.snapshot()

    organisms = []
    for cell in sorted(occupied, key=lambda c: (c.q, c.r)):
        organism_id = occupied[cell]
        organisms.append({
            "id": organism_id,
            "q": cell.q,
            "r": cell.r,
            "region": ground_truth.region_of_cell(cell),
        })

    fields = {_label(metadata, fid): value for fid, value in sorted(environment.field_values().items())}

    cells = {}
    for cell in sorted(occupied, key=lambda c: (c.q, c.r)):
        key = f"{cell.q},{cell.r}"
        resources = {}
        if environment.is_materialized(cell):
            resources = {
                _label(metadata, rid): quantity
                for rid, quantity in sorted(environment.resource_pool(cell).items())
            }
        hazards = {
            _label(metadata, hid): exposure
            for hid, exposure in sorted(environment.hazard_exposures_at(cell, local_density=0.0).items())
        }
        cells[key] = {"resources": resources, "hazards": hazards}

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
        exposures = environment.hazard_exposures_at(cell, local_density=0.0)
        for hazard_id, exposure in sorted(exposures.items()):
            lines.append(f"    hazard   {_label(metadata, hazard_id):24s} exposure(density=0) = {exposure:.3f}")
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
