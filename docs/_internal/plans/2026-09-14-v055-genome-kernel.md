# v0.55 Genome Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `symbiont.cognition` package with a closed genome schema, hard kernel limits, a strict validating codec, genome identity/hash, and checkpoint persistence — a standalone foundation nothing yet consumes, ready for v0.56's cognitive graph to build on.

**Architecture:** Four new modules (`types.py`, `limits.py`, `genome.py`, `checkpoint.py`) under `src/symbiont/cognition/`. `GenomeCodec.load()` does strict structural/type/range validation of untrusted JSON-shaped input (never `eval`); `GenomeCodec.validate()` separately cross-checks a structurally-valid genome against the hard, non-learnable `KernelLimits` and the running kernel version. `OrganismRuntime` gets an optional `genome` parameter, fully backward-compatible when omitted.

**Tech Stack:** Python 3.11+, dataclasses, `hashlib.sha256`, `re`, pytest. No new dependencies.

**Spec:** `docs/_internal/specs/2026-09-14-v055-genome-kernel-design.md` — read both together. Master design: `docs/design/endogenous-plasticity.md` §4.1-4.2, §5.1-5.3, §7.4, §10-13.

## Global Constraints

- No graph, activation, learning, structure, or evolution code — v0.56-v0.59 (spec §2).
- No new dependencies; no `eval`/`exec` anywhere in genome parsing.
- `KernelLimits` is never part of the genome and is never learnable (master doc §4.1, §13 invariant 1).
- Genome checkpoint is its own bolt-on namespace (`payload["genome"]`), not part of `host/checkpoint.py`'s `CHECKPOINT_SCHEMA_VERSION` chain (spec §3.5, §5 decisions table).
- `OrganismRuntime` with no genome must be byte-for-byte unaffected — every existing test in `test_organism_runtime.py` must keep passing unmodified.
- `genome_id`/`parent_ids` pattern: `^genome_[A-Za-z0-9_-]{1,64}$`; `parent_ids` capped at 8 entries.

---

## Task 1: Closed catalogs and ranges (`cognition/types.py`)

**Files:**
- Create: `src/symbiont/cognition/__init__.py` (empty docstring module, package marker)
- Create: `src/symbiont/cognition/types.py`
- Modify: `tests/experimental_integrity/test_ground_truth_boundary.py`
- Test: `tests/unit/cognition/test_types.py` (new directory)

**Interfaces:**
- Produces: `NodeKind` (StrEnum: `SENSE`, `CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT`), `EdgeKind` (StrEnum: `EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`), `WEIGHT_RANGE: tuple[float, float]`, `PLASTICITY_RANGE: tuple[float, float]`, `GATE_RANGE: tuple[float, float]`, `EDGE_DELAY_TICKS_RANGE: tuple[int, int]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/__init__.py
```

(empty file — makes the directory a package so pytest discovers it consistently with the rest of `tests/unit/`.)

```python
# tests/unit/cognition/test_types.py
from __future__ import annotations

from symbiont.cognition.types import (
    EDGE_DELAY_TICKS_RANGE,
    GATE_RANGE,
    PLASTICITY_RANGE,
    WEIGHT_RANGE,
    EdgeKind,
    NodeKind,
)


def test_node_kind_catalog_is_exactly_the_documented_six():
    assert {kind.value for kind in NodeKind} == {
        "sense",
        "concept",
        "state",
        "predictor",
        "gate",
        "readout",
    }


def test_no_action_node_kind_exists():
    assert not any(kind.value == "action" for kind in NodeKind)


def test_edge_kind_catalog_is_exactly_the_documented_four():
    assert {kind.value for kind in EdgeKind} == {"excitatory", "inhibitory", "predictive", "gating"}


def test_ranges_match_the_design_doc():
    assert WEIGHT_RANGE == (-2.0, 2.0)
    assert PLASTICITY_RANGE == (0.0, 1.0)
    assert GATE_RANGE == (0.0, 1.0)
    assert EDGE_DELAY_TICKS_RANGE == (0, 1)
```

