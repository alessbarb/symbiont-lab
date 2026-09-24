"""Genetic and explicitly optional epigenetic inheritance for Genome v2."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Mapping

from .genome import Genome, flatten_genes
from .mutation import mutate_genome
from .recombination import recombine_genomes
from .schema import DEFAULT_GENOME_SCHEMA, GenomeSchema


@dataclass(frozen=True, slots=True)
class EpigeneticMark:
    locus: str
    delta: float
    strength: float = 1.0
    generations_left: int = 3

    def __post_init__(self) -> None:
        if not self.locus:
            raise ValueError("epigenetic locus must not be empty")
        if not math.isfinite(self.delta):
            raise ValueError("epigenetic delta must be finite")
        if not math.isfinite(self.strength) or not 0.0 <= self.strength <= 1.0:
            raise ValueError("epigenetic strength must be in [0,1]")
        if self.generations_left < 0:
            raise ValueError("generations_left must be non-negative")

    def decay(self, fraction: float) -> "EpigeneticMark | None":
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError("epigenetic decay must be in [0,1]")
        strength = self.strength * (1.0 - fraction)
        remaining = self.generations_left - 1
        if strength < 0.05 or remaining <= 0:
            return None
        return EpigeneticMark(
            locus=self.locus,
            delta=self.delta,
            strength=strength,
            generations_left=remaining,
        )


@dataclass(slots=True)
class GermlineState:
    """Lifetime germline metadata; acquired capture is disabled by default."""

    birth_expression: dict[str, float | int]
    inherited_marks: dict[str, EpigeneticMark] = field(default_factory=dict)
    acquired_marks: dict[str, EpigeneticMark] = field(default_factory=dict)
    acquired_capture_enabled: bool = False

    @classmethod
    def from_genome(
        cls,
        genome: Genome,
        *,
        inherited_marks: tuple[EpigeneticMark, ...] = (),
        acquired_capture_enabled: bool = False,
    ) -> "GermlineState":
        return cls(
            birth_expression=dict(flatten_genes(genome)),
            inherited_marks={mark.locus: mark for mark in inherited_marks},
            acquired_marks={},
            acquired_capture_enabled=acquired_capture_enabled,
        )

    def effective_value(
        self,
        genome: Genome,
        locus: str,
        *,
        schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
    ) -> float | int:
        base = flatten_genes(genome)[locus]
        spec = schema.spec(locus)
        value = float(base)
        for marks in (self.inherited_marks, self.acquired_marks):
            mark = marks.get(locus)
            if mark is not None:
                value += mark.delta * mark.strength
        return spec.clamp(value)

    def capture_acquired_variation(
        self,
        current_expression: Mapping[str, float],
        *,
        genome: Genome,
        schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
        min_delta: float = 0.02,
    ) -> tuple[str, ...]:
        """Capture only when an experiment explicitly enables this channel."""
        if not self.acquired_capture_enabled:
            return ()
        captured: list[str] = []
        max_marks = genome.inheritance.max_epigenetic_marks
        for locus, current in sorted(current_expression.items()):
            if len(self.acquired_marks) >= max_marks and locus not in self.acquired_marks:
                break
            spec = schema.spec(locus)
            if not spec.regulable:
                continue
            birth = float(self.birth_expression.get(locus, flatten_genes(genome)[locus]))
            delta = float(current) - birth
            if abs(delta) < min_delta:
                continue
            self.acquired_marks[locus] = EpigeneticMark(locus=locus, delta=delta)
            captured.append(locus)
        return tuple(captured)


@dataclass(frozen=True, slots=True)
class InheritancePackage:
    genome: Genome
    epigenetic_marks: tuple[EpigeneticMark, ...]
    parent_ids: tuple[str, ...]
    generation: int


def create_offspring_package(
    parent_genome: Genome,
    parent_germline: GermlineState,
    *,
    seed: int,
    generation: int,
    second_parent_genome: Genome | None = None,
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
    transmit_epigenetics: bool = False,
) -> InheritancePackage:
    """Create offspring without learned cognitive or embodiment state."""
    if second_parent_genome is None:
        child = mutate_genome(parent_genome, seed=seed, schema=schema)
        parents = (parent_genome.genome_id,)
    else:
        recombined = recombine_genomes(
            parent_genome,
            second_parent_genome,
            seed=seed,
            schema=schema,
        )
        child = mutate_genome(recombined, seed=seed ^ 0x5A17, schema=schema)
        parents = (parent_genome.genome_id, second_parent_genome.genome_id)

    marks: list[EpigeneticMark] = []
    if transmit_epigenetics:
        candidates = {
            **parent_germline.inherited_marks,
            **parent_germline.acquired_marks,
        }
        for locus, mark in sorted(candidates.items()):
            if not schema.spec(locus).regulable:
                continue
            decayed = mark.decay(parent_genome.inheritance.epigenetic_decay)
            if decayed is not None:
                marks.append(decayed)
        marks = marks[: child.inheritance.max_epigenetic_marks]

    return InheritancePackage(
        genome=child,
        epigenetic_marks=tuple(marks),
        parent_ids=parents,
        generation=generation,
    )


__all__ = [
    "EpigeneticMark",
    "GermlineState",
    "InheritancePackage",
    "create_offspring_package",
]
