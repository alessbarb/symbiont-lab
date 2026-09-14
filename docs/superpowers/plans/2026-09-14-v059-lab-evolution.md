# v0.59 Laboratory Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `symbiont_lab/evolution/` package — declarative genome mutation, Pareto-archive selection over evaluation results, and an append-only cycle-protected lineage archive — closing out the endogenous-plasticity milestone sequence (v0.55-v0.59).

**Architecture:** `mutation.py` holds pure `Genome -> Genome` functions (never in place — `Genome` is frozen). `evaluation.py` holds `EvaluationResult` and `select_archive()`, built directly on `symbiont.cognition.metaplasticity.dominates()`. `lineage.py` holds `LineageRecord`/`LineageArchive`, an in-memory append-only log with cycle detection. All three import from `symbiont.cognition.*` (always allowed); nothing in `symbiont/` imports back.

**Tech Stack:** Python 3.11+, dataclasses, `random`, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-14-v059-lab-evolution-design.md` — read both together. Master design: `docs/design/endogenous-plasticity.md` §8, §19.3.

## Global Constraints

- No simulation harness, no automatic generational loop, no visualization — building blocks only (spec §2).
- `Genome` stays frozen — every mutation function returns a new `Genome`, never mutates the input (spec §3.1).
- `select_archive()` returns only non-dominated results (Pareto front via `symbiont.cognition.metaplasticity.dominates`), capped at `max_archive_size`, never a weighted-score ranking (spec §3.2).
- `LineageArchive.record()` rejects a duplicate `genome_id` and any `parent_ids` chain that would create a cycle (spec §3.3).
- Evolution code lives entirely in `symbiont_lab/`; `symbiont/` must contain none of it (spec §1) — enforced by a new AST test.

---

## Task 1: Package scaffold and the evolution-boundary AST test

**Files:**
- Create: `src/symbiont_lab/evolution/__init__.py`
- Create: `tests/unit/lab/evolution/__init__.py`
- Modify: `tests/experimental_integrity/test_ground_truth_boundary.py`

**Interfaces:**
- Produces: the `symbiont_lab.evolution` package (empty, just the module marker).

- [ ] **Step 1: Write the failing test**

```python
# tests/experimental_integrity/test_ground_truth_boundary.py (append)
def test_symbiont_never_contains_evolution_code():
    """Evolution belongs entirely to symbiont_lab, never the resident
    organism (master doc §8: "un individuo no se reproduce ni se
    despliega a sí mismo") -- a structural check, not just a style
    preference."""
    repo_root = Path(__file__).resolve().parents[2]
    symbiont_src = repo_root / "src" / "symbiont"
    forbidden_names = {"mutation.py", "evolution.py", "selection.py", "lineage.py"}
    hits = [
        str(path.relative_to(repo_root))
        for path in symbiont_src.rglob("*.py")
        if path.name in forbidden_names
    ]
    assert not hits, f"symbiont/ must never contain evolution code: {hits}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/experimental_integrity/test_ground_truth_boundary.py -v -k never_contains_evolution`
