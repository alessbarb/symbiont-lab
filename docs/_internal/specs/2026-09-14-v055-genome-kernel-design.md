# v0.55 — Genome kernel

**Status:** approved for implementation planning
**Base:** `main` (v0.54.0, Milestone E closed)
**Master design:** `docs/design/endogenous-plasticity.md` (owner-provided,
sections referenced below by number) — this document slices out only
v0.55's scope; v0.56-v0.59 get their own slice specs later.
**Roadmap entry:** new Milestone (not yet in `docs/roadmap.md` — this PR
adds it), master doc §17: "Kernel de genoma — Esquema cerrado, límites,
codec, identidad y checkpoint."

## 1. Scope

Per the master doc's own versioning discipline (§17: "Cada versión debe
ser útil de forma aislada"), v0.55 delivers a **standalone, useful-by-
itself** slice: a closed genome schema, hard kernel limits, a validating
codec, genome identity (id + hash), and checkpoint persistence for that
identity. It does **not** include the cognitive graph, activation, learning,
structural plasticity, or evolution — those are v0.56-v0.59 (master doc
§17). A genome can be declared, validated, and checkpointed before anything
in the codebase consumes it.

## 2. Non-goals (this slice)

- No `CognitiveGraph`, `PlasticEdge`, activation, or any node/edge runtime
  behavior (v0.56).
- No learning, Oja updates, eligibility traces, or metaplasticity (v0.57,
  v0.58).
- No structural mutation, consolidation, or pruning (v0.58).
- No generational evolution / `symbiont_lab/evolution/` (v0.59) — that
  package is not created yet.
- No optional genome signature (master doc §13 marks it "opcional"; deferred).
- No wiring of the genome into cognition/attention/second-look decisions —
  nothing exists yet to consume it.

## 3. Design

### 3.1 New package: `src/symbiont/cognition/`

Per master doc §10's suggested module list, this slice creates:

```text
src/symbiont/cognition/
  __init__.py
  types.py        # closed node/edge catalogs + numeric range constants (§5.1, §5.2, §5.3)
  limits.py       # KernelLimits — hard, owner-configured, never learnable (§7.4)
  genome.py       # Genome dataclasses, GenomeCodec (§4.2, §10, §11)
  checkpoint.py   # genome checkpoint bolt-on (§12, identity only this slice)
```

