"""Closed Genome v2 schema owned by the Symbiont kernel.

The schema describes which values may vary genetically. It is not part of an
individual genotype and therefore never changes an organism's genotype hash.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any, Mapping


class GeneType(StrEnum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"


class MutationMode(StrEnum):
    LINEAR = "linear"
    INTEGER_STEP = "integer_step"
    LOG_SCALE = "log_scale"
    TOGGLE = "toggle"
    CHOICE = "choice"


@dataclass(frozen=True, slots=True)
class GeneSpec:
    locus: str
    gene_type: GeneType
    minimum: float | int | None = None
    maximum: float | int | None = None
    mutation_probability: float = 0.1
    mutation_scale: float = 0.05
    mutation_mode: MutationMode = MutationMode.LINEAR
    inheritable: bool = True
    regulable: bool = False
    recombination_group: str = ""
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.locus:
            raise ValueError("gene locus must not be empty")
        if not math.isfinite(self.mutation_probability) or not 0.0 <= self.mutation_probability <= 1.0:
            raise ValueError(f"{self.locus}: mutation_probability must be in [0,1]")
        if not math.isfinite(self.mutation_scale) or self.mutation_scale < 0.0:
            raise ValueError(f"{self.locus}: mutation_scale must be finite and non-negative")
        if self.gene_type == GeneType.ENUM:
            if not self.choices or len(set(self.choices)) != len(self.choices):
                raise ValueError(f"{self.locus}: enum choices must be non-empty and unique")
        elif self.choices:
            raise ValueError(f"{self.locus}: choices are valid only for enum genes")
        if self.gene_type in (GeneType.FLOAT, GeneType.INT):
            if self.minimum is None or self.maximum is None:
                raise ValueError(f"{self.locus}: numeric genes require minimum and maximum")
            if self.minimum > self.maximum:
                raise ValueError(f"{self.locus}: minimum must be <= maximum")

    def validate(self, value: Any) -> float | int | bool | str:
        if self.gene_type == GeneType.BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{self.locus}: expected bool")
            return value
        if self.gene_type == GeneType.ENUM:
            if not isinstance(value, str) or value not in self.choices:
                raise ValueError(f"{self.locus}: expected one of {self.choices!r}")
            return value
        if isinstance(value, bool):
            raise ValueError(f"{self.locus}: boolean is not numeric")
        if self.gene_type == GeneType.INT:
            if not isinstance(value, int):
                raise ValueError(f"{self.locus}: expected int")
            result: float | int = value
        else:
            if not isinstance(value, (int, float)):
                raise ValueError(f"{self.locus}: expected float")
            result = float(value)
            if not math.isfinite(result):
                raise ValueError(f"{self.locus}: value must be finite")
        assert self.minimum is not None and self.maximum is not None
        if result < self.minimum or result > self.maximum:
            raise ValueError(
                f"{self.locus}: {result!r} outside [{self.minimum!r}, {self.maximum!r}]"
            )
        return result

    def clamp(self, value: float | int) -> float | int:
        if self.gene_type not in (GeneType.FLOAT, GeneType.INT):
            raise TypeError(f"{self.locus}: clamp is valid only for numeric genes")
        assert self.minimum is not None and self.maximum is not None
        bounded = max(float(self.minimum), min(float(self.maximum), float(value)))
        if self.gene_type == GeneType.INT:
            return int(round(bounded))
        return bounded


class GenomeSchema:
    """Immutable closed catalogue of evolvable loci."""

    def __init__(self, specs: Mapping[str, GeneSpec]) -> None:
        copied = dict(specs)
        if not copied or any(name != spec.locus for name, spec in copied.items()):
            raise ValueError("genome schema keys must exactly match GeneSpec.locus")
        self._specs = copied

    @property
    def specs(self) -> Mapping[str, GeneSpec]:
        return dict(self._specs)

    def spec(self, locus: str) -> GeneSpec:
        try:
            return self._specs[locus]
        except KeyError as exc:
            raise ValueError(f"unknown gene locus {locus!r}") from exc

    def validate_flat(self, values: Mapping[str, Any], *, require_all: bool = True) -> dict[str, Any]:
        unknown = set(values) - set(self._specs)
        if unknown:
            raise ValueError(f"unknown genome loci: {sorted(unknown)}")
        if require_all:
            missing = set(self._specs) - set(values)
            if missing:
                raise ValueError(f"missing genome loci: {sorted(missing)}")
        return {locus: self._specs[locus].validate(value) for locus, value in values.items()}

    def recombination_groups(self) -> dict[str, tuple[str, ...]]:
        groups: dict[str, list[str]] = {}
        for locus, spec in self._specs.items():
            group = spec.recombination_group or locus
            groups.setdefault(group, []).append(locus)
        return {group: tuple(sorted(loci)) for group, loci in groups.items()}


def _float(
    locus: str,
    low: float,
    high: float,
    *,
    scale: float = 0.05,
    p: float = 0.1,
    regulable: bool = False,
    group: str = "",
) -> GeneSpec:
    return GeneSpec(
        locus=locus,
        gene_type=GeneType.FLOAT,
        minimum=low,
        maximum=high,
        mutation_probability=p,
        mutation_scale=scale,
        mutation_mode=MutationMode.LINEAR,
        regulable=regulable,
        recombination_group=group,
    )


def _int(
    locus: str,
    low: int,
    high: int,
    *,
    step: float = 1.0,
    p: float = 0.1,
    group: str = "",
) -> GeneSpec:
    return GeneSpec(
        locus=locus,
        gene_type=GeneType.INT,
        minimum=low,
        maximum=high,
        mutation_probability=p,
        mutation_scale=step,
        mutation_mode=MutationMode.INTEGER_STEP,
        recombination_group=group,
    )


DEFAULT_GENOME_SCHEMA = GenomeSchema(
    {
        "development.soft_node_budget": _int("development.soft_node_budget", 8, 768, step=8, group="development.capacity"),
        "development.soft_edge_budget": _int("development.soft_edge_budget", 16, 6144, step=32, group="development.capacity"),
        "development.sense_node_budget": _int("development.sense_node_budget", 4, 256, step=4, group="development.capacity"),
        "development.capacity_growth_sensitivity": _float("development.capacity_growth_sensitivity", 0.0, 1.0, scale=0.04),
        "development.consolidation_interval_ticks": _int("development.consolidation_interval_ticks", 1, 4096, step=8),
        "plasticity.learning_rate.baseline": _float("plasticity.learning_rate.baseline", 0.0001, 0.5, scale=0.01, regulable=True, group="plasticity.learning_rate"),
        "plasticity.learning_rate.minimum": _float("plasticity.learning_rate.minimum", 0.0, 0.5, scale=0.005, group="plasticity.learning_rate"),
        "plasticity.learning_rate.maximum": _float("plasticity.learning_rate.maximum", 0.0001, 1.0, scale=0.02, group="plasticity.learning_rate"),
        "plasticity.learning_rate.adaptation_rate": _float("plasticity.learning_rate.adaptation_rate", 0.00001, 0.25, scale=0.005, group="plasticity.learning_rate"),
        "plasticity.eligibility_decay": _float("plasticity.eligibility_decay", 0.0, 1.0, scale=0.02),
        "plasticity.structural_plasticity.baseline": _float("plasticity.structural_plasticity.baseline", 0.0, 1.0, scale=0.03, regulable=True, group="plasticity.structural"),
        "plasticity.structural_plasticity.minimum": _float("plasticity.structural_plasticity.minimum", 0.0, 1.0, scale=0.02, group="plasticity.structural"),
        "plasticity.structural_plasticity.maximum": _float("plasticity.structural_plasticity.maximum", 0.0, 1.0, scale=0.02, group="plasticity.structural"),
        "plasticity.structural_plasticity.adaptation_rate": _float("plasticity.structural_plasticity.adaptation_rate", 0.0, 0.25, scale=0.005, group="plasticity.structural"),
        "regulation.uncertainty_gain": _float("regulation.uncertainty_gain", 0.0, 2.0, scale=0.05),
        "regulation.novelty_gain": _float("regulation.novelty_gain", 0.0, 2.0, scale=0.05),
        "regulation.prediction_error_gain": _float("regulation.prediction_error_gain", 0.0, 2.0, scale=0.05),
        "regulation.controllability_loss_gain": _float("regulation.controllability_loss_gain", 0.0, 2.0, scale=0.05),
        "regulation.embodiment_mismatch_gain": _float("regulation.embodiment_mismatch_gain", 0.0, 2.0, scale=0.05),
        "regulation.regulation_smoothing": _float("regulation.regulation_smoothing", 0.001, 1.0, scale=0.02),
        "regulation.regulation_decay": _float("regulation.regulation_decay", 0.0, 1.0, scale=0.02),
        "sensorimotor.spontaneous_activity_baseline": _float("sensorimotor.spontaneous_activity_baseline", 0.0, 1.0, scale=0.03, regulable=True),
        "sensorimotor.uncertainty_exploration_gain": _float("sensorimotor.uncertainty_exploration_gain", 0.0, 2.0, scale=0.05),
        "sensorimotor.prediction_error_exploration_gain": _float("sensorimotor.prediction_error_exploration_gain", 0.0, 2.0, scale=0.05),
        "sensorimotor.exploration_habituation": _float("sensorimotor.exploration_habituation", 0.0, 0.25, scale=0.005),
        "sensorimotor.reacclimation_sensitivity": _float("sensorimotor.reacclimation_sensitivity", 0.0, 2.0, scale=0.05),
        "structure.growth_threshold.baseline": _float("structure.growth_threshold.baseline", 0.0, 1.0, scale=0.03, regulable=True, group="structure.growth"),
        "structure.growth_threshold.minimum": _float("structure.growth_threshold.minimum", 0.0, 1.0, scale=0.02, group="structure.growth"),
        "structure.growth_threshold.maximum": _float("structure.growth_threshold.maximum", 0.0, 1.0, scale=0.02, group="structure.growth"),
        "structure.growth_threshold.adaptation_rate": _float("structure.growth_threshold.adaptation_rate", 0.0, 0.25, scale=0.005, group="structure.growth"),
        "structure.pruning_threshold.baseline": _float("structure.pruning_threshold.baseline", 0.0, 1.0, scale=0.02, regulable=True, group="structure.pruning"),
        "structure.pruning_threshold.minimum": _float("structure.pruning_threshold.minimum", 0.0, 1.0, scale=0.02, group="structure.pruning"),
        "structure.pruning_threshold.maximum": _float("structure.pruning_threshold.maximum", 0.0, 1.0, scale=0.02, group="structure.pruning"),
        "structure.pruning_threshold.adaptation_rate": _float("structure.pruning_threshold.adaptation_rate", 0.0, 0.25, scale=0.005, group="structure.pruning"),
        "structure.minimum_support": _int("structure.minimum_support", 1, 4096, step=2),
        "structure.tentative_lifetime_ticks": _int("structure.tentative_lifetime_ticks", 1, 65536, step=8),
        "evolvability.development_mutation_scale": _float("evolvability.development_mutation_scale", 0.0, 2.0, scale=0.05),
        "evolvability.plasticity_mutation_scale": _float("evolvability.plasticity_mutation_scale", 0.0, 2.0, scale=0.05),
        "evolvability.regulation_mutation_scale": _float("evolvability.regulation_mutation_scale", 0.0, 2.0, scale=0.05),
        "evolvability.sensorimotor_mutation_scale": _float("evolvability.sensorimotor_mutation_scale", 0.0, 2.0, scale=0.05),
        "evolvability.structure_mutation_scale": _float("evolvability.structure_mutation_scale", 0.0, 2.0, scale=0.05),
        "evolvability.recombination_linkage": _float("evolvability.recombination_linkage", 0.0, 1.0, scale=0.03),
    }
)


__all__ = [
    "DEFAULT_GENOME_SCHEMA",
    "GeneSpec",
    "GeneType",
    "GenomeSchema",
    "MutationMode",
]