Expected: This test should already PASS before any implementation, since
no such files exist yet under `src/symbiont/` — confirm that first (a
guard against a false sense of security later), then proceed: it is not
"TDD-failing" in the traditional sense, but its presence from this point
forward regression-guards every subsequent task in this plan.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont_lab/evolution/__init__.py
"""Genome mutation, evaluation-result selection, and lineage archiving
for laboratory evolution (roadmap v0.59). Evolution belongs entirely to
symbiont_lab -- an individual organism never reproduces or deploys
itself; this package is the scientific apparatus's job, not the
organism's.
"""
```

```python
# tests/unit/lab/evolution/__init__.py
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/experimental_integrity/test_ground_truth_boundary.py -v`
Expected: PASS, all tests including every pre-existing one.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont_lab/evolution/__init__.py tests/unit/lab/evolution/__init__.py tests/experimental_integrity/test_ground_truth_boundary.py
git commit -m "$(cat <<'EOF'
feat(lab): scaffold symbiont_lab.evolution and its boundary test

New package for v0.59 laboratory evolution. Adds an explicit
structural test confirming symbiont/ never contains evolution/
mutation/selection/lineage code of its own -- an individual organism
never reproduces or deploys itself (master doc §8); that is entirely
symbiont_lab's job.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: Genome mutation operators (`evolution/mutation.py`)

**Files:**
- Create: `src/symbiont_lab/evolution/mutation.py`
- Test: `tests/unit/lab/evolution/test_mutation.py`

**Interfaces:**
- Consumes: `Genome`, `DevelopmentGenes`, `PlasticityGenes`, `StructureGenes`, `MutationPolicyGenes`, `RangeSpec`, `GenomeCodec` (from `symbiont.cognition.genome`).
- Produces: `mutate_continuous_fields(genome: Genome, *, sigma: float, max_fields: int, rng: random.Random) -> Genome`, `mutate_soft_budget(genome: Genome, *, field: Literal["soft_node_budget", "soft_edge_budget"], delta: int) -> Genome`, `derive_child_genome(parent: Genome, *, new_genome_id: str, mutated: Genome) -> Genome`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/lab/evolution/test_mutation.py
from __future__ import annotations

import random

import pytest

from symbiont.cognition.genome import DevelopmentGenes, Genome, GenomeCodec, MutationPolicyGenes, PlasticityGenes, RangeSpec, StructureGenes
from symbiont_lab.evolution.mutation import derive_child_genome, mutate_continuous_fields, mutate_soft_budget

_VALID_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_parent0000000000000000000",
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


def _parent_genome() -> Genome:
    return GenomeCodec().load(_VALID_PAYLOAD)


def test_mutate_continuous_fields_returns_a_new_genome_object():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=0.01, max_fields=3, rng=random.Random(1))
    assert mutated is not parent
    assert isinstance(mutated, Genome)


def test_mutate_continuous_fields_stays_within_each_fields_own_bounds():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=1.0, max_fields=3, rng=random.Random(1))
    lr = mutated.plasticity.learning_rate
    assert lr.minimum <= lr.initial <= lr.maximum
    assert 0.0 <= mutated.plasticity.eligibility_decay <= 1.0
    assert 0.0 <= mutated.structure.grow_threshold <= 1.0
    assert 0.0 <= mutated.structure.prune_threshold <= 1.0


def test_mutate_continuous_fields_is_deterministic_for_the_same_seed():
    parent = _parent_genome()
    a = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(7))
    b = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(7))
    assert a == b


def test_mutate_continuous_fields_different_seeds_can_diverge():
    parent = _parent_genome()
    a = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(1))
    b = mutate_continuous_fields(parent, sigma=0.02, max_fields=3, rng=random.Random(2))
    assert a != b


def test_mutate_soft_budget_changes_only_the_targeted_field():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=8)
    assert mutated.development.soft_node_budget == 72
    assert mutated.development.soft_edge_budget == parent.development.soft_edge_budget


def test_mutate_soft_budget_never_goes_negative():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=-9999)
    assert mutated.development.soft_node_budget >= 1


def test_derive_child_genome_sets_parent_ids_and_new_id():
    parent = _parent_genome()
    mutated = mutate_soft_budget(parent, field="soft_node_budget", delta=8)
    child = derive_child_genome(parent, new_genome_id="genome_child00000000000000000000", mutated=mutated)
    assert child.genome_id == "genome_child00000000000000000000"
    assert child.parent_ids == (parent.genome_id,)
    assert child.development.soft_node_budget == 72


def test_derive_child_genome_round_trips_through_the_codec():
    parent = _parent_genome()
    mutated = mutate_continuous_fields(parent, sigma=0.01, max_fields=2, rng=random.Random(3))
    child = derive_child_genome(parent, new_genome_id="genome_child00000000000000000001", mutated=mutated)
    reloaded = GenomeCodec().load(
        {
            "schema_version": child.schema_version,
            "genome_id": child.genome_id,
            "parent_ids": list(child.parent_ids),
            "kernel_compatibility": child.kernel_compatibility,
            "development": {
                "initial_concepts": child.development.initial_concepts,
                "soft_node_budget": child.development.soft_node_budget,
                "soft_edge_budget": child.development.soft_edge_budget,
                "consolidation_interval_ticks": child.development.consolidation_interval_ticks,
            },
            "plasticity": {
                "learning_rate": {
                    "initial": child.plasticity.learning_rate.initial,
                    "min": child.plasticity.learning_rate.minimum,
                    "max": child.plasticity.learning_rate.maximum,
                },
                "forgetting_rate": {
                    "initial": child.plasticity.forgetting_rate.initial,
                    "min": child.plasticity.forgetting_rate.minimum,
                    "max": child.plasticity.forgetting_rate.maximum,
                },
                "eligibility_decay": child.plasticity.eligibility_decay,
            },
            "structure": {
                "grow_threshold": child.structure.grow_threshold,
                "prune_threshold": child.structure.prune_threshold,
                "minimum_support": child.structure.minimum_support,
                "tentative_lifetime_ticks": child.structure.tentative_lifetime_ticks,
            },
            "mutation_policy": {
                "continuous_sigma": child.mutation_policy.continuous_sigma,
                "max_fields_per_generation": child.mutation_policy.max_fields_per_generation,
            },
        }
    )
    assert reloaded == child
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/lab/evolution/test_mutation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont_lab.evolution.mutation'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont_lab/evolution/mutation.py
from __future__ import annotations

import random
from dataclasses import replace
from typing import Literal

from symbiont.cognition.genome import Genome, PlasticityGenes, RangeSpec, StructureGenes


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mutate_continuous_fields(genome: Genome, *, sigma: float, max_fields: int, rng: random.Random) -> Genome:
    candidates: list[str] = [
        "learning_rate",
        "forgetting_rate",
        "eligibility_decay",
        "grow_threshold",
        "prune_threshold",
        "continuous_sigma",
    ]
    chosen = rng.sample(candidates, k=min(max_fields, len(candidates)))

    plasticity = genome.plasticity
    structure = genome.structure
    continuous_sigma = genome.mutation_policy.continuous_sigma

    if "learning_rate" in chosen:
        spec = plasticity.learning_rate
        new_initial = _clip(spec.initial + rng.gauss(0.0, sigma), spec.minimum, spec.maximum)
        plasticity = replace(plasticity, learning_rate=RangeSpec(initial=new_initial, minimum=spec.minimum, maximum=spec.maximum))
    if "forgetting_rate" in chosen:
        spec = plasticity.forgetting_rate
        new_initial = _clip(spec.initial + rng.gauss(0.0, sigma), spec.minimum, spec.maximum)
        plasticity = replace(plasticity, forgetting_rate=RangeSpec(initial=new_initial, minimum=spec.minimum, maximum=spec.maximum))
    if "eligibility_decay" in chosen:
        plasticity = replace(plasticity, eligibility_decay=_clip(plasticity.eligibility_decay + rng.gauss(0.0, sigma), 0.0, 1.0))

    if "grow_threshold" in chosen:
        structure = replace(structure, grow_threshold=_clip(structure.grow_threshold + rng.gauss(0.0, sigma), 0.0, 1.0))
    if "prune_threshold" in chosen:
        structure = replace(structure, prune_threshold=_clip(structure.prune_threshold + rng.gauss(0.0, sigma), 0.0, 1.0))

    mutation_policy = genome.mutation_policy
    if "continuous_sigma" in chosen:
        mutation_policy = replace(mutation_policy, continuous_sigma=max(0.0, continuous_sigma + rng.gauss(0.0, sigma)))

    return replace(genome, plasticity=plasticity, structure=structure, mutation_policy=mutation_policy)


def mutate_soft_budget(genome: Genome, *, field: Literal["soft_node_budget", "soft_edge_budget"], delta: int) -> Genome:
    development = genome.development
    current = getattr(development, field)
    new_value = max(1, current + delta)
    development = replace(development, **{field: new_value})
    return replace(genome, development=development)


def derive_child_genome(parent: Genome, *, new_genome_id: str, mutated: Genome) -> Genome:
    return replace(mutated, genome_id=new_genome_id, parent_ids=(parent.genome_id,))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/lab/evolution/test_mutation.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont_lab/evolution/mutation.py tests/unit/lab/evolution/test_mutation.py
git commit -m "$(cat <<'EOF'
feat(lab): add declarative genome mutation operators

mutate_continuous_fields() perturbs up to max_fields continuous
leaves by a small Gaussian step, reclipped to each field's own
already-validated bounds. mutate_soft_budget() bounds-checks only
non-negativity here -- cross-checking against KernelLimits stays
GenomeCodec.validate()'s job, run by the caller after mutation.
derive_child_genome() sets parent_ids to exactly the single parent's
id and assigns the new id. Genome stays frozen throughout -- every
function returns a new instance via dataclasses.replace().

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 3: Evaluation result and Pareto-archive selection (`evolution/evaluation.py`)

**Files:**
- Create: `src/symbiont_lab/evolution/evaluation.py`
- Test: `tests/unit/lab/evolution/test_evaluation.py`

**Interfaces:**
- Consumes: `LearningObjective`, `dominates` (from `symbiont.cognition.metaplasticity`).
- Produces: `EvaluationResult` (frozen dataclass: `genome_id`, `objective: LearningObjective`, `regime_label: str`, `seed_pair_id: str`), `select_archive(results: tuple[EvaluationResult, ...], *, max_archive_size: int) -> tuple[EvaluationResult, ...]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/lab/evolution/test_evaluation.py
from __future__ import annotations