`graph.py`, `activation.py`, `learning.py`, `structure.py`,
`metaplasticity.py` (also in the doc's suggested list) are **not** created
in this slice — they belong to v0.56+ and would sit empty, violating the
"useful in isolation" discipline.

`tests/experimental_integrity/test_ground_truth_boundary.py`'s existing
`test_symbiont_contains_only_subject_modules` allowlist test must add
`"cognition"` or it fails the moment this package exists — this is
expected and part of the task, not a regression.

### 3.2 Closed catalogs and ranges (`cognition/types.py`)

Master doc §5.1/§5.2 define the closed node/edge kind catalogs; §5.3 defines
numeric ranges. These belong to the kernel (§4.1: "catálogo cerrado de
tipos de nodo y operadores") even though nothing constructs a graph node
yet — v0.56 imports these, this slice only defines and bounds-checks them.

```python
class NodeKind(StrEnum):
    SENSE = "sense"
    CONCEPT = "concept"
    STATE = "state"
    PREDICTOR = "predictor"
    GATE = "gate"
    READOUT = "readout"

class EdgeKind(StrEnum):
    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"
    PREDICTIVE = "predictive"
    GATING = "gating"

WEIGHT_RANGE = (-2.0, 2.0)
PLASTICITY_RANGE = (0.0, 1.0)
GATE_RANGE = (0.0, 1.0)
EDGE_DELAY_TICKS_RANGE = (0, 1)
```

No node type named `ACTION` exists — enforced structurally by this being a
closed enum with no such member, matching master doc §5.1's explicit
statement.

### 3.3 `KernelLimits` (`cognition/limits.py`)

Hard, owner-configured, **never part of the genome** (master doc §4.1: "El
kernel no forma parte del genoma y ningún peso puede alterar sus límites").
Defaults from master doc §7.4's table:

```python
@dataclass(slots=True, frozen=True)
class KernelLimits:
    max_nodes: int = 128
    max_concepts: int = 32
    max_edges: int = 1024
    max_tentative_edges: int = 128
    max_structural_mutations_per_consolidation: int = 8
    consolidation_interval_ticks: int = 32
    max_plastic_checkpoint_bytes: int = 2 * 1024 * 1024
```

All fields validated positive in `__post_init__` (same discipline as every
other limits/config dataclass in the codebase, e.g. `HostLifecycle`,
`AttentionBudget`).

### 3.4 Genome schema and codec (`cognition/genome.py`)

Structure exactly matches master doc §11's JSON example. Each nested
section is its own frozen dataclass:

```python
@dataclass(slots=True, frozen=True)
class RangeSpec:
    initial: float
    minimum: float
    maximum: float
    # validated: minimum <= initial <= maximum, all finite

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
    eligibility_decay: float  # [0.0, 1.0]

@dataclass(slots=True, frozen=True)
class StructureGenes:
    grow_threshold: float      # [0.0, 1.0]
    prune_threshold: float     # [0.0, 1.0]
    minimum_support: int
    tentative_lifetime_ticks: int

@dataclass(slots=True, frozen=True)
class MutationPolicyGenes:
    continuous_sigma: float    # >= 0.0
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
        """sha256 of the canonical (sorted-key) JSON representation —
        identity/tamper-check, not a secret. Recomputed on demand, never
        stored as mutable state."""
```

**`GenomeCodec.load(payload)`** — strict, closed-schema parse. This is the
non-executable-content boundary (master doc §2 non-goals: never
"generar/editar/importar/ejecutar" code; §13 invariant 3: no learned field
is ever used as a path/module/command):

- Top-level keys must be **exactly** `{schema_version, genome_id,
  parent_ids, kernel_compatibility, development, plasticity, structure,
  mutation_policy}` — any missing or unknown key is a hard rejection, not
  a warning.
- `genome_id` and every entry in `parent_ids` must match
  `^genome_[A-Za-z0-9_-]{1,64}$` — a safe opaque token, structurally
  incapable of being a path, module name, or expression.
- `kernel_compatibility` must match a closed grammar:
  `(>=|<=|>|<|==)\d+\.\d+(\.\d+)?` clauses joined by `,` — parsed by a
  small hand-written tokenizer, **never** `eval`/`exec`.
- Every numeric field is type- and range-checked; `RangeSpec.initial` must
  satisfy `minimum <= initial <= maximum`, all three finite
  (`math.isfinite`).
- `parent_ids` capped at a small fixed length (e.g. 8) — no unbounded
  lineage chains smuggled through a single genome payload.

**`GenomeCodec.validate(genome, kernel_limits)`** — cross-checks the
already-structurally-valid genome against the *hard* kernel limits (never
the reverse — a genome can only request less than the kernel allows, never
more):

- `development.soft_node_budget <= kernel_limits.max_nodes`
- `development.soft_edge_budget <= kernel_limits.max_edges`
- `development.initial_concepts <= kernel_limits.max_concepts`
- `kernel_compatibility` range must currently be satisfied by
  `symbiont.__version__` (parsed as a `(major, minor, patch)` tuple;
  a two-component bound like `0.55` is treated as `0.55.0`).

A genome failing either `load()` or `validate()` raises a dedicated
`GenomeError(ValueError)` with a specific, actionable reason — never a bare
`ValueError`/`KeyError`/`TypeError` leaking internal structure, matching
`CheckpointError`'s existing precedent in `host/checkpoint.py`.

### 3.5 Checkpoint identity (`cognition/checkpoint.py`)

Genome content is small, bounded, and declarative — unlike sensory EWMA
state, persisting it **in full** is safe (it is config, not raw telemetry).
Follows the `sensory_development` bolt-on pattern (own namespace, own
internal `schema_version`, not part of `host/checkpoint.py`'s
`CHECKPOINT_SCHEMA_VERSION` chain) rather than the `self_model` pattern —
genome versioning is a wholly separate concern (declarative config schema
evolution) from the acclimation/rhythm/drift/self-model numeric-state
schema chain, and forcing them into one version number would couple two
unrelated evolution paths.

```python
def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
    """None in, None out — an organism with no genome checkpoints nothing
    new here."""

def restore_genome_checkpoint(
    payload: dict[str, Any] | None, *, kernel_limits: KernelLimits
) -> Genome | None:
    """Re-validates fully (load + validate) on restore — a checkpoint is
    untrusted input, same discipline as every other restore path in this
    codebase (roadmap safety finding A07 precedent). Also recomputes
    genome_hash from the restored fields and rejects a mismatch against
    the persisted hash — defense in depth against a hand-edited or
    corrupted checkpoint claiming a genome it doesn't actually match."""
```

Exported payload shape: the full genome content (matching §11's JSON
shape) plus `"genome_hash": <sha256 hex>` for the tamper check above.

### 3.6 `OrganismRuntime` wiring (minimal, additive)

```python
def __init__(self, *, ..., genome: Genome | None = None, kernel_limits: KernelLimits | None = None) -> None:
    self._genome = genome
    self._kernel_limits = kernel_limits if kernel_limits is not None else KernelLimits()
```

- `OrganismRuntime.genome` property (`Genome | None`).
- `checkpoint()`: `payload["genome"] = export_genome_checkpoint(self._genome)`.
- `from_checkpoint()`: restores via `restore_genome_checkpoint(payload.get("genome"), kernel_limits=kwargs.get("kernel_limits") or KernelLimits())`, passed to the constructor.
- **No other behavior changes.** A runtime with no genome (the default,
  every existing test) is byte-for-byte unaffected — this is the same
  additive discipline as every self-model/attention change in v0.53/v0.54.

### 3.7 AST/architecture boundary

`test_ast_symbiont_never_imports_symbiont_lab` already `rglob`s all of
`src/symbiont`, so it automatically covers `cognition/` with no changes
needed. Add one explicit, narrowly-scoped test naming `cognition/`
directly (master doc §10: "la regla AST existente debe ampliarse para
demostrarlo") so the boundary is documented at the package level, not only
implied by a generic rglob.

## 4. Testing

- **Types/limits**: `KernelLimits` rejects non-positive fields; closed
  enums have exactly the documented members (regression guard against an
  accidental `ACTION` or extra kind being added later).
- **Genome load — rejection matrix**: missing top-level key, unknown
  top-level key, malformed `genome_id`/`parent_ids` (path-like, containing
  slashes/spaces/control characters), oversized `parent_ids`, malformed
  `kernel_compatibility` grammar, non-finite/out-of-range numeric field,
  `RangeSpec` with `initial` outside `[minimum, maximum]`, wrong JSON
  types (string where int expected, etc.), excessive nesting depth.
- **Genome load — acceptance**: master doc §11's exact example round-trips
  through `load()` without error.
- **`validate()`**: a genome whose soft budgets exceed `KernelLimits`
  fields is rejected; a genome whose `kernel_compatibility` excludes the
  running `symbiont.__version__` is rejected; a genome within all bounds
  passes.
- **`genome_hash`**: deterministic and independent of source dict key
  order; two genomes differing in one field produce different hashes.
- **Checkpoint round-trip**: `export_genome_checkpoint`/
  `restore_genome_checkpoint` round-trips a valid genome exactly; a
  tampered payload (one field changed post-export, hash left stale) is
  rejected on restore; `None` genome round-trips to `None`.
- **`OrganismRuntime` wiring**: a runtime with no genome behaves exactly
  as before (regression guard against every existing test in
  `test_organism_runtime.py`); a runtime constructed with a genome
  round-trips it through `checkpoint()`/`from_checkpoint()`.
- **Architecture**: the new explicit `cognition`-scoped AST test; the
  allowlist test passes once updated to include `cognition`.

## 5. Decisions

| Question | Decision |
| --- | --- |
| Module scope this slice | `types.py`, `limits.py`, `genome.py`, `checkpoint.py` only — no graph/learning/structure/metaplasticity files created empty |
| Checkpoint versioning | Genome gets its own bolt-on namespace (like `sensory_development`), not folded into `host/checkpoint.py`'s `CHECKPOINT_SCHEMA_VERSION` chain |
| Genome signature | Deferred (master doc marks it optional) |
| Kernel version source | `symbiont.__version__`, parsed as `(major, minor, patch)` |
| Runtime wiring | Fully optional constructor param, zero behavior change when absent |
| §19 open product decisions (identity/herencia/selección/narrativa) | Not applicable to v0.55 — they concern v0.58 (herencia/narrativa) and v0.59 (selección); revisit when scoping those slices |