Also add the allowlist and AST-boundary updates now (they fail the moment
`cognition/` exists, so this task must include the fix):

```python
# tests/experimental_integrity/test_ground_truth_boundary.py
# In test_symbiont_contains_only_subject_modules, change:
    allowed = {"__init__.py", "__pycache__", "core", "environment", "host", "simulation"}
# to:
    allowed = {"__init__.py", "__pycache__", "cognition", "core", "environment", "host", "simulation"}
```

Add a new, explicitly-scoped test to the same file:

```python
def test_cognition_never_imports_symbiont_lab():
    """Narrower, package-specific instance of the general AST boundary
    (roadmap v0.55) — the cognitive-graph package must never depend on
    the evaluation apparatus that will eventually score it."""
    repo_root = Path(__file__).resolve().parents[2]
    cognition_src = repo_root / "src" / "symbiont" / "cognition"
    assert cognition_src.is_dir(), f"Not found: {cognition_src}"

    violations: list[str] = []
    for py_file in cognition_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "symbiont_lab" or alias.name.startswith("symbiont_lab."):
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "symbiont_lab" or node.module.startswith("symbiont_lab.")):
                    violations.append(f"{py_file.relative_to(repo_root)} imports from {node.module}")

    assert not violations, "Architectural boundary violation(s):\n" + "\n".join(violations)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_types.py tests/experimental_integrity/test_ground_truth_boundary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition'`; the allowlist test also fails once the directory exists but before this task's allowlist edit lands (run the import-failing version first, confirm, then apply the allowlist edit as part of Step 3 alongside the real module).

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/__init__.py
"""Cognitive graph, genome and plasticity kernel (roadmap v0.55+).

This package never imports symbiont_lab — cognition must stay
independent of the evaluation apparatus that will eventually score it
(see tests/experimental_integrity/test_ground_truth_boundary.py).
"""
```

```python
# src/symbiont/cognition/types.py
from __future__ import annotations

from enum import StrEnum


class NodeKind(StrEnum):
    """Closed catalog (roadmap v0.55, master doc §5.1). There is
    deliberately no ACTION kind — readouts feed existing, already-governed
    consultative circuits; the graph itself never acts."""

    SENSE = "sense"
    CONCEPT = "concept"
    STATE = "state"
    PREDICTOR = "predictor"
    GATE = "gate"
    READOUT = "readout"


class EdgeKind(StrEnum):
    """Closed catalog (master doc §5.2)."""

    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"
    PREDICTIVE = "predictive"
    GATING = "gating"


