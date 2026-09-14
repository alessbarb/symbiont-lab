# v0.58 — Metaplasticity and structure

**Status:** approved for implementation planning
**Base:** `main` (v0.57.0, label-free learning merged)
**Master design:** `docs/design/endogenous-plasticity.md` §6.4-§6.5, §7,
§13 invariants 8-10.
**Roadmap entry:** master doc §17: "Metaplasticidad y estructura —
Parámetros lentos, conceptos emergentes, consolidación, poda y rollback."

## 1. Scope

Five mechanisms, each a pure/composable module extending the v0.56/v0.57
data structures — **no runtime wiring** into `OrganismRuntime`, same
precedent as v0.56/v0.57 (a standalone toolkit; full tick-loop integration
is deferred to whichever future version actually needs the organism to
grow structurally during real residence, so the tick loop changes once
rather than at every cognition milestone):

1. **Composite learning objective** (§6.4) — a five-dimension observable
   vector, Pareto-comparable, never a single hidden scalar.
2. **Metaplasticity** (§6.5) — slow, bounded, revertible adaptation of a
   handful of named parameters within genome-declared ranges.
3. **Structural edge creation** (§7.1) — candidate edges tracked by
   co-activation support, born `tentative`, consolidated only if they
   measurably help outside the window that created them.
4. **Concept creation** (§7.2) — a `CONCEPT` node born from a small stable
   co-varying cluster, opaque id, no invented semantic label.
5. **Pruning lifecycle** (§7.3) — `active → weak → quarantined → removed`,
   using `PlasticEdge`'s existing (since v0.56, unused until now) `support`,
   `age_ticks`, `stable_ticks`, `last_use_tick` fields.

Safe-mode / rollback (§13 invariants 8-10) is included as a small, pure
state tracker (`SafetyState`) — not full checkpoint-rollback integration
(that touches `core/runtime.py`'s checkpoint methods, out of scope until
this module is actually wired in).

## 2. Non-goals

- No `OrganismRuntime` wiring (§1).
- No genome-driven initial topology generation (still deferred, per v0.56).
- No evolution/lab selection — v0.59.
- `CognitiveGraph` stays immutable once constructed; structural mutation
  produces a **new** `CognitiveGraph` via `apply_mutations()` rather than
  mutating topology in place — keeps the existing, already-tested
  construction-time validation as the single source of truth for every
  resulting graph, instead of a second in-place validation path.

## 3. Design

### 3.1 Composite objective (`cognition/metaplasticity.py`)

```python
@dataclass(slots=True, frozen=True)
class LearningObjective:
    prediction_error: float       # lower is better
    representation_cost: float    # lower is better (e.g. node/edge count pressure)
    instability: float            # lower is better (e.g. recent weight churn)
    information_retained: float   # higher is better
    calibration: float            # higher is better

def dominates(a: LearningObjective, b: LearningObjective) -> bool:
    """True if a is at least as good as b on every dimension and strictly
    better on at least one -- standard Pareto dominance, never a weighted
    sum (master doc §6.4: no single hidden global objective)."""
```

### 3.2 Metaplasticity (`cognition/metaplasticity.py`)

```python
@dataclass(slots=True)
class MetaParameter:
    value: float
    minimum: float
    maximum: float
    max_step: float

    def propose(self, *, candidate_delta: float, previous_window_objective: LearningObjective, current_window_objective: LearningObjective) -> None:
        """Applies candidate_delta (clipped to +/- max_step, then to
        [minimum, maximum]) only if current_window_objective is not
        dominated by previous_window_objective (i.e. things did not get
        strictly worse) -- master doc §6.5's "revierte si empeora"
        simplified to "only commit if not worse," which has the same
        net effect (a harmful change never persists) without needing to
        speculatively apply-then-undo."""
```

Eight named parameters exist as plain `MetaParameter` instances a caller
constructs and holds (e.g. one dict `{"learning_rate": MetaParameter(...),
...}`) — this module does not itself own a fixed registry of all eight;
it provides the mechanism, matching the "no metaplasticity of consent/
limits/formats" invariant (§13) by construction: nothing outside a
caller-held `MetaParameter` instance is ever touched.

