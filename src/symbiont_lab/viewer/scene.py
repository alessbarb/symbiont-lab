"""Temporal scene model for passive naturalist visualization."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from .camera import axial_to_world
from .projection import VisualOrganism, VisualSnapshot


@dataclass
class OrganismTrack:
    organism: VisualOrganism
    previous: tuple[float, float]
    target: tuple[float, float]
    changed_at: float
    seen_at: float

    def position(self, now: float, transition_seconds: float) -> tuple[float, float]:
        if transition_seconds <= 0:
            return self.target
        alpha = max(0.0, min(1.0, (now - self.changed_at) / transition_seconds))
        # Smoothstep prevents abrupt starts/stops while preserving endpoints.
        alpha = alpha * alpha * (3.0 - 2.0 * alpha)
        return (
            self.previous[0] + (self.target[0] - self.previous[0]) * alpha,
            self.previous[1] + (self.target[1] - self.previous[1]) * alpha,
        )


@dataclass(frozen=True)
class Morphology:
    lobes: int
    symmetry_offset: float
    core_scale: float
    appendage_scale: float
    pulse_phase: float


@dataclass
class VisualEffect:
    kind: str
    x: float
    y: float
    born_at: float
    lifetime: float
    strength: float = 1.0

    def age(self, now: float) -> float:
        return max(0.0, now - self.born_at)

    def progress(self, now: float) -> float:
        return max(0.0, min(1.0, self.age(now) / max(self.lifetime, 1e-9)))


def morphology_for(organism: VisualOrganism) -> Morphology:
    """Stable appearance from observable phenotype-related state and identity."""
    seed = f"{organism.organism_id}:{organism.generation}:{organism.senses_count}".encode()
    digest = hashlib.blake2b(seed, digest_size=8).digest()
    unit = int.from_bytes(digest, "big") / float((1 << 64) - 1)
    lobes = max(3, min(9, 3 + organism.senses_count // 2 + digest[0] % 3))
    return Morphology(
        lobes=lobes,
        symmetry_offset=(digest[1] / 255.0) * math.tau,
        core_scale=0.85 + (digest[2] / 255.0) * 0.3,
        appendage_scale=0.75 + (digest[3] / 255.0) * 0.5,
        pulse_phase=unit * math.tau,
    )


def classify_event(kind: str) -> tuple[str, float, float] | None:
    """Map apparatus event names to non-textual physical manifestations."""
    upper = kind.upper()
    if "DEATH" in upper:
        return ("collapse", 2.2, 1.0)
    if "BIRTH" in upper or "REPRO" in upper or "SPAWN" in upper:
        return ("emerge", 1.8, 1.0)
    if "DAMAGE" in upper or "HAZARD" in upper or "COLLISION" in upper:
        return ("shock", 0.9, 1.0)
    if "RESOURCE" in upper or "ACQUI" in upper or "CONSUM" in upper:
        return ("absorb", 0.8, 0.8)
    if "MOVE" in upper or "MOTION" in upper:
        return ("motion", 0.6, 0.45)
    if "REPAIR" in upper or "RECOVER" in upper:
        return ("recover", 1.0, 0.7)
    return None


@dataclass
class HabitatScene:
    spacing: float = 46.0
    transition_seconds: float = 0.42
    snapshot: VisualSnapshot | None = None
    tracks: dict[str, OrganismTrack] = field(default_factory=dict)
    effects: list[VisualEffect] = field(default_factory=list)

    def ingest_snapshot(self, snapshot: VisualSnapshot, now: float) -> None:
        previous_ids = set(self.tracks)
        self.snapshot = snapshot
        for organism in snapshot.organisms:
            target = axial_to_world(organism.q, organism.r, self.spacing)
            track = self.tracks.get(organism.organism_id)
            if track is None:
                self.tracks[organism.organism_id] = OrganismTrack(
                    organism=organism,
                    previous=target,
                    target=target,
                    changed_at=now,
                    seen_at=now,
                )
            else:
                current = track.position(now, self.transition_seconds)
                changed = target != track.target
                track.previous = current if changed else track.previous
                track.target = target
                track.changed_at = now if changed else track.changed_at
                track.seen_at = now
                track.organism = organism
            previous_ids.discard(organism.organism_id)

        # A vanished organism is observer-absent, not silently declared dead.
        for missing in previous_ids:
            if now - self.tracks[missing].seen_at > 3.0:
                self.tracks.pop(missing, None)

    def ingest_events(self, events: list[dict], now: float) -> None:
        for event in events:
            kind = str(event.get("kind", event.get("type", "")))
            classified = classify_event(kind)
            if classified is None:
                continue
            visual_kind, lifetime, strength = classified
            actor = event.get("actor")
            track = self.tracks.get(str(actor)) if actor is not None else None
            if track is None:
                continue
            x, y = track.position(now, self.transition_seconds)
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                raw_damage = payload.get("damage")
                try:
                    if raw_damage is not None:
                        strength = max(strength, min(2.0, abs(float(raw_damage))))
                except (TypeError, ValueError):
                    pass
            self.effects.append(VisualEffect(visual_kind, x, y, now, lifetime, strength))
        self.effects = self.effects[-512:]

    def organism_positions(self, now: float) -> list[tuple[VisualOrganism, float, float, Morphology]]:
        return [
            (track.organism, *track.position(now, self.transition_seconds), morphology_for(track.organism))
            for track in self.tracks.values()
        ]

    def update(self, now: float) -> None:
        self.effects[:] = [effect for effect in self.effects if effect.progress(now) < 1.0]