WEIGHT_RANGE: tuple[float, float] = (-2.0, 2.0)
PLASTICITY_RANGE: tuple[float, float] = (0.0, 1.0)
GATE_RANGE: tuple[float, float] = (0.0, 1.0)
EDGE_DELAY_TICKS_RANGE: tuple[int, int] = (0, 1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_types.py tests/experimental_integrity/test_ground_truth_boundary.py -v`
Expected: PASS, all tests including every pre-existing one in the boundary file.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/__init__.py src/symbiont/cognition/types.py tests/unit/cognition/__init__.py tests/unit/cognition/test_types.py tests/experimental_integrity/test_ground_truth_boundary.py
git commit -m "$(cat <<'EOF'
feat(cognition): add closed node/edge catalogs and ranges

New symbiont.cognition package (v0.55 genome kernel, first slice):
NodeKind/EdgeKind closed StrEnum catalogs and the weight/plasticity/
gate/edge-delay numeric ranges from the endogenous-plasticity design
doc. No ACTION node kind exists -- structurally enforced by the
closed enum. Extends the architectural-boundary test suite with a
package-scoped AST check and updates the subject-module allowlist.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: `KernelLimits` (`cognition/limits.py`)

**Files:**
- Create: `src/symbiont/cognition/limits.py`
- Test: `tests/unit/cognition/test_limits.py`

**Interfaces:**
- Produces: `KernelLimits` frozen dataclass with fields `max_nodes`, `max_concepts`, `max_edges`, `max_tentative_edges`, `max_structural_mutations_per_consolidation`, `consolidation_interval_ticks`, `max_plastic_checkpoint_bytes` — all `int`, defaulted per spec §3.3.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_limits.py
from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits


def test_defaults_match_the_design_doc_table():
    limits = KernelLimits()
    assert limits.max_nodes == 128
    assert limits.max_concepts == 32
    assert limits.max_edges == 1024
    assert limits.max_tentative_edges == 128
    assert limits.max_structural_mutations_per_consolidation == 8
    assert limits.consolidation_interval_ticks == 32
    assert limits.max_plastic_checkpoint_bytes == 2 * 1024 * 1024


@pytest.mark.parametrize(
    "field",
    [
        "max_nodes",
        "max_concepts",
        "max_edges",
        "max_tentative_edges",
        "max_structural_mutations_per_consolidation",
        "consolidation_interval_ticks",
        "max_plastic_checkpoint_bytes",
    ],
)
def test_every_field_rejects_non_positive_values(field):
    with pytest.raises(ValueError):
        KernelLimits(**{field: 0})
    with pytest.raises(ValueError):
        KernelLimits(**{field: -1})


def test_kernel_limits_is_frozen():
    limits = KernelLimits()
    with pytest.raises(Exception):
        limits.max_nodes = 999
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_limits.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.limits'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/limits.py
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(slots=True, frozen=True)
class KernelLimits:
    """Hard, owner-configured resource ceilings for the cognitive graph
    (master doc §7.4). Never part of a genome and never learnable (§4.1,
    §13 invariant 1) -- a genome's soft budgets are validated against
    these but can never exceed them."""

    max_nodes: int = 128
    max_concepts: int = 32
    max_edges: int = 1024
    max_tentative_edges: int = 128
    max_structural_mutations_per_consolidation: int = 8
    consolidation_interval_ticks: int = 32
    max_plastic_checkpoint_bytes: int = 2 * 1024 * 1024

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be positive")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_limits.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/limits.py tests/unit/cognition/test_limits.py
git commit -m "$(cat <<'EOF'
feat(cognition): add KernelLimits, the hard non-learnable ceilings

Defaults copied verbatim from the endogenous-plasticity design doc's
resource table (128 nodes, 32 concepts, 1024 edges, 128 tentative
edges, 8 structural mutations per consolidation, 32-tick
consolidation interval, 2 MiB checkpoint budget). Every field
validated positive.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 3: Genome dataclasses and `GenomeCodec.load()` (`cognition/genome.py`)

**Files:**
- Create: `src/symbiont/cognition/genome.py`
- Test: `tests/unit/cognition/test_genome.py`

**Interfaces:**
- Consumes: nothing new (pure module).
- Produces: `GenomeError(ValueError)`, `RangeSpec`, `DevelopmentGenes`, `PlasticityGenes`, `StructureGenes`, `MutationPolicyGenes`, `Genome` (with `.genome_hash` property), `GenomeCodec.load(payload: Mapping[str, object]) -> Genome`, `parse_kernel_compatibility(spec: str) -> tuple[tuple[str, tuple[int, int, int]], ...]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_genome.py
from __future__ import annotations

import copy

import pytest

from symbiont.cognition.genome import GenomeCodec, GenomeError, parse_kernel_compatibility

VALID_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_018f0000000000000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 4,
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "consolidation_interval_ticks": 32,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.02, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.92,
    },
    "structure": {
        "grow_threshold": 0.18,
        "prune_threshold": 0.01,
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


def test_master_doc_example_loads_successfully():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    assert genome.genome_id == "genome_018f0000000000000000000000"
    assert genome.development.soft_node_budget == 64
    assert genome.plasticity.learning_rate.initial == 0.02


@pytest.mark.parametrize("missing_key", list(VALID_PAYLOAD.keys()))
def test_load_rejects_missing_top_level_key(missing_key):
    payload = copy.deepcopy(VALID_PAYLOAD)
    del payload[missing_key]
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_unknown_top_level_key():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["extra_field"] = "not allowed"
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


@pytest.mark.parametrize(
    "bad_id",
    ["", "not_prefixed", "genome_/etc/passwd", "genome_" + "x" * 65, "genome_has space"],
)
def test_load_rejects_malformed_genome_id(bad_id):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["genome_id"] = bad_id
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_too_many_parent_ids():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["parent_ids"] = [f"genome_parent{i:02d}" for i in range(9)]
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_accepts_parent_ids_at_the_cap():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["parent_ids"] = [f"genome_parent{i:02d}" for i in range(8)]
    genome = GenomeCodec().load(payload)
    assert len(genome.parent_ids) == 8


@pytest.mark.parametrize(
    "bad_compat",
    ["", "not a version spec", ">=abc", "1.2.3", ">=0.55;<0.60", "eval(1)"],
)
def test_load_rejects_malformed_kernel_compatibility(bad_compat):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["kernel_compatibility"] = bad_compat
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_parse_kernel_compatibility_accepts_multi_clause_spec():
    clauses = parse_kernel_compatibility(">=0.55,<0.60")
    assert clauses == ((">=", (0, 55, 0)), ("<", (0, 60, 0)))


def test_load_rejects_range_spec_with_initial_outside_bounds():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["plasticity"]["learning_rate"] = {"initial": 0.5, "min": 0.001, "max": 0.08}
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("initial_concepts", -1),
        ("soft_node_budget", 0),
        ("soft_edge_budget", 0),
        ("consolidation_interval_ticks", 0),
    ],
)
def test_load_rejects_invalid_development_fields(field, value):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"][field] = value
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_wrong_json_type():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_node_budget"] = "sixty-four"
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_genome_hash_is_deterministic_and_key_order_independent():
    genome_a = GenomeCodec().load(VALID_PAYLOAD)
    reordered = dict(reversed(list(VALID_PAYLOAD.items())))
    genome_b = GenomeCodec().load(reordered)
    assert genome_a.genome_hash == genome_b.genome_hash


