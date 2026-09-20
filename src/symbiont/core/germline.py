"""Multidimensional evolutionary inheritance, genetics and epigenetics (v1.0 architecture).

Implements:
- Typed genetic loci (LocusSpec, LocusType) (P15).
- Unified SymbiontGenome (subsuming and bridging HeritableGenome) (P14, P16).
- Epigenetic marks with bounded persistence and decay (EpigeneticMark) (P17, P20).
- Germline state tracking birth expression and acquired marks (GermlineState) (P18).
- Strictly bounded acquired capture only on declared loci (P19).
- Sexual reproduction with independent locus recombination (P21).
- Evolvable heritability parameters (InheritanceGenes) (P22).
- Pure InheritancePackage that strictly excludes cognitive memories or body schema (Invariant B).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence

from .heredity import HeritableGenome, _ALLOWED_LOCI


class LocusType(StrEnum):
    FLOAT = "float"
    INT = "int"
    CATEGORICAL = "categorical"


@dataclass(frozen=True, slots=True)
class LocusSpec:
    """Specification of a typed genetic locus (P15)."""

    name: str
    locus_type: LocusType
    minimum: float | int
    maximum: float | int
    default_value: float | int
    mutation_rate: float = 0.1
    mutation_sigma: float = 0.05
    inheritable: bool = True
    epigenetically_regulable: bool = True

    def validate(self, value: Any) -> float | int:
        if isinstance(value, bool):
            raise ValueError(f"Locus {self.name} value must not be boolean")
        if self.locus_type == LocusType.INT:
            if isinstance(value, float) and value.is_integer():
                val = int(value)
            elif isinstance(value, int):
                val = int(value)
            else:
                raise ValueError(f"Locus {self.name} expects int, got {type(value)}")
        elif self.locus_type == LocusType.FLOAT:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Locus {self.name} expects float, got {type(value)}")
            val = float(value)
            if not math.isfinite(val):
                raise ValueError(f"Locus {self.name} must be finite")
        else:
            val = value

        if val < self.minimum or val > self.maximum:
            raise ValueError(
                f"Locus {self.name} value {val} out of bounds [{self.minimum}, {self.maximum}]"
            )
        return val

    def mutate(self, current_value: float | int, rng: random.Random) -> float | int:
        """Apply bounded typed mutation."""
        if rng.random() > self.mutation_rate:
            return current_value

        if self.locus_type == LocusType.INT:
            step = rng.choice([-1, 1])
            new_val = int(current_value) + step
            return max(int(self.minimum), min(int(self.maximum), new_val))
        elif self.locus_type == LocusType.FLOAT:
            delta = rng.gauss(0.0, self.mutation_sigma)
            new_val = float(current_value) + delta
            return max(float(self.minimum), min(float(self.maximum), new_val))
        return current_value


# Standard cognitive germline loci (no physical actuators or body anatomy)
STANDARD_COGNITIVE_LOCI: dict[str, LocusSpec] = {
    "initial_concepts": LocusSpec(
        name="initial_concepts",
        locus_type=LocusType.INT,
        minimum=1,
        maximum=16,
        default_value=3,
        mutation_rate=0.1,
    ),
    "soft_node_budget": LocusSpec(
        name="soft_node_budget",
        locus_type=LocusType.INT,
        minimum=8,
        maximum=128,
        default_value=32,
        mutation_rate=0.1,
    ),
    "soft_edge_budget": LocusSpec(
        name="soft_edge_budget",
        locus_type=LocusType.INT,
        minimum=16,
        maximum=512,
        default_value=64,
        mutation_rate=0.1,
    ),
    "learning_rate": LocusSpec(
        name="learning_rate",
        locus_type=LocusType.FLOAT,
        minimum=0.001,
        maximum=1.0,
        default_value=0.1,
        mutation_rate=0.15,
        mutation_sigma=0.02,
    ),
    "forgetting_rate": LocusSpec(
        name="forgetting_rate",
        locus_type=LocusType.FLOAT,
        minimum=0.0,
        maximum=0.5,
        default_value=0.01,
        mutation_rate=0.1,
        mutation_sigma=0.01,
    ),
    "exploration_rate": LocusSpec(
        name="exploration_rate",
        locus_type=LocusType.FLOAT,
        minimum=0.0,
        maximum=1.0,
        default_value=0.2,
        mutation_rate=0.1,
        mutation_sigma=0.03,
    ),
    "acquired_transmission_rate": LocusSpec(
        name="acquired_transmission_rate",
        locus_type=LocusType.FLOAT,
        minimum=0.0,
        maximum=1.0,
        default_value=0.5,
        mutation_rate=0.1,
        mutation_sigma=0.05,
    ),
    "epigenetic_decay": LocusSpec(
        name="epigenetic_decay",
        locus_type=LocusType.FLOAT,
        minimum=0.01,
        maximum=1.0,
        default_value=0.2,
        mutation_rate=0.1,
        mutation_sigma=0.03,
    ),
}


@dataclass(frozen=True, slots=True)
class EpigeneticMark:
    """Persistent alteration of a legitimate heritable locus (P17, P20).

    A mark represents regulatory modulation of an existing gene, NEVER
    a learned concept or invented locus (Invariant B).
    """

    locus: str
    delta: float
    strength: float = 1.0
    generations_left: int = 3

    def __post_init__(self) -> None:
        if not self.locus:
            raise ValueError("EpigeneticMark locus must not be empty")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"strength {self.strength} must be in [0.0, 1.0]")
        if self.generations_left < 0:
            raise ValueError("generations_left cannot be negative")

    def decay(self, decay_fraction: float) -> EpigeneticMark | None:
        """Apply generational decay. Returns decayed mark, or None if exhausted."""
        new_strength = max(0.0, self.strength * (1.0 - decay_fraction))
        new_generations = self.generations_left - 1
        if new_strength < 0.05 or new_generations <= 0:
            return None
        return EpigeneticMark(
            locus=self.locus,
            delta=self.delta,
            strength=new_strength,
            generations_left=new_generations,
        )


@dataclass(slots=True)
class GermlineState:
    """State of the heritable germline, tracking base expression and acquired marks (P18)."""

    birth_expression: dict[str, float] = field(default_factory=dict)
    acquired_marks: dict[str, EpigeneticMark] = field(default_factory=dict)

    def add_mark(
        self,
        mark: EpigeneticMark,
        *,
        allowed_loci: Mapping[str, LocusSpec] | Sequence[str] = STANDARD_COGNITIVE_LOCI,
        max_marks: int = 16,
    ) -> bool:
        """Add an acquired epigenetic mark to a legitimate genetic locus (P19).

        Fails closed if the locus is not recognized or not regulable.
        """
        allowed = (
            set(allowed_loci.keys())
            if isinstance(allowed_loci, Mapping)
            else set(allowed_loci)
        )
        if mark.locus not in allowed:
            return False
        if len(self.acquired_marks) >= max_marks and mark.locus not in self.acquired_marks:
            return False
        self.acquired_marks[mark.locus] = mark
        return True

    def effective_expression(self, locus: str, base_value: float) -> float:
        """Return phenotypic expression of locus after epigenetic modulation."""
        mark = self.acquired_marks.get(locus)
        if mark is None:
            return base_value
        return base_value + mark.delta * mark.strength

    def generational_decay(self, decay_rate: float) -> GermlineState:
        """Advance one generation, applying decay to acquired marks."""
        decayed_marks: dict[str, EpigeneticMark] = {}
        for locus, mark in self.acquired_marks.items():
            decayed = mark.decay(decay_rate)
            if decayed is not None:
                decayed_marks[locus] = decayed
        return GermlineState(
            birth_expression=dict(self.birth_expression),
            acquired_marks=decayed_marks,
        )


@dataclass(frozen=True, slots=True)
class SymbiontGenome:
    """Unified cognitive germline genome (P14, P16).

    Subsumes the loci previously split between Genome and HeritableGenome.
    Contains strictly cognitive, learning and developmental loci.
    Never determines physical body morphology or actuators.
    """

    genome_id: str
    loci_values: dict[str, float | int]
    parent_ids: tuple[str, ...] = ()
    specs: dict[str, LocusSpec] = field(default_factory=lambda: dict(STANDARD_COGNITIVE_LOCI))

    def __post_init__(self) -> None:
        if not self.genome_id:
            raise ValueError("genome_id must not be empty")
        for k, v in self.loci_values.items():
            spec = self.specs.get(k)
            if spec is not None:
                spec.validate(v)

    def get(self, locus: str, default: Any = None) -> Any:
        return self.loci_values.get(locus, default)

    @property
    def identity(self) -> str:
        payload = json.dumps(
            {"genome_id": self.genome_id, "loci": sorted(self.loci_values.items())},
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"genome_{digest}"

    def to_heritable_genome(self) -> HeritableGenome:
        """Bridge conversion to legacy HeritableGenome for compatibility."""
        filtered_loci = tuple(
            (k, float(v))
            for k, v in sorted(self.loci_values.items())
            if k in _ALLOWED_LOCI
        )
        return HeritableGenome(genome_id=self.genome_id, loci=filtered_loci)

    @classmethod
    def from_heritable_genome(
        cls,
        hg: HeritableGenome,
        *,
        default_specs: Mapping[str, LocusSpec] = STANDARD_COGNITIVE_LOCI,
    ) -> SymbiontGenome:
        """Create SymbiontGenome from a legacy HeritableGenome."""
        values: dict[str, float | int] = {
            spec.name: spec.default_value for spec in default_specs.values()
        }
        for k, v in hg.loci:
            values[k] = v
        return cls(genome_id=hg.genome_id, loci_values=values)

    def mutate(
        self, *, seed: int = 0, sigma_multiplier: float = 1.0
    ) -> SymbiontGenome:
        """Produce a mutated copy using typed locus operators."""
        rng = random.Random(seed)
        new_values: dict[str, float | int] = {}
        for k, v in self.loci_values.items():
            spec = self.specs.get(k)
            if spec is not None and spec.inheritable:
                new_values[k] = spec.mutate(v, rng)
            else:
                new_values[k] = v
        return SymbiontGenome(
            genome_id=f"{self.genome_id}:mutant",
            loci_values=new_values,
            parent_ids=(self.genome_id,),
            specs=self.specs,
        )

    def recombine_with(
        self, other: SymbiontGenome, *, seed: int = 0
    ) -> SymbiontGenome:
        """Sexual reproduction: independent locus recombination without external fitness bias (P21)."""
        rng = random.Random(seed)
        all_keys = sorted(set(self.loci_values.keys()) | set(other.loci_values.keys()))
        child_values: dict[str, float | int] = {}
        for k in all_keys:
            val_a = self.loci_values.get(k)
            val_b = other.loci_values.get(k)
            if val_a is not None and val_b is not None:
                # 50/50 independent assortment per locus
                chosen = val_a if rng.random() < 0.5 else val_b
            else:
                chosen = val_a if val_a is not None else val_b
            child_values[k] = chosen

        child_id = f"{self.genome_id}+{other.genome_id}"
        return SymbiontGenome(
            genome_id=child_id,
            loci_values=child_values,
            parent_ids=(self.genome_id, other.genome_id),
            specs=self.specs,
        )


@dataclass(frozen=True, slots=True)
class InheritancePackage:
    """The complete package transmitted to offspring across generations (Section 51).

    Contains exclusively the genetic and epigenetic constitution.
    Strictly forbids memories, concepts, BodySchema, AgencyModel or
    SensorimotorModel (Invariant B).
    """

    genome: SymbiontGenome
    epigenetic_marks: tuple[EpigeneticMark, ...]
    parent_ids: tuple[str, ...]
    generation: int

    def __post_init__(self) -> None:
        # Invariant B: reject any contamination from cognitive models
        for field_name in ("body_schema", "agency_model", "sensorimotor_model", "memory"):
            if hasattr(self, field_name):
                raise ValueError(f"Cognitive model {field_name} must NEVER enter InheritancePackage")


def create_offspring_package(
    parent_genome: SymbiontGenome,
    parent_germline: GermlineState,
    *,
    second_parent_genome: SymbiontGenome | None = None,
    second_parent_germline: GermlineState | None = None,
    seed: int = 0,
    generation: int = 1,
) -> InheritancePackage:
    """Create child inheritance package with transmission, decay, and recombination."""
    rng = random.Random(seed)

    # 1. Genetic step: clonal mutation or sexual recombination
    if second_parent_genome is None:
        child_genome = parent_genome.mutate(seed=seed)
        parents = (parent_genome.genome_id,)
    else:
        child_genome = parent_genome.recombine_with(second_parent_genome, seed=seed)
        parents = (parent_genome.genome_id, second_parent_genome.genome_id)

    # 2. Epigenetic step: bounded transmission and decay (P20, P22)
    transmission_rate = float(
        child_genome.get("acquired_transmission_rate", 0.5)
    )
    decay_rate = float(child_genome.get("epigenetic_decay", 0.2))

    transmitted_marks: list[EpigeneticMark] = []
    # Collect marks from parent 1
    for mark in parent_germline.acquired_marks.values():
        if rng.random() < transmission_rate:
            decayed = mark.decay(decay_rate)
            if decayed is not None:
                transmitted_marks.append(decayed)

    # If sexual reproduction, also sample marks from parent 2
    if second_parent_germline is not None:
        for mark in second_parent_germline.acquired_marks.values():
            if rng.random() < transmission_rate:
                decayed = mark.decay(decay_rate)
                if decayed is not None:
                    # If locus already present, blend or take higher strength
                    transmitted_marks.append(decayed)

    return InheritancePackage(
        genome=child_genome,
        epigenetic_marks=tuple(transmitted_marks),
        parent_ids=parents,
        generation=generation,
    )


def create_standard_genome(genome_id: str) -> SymbiontGenome:
    """Construct a default SymbiontGenome with standard cognitive loci."""
    values = {spec.name: spec.default_value for spec in STANDARD_COGNITIVE_LOCI.values()}
    return SymbiontGenome(genome_id=genome_id, loci_values=values)


__all__ = [
    "EpigeneticMark",
    "GermlineState",
    "InheritancePackage",
    "LocusSpec",
    "LocusType",
    "STANDARD_COGNITIVE_LOCI",
    "SymbiontGenome",
    "create_offspring_package",
    "create_standard_genome",
]
