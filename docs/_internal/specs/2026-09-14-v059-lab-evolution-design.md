# v0.59 — Laboratory evolution

**Status:** approved for implementation planning
**Base:** `main` (v0.58.0, metaplasticity and structure merged)
**Master design:** `docs/design/endogenous-plasticity.md` §8, §19.3.
**Roadmap entry:** master doc §17: "Evolución de laboratorio — Mutación
generacional, evaluación multientorno, linaje y visualización."

## 1. Scope

A new package, `symbiont_lab/evolution/`, matching master doc §10's
suggested module list — genome mutation, an evaluation record (not a
simulation harness; scoring itself belongs to whatever experiment runs
the organism, already `symbiont_lab`'s domain), Pareto-archive selection,
and an append-only lineage log:

```text
symbiont_lab/evolution/
  mutation.py    # declarative genome mutation operators (§8.2)
  evaluation.py  # EvaluationResult record + Pareto-archive selection (§8.3)
  lineage.py     # append-only lineage archive (§8.1)
```

`symbiont_lab` already freely imports `symbiont` (the existing AST
boundary test only forbids the reverse) — this package imports
`symbiont.cognition.genome.Genome`/`GenomeCodec` and
`symbiont.cognition.metaplasticity.LearningObjective`/`dominates`
directly, no new modules needed there.

Evolution belongs entirely to `symbiont_lab`, never the resident
organism (§8: "Un individuo no se reproduce ni se despliega a sí mismo") —
this is an architectural boundary, not just a style preference, so this
slice adds an explicit AST test alongside the existing
`test_ast_symbiont_never_imports_symbiont_lab` confirming
`symbiont/` contains no evolution/mutation/selection code of its own.

## 2. Non-goals

- No actual multi-environment simulation harness (§8.3's "cada genoma se
  prueba con semillas emparejadas en varios regímenes") — this slice
  defines the *result record* a harness would produce and the *selection
  logic* over a batch of results; running organisms across regimes to
  produce those results is existing `symbiont_lab` experiment-harness
  territory (`experiments/`, `studies/`), reused rather than duplicated,
  and wiring a concrete evolutionary experiment protocol is left to
  whoever writes that specific study, not this foundational package.
- No visualization / Observatory lineage UI (§17's "visualización" — a
  separate, later Observatory-side task, not a `symbiont_lab/evolution/`
  concern).
- No automatic generational loop (spawn → evaluate → select → repeat) —
  this slice provides the building blocks (`mutate`, `select_archive`,
  `LineageArchive`) a caller composes; the master doc's own §19.3
  recommendation ("archivo automático, activación humana") means
  selection *proposes* archive membership but a new genome's *birth* is a
  human-triggered action outside this package's scope.

## 3. Design

### 3.1 Mutation (`evolution/mutation.py`)

Master doc §8.2's five admitted mutation kinds, each a pure function
`Genome -> Genome` (never in place — `Genome` is already frozen):

```python
def mutate_continuous_fields(genome: Genome, *, sigma: float, max_fields: int, rng: random.Random) -> Genome:
    """Perturbs up to max_fields continuous numeric leaves (RangeSpec
    .initial values, eligibility_decay, thresholds, continuous_sigma
    itself) by a small Gaussian perturbation (stddev=sigma), each
    reclipped to its own field's already-validated bounds. Field
    selection is rng-driven and capped by mutation_policy.max_fields_per_generation."""

def mutate_soft_budget(genome: Genome, *, field: Literal["soft_node_budget", "soft_edge_budget"], delta: int) -> Genome:
    """Bounded change to a soft development budget -- never validated
    against KernelLimits here (that stays GenomeCodec.validate()'s job,
    called by the caller after mutation, same as loading any genome)."""

def derive_child_genome(parent: Genome, *, new_genome_id: str, mutations: tuple[Genome, ...]) -> Genome:
    """Produces the final child genome: takes the parent's fields,
    applies the given already-mutated intermediate genomes' *changed*
    fields (composing multiple mutation function outputs), sets
    parent_ids=(parent.genome_id,) (capped at the existing 8-parent
    limit from v0.55 -- a single parent here, so always within bounds),
    and the new genome_id. Re-validated by the caller via
    GenomeCodec.load()/.validate() before it is treated as a real
    genome -- this function does not re-run the codec itself, since a
    composed set of already-individually-valid field changes cannot
    introduce a new *structural* violation (unknown keys, wrong types),
    only a possible *range* violation (e.g. a budget mutation pushing
    past a kernel limit), which validate() already exists to catch."""
```

No mutation of schema, operator catalog, absolute maxima, permission
policy, or the kernel itself (§8.2's explicit prohibition — trivially true
here since nothing in this module ever touches `KernelLimits` or the
closed `NodeKind`/`EdgeKind` catalogs).

### 3.2 Evaluation result and Pareto-archive selection (`evolution/evaluation.py`)

```python
@dataclass(slots=True, frozen=True)
class EvaluationResult:
    genome_id: str
    objective: LearningObjective     # from symbiont.cognition.metaplasticity
    regime_label: str                # opaque caller-defined regime/seed-pair identifier, never host identity
    seed_pair_id: str                # which paired-seed comparison this came from (§8.3: "seeds emparejadas")

def select_archive(
    results: tuple[EvaluationResult, ...], *, max_archive_size: int
) -> tuple[EvaluationResult, ...]:
    """Returns the non-dominated subset of results (Pareto front, via
    metaplasticity.dominates), capped at max_archive_size -- when the
    front itself exceeds the cap, keeps the max_archive_size entries
    with the most distinct dominance relationships to the rest (a
    simple crowding proxy: prefer results that dominate more of the
    remaining discarded set), never a hidden single-score ranking.
    Never reads or returns anything resembling "did this genome win" as
    a label attached to a genome -- callers get a new archive, not a
    per-individual verdict (§8.3: "La selección nunca alimenta al
    individuo con la etiqueta de si "ganó"")."""
```

### 3.3 Lineage archive (`evolution/lineage.py`)

```python
@dataclass(slots=True, frozen=True)
class LineageRecord:
    genome_id: str
    parent_ids: tuple[str, ...]
    genome_hash: str
    created_at_generation: int

class LineageArchive:
    def __init__(self) -> None: ...
    def record(self, entry: LineageRecord) -> None: ...
    def ancestors_of(self, genome_id: str) -> tuple[LineageRecord, ...]: ...
    def export(self) -> tuple[dict[str, object], ...]: ...
    @classmethod
    def restore(cls, payload: tuple[dict[str, object], ...]) -> "LineageArchive": ...
```

Append-only (`record()` never overwrites an existing `genome_id` — raises
if called twice for the same id, since a lineage entry is a historical
fact, not mutable state). `ancestors_of()` walks `parent_ids` transitively,
bounded by the archive's own size (no unbounded recursion risk — a
lineage graph only grows by explicit `record()` calls, and a malformed
cycle is rejected: `record()` raises if `genome_id` appears in its own
`parent_ids` chain, checked via the same `ancestors_of()` walk before
insertion).

## 4. Testing

- **Mutation**: `mutate_continuous_fields` never exceeds `max_fields`
  changed leaves, never produces a value outside that field's own
  existing bounds (reuses `GenomeCodec.validate()`/`RangeSpec`'s own
  validation as the check, not a duplicate range table); same seed
  produces the same mutation (determinism); `derive_child_genome` sets
  `parent_ids` to exactly `(parent.genome_id,)` and a fresh `genome_id`,
  and the result still round-trips through `GenomeCodec.load()`.
- **Evaluation/selection**: `select_archive` returns only non-dominated
  results; a result dominated by another in the batch never appears in
  the output; respects `max_archive_size`; a batch entirely on one
  Pareto front larger than the cap is truncated, never raises; an empty
  batch returns an empty archive.
- **Lineage**: `record()` twice for the same `genome_id` raises;
  `ancestors_of()` returns the correct transitive chain for a 3-generation
  lineage; a self-referential or cyclic `parent_ids` is rejected at
  `record()` time; `export()`/`restore()` round-trips exactly.
- **Architecture**: the new AST test confirming `symbiont/` contains no
  evolution/mutation/selection code passes; the existing
  `test_ast_symbiont_never_imports_symbiont_lab` still passes
  (`symbiont_lab/evolution/` importing `symbiont.cognition.*` is fine —
  only the reverse direction is forbidden).

## 5. Decisions

| Question | Decision |
| --- | --- |
| Simulation harness | Out of scope — reuse existing `symbiont_lab` experiment infrastructure for actually running organisms; this package only defines the result record and selection logic |
| Automatic generational loop | Out of scope — building blocks only, composed by a caller; birth of a new genome stays human-triggered per master doc §19.3's own recommendation |
| Selection algorithm | Pareto-front archive, capped by a crowding-like proxy — never a single weighted score |
| Lineage cycle protection | `record()` rejects any `parent_ids` chain that would create a cycle, checked via the same traversal `ancestors_of()` already provides |
| Visualization | Out of scope — a later, separate Observatory-side task |
