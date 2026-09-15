"""Bounded reproductive pressure and clonal budding (v0.66)."""
from __future__ import annotations

from dataclasses import dataclass

from .birth_authority import BirthRecord, HabitatBirthAuthority
from .heredity import HeritableGenome, recombine_loci


@dataclass(frozen=True, slots=True)
class ReproductiveStatus:
    blocked_ticks: int
    ready: bool
    reserve: float


class ReproductivePressure:
    def __init__(self, *, threshold_ticks: int = 8, reserve: float = 1.0) -> None:
        if threshold_ticks < 1 or not 0.0 <= reserve <= 1.0:
            raise ValueError("invalid reproductive pressure limits")
        self.threshold_ticks = threshold_ticks
        self.reserve = float(reserve)
        self.blocked_ticks = 0

    def observe(self, *, viable: bool, adaptive: bool, capacity_exhausted: bool, blocked_growth: bool) -> ReproductiveStatus:
        if viable and adaptive and capacity_exhausted and blocked_growth:
            self.blocked_ticks = min(self.threshold_ticks, self.blocked_ticks + 1)
        else:
            self.blocked_ticks = max(0, self.blocked_ticks - 1)
        return ReproductiveStatus(self.blocked_ticks, self.blocked_ticks >= self.threshold_ticks and self.reserve > 0.0, self.reserve)

    def consume(self, cost: float = 1.0) -> None:
        if cost <= 0.0 or cost > self.reserve:
            raise ValueError("insufficient reproductive reserve")
        self.reserve -= cost
        self.blocked_ticks = 0


def clonal_bud(*, parent_id: str, genome_id: str, generation: int, authority: HabitatBirthAuthority,
               pressure: ReproductivePressure, resource_units: float = 1.0) -> BirthRecord | None:
    status = ReproductiveStatus(pressure.blocked_ticks, pressure.blocked_ticks >= pressure.threshold_ticks and pressure.reserve > 0.0, pressure.reserve)
    if not status.ready:
        return None
    record = authority.birth(genome_id=genome_id, parent_ids=(parent_id,), generation=generation + 1, resource_units=resource_units)
    if record is None:
        return None
    pressure.consume()
    return record


def paired_reproduce(*, parent_a: str, parent_b: str, genome_a: HeritableGenome,
                     genome_b: HeritableGenome, generation: int,
                     authority: HabitatBirthAuthority, choose_a: bool = True,
                     resource_units: float = 1.0) -> BirthRecord | None:
    """Create one validated offspring record; habitat allocation is atomic."""
    if parent_a == parent_b:
        return None
    genome = recombine_loci(genome_a, genome_b, choose_a=choose_a)
    return authority.birth(genome_id=genome.identity, parent_ids=(parent_a, parent_b),
                           generation=generation + 1, resource_units=resource_units)


__all__ = ["ReproductivePressure", "ReproductiveStatus", "clonal_bud", "paired_reproduce"]