### 3.3 Structural edge creation (`cognition/structure.py`)

```python
@dataclass(slots=True, frozen=True)
class Mutation:
    kind: Literal["add_edge", "add_node", "quarantine_edge", "remove_edge"]
    payload: Mapping[str, object]  # shape depends on kind, validated by apply_mutations

@dataclass(slots=True, frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None = None

class StructuralPlasticity:
    def __init__(self, *, min_candidate_support: int, tentative_lifetime_ticks: int, cooldown_ticks: int) -> None: ...
    def observe_coactivation(self, *, source_id: str, target_id: str, source_active: bool, target_active: bool, tick: int) -> None: ...
    def propose(self, graph: CognitiveGraph, *, kernel_limits: KernelLimits, tick: int) -> tuple[Mutation, ...]: ...

def validate_mutation(mutation: Mutation, graph: CognitiveGraph, kernel_limits: KernelLimits) -> ValidationResult: ...
def apply_mutations(graph: CognitiveGraph, mutations: tuple[Mutation, ...], kernel_limits: KernelLimits) -> CognitiveGraph: ...
```

Candidate creation rule (§7.1, in `propose()`): a co-activation counter
`(source_id, target_id)` reaching `min_candidate_support` produces an
`add_edge` mutation for a new `tentative` edge (small weight, e.g.
`0.05`) — only if: both nodes already exist in `graph`; no existing edge
already connects that exact `(source, target, kind)`; the graph is not
already at `kernel_limits.max_edges`; and the pair is not still inside
`cooldown_ticks` of a previous mutation involving either endpoint (a
per-node cooldown map, reset whenever that node participates in an
accepted mutation). "Aporta información condicional" (conditional
information gain over existing edges) is checked via the simplest
sound proxy available without ground truth: the new edge is proposed only
if no existing edge already connects the same `(source_id, target_id)`
pair in any kind — a stricter redundancy check (e.g. correlation with an
existing edge's contribution) is deferred; duplicate-relationship
rejection is not deferred, and is enforced by `CognitiveGraph`'s own
existing construction validation when `apply_mutations()` rebuilds the
graph (a second line of defense, not a new mechanism).

Consolidation (promoting `tentative` → ordinary, i.e. the mutation is
simply "kept" — this module has no separate tentative/permanent edge
field; "tentative" is a status derived from `age_ticks < tentative_lifetime_ticks
and support < minimum_support`, not a stored flag) happens implicitly:
`evaluate_edge_lifecycle()` (§3.5) is what actually decides an edge's
fate over time; structural creation only decides *whether a new edge is
born*, not whether it survives.

### 3.4 Concept creation (`cognition/structure.py`)

```python
def propose_concept(
    candidate_node_ids: tuple[str, ...], *, graph: CognitiveGraph, kernel_limits: KernelLimits, rng: random.Random
) -> Mutation | None:
    """candidate_node_ids: 2-4 node ids the caller has already identified
    as a stable co-varying cluster (clustering/co-variance detection is a
    caller concern -- this function only handles the *creation* mechanics
    once a cluster is already known, matching master doc §7.2's own
    framing: it describes what a concept IS, not a specific clustering
    algorithm). Returns None if candidate_node_ids has the wrong size, any
    id is unknown, or kernel_limits.max_concepts is already reached.
    Otherwise returns an add_node Mutation for a new CONCEPT node with an
    opaque id (rng-derived token, e.g. f"concept_{rng.getrandbits(64):016x}"
    -- never derived from the candidate ids' content, matching master doc
    §7.2: "no del contenido ni de rutas") plus add_edge Mutations wiring
    each candidate as an EXCITATORY source into the new concept at a small
    fixed initial weight."""
```

### 3.5 Pruning lifecycle (`cognition/structure.py`)

```python
class EdgeLifecycleState(StrEnum):
    ACTIVE = "active"
    WEAK = "weak"
    QUARANTINED = "quarantined"
    REMOVED = "removed"

def evaluate_edge_lifecycle(
    edge: PlasticEdge, *, current_tick: int, prune_threshold: float, minimum_support: int, quarantine_window_ticks: int
) -> EdgeLifecycleState:
    """Pure function of the edge's own already-tracked fields (support,
    age_ticks, last_use_tick) plus |weight| against prune_threshold --
    WEAK when |weight| < prune_threshold and support >= minimum_support
    (established enough to judge, but weak); QUARANTINED once WEAK has
    persisted past quarantine_window_ticks since last_use_tick; REMOVED
    once QUARANTINED has persisted a second quarantine_window_ticks with
    no recovery (no increase in |weight| or use). Otherwise ACTIVE."""
```

A `REMOVED` edge is not deleted by this function — it reports the state;
the caller (a future runtime-wiring version) is responsible for actually
excluding it when rebuilding the graph via `apply_mutations()`'s
`remove_edge` mutation kind. This keeps `evaluate_edge_lifecycle` a pure
read, matching this module's overall discipline (no hidden side effects
in a function that looks like a query).

