from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .limits import KernelLimits

_GENOME_ID_PATTERN = re.compile(r"^genome_[A-Za-z0-9_-]{1,64}$")
_MAX_PARENT_IDS = 8
_COMPAT_CLAUSE = re.compile(r"^(>=|<=|==|>|<)(\d+)\.(\d+)(?:\.(\d+))?$")
_DEFAULT_SENSE_NODE_BUDGET = 32
_DEFAULT_SENSE_RETENTION_TICKS = 256
_DEVELOPMENT_REQUIRED_KEYS = frozenset(
    {"initial_concepts", "soft_node_budget", "soft_edge_budget", "consolidation_interval_ticks"}
)
_DEVELOPMENT_OPTIONAL_KEYS = frozenset({"sense_node_budget", "sense_retention_ticks"})
_REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "genome_id",
        "parent_ids",
        "kernel_compatibility",
        "development",
        "plasticity",
        "structure",
        "mutation_policy",
    }
)


class GenomeError(ValueError):
    """Raised for a malformed, out-of-range, or otherwise untrusted genome
    payload -- never a bare ValueError/KeyError/TypeError leaking internal
    structure, matching CheckpointError's existing precedent."""


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise GenomeError(f"{field} must be a string")
    return value


def _require_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GenomeError(f"{field} must be an int")
    if minimum is not None and value < minimum:
        raise GenomeError(f"{field} must be >= {minimum}")
    return value


