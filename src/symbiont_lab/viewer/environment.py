"""Temporal environment projection for the Pygame ecosystem.

This module smooths observer-visible physical fields between snapshots and derives
only presentation quantities (relief shading and ambient motion seeds).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .projection import VisualCell


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


@dataclass(frozen=True)
class SmoothedCell:
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


@dataclass
class CellTrack:
    previous: VisualCell
    target: VisualCell
    changed_at: float

    def sample(self, now: float, transition_seconds: float) -> SmoothedCell:
        if transition_seconds <= 0:
            t = 1.0
        else:
            t = max(0.0, min(1.0, (now - self.changed_at) / transition_seconds))
            t = t * t * (3.0 - 2.0 * t)
        return SmoothedCell(
            q=self.target.q,
            r=self.target.r,
            elevation=_lerp(self.previous.elevation, self.target.elevation, t),
            moisture=_lerp(self.previous.moisture, self.target.moisture, t),
            temperature=_lerp(self.previous.temperature, self.target.temperature, t),
            fertility=_lerp(self.previous.fertility, self.target.fertility, t),
            traces=_lerp(self.previous.traces, self.target.traces, t),
            disturbance=_lerp(self.previous.disturbance, self.target.disturbance, t),
            density=_lerp(self.previous.density, self.target.density, t),
            resource_level=_lerp(self.previous.resource_level, self.target.resource_level, t),
            hazard_level=_lerp(self.previous.hazard_level, self.target.hazard_level, t),
        )


@dataclass
class EnvironmentScene:
    transition_seconds: float = 0.9
    tracks: dict[tuple[int, int], CellTrack] = field(default_factory=dict)

    def ingest(self, cells: tuple[VisualCell, ...], now: float) -> None:
        incoming = {(cell.q, cell.r): cell for cell in cells}
        for key, target in incoming.items():
            track = self.tracks.get(key)
            if track is None:
                self.tracks[key] = CellTrack(target, target, now)
                continue
            current = track.sample(now, self.transition_seconds)
            previous = VisualCell(
                q=current.q,
                r=current.r,
                elevation=current.elevation,
                moisture=current.moisture,
                temperature=current.temperature,
                fertility=current.fertility,
                traces=current.traces,
                disturbance=current.disturbance,
                density=current.density,
                resource_level=current.resource_level,
                hazard_level=current.hazard_level,
            )
            if target != track.target:
                track.previous = previous
                track.target = target
                track.changed_at = now
        for key in tuple(self.tracks):
            if key not in incoming:
                self.tracks.pop(key, None)

    def sample_keys(self, keys: list[tuple[int, int]], now: float) -> list[SmoothedCell]:
        result: list[SmoothedCell] = []
        for key in keys:
            track = self.tracks.get(key)
            if track is not None:
                result.append(track.sample(now, self.transition_seconds))
        return result


def relief_factor(cell: SmoothedCell, neighbors: dict[tuple[int, int], SmoothedCell]) -> float:
    """Simple directional relief light from observed elevation gradient."""
    east = neighbors.get((cell.q + 1, cell.r))
    southwest = neighbors.get((cell.q, cell.r + 1))
    de = (east.elevation - cell.elevation) if east is not None else 0.0
    ds = (southwest.elevation - cell.elevation) if southwest is not None else 0.0
    # Northwest-like virtual light: uphill to east/south darkens this face.
    return max(0.72, min(1.22, 1.0 - de * 0.55 - ds * 0.35))


def ambient_seed(q: int, r: int, lane: int = 0) -> float:
    digest = hashlib.blake2b(f"{q}:{r}:{lane}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float((1 << 64) - 1)