### 3.6 Safe mode (`cognition/metaplasticity.py`)

```python
@dataclass(slots=True)
class SafetyState:
    consecutive_failures: int = 0
    frozen: bool = False

    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...  # frozen becomes True at 3 consecutive (§13 invariant 9)
    def reset(self) -> None: ...           # explicit recovery, never automatic silent unfreeze
```

## 4. Testing

- **Objective/Pareto**: `dominates()` is reflexive-false (never dominates
  itself), correctly orders a strictly-better-on-all-dims pair, and
  returns `False` for a genuinely mixed (better on one dim, worse on
  another) pair.
- **Metaplasticity**: a candidate delta commits when the current-window
  objective dominates or ties the previous; never commits when dominated
  by the previous (things got worse); never exceeds `max_step` in one
  call; never leaves `[minimum, maximum]` under adversarial repeated calls.
- **Structural creation**: a pair reaching `min_candidate_support`
  produces exactly one `add_edge` mutation; a pair already connected is
  never re-proposed; a pair on cooldown is not proposed; proposing beyond
  `kernel_limits.max_edges` yields no mutation for that pair.
- **`apply_mutations`**: accepted mutations produce a new `CognitiveGraph`
  containing them; a mutation that would violate `CognitiveGraph`'s own
  construction validation (e.g. pushing past `max_edges`) is rejected via
  `validate_mutation` before ever reaching graph reconstruction.
- **Concept creation**: rejects a candidate set outside 2-4 members;
  rejects an unknown node id; rejects when `max_concepts` reached; two
  calls with the same RNG seed produce the same opaque id (determinism);
  two different seeds produce different ids (no content-derived id leak).
- **Pruning lifecycle**: an edge with high support and strong weight stays
  `ACTIVE`; one with low `|weight|` past `minimum_support` becomes `WEAK`;
  sustained weakness past `quarantine_window_ticks` becomes `QUARANTINED`;
  a quarantined edge whose weight recovers (caller re-evaluates after a
  weight change) returns to `ACTIVE`/`WEAK` rather than continuing toward
  `REMOVED` — quarantine is genuinely a recovery window, not a one-way
  countdown; sustained quarantine with no recovery reaches `REMOVED`.
- **Safe mode**: three consecutive failures freezes; any intervening
  success resets the counter to zero (not just decrements); `frozen` never
  clears itself without an explicit `reset()` call.

## 5. Decisions

| Question | Decision |
| --- | --- |
| Runtime wiring | None yet, matching v0.56/v0.57 precedent |
| Metaplasticity revert mechanism | Simplified to "commit only if not worse" (net-equivalent to speculative-apply-then-revert, without the extra state) |
| Structural mutation model | `CognitiveGraph` stays immutable; `apply_mutations()` rebuilds via the existing constructor, reusing its validation rather than duplicating it |
| "Conditional information" check for edge creation | Simplest sound proxy: no existing edge on the same endpoint pair (any kind) — a correlation-based redundancy check is deferred |
| Concept clustering algorithm | Out of scope — `propose_concept()` takes an already-identified candidate cluster; detecting *which* nodes co-vary is a caller concern |
| Pruning state storage | Not stored — `evaluate_edge_lifecycle()` is a pure function of the edge's existing fields, recomputed on demand |