def test_genome_hash_changes_when_content_changes():
    genome_a = GenomeCodec().load(VALID_PAYLOAD)
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["plasticity"]["eligibility_decay"] = 0.5
    genome_b = GenomeCodec().load(payload)
    assert genome_a.genome_hash != genome_b.genome_hash
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_genome.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.genome'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/genome.py
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

_GENOME_ID_PATTERN = re.compile(r"^genome_[A-Za-z0-9_-]{1,64}$")
_MAX_PARENT_IDS = 8
_COMPAT_CLAUSE = re.compile(r"^(>=|<=|==|>|<)(\d+)\.(\d+)(?:\.(\d+))?$")
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


def _genome_to_plain_dict(genome: Genome) -> dict[str, Any]:
    return {
        "schema_version": genome.schema_version,
        "genome_id": genome.genome_id,
        "parent_ids": list(genome.parent_ids),
        "kernel_compatibility": genome.kernel_compatibility,
        "development": asdict(genome.development),
        "plasticity": {
            "learning_rate": asdict(genome.plasticity.learning_rate),
            "forgetting_rate": asdict(genome.plasticity.forgetting_rate),
            "eligibility_decay": genome.plasticity.eligibility_decay,
        },
        "structure": asdict(genome.structure),
        "mutation_policy": asdict(genome.mutation_policy),
    }


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

        development_payload = _require_mapping(
            payload["development"],
            "development",
            required_keys=frozenset(
                {"initial_concepts", "soft_node_budget", "soft_edge_budget", "consolidation_interval_ticks"}
            ),
        )
        development = DevelopmentGenes(
            initial_concepts=_require_int(development_payload["initial_concepts"], "development.initial_concepts", minimum=0),
            soft_node_budget=_require_int(development_payload["soft_node_budget"], "development.soft_node_budget", minimum=1),
            soft_edge_budget=_require_int(development_payload["soft_edge_budget"], "development.soft_edge_budget", minimum=1),
            consolidation_interval_ticks=_require_int(
                development_payload["consolidation_interval_ticks"], "development.consolidation_interval_ticks", minimum=1
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
            grow_threshold=_require_float(structure_payload["grow_threshold"], "structure.grow_threshold", minimum=0.0, maximum=1.0),
            prune_threshold=_require_float(structure_payload["prune_threshold"], "structure.prune_threshold", minimum=0.0, maximum=1.0),
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
            continuous_sigma=_require_float(mutation_payload["continuous_sigma"], "mutation_policy.continuous_sigma", minimum=0.0),
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


def _load_range_spec(payload: Any, field: str) -> RangeSpec:
    mapping = _require_mapping(payload, field, required_keys=frozenset({"initial", "min", "max"}))
    return RangeSpec(
        initial=_require_float(mapping["initial"], f"{field}.initial"),
        minimum=_require_float(mapping["min"], f"{field}.min"),
        maximum=_require_float(mapping["max"], f"{field}.max"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_genome.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/genome.py tests/unit/cognition/test_genome.py
git commit -m "$(cat <<'EOF'
feat(cognition): add Genome dataclasses and GenomeCodec.load()

Strict, closed-schema structural validation of untrusted genome JSON:
exact top-level and nested key sets (no unknown fields), a safe
opaque-token pattern for genome_id/parent_ids (capped at 8 parents),
a hand-written non-eval grammar parser for kernel_compatibility
version-range clauses, and finite/ranged numeric validation
throughout. genome_hash is a deterministic sha256 over the canonical
(sorted-key) representation, independent of source dict key order.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: `GenomeCodec.validate()` — cross-check against `KernelLimits`

**Files:**
- Modify: `src/symbiont/cognition/genome.py`
- Test: `tests/unit/cognition/test_genome.py`

**Interfaces:**
- Consumes: `KernelLimits` (Task 2), `Genome`/`GenomeError` (Task 3).
- Produces: `GenomeCodec.validate(genome: Genome, kernel_limits: KernelLimits, *, running_version: tuple[int, int, int]) -> None`, `satisfies_kernel_compatibility(spec: str, running_version: tuple[int, int, int]) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_genome.py (append)
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.genome import satisfies_kernel_compatibility


def test_satisfies_kernel_compatibility_true_within_range():
    assert satisfies_kernel_compatibility(">=0.55,<0.60", (0, 57, 2))


def test_satisfies_kernel_compatibility_false_outside_range():
    assert not satisfies_kernel_compatibility(">=0.55,<0.60", (0, 60, 0))
    assert not satisfies_kernel_compatibility(">=0.55,<0.60", (0, 54, 9))


def test_validate_passes_a_genome_within_all_kernel_limits():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    GenomeCodec().validate(genome, KernelLimits(), running_version=(0, 55, 0))  # must not raise


def test_validate_rejects_soft_node_budget_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_node_budget"] = 999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_nodes=128), running_version=(0, 55, 0))


def test_validate_rejects_soft_edge_budget_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_edge_budget"] = 9999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_edges=1024), running_version=(0, 55, 0))


def test_validate_rejects_initial_concepts_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["initial_concepts"] = 999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_concepts=32), running_version=(0, 55, 0))


def test_validate_rejects_a_running_version_outside_kernel_compatibility():
    genome = GenomeCodec().load(VALID_PAYLOAD)  # kernel_compatibility: >=0.55,<0.60
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(), running_version=(0, 60, 0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_genome.py -v -k "validate or satisfies_kernel_compatibility"`
Expected: FAIL — `AttributeError: 'GenomeCodec' object has no attribute 'validate'` / `ImportError: cannot import name 'satisfies_kernel_compatibility'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/genome.py`, near `parse_kernel_compatibility`:

```python
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
```

Add a `validate` method to `GenomeCodec`:

```python
    def validate(self, genome: Genome, kernel_limits: "KernelLimits", *, running_version: tuple[int, int, int]) -> None:
        if genome.development.soft_node_budget > kernel_limits.max_nodes:
            raise GenomeError(
                f"development.soft_node_budget ({genome.development.soft_node_budget}) exceeds "
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
        if not satisfies_kernel_compatibility(genome.kernel_compatibility, running_version):
            raise GenomeError(
                f"genome kernel_compatibility {genome.kernel_compatibility!r} does not admit "
                f"running version {running_version}"
            )
```

Add the import needed for the type hint (avoid a circular import — `limits.py` doesn't import `genome.py`, so a plain top-level import is safe):

```python
from .limits import KernelLimits
```

(place this import near the top of `genome.py` with the other imports, and drop the quotes around `"KernelLimits"` in the `validate` signature above since it's now a real import.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_genome.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/genome.py tests/unit/cognition/test_genome.py
git commit -m "$(cat <<'EOF'
feat(cognition): add GenomeCodec.validate() against KernelLimits

Cross-checks a structurally-valid genome's soft budgets against the
hard KernelLimits (a genome can only request less than the kernel
allows, never more) and confirms the running kernel version satisfies
the genome's declared kernel_compatibility range.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 5: Genome checkpoint bolt-on (`cognition/checkpoint.py`)

**Files:**
- Create: `src/symbiont/cognition/checkpoint.py`
- Test: `tests/unit/cognition/test_checkpoint.py`

**Interfaces:**
- Consumes: `Genome`, `GenomeCodec`, `GenomeError` (Task 3/4), `KernelLimits` (Task 2).
- Produces: `export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None`, `restore_genome_checkpoint(payload: dict[str, Any] | None, *, kernel_limits: KernelLimits, running_version: tuple[int, int, int]) -> Genome | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_checkpoint.py
from __future__ import annotations

import copy

import pytest

from symbiont.cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from symbiont.cognition.genome import GenomeCodec, GenomeError
from symbiont.cognition.limits import KernelLimits
from tests.unit.cognition.test_genome import VALID_PAYLOAD

_RUNNING_VERSION = (0, 55, 0)


def test_none_genome_round_trips_to_none():
    assert export_genome_checkpoint(None) is None
    assert restore_genome_checkpoint(None, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION) is None


def test_valid_genome_round_trips_exactly():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    restored = restore_genome_checkpoint(payload, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION)
    assert restored == genome
    assert restored.genome_hash == genome.genome_hash


def test_exported_payload_carries_genome_hash():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    assert payload["genome_hash"] == genome.genome_hash


def test_tampered_payload_is_rejected_on_restore():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    tampered = copy.deepcopy(payload)
    tampered["plasticity"]["eligibility_decay"] = 0.01  # changed, hash left stale
    with pytest.raises(GenomeError):
        restore_genome_checkpoint(tampered, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION)


def test_restore_rejects_a_genome_that_no_longer_satisfies_kernel_limits():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    with pytest.raises(GenomeError):
        restore_genome_checkpoint(payload, kernel_limits=KernelLimits(max_nodes=1), running_version=_RUNNING_VERSION)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_checkpoint.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.checkpoint'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/checkpoint.py
from __future__ import annotations

from typing import Any

from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .limits import KernelLimits


def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
    """None in, None out -- an organism with no genome checkpoints
    nothing new here. Genome content is small, bounded, declarative
    config, not raw telemetry, so it is persisted in full (roadmap
    v0.55 design spec §3.5)."""
    if genome is None:
        return None
    payload = _genome_to_plain_dict(genome)
    payload["genome_hash"] = genome.genome_hash
    return payload


def restore_genome_checkpoint(
    payload: dict[str, Any] | None,
    *,
    kernel_limits: KernelLimits,
    running_version: tuple[int, int, int],
) -> Genome | None:
    """Re-validates fully (load + validate) on restore -- a checkpoint is
    untrusted input, same discipline as every other restore path in this
    codebase. Also recomputes genome_hash from the restored fields and
    rejects a mismatch against the persisted hash, defending against a
    hand-edited or corrupted checkpoint claiming a genome it doesn't
    actually match."""
    if payload is None:
        return None
    if not isinstance(payload, dict) or "genome_hash" not in payload:
        raise GenomeError("genome checkpoint payload must be an object with a genome_hash")
    persisted_hash = payload["genome_hash"]
    genome_fields = {key: value for key, value in payload.items() if key != "genome_hash"}
    codec = GenomeCodec()
    genome = codec.load(genome_fields)
    if genome.genome_hash != persisted_hash:
        raise GenomeError("genome checkpoint hash mismatch -- payload may be corrupted or tampered")
    codec.validate(genome, kernel_limits, running_version=running_version)
    return genome
```

`_genome_to_plain_dict` is a private helper in `genome.py` from Task 3;
importing it directly here (both modules are in the same package) is
appropriate rather than duplicating the serialization logic.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_checkpoint.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/checkpoint.py tests/unit/cognition/test_checkpoint.py
git commit -m "$(cat <<'EOF'
feat(cognition): add genome checkpoint export/restore

export_genome_checkpoint()/restore_genome_checkpoint() persist a
genome's full declarative content plus its genome_hash. Restore
re-validates fully (load + validate against KernelLimits and the
running kernel version) and rejects any payload whose recomputed hash
doesn't match the persisted one -- defense in depth against a
corrupted or hand-edited checkpoint.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 6: `OrganismRuntime` wiring

**Files:**
- Modify: `src/symbiont/core/runtime.py`
- Test: `tests/unit/core/test_organism_runtime.py`

**Interfaces:**
- Consumes: `Genome`, `export_genome_checkpoint`, `restore_genome_checkpoint` (Task 5), `KernelLimits` (Task 2).
- Produces: `OrganismRuntime.__init__(..., genome: Genome | None = None, kernel_limits: KernelLimits | None = None)`, `OrganismRuntime.genome` property.

- [ ] **Step 1: Write the failing tests**

```python
def test_runtime_with_no_genome_is_unaffected():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    assert runtime.genome is None
    payload = runtime.checkpoint()
    assert payload["genome"] is None


def test_runtime_constructed_with_a_genome_round_trips_it_through_checkpoint():
    from symbiont.cognition.genome import GenomeCodec
    from tests.unit.cognition.test_genome import VALID_PAYLOAD

    genome = GenomeCodec().load(VALID_PAYLOAD)
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0, genome=genome)
    assert runtime.genome == genome

    payload = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)
    assert restored.genome == genome
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k "no_genome or round_trips_it_through_checkpoint"`
Expected: FAIL — `TypeError: OrganismRuntime.__init__() got an unexpected keyword argument 'genome'`.

- [ ] **Step 3: Implement**

In `src/symbiont/core/runtime.py`, add imports:

```python
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome
from ..cognition.limits import KernelLimits
```

Add constructor parameters (near `self_model: SelfModel | None = None`):

```python
        self_model: SelfModel | None = None,
        genome: Genome | None = None,
        kernel_limits: KernelLimits | None = None,
    ) -> None:
```

Store them alongside `self._self_model`:

```python
        self._self_model = self_model if self_model is not None else SelfModel()
        self._genome = genome
        self._kernel_limits = kernel_limits if kernel_limits is not None else KernelLimits()
```

Add a property next to `self_model`:

```python
    @property
    def genome(self) -> Genome | None:
        return self._genome
```

Update `checkpoint()`:

```python
        payload["self_model"] = self._self_model.export()
        payload["genome"] = export_genome_checkpoint(self._genome)
        return payload
```

Update `from_checkpoint()` — genome restoration needs the running kernel
version; use `symbiont.__version__`, parsed into a `(major, minor, patch)`
tuple:

```python
        from .. import __version__ as _symbiont_version

        def _parse_running_version(version_string: str) -> tuple[int, int, int]:
            parts = version_string.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            payload.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )
        return cls(
            **kwargs,
            acclimation=acclimation,
            rhythm_model=rhythm_model,
            drift_baselines=drift_baselines,
            adaptive_senses=adaptive_senses,
            self_model=self_model,
            genome=genome,
            tick_count=payload.get("saved_at_tick") or 0,
        )
```

(place the `_parse_running_version` helper and the `_symbiont_version`
import right before this point in `from_checkpoint`, alongside the
existing `adaptive_senses`/`self_model` restoration block — don't duplicate
it if `kwargs` already forwards `kernel_limits` to `cls(...)`; since
`kernel_limits` is a named `cls(...)` constructor parameter, remove it from
`kwargs` before the `**kwargs` spread to avoid a duplicate-keyword error,
the same way `min_samples` is already read via `kwargs.get(...)` without
being separately popped — check `min_samples`'s handling immediately above
for the exact existing pattern to follow, since `OrganismRuntime.__init__`
does not accept `min_samples` as one of its own parameters but
`from_checkpoint`'s `**kwargs` does forward it to `HostAcclimation`/
`RhythmModel` constructors, not to `cls(...)` — `kernel_limits`, by
contrast, **is** accepted by `cls(...)`, so `kwargs.get("kernel_limits")`
must not also appear in the `**kwargs` spread into `cls(...)` twice; since
`kwargs` already naturally contains it once and `cls(...)` receives
`**kwargs` once, this is not actually a duplication — reading via
`kwargs.get(...)` for the local variable while also spreading `**kwargs`
is safe and requires no popping.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_organism_runtime.py -v`
Expected: PASS, all tests including every pre-existing v0.53/v0.54 test (genome defaults to `None`, zero behavior change).

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/core/runtime.py tests/unit/core/test_organism_runtime.py
git commit -m "$(cat <<'EOF'
feat(core): wire an optional genome into OrganismRuntime

OrganismRuntime accepts an optional genome + kernel_limits and
persists/restores the genome's full identity through checkpoints.
Fully additive: a runtime with no genome (the default, every existing
test) is unaffected. Nothing yet consumes the genome to configure
behavior -- that begins with v0.56's cognitive graph.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**
- §3.1 new package + allowlist/AST boundary → Task 1.
- §3.2 closed catalogs/ranges → Task 1.
- §3.3 `KernelLimits` → Task 2.
- §3.4 `Genome` dataclasses, `GenomeCodec.load()` (structural), `.validate()` (cross-check) → Tasks 3, 4.
- §3.5 checkpoint bolt-on with hash tamper-check → Task 5.
- §3.6 `OrganismRuntime` wiring, additive → Task 6.
- §3.7 AST boundary → folded into Task 1 (it breaks the moment the package exists, so it cannot be deferred to a later task).
- Non-goals (§2): no task creates `graph.py`/`activation.py`/`learning.py`/`structure.py`/`metaplasticity.py`, no task touches `symbiont_lab`.

**Type consistency check:** `GenomeCodec.load`/`.validate` signatures in Task 3/4 match their use in Task 5's `restore_genome_checkpoint` and Task 6's runtime wiring. `KernelLimits` field names in Task 2 match every reference in Tasks 4-6. `Genome.genome_hash` (property, not a stored field) is used consistently as `genome.genome_hash` everywhere, never reassigned or treated as mutable state.