from symbiont.cognition.metaplasticity import LearningObjective
from symbiont_lab.evolution.evaluation import EvaluationResult, select_archive


def _result(genome_id: str, **objective_kwargs) -> EvaluationResult:
    defaults = dict(prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5)
    defaults.update(objective_kwargs)
    return EvaluationResult(
        genome_id=genome_id, objective=LearningObjective(**defaults), regime_label="regime-a", seed_pair_id="seed-1"
    )


def test_empty_batch_returns_empty_archive():
    assert select_archive((), max_archive_size=10) == ()


def test_dominated_result_is_excluded():
    better = _result("better", prediction_error=0.1)
    worse = _result("worse", prediction_error=0.5)
    archive = select_archive((better, worse), max_archive_size=10)
    assert better in archive
    assert worse not in archive


def test_mutually_non_dominated_results_both_survive():
    a = _result("a", prediction_error=0.1, representation_cost=0.9)
    b = _result("b", prediction_error=0.9, representation_cost=0.1)
    archive = select_archive((a, b), max_archive_size=10)
    assert a in archive
    assert b in archive


def test_archive_never_exceeds_max_size():
    results = tuple(
        _result(f"g{i}", prediction_error=0.1 * i, representation_cost=1.0 - 0.1 * i) for i in range(10)
    )
    archive = select_archive(results, max_archive_size=3)
    assert len(archive) <= 3