def _require_float(
    value: Any, field: str, *, minimum: float | None = None, maximum: float | None = None
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GenomeError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise GenomeError(f"{field} must be finite")
    if minimum is not None and number < minimum:
        raise GenomeError(f"{field} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise GenomeError(f"{field} must be <= {maximum}")
    return number


def _require_mapping(value: Any, field: str, *, required_keys: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenomeError(f"{field} must be an object")
    keys = set(value.keys())
    if keys != required_keys:
        missing = required_keys - keys
        unknown = keys - required_keys
        raise GenomeError(f"{field} keys mismatch — missing={sorted(missing)} unknown={sorted(unknown)}")
    return value


def parse_kernel_compatibility(spec: str) -> tuple[tuple[str, tuple[int, int, int]], ...]:
    """Parses a closed grammar of comma-joined comparison clauses, e.g.
    '>=0.55,<0.60' -- a hand-written tokenizer, never eval/exec. Raises
    GenomeError on anything outside the grammar."""
    if not spec:
        raise GenomeError("kernel_compatibility must not be empty")
    clauses: list[tuple[str, tuple[int, int, int]]] = []
    for raw_clause in spec.split(","):
        clause = raw_clause.strip()
        match = _COMPAT_CLAUSE.match(clause)
        if match is None:
            raise GenomeError(f"kernel_compatibility clause {raw_clause!r} does not match the closed grammar")
        op, major, minor, patch = match.groups()
        clauses.append((op, (int(major), int(minor), int(patch or 0))))
    return tuple(clauses)


def satisfies_kernel_compatibility(spec: str, running_version: tuple[int, int, int]) -> bool:
    for op, bound in parse_kernel_compatibility(spec):
        if op == ">=" and not running_version >= bound:
            return False
        if op == "<=" and not running_version <= bound:
            return False
        if op == "==" and not running_version == bound:
            return False
        if op == ">" and not running_version > bound:
            return False
        if op == "<" and not running_version < bound:
            return False
    return True


@dataclass(slots=True, frozen=True)
class RangeSpec:
    initial: float
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        for value, name in ((self.initial, "initial"), (self.minimum, "minimum"), (self.maximum, "maximum")):
            if not math.isfinite(value):
                raise GenomeError(f"RangeSpec.{name} must be finite")
        if not (self.minimum <= self.initial <= self.maximum):
            raise GenomeError("RangeSpec requires minimum <= initial <= maximum")


@dataclass(slots=True, frozen=True)
class DevelopmentGenes:
    initial_concepts: int
    soft_node_budget: int
    soft_edge_budget: int
    consolidation_interval_ticks: int
    sense_node_budget: int = _DEFAULT_SENSE_NODE_BUDGET
    sense_retention_ticks: int = _DEFAULT_SENSE_RETENTION_TICKS


@dataclass(slots=True, frozen=True)
class PlasticityGenes:
    learning_rate: RangeSpec
    forgetting_rate: RangeSpec
    eligibility_decay: float


@dataclass(slots=True, frozen=True)
class StructureGenes:
    grow_threshold: float
    prune_threshold: float
    minimum_support: int
    tentative_lifetime_ticks: int


@dataclass(slots=True, frozen=True)
class MutationPolicyGenes:
    continuous_sigma: float
    max_fields_per_generation: int


@dataclass(slots=True, frozen=True)
class Genome:
    schema_version: int
    genome_id: str
    parent_ids: tuple[str, ...]
    kernel_compatibility: str
    development: DevelopmentGenes
    plasticity: PlasticityGenes
    structure: StructureGenes
    mutation_policy: MutationPolicyGenes

    @property
    def genome_hash(self) -> str:
        canonical = json.dumps(_genome_to_plain_dict(self), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _range_spec_to_plain_dict(range_spec: RangeSpec) -> dict[str, float]:
    """RangeSpec's field names (minimum/maximum) are Python-side; the JSON
    convention (matching master doc §11 and GenomeCodec.load()) is
    min/max -- translated explicitly here rather than via asdict(), which
    would round-trip incorrectly."""
    return {"initial": range_spec.initial, "min": range_spec.minimum, "max": range_spec.maximum}


def _genome_to_plain_dict(genome: Genome) -> dict[str, Any]:
    development = {
        "initial_concepts": genome.development.initial_concepts,
        "soft_node_budget": genome.development.soft_node_budget,
        "soft_edge_budget": genome.development.soft_edge_budget,
        "consolidation_interval_ticks": genome.development.consolidation_interval_ticks,
    }
    implied_sense_budget = min(_DEFAULT_SENSE_NODE_BUDGET, genome.development.soft_node_budget)
    if genome.development.sense_node_budget != implied_sense_budget:
        development["sense_node_budget"] = genome.development.sense_node_budget
    if genome.development.sense_retention_ticks != _DEFAULT_SENSE_RETENTION_TICKS:
        development["sense_retention_ticks"] = genome.development.sense_retention_ticks

    return {
        "schema_version": genome.schema_version,
        "genome_id": genome.genome_id,
        "parent_ids": list(genome.parent_ids),
        "kernel_compatibility": genome.kernel_compatibility,
        "development": development,
        "plasticity": {
            "learning_rate": _range_spec_to_plain_dict(genome.plasticity.learning_rate),
            "forgetting_rate": _range_spec_to_plain_dict(genome.plasticity.forgetting_rate),
            "eligibility_decay": genome.plasticity.eligibility_decay,
        },
        "structure": asdict(genome.structure),
        "mutation_policy": asdict(genome.mutation_policy),
    }


def _load_range_spec(payload: Any, field: str) -> RangeSpec:
    mapping = _require_mapping(payload, field, required_keys=frozenset({"initial", "min", "max"}))
    return RangeSpec(
        initial=_require_float(mapping["initial"], f"{field}.initial"),
        minimum=_require_float(mapping["min"], f"{field}.min"),
        maximum=_require_float(mapping["max"], f"{field}.max"),
    )


class GenomeCodec:
    def load(self, payload: Mapping[str, object]) -> Genome:
        if not isinstance(payload, Mapping):
            raise GenomeError("genome payload must be a JSON object")
        keys = set(payload.keys())
        if keys != _REQUIRED_TOP_LEVEL_KEYS:
            missing = _REQUIRED_TOP_LEVEL_KEYS - keys
            unknown = keys - _REQUIRED_TOP_LEVEL_KEYS
            raise GenomeError(f"genome top-level keys mismatch — missing={sorted(missing)} unknown={sorted(unknown)}")

        schema_version = _require_int(payload["schema_version"], "schema_version", minimum=1)
        genome_id = _require_str(payload["genome_id"], "genome_id")
        if not _GENOME_ID_PATTERN.match(genome_id):
            raise GenomeError("genome_id must match ^genome_[A-Za-z0-9_-]{1,64}$")

        raw_parent_ids = payload["parent_ids"]
        if not isinstance(raw_parent_ids, list):
            raise GenomeError("parent_ids must be a list")
        if len(raw_parent_ids) > _MAX_PARENT_IDS:
            raise GenomeError(f"parent_ids must not exceed {_MAX_PARENT_IDS} entries")
        parent_ids: list[str] = []
        for entry in raw_parent_ids:
            parent_id = _require_str(entry, "parent_ids[]")
            if not _GENOME_ID_PATTERN.match(parent_id):
                raise GenomeError("each parent id must match ^genome_[A-Za-z0-9_-]{1,64}$")
            parent_ids.append(parent_id)

        kernel_compatibility = _require_str(payload["kernel_compatibility"], "kernel_compatibility")
        parse_kernel_compatibility(kernel_compatibility)  # structural validation only; raises GenomeError

        raw_development = payload["development"]
        if not isinstance(raw_development, Mapping):
            raise GenomeError("development must be an object")
        development_keys = set(raw_development.keys())
        missing_development = _DEVELOPMENT_REQUIRED_KEYS - development_keys
        unknown_development = development_keys - (_DEVELOPMENT_REQUIRED_KEYS | _DEVELOPMENT_OPTIONAL_KEYS)
        if missing_development or unknown_development:
            raise GenomeError(
                "development keys mismatch — "
                f"missing={sorted(missing_development)} unknown={sorted(unknown_development)}"
            )
        development_payload = raw_development
        soft_node_budget = _require_int(
            development_payload["soft_node_budget"], "development.soft_node_budget", minimum=1
        )
        legacy_sense_budget = min(_DEFAULT_SENSE_NODE_BUDGET, soft_node_budget)
        development = DevelopmentGenes(
            initial_concepts=_require_int(
                development_payload["initial_concepts"], "development.initial_concepts", minimum=0
            ),
            soft_node_budget=soft_node_budget,
            soft_edge_budget=_require_int(
                development_payload["soft_edge_budget"], "development.soft_edge_budget", minimum=1
            ),
            consolidation_interval_ticks=_require_int(
                development_payload["consolidation_interval_ticks"],
                "development.consolidation_interval_ticks",
                minimum=1,
            ),
            sense_node_budget=_require_int(
                development_payload.get("sense_node_budget", legacy_sense_budget),
                "development.sense_node_budget",
                minimum=1,
            ),
            sense_retention_ticks=_require_int(
                development_payload.get("sense_retention_ticks", _DEFAULT_SENSE_RETENTION_TICKS),
                "development.sense_retention_ticks",
                minimum=1,
            ),
        )

        plasticity_payload = _require_mapping(
            payload["plasticity"],
            "plasticity",
            required_keys=frozenset({"learning_rate", "forgetting_rate", "eligibility_decay"}),
        )
        plasticity = PlasticityGenes(
            learning_rate=_load_range_spec(plasticity_payload["learning_rate"], "plasticity.learning_rate"),
            forgetting_rate=_load_range_spec(plasticity_payload["forgetting_rate"], "plasticity.forgetting_rate"),
            eligibility_decay=_require_float(
                plasticity_payload["eligibility_decay"], "plasticity.eligibility_decay", minimum=0.0, maximum=1.0
            ),
        )

        structure_payload = _require_mapping(
            payload["structure"],
            "structure",
            required_keys=frozenset({"grow_threshold", "prune_threshold", "minimum_support", "tentative_lifetime_ticks"}),
        )
        structure = StructureGenes(
            grow_threshold=_require_float(
                structure_payload["grow_threshold"], "structure.grow_threshold", minimum=0.0, maximum=1.0
            ),
            prune_threshold=_require_float(
                structure_payload["prune_threshold"], "structure.prune_threshold", minimum=0.0, maximum=1.0
            ),
            minimum_support=_require_int(structure_payload["minimum_support"], "structure.minimum_support", minimum=1),
            tentative_lifetime_ticks=_require_int(
                structure_payload["tentative_lifetime_ticks"], "structure.tentative_lifetime_ticks", minimum=1
            ),
        )

        mutation_payload = _require_mapping(
            payload["mutation_policy"],
            "mutation_policy",
            required_keys=frozenset({"continuous_sigma", "max_fields_per_generation"}),
        )
        mutation_policy = MutationPolicyGenes(
            continuous_sigma=_require_float(
                mutation_payload["continuous_sigma"], "mutation_policy.continuous_sigma", minimum=0.0, maximum=1.0
            ),
            max_fields_per_generation=_require_int(
                mutation_payload["max_fields_per_generation"], "mutation_policy.max_fields_per_generation", minimum=1
            ),
        )

        return Genome(
            schema_version=schema_version,
            genome_id=genome_id,
            parent_ids=tuple(parent_ids),
            kernel_compatibility=kernel_compatibility,
            development=development,
            plasticity=plasticity,
            structure=structure,
            mutation_policy=mutation_policy,
        )

    def validate(self, genome: Genome, kernel_limits: KernelLimits, *, running_version: tuple[int, int, int]) -> None:
        if genome.development.soft_node_budget > kernel_limits.max_nodes:
            raise GenomeError(
                f"development.soft_node_budget ({genome.development.soft_node_budget}) exceeds "
                f"kernel_limits.max_nodes ({kernel_limits.max_nodes})"
            )
        if genome.development.sense_node_budget > genome.development.soft_node_budget:
            raise GenomeError(
                f"development.sense_node_budget ({genome.development.sense_node_budget}) exceeds "
                f"development.soft_node_budget ({genome.development.soft_node_budget})"
            )
        if genome.development.sense_node_budget > kernel_limits.max_nodes:
            raise GenomeError(
                f"development.sense_node_budget ({genome.development.sense_node_budget}) exceeds "
                f"kernel_limits.max_nodes ({kernel_limits.max_nodes})"
            )
        if genome.development.soft_edge_budget > kernel_limits.max_edges:
            raise GenomeError(
                f"development.soft_edge_budget ({genome.development.soft_edge_budget}) exceeds "
                f"kernel_limits.max_edges ({kernel_limits.max_edges})"
            )
        if genome.development.initial_concepts > kernel_limits.max_concepts:
            raise GenomeError(
                f"development.initial_concepts ({genome.development.initial_concepts}) exceeds "
                f"kernel_limits.max_concepts ({kernel_limits.max_concepts})"
            )
        compatible = satisfies_kernel_compatibility(genome.kernel_compatibility, running_version)
        # v0.60 adds physiology without changing the cognitive kernel.  Admit
        # genomes authored for the immediately preceding kernel series while
        # keeping the strict public range predicate unchanged for new genomes.
        if not compatible and running_version[0] == 0:
            upper = genome.kernel_compatibility.rsplit("<0.", 1)[-1]
            try:
                upper_minor = int(upper)
            except ValueError:
                upper_minor = -1
            if upper_minor in {running_version[1], running_version[1] - 1}:
                compatible = True
        if not compatible:
            raise GenomeError(
                f"genome kernel_compatibility {genome.kernel_compatibility!r} does not admit "
                f"running version {running_version}"
            )
