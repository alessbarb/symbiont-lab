"""Canonical Genome v2 model and strict codec."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping

from .schema import DEFAULT_GENOME_SCHEMA, GenomeSchema

_GENOME_ID_PATTERN = re.compile(r"^genome_[A-Za-z0-9_:+-]{1,96}$")
_COMPAT_CLAUSE = re.compile(r"^(>=|<=|==|>|<)(\d+)\.(\d+)(?:\.(\d+))?$")


class GenomeError(ValueError):
    pass


@dataclass(frozen=True, slots=True, init=False)
class AdaptiveGeneRange:
    baseline: float
    minimum: float
    maximum: float
    adaptation_rate: float

    def __init__(
        self,
        baseline: float | None = None,
        minimum: float = 0.0,
        maximum: float = 1.0,
        adaptation_rate: float = 0.0,
        *,
        initial: float | None = None,
    ) -> None:
        if baseline is None:
            if initial is None:
                raise GenomeError("AdaptiveGeneRange requires baseline or initial")
            baseline = initial
        elif initial is not None and float(initial) != float(baseline):
            raise GenomeError("baseline and initial disagree")
        object.__setattr__(self, "baseline", float(baseline))
        object.__setattr__(self, "minimum", float(minimum))
        object.__setattr__(self, "maximum", float(maximum))
        object.__setattr__(self, "adaptation_rate", float(adaptation_rate))
        self.__post_init__()

    def __post_init__(self) -> None:
        for name, value in (
            ("baseline", self.baseline),
            ("minimum", self.minimum),
            ("maximum", self.maximum),
            ("adaptation_rate", self.adaptation_rate),
        ):
            if not math.isfinite(value):
                raise GenomeError(f"AdaptiveGeneRange.{name} must be finite")
        if not self.minimum <= self.baseline <= self.maximum:
            raise GenomeError("AdaptiveGeneRange requires minimum <= baseline <= maximum")
        if self.adaptation_rate < 0.0:
            raise GenomeError("AdaptiveGeneRange.adaptation_rate must be non-negative")

    @property
    def initial(self) -> float:
        return self.baseline


RangeSpec = AdaptiveGeneRange


@dataclass(frozen=True, slots=True)
class DevelopmentGenes:
    soft_node_budget: int
    soft_edge_budget: int
    sense_node_budget: int
    capacity_growth_sensitivity: float
    consolidation_interval_ticks: int

    @property
    def initial_concepts(self) -> int:
        return 0

    @property
    def sense_retention_ticks(self) -> int:
        return 256


@dataclass(frozen=True, slots=True)
class PlasticityGenes:
    learning_rate: AdaptiveGeneRange
    eligibility_decay: float
    structural_plasticity: AdaptiveGeneRange


@dataclass(frozen=True, slots=True)
class RegulationGenes:
    uncertainty_gain: float
    novelty_gain: float
    prediction_error_gain: float
    controllability_loss_gain: float
    embodiment_mismatch_gain: float
    regulation_smoothing: float
    regulation_decay: float


@dataclass(frozen=True, slots=True)
class SensorimotorGenes:
    spontaneous_activity_baseline: float
    uncertainty_exploration_gain: float
    prediction_error_exploration_gain: float
    exploration_habituation: float
    reacclimation_sensitivity: float


@dataclass(frozen=True, slots=True)
class StructuralGenes:
    growth_threshold: AdaptiveGeneRange
    pruning_threshold: AdaptiveGeneRange
    minimum_support: int
    tentative_lifetime_ticks: int

    @property
    def grow_threshold(self) -> float:
        return self.growth_threshold.baseline

    @property
    def prune_threshold(self) -> float:
        return self.pruning_threshold.baseline


StructureGenes = StructuralGenes


@dataclass(frozen=True, slots=True)
class EvolvabilityGenes:
    development_mutation_scale: float
    plasticity_mutation_scale: float
    regulation_mutation_scale: float
    sensorimotor_mutation_scale: float
    structure_mutation_scale: float
    recombination_linkage: float


@dataclass(frozen=True, slots=True)
class MutationPolicyGenes:
    continuous_sigma: float
    max_fields_per_generation: int


@dataclass(frozen=True, slots=True)
class MotorGenes:
    """Removed v1 body constitution. Any construction is a hard failure."""

    slot_count: int = 0
    basal_cost: float = 0.0
    initial_health: float = 0.0
    execution_threshold: float = 0.0

    def __post_init__(self) -> None:
        raise GenomeError(
            "MotorGenes were removed in Genome v2; actuator cardinality and "
            "physical health belong to the embodiment"
        )


@dataclass(frozen=True, slots=True)
class Genome:
    schema_version: int
    genome_id: str
    kernel_compatibility: str
    development: DevelopmentGenes
    plasticity: PlasticityGenes
    regulation: RegulationGenes
    sensorimotor: SensorimotorGenes
    structure: StructuralGenes
    evolvability: EvolvabilityGenes

    @property
    def genome_instance_id(self) -> str:
        """Lineage/materialization identity, distinct from genotype_hash."""
        return self.genome_id

    @property
    def identity(self) -> str:
        """Compatibility alias for the genome instance identity."""
        return self.genome_id

    @property
    def mutation_policy(self) -> MutationPolicyGenes:
        values = (
            self.evolvability.development_mutation_scale,
            self.evolvability.plasticity_mutation_scale,
            self.evolvability.regulation_mutation_scale,
            self.evolvability.sensorimotor_mutation_scale,
            self.evolvability.structure_mutation_scale,
        )
        return MutationPolicyGenes(
            continuous_sigma=sum(values) / len(values),
            max_fields_per_generation=3,
        )

    @property
    def genome_hash(self) -> str:
        canonical = json.dumps(_genome_to_plain_dict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def genotype_hash(self) -> str:
        material = {"schema_version": self.schema_version, "genes": _gene_tree(self)}
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_kernel_compatibility(spec: str) -> tuple[tuple[str, tuple[int, int, int]], ...]:
    if not isinstance(spec, str) or not spec:
        raise GenomeError("kernel_compatibility must be a non-empty string")
    clauses: list[tuple[str, tuple[int, int, int]]] = []
    for raw in spec.split(","):
        match = _COMPAT_CLAUSE.fullmatch(raw.strip())
        if match is None:
            raise GenomeError(f"invalid kernel compatibility clause {raw!r}")
        op, major, minor, patch = match.groups()
        clauses.append((op, (int(major), int(minor), int(patch or 0))))
    return tuple(clauses)


def satisfies_kernel_compatibility(spec: str, running_version: tuple[int, int, int]) -> bool:
    for op, bound in parse_kernel_compatibility(spec):
        if op == ">=" and running_version < bound:
            return False
        if op == "<=" and running_version > bound:
            return False
        if op == "==" and running_version != bound:
            return False
        if op == ">" and running_version <= bound:
            return False
        if op == "<" and running_version >= bound:
            return False
    return True


def legacy_validation_version(spec: str, running_version: tuple[int, int, int]) -> tuple[int, int, int]:
    if spec in {">=0.55,<0.60", ">=0.59,<0.60"} and running_version[0] == 0 and running_version[1] >= 60:
        return (0, 59, 4)
    return running_version


def _range_to_dict(value: AdaptiveGeneRange) -> dict[str, float]:
    return {
        "baseline": value.baseline,
        "min": value.minimum,
        "max": value.maximum,
        "adaptation_rate": value.adaptation_rate,
    }


def _gene_tree(genome: Genome) -> dict[str, Any]:
    return {
        "development": asdict(genome.development),
        "plasticity": {
            "learning_rate": _range_to_dict(genome.plasticity.learning_rate),
            "eligibility_decay": genome.plasticity.eligibility_decay,
            "structural_plasticity": _range_to_dict(genome.plasticity.structural_plasticity),
        },
        "regulation": asdict(genome.regulation),
        "sensorimotor": asdict(genome.sensorimotor),
        "structure": {
            "growth_threshold": _range_to_dict(genome.structure.growth_threshold),
            "pruning_threshold": _range_to_dict(genome.structure.pruning_threshold),
            "minimum_support": genome.structure.minimum_support,
            "tentative_lifetime_ticks": genome.structure.tentative_lifetime_ticks,
        },
        "evolvability": asdict(genome.evolvability),
    }


def _genome_to_plain_dict(genome: Genome) -> dict[str, Any]:
    return {
        "schema_version": genome.schema_version,
        "genome_id": genome.genome_id,
        "kernel_compatibility": genome.kernel_compatibility,
        **_gene_tree(genome),
    }


def flatten_genes(genome: Genome) -> dict[str, float | int]:
    tree = _gene_tree(genome)
    values: dict[str, float | int] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                mapped = {"min": "minimum", "max": "maximum"}.get(key, key)
                walk(f"{prefix}.{mapped}" if prefix else mapped, child)
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GenomeError(f"non-numeric gene at {prefix}")
        values[prefix] = value

    walk("", tree)
    return values


def _require_mapping(value: Any, field: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenomeError(f"{field} must be an object")
    actual = set(value)
    if actual != keys:
        raise GenomeError(
            f"{field} keys mismatch - missing={sorted(keys-actual)} unknown={sorted(actual-keys)}"
        )
    return value


def _number(value: Any, field: str, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GenomeError(f"{field} must be numeric")
    if integer:
        if not isinstance(value, int):
            raise GenomeError(f"{field} must be an int")
        return value
    result = float(value)
    if not math.isfinite(result):
        raise GenomeError(f"{field} must be finite")
    return result


def _load_range(value: Any, field: str) -> AdaptiveGeneRange:
    mapping = _require_mapping(value, field, {"baseline", "min", "max", "adaptation_rate"})
    return AdaptiveGeneRange(
        baseline=float(_number(mapping["baseline"], f"{field}.baseline")),
        minimum=float(_number(mapping["min"], f"{field}.min")),
        maximum=float(_number(mapping["max"], f"{field}.max")),
        adaptation_rate=float(_number(mapping["adaptation_rate"], f"{field}.adaptation_rate")),
    )


class GenomeCodec:
    TOP_LEVEL = {
        "schema_version",
        "genome_id",
        "kernel_compatibility",
        "development",
        "plasticity",
        "regulation",
        "sensorimotor",
        "structure",
        "evolvability",
    }

    def __init__(self, schema: GenomeSchema = DEFAULT_GENOME_SCHEMA) -> None:
        self.schema = schema

    def load(self, payload: Mapping[str, object]) -> Genome:
        if not isinstance(payload, Mapping) or set(payload) != self.TOP_LEVEL:
            actual = set(payload) if isinstance(payload, Mapping) else set()
            raise GenomeError(
                f"genome top-level keys mismatch - missing={sorted(self.TOP_LEVEL-actual)} "
                f"unknown={sorted(actual-self.TOP_LEVEL)}"
            )
        schema_version = _number(payload["schema_version"], "schema_version", integer=True)
        if schema_version != 2:
            raise GenomeError("GenomeCodec v2 accepts schema_version == 2 only")
        genome_id = payload["genome_id"]
        if not isinstance(genome_id, str) or not _GENOME_ID_PATTERN.fullmatch(genome_id):
            raise GenomeError("invalid genome_id")
        compatibility = payload["kernel_compatibility"]
        if not isinstance(compatibility, str):
            raise GenomeError("kernel_compatibility must be a string")
        parse_kernel_compatibility(compatibility)

        d = _require_mapping(
            payload["development"],
            "development",
            {"soft_node_budget", "soft_edge_budget", "sense_node_budget", "capacity_growth_sensitivity", "consolidation_interval_ticks"},
        )
        development = DevelopmentGenes(
            soft_node_budget=int(_number(d["soft_node_budget"], "development.soft_node_budget", integer=True)),
            soft_edge_budget=int(_number(d["soft_edge_budget"], "development.soft_edge_budget", integer=True)),
            sense_node_budget=int(_number(d["sense_node_budget"], "development.sense_node_budget", integer=True)),
            capacity_growth_sensitivity=float(_number(d["capacity_growth_sensitivity"], "development.capacity_growth_sensitivity")),
            consolidation_interval_ticks=int(_number(d["consolidation_interval_ticks"], "development.consolidation_interval_ticks", integer=True)),
        )

        p = _require_mapping(
            payload["plasticity"],
            "plasticity",
            {"learning_rate", "eligibility_decay", "structural_plasticity"},
        )
        plasticity = PlasticityGenes(
            learning_rate=_load_range(p["learning_rate"], "plasticity.learning_rate"),
            eligibility_decay=float(_number(p["eligibility_decay"], "plasticity.eligibility_decay")),
            structural_plasticity=_load_range(p["structural_plasticity"], "plasticity.structural_plasticity"),
        )

        r = _require_mapping(
            payload["regulation"],
            "regulation",
            {"uncertainty_gain", "novelty_gain", "prediction_error_gain", "controllability_loss_gain", "embodiment_mismatch_gain", "regulation_smoothing", "regulation_decay"},
        )
        regulation = RegulationGenes(**{key: float(_number(r[key], f"regulation.{key}")) for key in r})

        s = _require_mapping(
            payload["sensorimotor"],
            "sensorimotor",
            {"spontaneous_activity_baseline", "uncertainty_exploration_gain", "prediction_error_exploration_gain", "exploration_habituation", "reacclimation_sensitivity"},
        )
        sensorimotor = SensorimotorGenes(
            spontaneous_activity_baseline=float(_number(s["spontaneous_activity_baseline"], "sensorimotor.spontaneous_activity_baseline")),
            uncertainty_exploration_gain=float(_number(s["uncertainty_exploration_gain"], "sensorimotor.uncertainty_exploration_gain")),
            prediction_error_exploration_gain=float(_number(s["prediction_error_exploration_gain"], "sensorimotor.prediction_error_exploration_gain")),
            exploration_habituation=float(_number(s["exploration_habituation"], "sensorimotor.exploration_habituation")),
            reacclimation_sensitivity=float(_number(s["reacclimation_sensitivity"], "sensorimotor.reacclimation_sensitivity")),
        )

        st = _require_mapping(
            payload["structure"],
            "structure",
            {"growth_threshold", "pruning_threshold", "minimum_support", "tentative_lifetime_ticks"},
        )
        structure = StructuralGenes(
            growth_threshold=_load_range(st["growth_threshold"], "structure.growth_threshold"),
            pruning_threshold=_load_range(st["pruning_threshold"], "structure.pruning_threshold"),
            minimum_support=int(_number(st["minimum_support"], "structure.minimum_support", integer=True)),
            tentative_lifetime_ticks=int(_number(st["tentative_lifetime_ticks"], "structure.tentative_lifetime_ticks", integer=True)),
        )

        e = _require_mapping(
            payload["evolvability"],
            "evolvability",
            {"development_mutation_scale", "plasticity_mutation_scale", "regulation_mutation_scale", "sensorimotor_mutation_scale", "structure_mutation_scale", "recombination_linkage"},
        )
        evolvability = EvolvabilityGenes(**{key: float(_number(e[key], f"evolvability.{key}")) for key in e})

        genome = Genome(
            schema_version=2,
            genome_id=genome_id,
            kernel_compatibility=compatibility,
            development=development,
            plasticity=plasticity,
            regulation=regulation,
            sensorimotor=sensorimotor,
            structure=structure,
            evolvability=evolvability,
        )
        self._validate_schema(genome)
        return genome

    def _validate_schema(self, genome: Genome) -> None:
        flat = flatten_genes(genome)
        try:
            self.schema.validate_flat(flat)
        except ValueError as exc:
            raise GenomeError(str(exc)) from exc
        if genome.development.sense_node_budget > genome.development.soft_node_budget:
            raise GenomeError("sense_node_budget cannot exceed soft_node_budget")

    def validate(self, genome: Genome, kernel_limits: Any, *, running_version: tuple[int, int, int]) -> None:
        self._validate_schema(genome)
        if not satisfies_kernel_compatibility(genome.kernel_compatibility, running_version):
            raise GenomeError(
                f"genome kernel_compatibility {genome.kernel_compatibility!r} does not admit running version {running_version}"
            )
        if genome.development.soft_node_budget > int(kernel_limits.max_nodes):
            raise GenomeError("soft_node_budget exceeds KernelLimits.max_nodes")
        if genome.development.sense_node_budget > int(kernel_limits.max_nodes):
            raise GenomeError("sense_node_budget exceeds KernelLimits.max_nodes")
        if genome.development.soft_edge_budget > int(kernel_limits.max_edges):
            raise GenomeError("soft_edge_budget exceeds KernelLimits.max_edges")


__all__ = [
    "AdaptiveGeneRange",
    "DevelopmentGenes",
    "EvolvabilityGenes",
    "Genome",
    "GenomeCodec",
    "GenomeError",
    "MotorGenes",
    "MutationPolicyGenes",
    "PlasticityGenes",
    "RangeSpec",
    "RegulationGenes",
    "SensorimotorGenes",
    "StructuralGenes",
    "StructureGenes",
    "flatten_genes",
    "legacy_validation_version",
    "parse_kernel_compatibility",
    "satisfies_kernel_compatibility",
    "_genome_to_plain_dict",
]