def test_identical_results_all_survive_since_none_dominates_another():
    a = _result("a")
    b = _result("b")
    archive = select_archive((a, b), max_archive_size=10)
    assert a in archive
    assert b in archive
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/lab/evolution/test_evaluation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont_lab.evolution.evaluation'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont_lab/evolution/evaluation.py
from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.metaplasticity import LearningObjective, dominates


@dataclass(slots=True, frozen=True)
class EvaluationResult:
    genome_id: str
    objective: LearningObjective
    regime_label: str
    seed_pair_id: str


def select_archive(results: tuple[EvaluationResult, ...], *, max_archive_size: int) -> tuple[EvaluationResult, ...]:
    front: list[EvaluationResult] = []
    for candidate in results:
        if any(dominates(other.objective, candidate.objective) for other in results if other is not candidate):
            continue
        front.append(candidate)

    if len(front) <= max_archive_size:
        return tuple(front)

    def domination_count(result: EvaluationResult) -> int:
        return sum(1 for other in results if dominates(result.objective, other.objective))

    ranked = sorted(front, key=lambda result: (-domination_count(result), result.genome_id))
    return tuple(ranked[:max_archive_size])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/lab/evolution/test_evaluation.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont_lab/evolution/evaluation.py tests/unit/lab/evolution/test_evaluation.py
git commit -m "$(cat <<'EOF'
feat(lab): add EvaluationResult and Pareto-archive selection

select_archive() keeps only the non-dominated subset of a result
batch (via symbiont.cognition.metaplasticity.dominates), capped at
max_archive_size with a crowding-like proxy (prefer results that
dominate more of the full batch) when the front itself is larger than
the cap. Never a weighted-score ranking, never a per-genome win/loss
label -- master doc §8.3: selection produces a new archive, not a
verdict fed back to an individual.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: Lineage archive (`evolution/lineage.py`)

**Files:**
- Create: `src/symbiont_lab/evolution/lineage.py`
- Test: `tests/unit/lab/evolution/test_lineage.py`

