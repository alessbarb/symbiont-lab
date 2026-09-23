"""Multidimensional evolutionary inheritance, genetics and epigenetics (v1.0 architecture).

Implements:
- Typed genetic loci (LocusSpec, LocusType) (P15).
- Unified SymbiontGenome (subsuming and bridging HeritableGenome) (P14, P16).
- Epigenetic marks with bounded persistence and decay (EpigeneticMark) (P17, P20).
- Germline state tracking birth expression and acquired marks (GermlineState) (P18).
- Strictly bounded acquired capture only on declared loci (P19, AUD-010, AUD-028).
- Sexual reproduction with independent locus recombination and mutation (P21, AUD-022, AUD-023).
- Evolvable heritability parameters (InheritanceGenes) (P22, AUD-026, AUD-027).
- Pure InheritancePackage that strictly excludes cognitive memories, body schema or semantic IDs (Invariant B, AUD-042, AUD-044).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import math
import random
from types import MappingProxyType
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

    def clamp(self, value: float | int) -> float | int:
        """Clamp a modulated value to within the locus bounds (AUD-024)."""
        if self.locus_type == LocusType.INT:
            return max(int(self.minimum), min(int(self.maximum), int(round(value))))
        return max(float(self.minimum), min(float(self.maximum), float(value)))

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
    "max_epigenetic_marks": LocusSpec(
        name="max_epigenetic_marks",
        locus_type=LocusType.INT,
        minimum=1,
        maximum=32,
        default_value=8,
        mutation_rate=0.05,
    ),
}


@dataclass(frozen=True, slots=True)
class InheritanceGenes:
    """Explicit parameters governing heritability and epigenetic transmission (AUD-027)."""

    parental_transmission_rate: float = 0.5
    epigenetic_decay: float = 0.2
    max_epigenetic_marks: int = 8

    def __post_init__(self) -> None:
        if not (0.0 <= self.parental_transmission_rate <= 1.0):
            raise ValueError("parental_transmission_rate must be in [0, 1]")
        if not (0.0 <= self.epigenetic_decay <= 1.0):
            raise ValueError("epigenetic_decay must be in [0, 1]")
        if self.max_epigenetic_marks < 1:
            raise ValueError("max_epigenetic_marks must be >= 1")


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
        if not math.isfinite(self.delta):
            raise ValueError("EpigeneticMark delta must be finite (AUD-025)")
        if not math.isfinite(self.strength) or not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength {self.strength} must be finite in [0.0, 1.0] (AUD-025)")
        if self.generations_left < 0:
            raise ValueError("generations_left cannot be negative")

    def decay(self, decay_fraction: float) -> EpigeneticMark | None:
        """Apply generational decay with strict bounds validation (AUD-025, AUD-029)."""
        if not math.isfinite(decay_fraction) or not (0.0 <= decay_fraction <= 1.0):
            raise ValueError(f"decay_fraction {decay_fraction} must be in [0.0, 1.0]")
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
    inherited_marks: dict[str, EpigeneticMark] = field(default_factory=dict)
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
        occupied_loci = set(self.inherited_marks) | set(self.acquired_marks)
        if len(occupied_loci) >= max_marks and mark.locus not in occupied_loci:
            return False
        self.acquired_marks[mark.locus] = mark
        return True

    def capture_acquired_variation(
        self,
        current_expression: Mapping[str, float],
        specs: Mapping[str, LocusSpec] = STANDARD_COGNITIVE_LOCI,
        *,
        min_delta: float = 0.02,
        max_marks: int = 16,
    ) -> list[str]:
        """Automatically detect persistent lifetime shift between birth and current state (AUD-010, AUD-028).

        Generates or updates EpigeneticMarks for regulable loci without requiring
        manual external intervention.
        """
        captured: list[str] = []
        for locus_name, spec in specs.items():
            if not spec.epigenetically_regulable:
                continue
            birth_val = self.birth_expression.get(locus_name, float(spec.default_value))
            curr_val = current_expression.get(locus_name, birth_val)
            delta = curr_val - birth_val
            if abs(delta) >= min_delta:
                mark = EpigeneticMark(
                    locus=locus_name,
                    delta=delta,
                    strength=1.0,
                    generations_left=3,
                )
                if self.add_mark(mark, allowed_loci=specs, max_marks=max_marks):
                    captured.append(locus_name)
        return captured

    def effective_expression(
        self,
        locus: str,
        base_value: float,
        spec: LocusSpec | None = None,
    ) -> float:
        """Return phenotypic expression of locus after epigenetic modulation clamped to spec (AUD-024)."""
        raw = float(base_value)
        inherited = self.inherited_marks.get(locus)
        if inherited is not None:
            raw += inherited.delta * inherited.strength
        acquired = self.acquired_marks.get(locus)
        if acquired is not None:
            raw += acquired.delta * acquired.strength
        if spec is not None:
            return float(spec.clamp(raw))
        return raw

    def generational_decay(self, decay_rate: float) -> GermlineState:
        """Advance one generation, applying decay to acquired marks with bound checks (AUD-029)."""
        if not math.isfinite(decay_rate) or not (0.0 <= decay_rate <= 1.0):
            raise ValueError(f"decay_rate {decay_rate} must be in [0.0, 1.0]")
        decayed_inherited: dict[str, EpigeneticMark] = {}
        for locus, mark in self.inherited_marks.items():
            decayed = mark.decay(decay_rate)
            if decayed is not None:
                decayed_inherited[locus] = decayed
        decayed_acquired: dict[str, EpigeneticMark] = {}
        for locus, mark in self.acquired_marks.items():
            decayed = mark.decay(decay_rate)
            if decayed is not None:
                decayed_acquired[locus] = decayed
        return GermlineState(
            birth_expression=dict(self.birth_expression),
            inherited_marks=decayed_inherited,
            acquired_marks=decayed_acquired,
        )


class SymbiontGenome:
    """Unified cognitive germline genome (P14, P16).

    Truly immutable (AUD-020). Rejects unknown loci fail-closed (AUD-019).
    Identity hashes full constitution including specs (AUD-021).
    Never determines physical body morphology or actuators.
    """

    def __init__(
        self,
        genome_id: str,
        loci_values: Mapping[str, float | int],
        parent_ids: Sequence[str] = (),
        specs: Mapping[str, LocusSpec] | None = None,
    ) -> None:
        if not genome_id:
            raise ValueError("genome_id must not be empty")

        active_specs = dict(specs) if specs is not None else dict(STANDARD_COGNITIVE_LOCI)

        # WARN(AUD-019): Fail closed if any locus is unknown
        unknown = set(loci_values.keys()) - set(active_specs.keys())
        if unknown:
            raise ValueError(f"unknown loci rejected by constitution: {sorted(unknown)}")

        validated: dict[str, float | int] = {}
        for k, v in loci_values.items():
            spec = active_specs[k]
            validated[k] = spec.validate(v)

        # AUD-020: Truly immutable state
        self._genome_id = str(genome_id)
        self._loci_values = MappingProxyType(validated)
        self._parent_ids = tuple(str(p) for p in parent_ids)
        self._specs = MappingProxyType(active_specs)

    @property
    def genome_id(self) -> str:
        return self._genome_id

    @property
    def loci_values(self) -> Mapping[str, float | int]:
        return self._loci_values

    @property
    def parent_ids(self) -> tuple[str, ...]:
        return self._parent_ids

    @property
    def specs(self) -> Mapping[str, LocusSpec]:
        return self._specs

    def get(self, locus: str, default: Any = None) -> Any:
        return self._loci_values.get(locus, default)

    @property
    def identity(self) -> str:
        """Deterministic fingerprint hashing genome_id, loci_values and specs (AUD-021)."""
        spec_summary = [
            (
                s.name,
                str(s.locus_type),
                s.minimum,
                s.maximum,
                s.mutation_rate,
                s.mutation_sigma,
                s.epigenetically_regulable,
            )
            for s in sorted(self._specs.values(), key=lambda item: item.name)
        ]
        payload = json.dumps(
            {
                "genome_id": self._genome_id,
                "loci": sorted(self._loci_values.items()),
                "specs": spec_summary,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"genome_{digest}"

    def to_heritable_genome(self) -> HeritableGenome:
        """Bridge conversion to legacy HeritableGenome for compatibility."""
        filtered_loci = tuple(
            (k, float(v))
            for k, v in sorted(self._loci_values.items())
            if k in _ALLOWED_LOCI
        )
        return HeritableGenome(genome_id=self._genome_id, loci=filtered_loci)

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
            if k in default_specs:
                spec = default_specs[k]
                if spec.locus_type == LocusType.INT:
                    values[k] = int(round(v))
                else:
                    values[k] = v
        return cls(genome_id=hg.genome_id, loci_values=values, specs=default_specs)

    def mutate(
        self, *, seed: int = 0, sigma_multiplier: float = 1.0
    ) -> SymbiontGenome:
        """Produce a mutated copy using typed locus operators."""
        rng = random.Random(seed)
        new_values: dict[str, float | int] = {}
        for k, v in self._loci_values.items():
            spec = self._specs.get(k)
            if spec is not None and spec.inheritable:
                new_values[k] = spec.mutate(v, rng)
            else:
                new_values[k] = v
        return SymbiontGenome(
            genome_id=f"{self._genome_id}:mutant",
            loci_values=new_values,
            parent_ids=(self._genome_id,),
            specs=self._specs,
        )

    def recombine_with(
        self, other: SymbiontGenome, *, seed: int = 0
    ) -> SymbiontGenome:
        """Sexual reproduction: independent locus recombination without external fitness bias (P21)."""
        rng = random.Random(seed)
        all_keys = sorted(set(self._loci_values.keys()) | set(other._loci_values.keys()))
        child_values: dict[str, float | int] = {}
        for k in all_keys:
            val_a = self._loci_values.get(k)
            val_b = other._loci_values.get(k)
            if val_a is not None and val_b is not None:
                chosen = val_a if rng.random() < 0.5 else val_b
            else:
                chosen = val_a if val_a is not None else val_b
            child_values[k] = chosen

        child_id = f"{self._genome_id}+{other._genome_id}"
        return SymbiontGenome(
            genome_id=child_id,
            loci_values=child_values,
            parent_ids=(self._genome_id, other._genome_id),
            specs=self._specs,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SymbiontGenome):
            return NotImplemented
        return self._genome_id == other._genome_id and dict(self._loci_values) == dict(other._loci_values)

    def __hash__(self) -> int:
        return hash((self._genome_id, tuple(sorted(self._loci_values.items()))))


@dataclass(frozen=True, slots=True)
class InheritancePackage:
    """The complete package transmitted to offspring across generations (Section 51).

    Contains exclusively the genetic and epigenetic constitution.
    Strictly forbids memories, concepts, BodySchema, AgencyModel or
    SensorimotorModel (Invariant B, AUD-042, AUD-044).
    """

    genome: SymbiontGenome
    epigenetic_marks: tuple[EpigeneticMark, ...]
    parent_ids: tuple[str, ...]
    generation: int

    def __post_init__(self) -> None:
        # WARN(Invariant B): reject any semantic or cognitive payload in loci or marks (AUD-042, AUD-044)
        forbidden_substrings = (
            "threat", "food", "body", "schema",
            "agency", "sensorimotor", "signal", "resource", "action",
        )
        for mark in self.epigenetic_marks:
            for forbidden in forbidden_substrings:
                if forbidden in mark.locus.lower():
                    raise ValueError(f"Forbidden semantic token '{forbidden}' in epigenetic mark locus")
            if mark.locus == "concept" or mark.locus.startswith("concept_") or mark.locus.endswith("_concept"):
                raise ValueError("Forbidden semantic token 'concept' in epigenetic mark locus")

        for k in self.genome.loci_values.keys():
            for forbidden in forbidden_substrings:
                if forbidden in k.lower():
                    raise ValueError(f"Forbidden semantic token '{forbidden}' in genome locus")
            if k == "concept" or k.startswith("concept_") or k.endswith("_concept"):
                raise ValueError("Forbidden semantic token 'concept' in genome locus")


def _transmissible_parent_marks(
    germline: GermlineState,
) -> dict[str, EpigeneticMark]:
    """Consolidate inherited + newly acquired regulation for reproduction.

    Ontogeny keeps the channels separate so a lifetime acquisition cannot
    overwrite inherited history. Reproduction emits at most one mark per locus,
    preserving the total effective regulatory contribution.
    """
    by_locus: dict[str, list[EpigeneticMark]] = {}
    for source in (germline.inherited_marks, germline.acquired_marks):
        for locus, mark in source.items():
            by_locus.setdefault(locus, []).append(mark)

    combined: dict[str, EpigeneticMark] = {}
    for locus, marks in by_locus.items():
        if len(marks) == 1:
            combined[locus] = marks[0]
            continue
        contribution = sum(mark.delta * mark.strength for mark in marks)
        combined[locus] = EpigeneticMark(
            locus=locus,
            delta=contribution,
            strength=1.0,
            generations_left=max(mark.generations_left for mark in marks),
        )
    return combined


def create_offspring_package(
    parent_genome: SymbiontGenome,
    parent_germline: GermlineState,
    *,
    second_parent_genome: SymbiontGenome | None = None,
    second_parent_germline: GermlineState | None = None,
    seed: int = 0,
    generation: int = 1,
) -> InheritancePackage:
    """Create child inheritance package with transmission, decay, recombination and mutation.

    Applies mutation after recombination (AUD-022).
    Uses parental transmission rate (AUD-026).
    Resolves sexual conflict so there is at most one mark per locus (AUD-023).
    """
    rng = random.Random(seed)

    # 1. Genetic step: clonal mutation OR sexual recombination + mutation (AUD-022)
    if second_parent_genome is None:
        child_genome = parent_genome.mutate(seed=seed)
        parents = (parent_genome.genome_id,)
        transmission_rate = float(parent_genome.get("acquired_transmission_rate", 0.5))
        decay_rate = float(parent_genome.get("epigenetic_decay", 0.2))
    else:
        recombined = parent_genome.recombine_with(second_parent_genome, seed=seed)
        child_genome = recombined.mutate(seed=seed)
        parents = (parent_genome.genome_id, second_parent_genome.genome_id)
        # Parental transmission rate from parent A and parent B (AUD-026)
        rate_a = float(parent_genome.get("acquired_transmission_rate", 0.5))
        rate_b = float(second_parent_genome.get("acquired_transmission_rate", 0.5))
        transmission_rate = (rate_a + rate_b) / 2.0
        decay_a = float(parent_genome.get("epigenetic_decay", 0.2))
        decay_b = float(second_parent_genome.get("epigenetic_decay", 0.2))
        decay_rate = (decay_a + decay_b) / 2.0

    # 2. Epigenetic step: bounded transmission and decay (P20, P22)
    marks_by_locus: dict[str, EpigeneticMark] = {}

    for mark in _transmissible_parent_marks(parent_germline).values():
        if rng.random() < transmission_rate:
            decayed = mark.decay(decay_rate)
            if decayed is not None:
                marks_by_locus[decayed.locus] = decayed

    if second_parent_germline is not None:
        for mark in _transmissible_parent_marks(second_parent_germline).values():
            if rng.random() < transmission_rate:
                decayed = mark.decay(decay_rate)
                if decayed is not None:
                    # AUD-023: Resolve sexual conflict into a single mark per locus
                    if decayed.locus in marks_by_locus:
                        existing = marks_by_locus[decayed.locus]
                        blended = EpigeneticMark(
                            locus=decayed.locus,
                            delta=(existing.delta + decayed.delta) / 2.0,
                            strength=max(existing.strength, decayed.strength),
                            generations_left=max(existing.generations_left, decayed.generations_left),
                        )
                        marks_by_locus[decayed.locus] = blended
                    else:
                        marks_by_locus[decayed.locus] = decayed

    # Child constitutional mark budget. If transmission produces more marks
    # than the child can carry, select without semantic/fitness preference
    # using the reproduction RNG, then canonicalize output ordering.
    max_child_marks = int(child_genome.get("max_epigenetic_marks", 8))
    transmitted_marks = list(marks_by_locus.values())
    if len(transmitted_marks) > max_child_marks:
        rng.shuffle(transmitted_marks)
        transmitted_marks = transmitted_marks[:max_child_marks]
    transmitted_marks.sort(key=lambda mark: mark.locus)

    return InheritancePackage(
        genome=child_genome,
        epigenetic_marks=tuple(transmitted_marks),
        parent_ids=parents,
        generation=generation,
    )


def create_germline_state(
    genome: SymbiontGenome,
    *,
    epigenetic_marks: Sequence[EpigeneticMark] = (),
) -> GermlineState:
    """Create canonical germline state with effective birth expression.

    Inherited epigenetic marks are part of the phenotype at birth. The
    birth_expression baseline therefore includes their effect so those marks
    are not later misclassified as newly acquired lifetime variation.
    """
    marks = {mark.locus: mark for mark in epigenetic_marks}
    provisional = GermlineState(
        birth_expression=dict(genome.loci_values),
        inherited_marks=marks,
    )
    effective_birth: dict[str, float] = {}
    for locus, base in genome.loci_values.items():
        spec = genome.specs.get(locus)
        effective_birth[locus] = provisional.effective_expression(
            locus,
            float(base),
            spec=spec,
        )
    return GermlineState(
        birth_expression=effective_birth,
        inherited_marks=marks,
        acquired_marks={},
    )


def create_standard_genome(genome_id: str) -> SymbiontGenome:
    """Construct a default SymbiontGenome with standard cognitive loci."""
    values = {spec.name: spec.default_value for spec in STANDARD_COGNITIVE_LOCI.values()}
    return SymbiontGenome(genome_id=genome_id, loci_values=values)


__all__ = [
    "EpigeneticMark",
    "GermlineState",
    "InheritanceGenes",
    "InheritancePackage",
    "LocusSpec",
    "LocusType",
    "STANDARD_COGNITIVE_LOCI",
    "SymbiontGenome",
    "create_offspring_package",
    "create_germline_state",
    "create_standard_genome",
]