**Interfaces:**
- Consumes: nothing new (pure module).
- Produces: `LineageRecord` (frozen dataclass: `genome_id`, `parent_ids: tuple[str, ...]`, `genome_hash`, `created_at_generation: int`), `LineageArchive` with `record(entry)`, `ancestors_of(genome_id) -> tuple[LineageRecord, ...]`, `export() -> tuple[dict[str, object], ...]`, classmethod `restore(payload)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/lab/evolution/test_lineage.py
from __future__ import annotations

import pytest

from symbiont_lab.evolution.lineage import LineageArchive, LineageRecord


def _record(genome_id: str, parent_ids: tuple[str, ...] = (), generation: int = 0) -> LineageRecord:
    return LineageRecord(genome_id=genome_id, parent_ids=parent_ids, genome_hash=f"hash-{genome_id}", created_at_generation=generation)


def test_record_and_retrieve_a_single_entry():
    archive = LineageArchive()
    archive.record(_record("root"))
    assert archive.ancestors_of("root") == ()


def test_duplicate_genome_id_is_rejected():
    archive = LineageArchive()
    archive.record(_record("root"))
    with pytest.raises(ValueError):
        archive.record(_record("root"))


def test_ancestors_of_walks_transitive_chain():
    archive = LineageArchive()
    archive.record(_record("grandparent", generation=0))
    archive.record(_record("parent", parent_ids=("grandparent",), generation=1))
    archive.record(_record("child", parent_ids=("parent",), generation=2))

    ancestors = archive.ancestors_of("child")
    assert [entry.genome_id for entry in ancestors] == ["parent", "grandparent"]


def test_self_referential_parent_is_rejected():
    archive = LineageArchive()
    with pytest.raises(ValueError):
        archive.record(_record("root", parent_ids=("root",)))


def test_cyclic_parent_chain_is_rejected():
    archive = LineageArchive()
    archive.record(_record("a", parent_ids=("b",)))
    with pytest.raises(ValueError):
        archive.record(_record("b", parent_ids=("a",)))


def test_export_and_restore_round_trips():
    archive = LineageArchive()
    archive.record(_record("root"))
    archive.record(_record("child", parent_ids=("root",), generation=1))

    payload = archive.export()
    restored = LineageArchive.restore(payload)

    assert [entry.genome_id for entry in restored.ancestors_of("child")] == ["root"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/lab/evolution/test_lineage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont_lab.evolution.lineage'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont_lab/evolution/lineage.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class LineageRecord:
    genome_id: str
    parent_ids: tuple[str, ...]
    genome_hash: str
    created_at_generation: int


class LineageArchive:
    def __init__(self) -> None:
        self._records: dict[str, LineageRecord] = {}

    def _would_create_cycle(self, genome_id: str, parent_ids: tuple[str, ...]) -> bool:
        stack = list(parent_ids)
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == genome_id:
                return True
            if current in seen or current not in self._records:
                continue
            seen.add(current)
            stack.extend(self._records[current].parent_ids)
        return False

    def record(self, entry: LineageRecord) -> None:
        if entry.genome_id in self._records:
            raise ValueError(f"genome_id {entry.genome_id!r} already recorded")
        if self._would_create_cycle(entry.genome_id, entry.parent_ids):
            raise ValueError(f"recording {entry.genome_id!r} with parents {entry.parent_ids} would create a cycle")
        self._records[entry.genome_id] = entry

    def ancestors_of(self, genome_id: str) -> tuple[LineageRecord, ...]:
        result: list[LineageRecord] = []
        seen: set[str] = set()
        stack = list(self._records[genome_id].parent_ids) if genome_id in self._records else []
        while stack:
            current_id = stack.pop(0)
            if current_id in seen or current_id not in self._records:
                continue
            seen.add(current_id)
            record = self._records[current_id]
            result.append(record)
            stack.extend(record.parent_ids)
        return tuple(result)

    def export(self) -> tuple[dict[str, Any], ...]:
        return tuple(asdict(record) for record in self._records.values())

    @classmethod
    def restore(cls, payload: tuple[dict[str, Any], ...]) -> "LineageArchive":
        archive = cls()
        for entry in payload:
            archive.record(
                LineageRecord(
                    genome_id=entry["genome_id"],
                    parent_ids=tuple(entry["parent_ids"]),
                    genome_hash=entry["genome_hash"],
                    created_at_generation=entry["created_at_generation"],
                )
            )
        return archive
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/lab/evolution/test_lineage.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont_lab/evolution/lineage.py tests/unit/lab/evolution/test_lineage.py
git commit -m "$(cat <<'EOF'
feat(lab): add append-only, cycle-protected lineage archive

LineageArchive.record() rejects a duplicate genome_id (a lineage
entry is a historical fact, not mutable state) and any parent_ids
chain -- including a direct self-reference -- that would create a
cycle, checked via the same transitive walk ancestors_of() already
provides. export()/restore() round-trip exactly. Closes out the
v0.55-v0.59 endogenous-plasticity milestone sequence.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**
- §3.1 mutation operators → Task 2.
- §3.2 evaluation result / Pareto-archive selection → Task 3.
- §3.3 lineage archive → Task 4.
- §1 package scaffold, AST boundary → Task 1.
- Non-goals (§2): no task adds a simulation harness, generational loop, or visualization.

**Type consistency check:** `EvaluationResult.objective` (Task 3) is typed as `symbiont.cognition.metaplasticity.LearningObjective`, matching the v0.58 type exactly. `LineageRecord`'s `genome_hash`/`genome_id` fields (Task 4) match the naming already used by `Genome.genome_hash`/`Genome.genome_id` (v0.55). `derive_child_genome`'s `parent_ids` output (Task 2) matches the `tuple[str, ...]` shape `Genome.parent_ids` already expects.
