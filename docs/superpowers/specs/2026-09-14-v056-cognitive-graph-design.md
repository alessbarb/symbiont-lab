# v0.56 — Cognitive graph

**Status:** approved for implementation planning
**Base:** `main` (v0.55.0, genome kernel merged)
**Master design:** `docs/design/endogenous-plasticity.md` §5 (network model),
§9 (tick cycle), §10 (contracts) — this slices out v0.56's scope only.
**Roadmap entry:** master doc §17: "Grafo cognitivo — Nodos/aristas,
activación recurrente determinista y readouts internos."

## 1. Scope

A static, deterministic cognitive graph: node/edge data structures, sensory
normalization (master doc §5.4), and synchronous double-buffered activation
propagation (§5.3). Constructed explicitly (nodes/edges supplied by the
caller) — **no genome-driven automatic topology generation** (that
algorithm isn't specified anywhere in the master doc and belongs to v0.58's
structural creation rules, §7.1-§7.2, which are the actual "how do edges
and concepts get created" mechanism). No learning, no structural mutation.

## 2. Non-goals (this slice)

- No learning: weights/bias/tau are set at construction and never change
  during `activate()` (v0.57).
- No eligibility trace *updates*, no Oja rule (v0.57). The `eligibility`
  field exists on `PlasticEdge` per master doc §5.2 but this slice never
  writes to it after construction.
- No structural creation/consolidation/pruning (v0.58).
- No metaplasticity / learned parameters (v0.57/58).
- No genome-to-topology generation algorithm (not specified in the master
  doc; deferred — see §1).
- No wiring into `OrganismRuntime`'s tick loop yet — this is a standalone,
  independently-testable engine. Wiring it into the tick cycle (master doc
  §9 steps 4-6) is v0.57's job, once there's something (prediction error)
  for the graph's output to feed into.

## 3. Two design gaps in the master doc, resolved here

The master doc's activation formula (§5.3) is:

$$u_j(t)=b_j+\sum_i g_{ij}(t)\,w_{ij}\,a_i(t-d_{ij})$$

This requires a per-edge gate $g_{ij}(t) \in [0,1]$ and a per-edge delay
$d_{ij} \in \{0,1\}$. But §5.2's `PlasticEdge` code sample lists only
`source_id, target_id, kind, weight, plasticity, eligibility, support,
age_ticks, stable_ticks, last_use_tick` — no `gate` and no `delay` field.
Both gaps were raised with the design owner before implementation; both
have owner-confirmed resolutions:

### 3.1 Gate — GATING edges modulate co-targeting edges (owner-confirmed)

A `GATING` edge from node $i$ to node $j$ does **not** contribute a term to
$u_j$ directly. Instead, its source activation becomes a multiplicative
gate applied to every *other* (non-`GATING`) edge that also targets $j$:

```text
for target node j:
    gate(j) = 1.0                                    # default: fully open
    for each GATING edge (i -> j):
        component = clip(edge.weight * a_i(t - edge.delay_ticks), 0.0, 1.0)
        gate(j) *= component                         # product: any closed gate suppresses j

    u_j = b_j + sum over non-GATING edges (i -> j) of
              gate(j) * edge.weight * a_i(t - edge.delay_ticks)
```

Multiple `GATING` edges targeting the same node combine by **product**
(AND-like — any one closed gate suppresses the target), the conservative
choice given no combination rule is specified. A `GATING` edge's own
`weight` field scales its gate contribution before clipping, giving a
future learning rule (v0.57+) something meaningful to adjust — an
unweighted gate would make that field permanently inert for this edge kind.

### 3.2 Delay — tied to source node kind, validated at construction

$d_{ij}=0$ means "this tick's value of the source"; $d_{ij}=1$ means
"last tick's value." A value is only available *this* tick, before graph
propagation runs, for a `SENSE` node — master doc §9 step 4 normalizes
sense readings before step 5 runs graph propagation "con el estado de
$t-1$." Every other node kind (`CONCEPT`, `STATE`, `PREDICTOR`, `GATE`,
`READOUT`) is computed *during* this same synchronous pass, so its "this
tick" value does not exist yet when another node's $u_j$ is being computed
— using it would be an undefined evaluation-order hazard in a graph that
must stay order-independent (master doc §5.3: "no depend[e] del orden de
los diccionarios").

**Resolved rule:** `delay_ticks == 0` is valid **only** when the edge's
source node has `kind == NodeKind.SENSE`; every other source kind must
declare `delay_ticks == 1`. Enforced as a `CognitiveGraph` construction-time
validation (`GraphError`), not a runtime check — an invalid graph is
rejected before it can ever run, not discovered mid-activation.

`PlasticEdge` gains `delay_ticks: int` (not in the master doc's illustrative
code sample, added for the reason above) alongside the fields the doc does
list. `PlasticEdge` is **mutable** (`@dataclass(slots=True)`, not frozen)
exactly as shown in the master doc — future learning (v0.57) updates
`weight`/`eligibility` in place.

## 4. Design

### 4.1 New modules

```text
src/symbiont/cognition/
  activation.py   # sensory normalization (§5.4)
  graph.py        # PlasticNode, PlasticEdge, CognitiveGraph, GraphFrame, TickContext
```

### 4.2 Sensory normalization (`cognition/activation.py`, master doc §5.4)

$$z_i(t)=\operatorname{clip}\left(\frac{x_i(t)-\mu_i}{\max(\sigma_i,\epsilon)},-z_{max},z_{max}\right), \qquad a_i(t)=\tanh(z_i(t)/s)$$

A small per-sense running-statistics tracker (same EWMA-mean/variance
shape as `RunningStat` in `core/model.py` and `SenseState` in
`host/adaptive.py` — this codebase already has that pattern twice; this is
a third, intentionally independent instance scoped to graph input, not a
shared dependency, since `symbiont.cognition` must not import from
`symbiont.host` beyond what's already established and this normalization
is a graph-input concern, not a host concern):

```python
@dataclass(slots=True)
class SensoryNormalizer:
    mean: float = 0.0
    variance: float = 0.0
    count: int = 0

    def normalize(self, raw_value: float, *, z_max: float = 4.0, softness: float = 2.0) -> float: ...
```

`z_max` and `softness` (`s` in the formula) are fixed constants (module
defaults), not learnable — this slice has no metaplasticity.

### 4.3 Graph data structures (`cognition/graph.py`)

```python
@dataclass(slots=True, frozen=True)
class PlasticNode:
    node_id: str
    kind: NodeKind
    bias: float = 0.0
    tau: float = 1.0          # temperature; validated range, see TAU_RANGE below

@dataclass(slots=True)
class PlasticEdge:
    source_id: str
    target_id: str
    kind: EdgeKind
    weight: float             # WEIGHT_RANGE [-2.0, 2.0]
    plasticity: float         # PLASTICITY_RANGE [0.0, 1.0]
    delay_ticks: int          # EDGE_DELAY_TICKS_RANGE {0, 1} -- see §3.2
    eligibility: float = 0.0
    support: int = 0
    age_ticks: int = 0
    stable_ticks: int = 0
    last_use_tick: int = 0

@dataclass(slots=True, frozen=True)
class TickContext:
    tick: int

@dataclass(slots=True, frozen=True)
class GraphFrame:
    tick: int
    activations: Mapping[str, float]   # every node, including SENSE echoes
    readouts: Mapping[str, float]      # subset: only NodeKind.READOUT nodes
```

`TAU_RANGE: tuple[float, float] = (0.1, 10.0)` added to `cognition/types.py`
in this slice (the master doc says "$\tau$ tiene rango validado" without
giving numbers; this is a fixed, conservative default — `tau` near 0
makes `tanh` saturate to a near-step function, `tau` far above 10 makes it
nearly linear/inert over the practical input range).

### 4.4 `CognitiveGraph`

```python
class CognitiveGraph:
    def __init__(self, *, nodes: tuple[PlasticNode, ...], edges: tuple[PlasticEdge, ...], kernel_limits: KernelLimits) -> None: ...
    def activate(self, inputs: Mapping[str, float], context: TickContext, *, previous: Mapping[str, float] | None = None) -> GraphFrame: ...
```

**Construction validation** (`GraphError(ValueError)`, same family
discipline as `GenomeError`/`CheckpointError`):

- Every node id unique; every edge's `source_id`/`target_id` refers to a
  declared node (no dangling edges).
- `len(nodes) <= kernel_limits.max_nodes`,
  `len(edges) <= kernel_limits.max_edges`,
  count of `NodeKind.CONCEPT` nodes `<= kernel_limits.max_concepts`.
- No node kind outside the closed `NodeKind` catalog (structurally
  guaranteed by the enum, checked defensively at the boundary anyway since
  nodes may arrive from external construction code).
- `PlasticNode.tau` within `TAU_RANGE`; `PlasticEdge.weight` within
  `WEIGHT_RANGE`; `PlasticEdge.plasticity` within `PLASTICITY_RANGE`;
  `PlasticEdge.delay_ticks` within `EDGE_DELAY_TICKS_RANGE` **and** `== 0`
  only if the source node's kind is `NodeKind.SENSE` (§3.2).
- No two edges with identical `(source_id, target_id, kind)` — a duplicate
  relationship, not a legitimate multi-edge (master doc §7.1 explicitly
  treats "no duplica una arista ya consolidada" as a structural invariant;
  enforcing it at construction here keeps the graph itself the single
  source of truth rather than relying on a future structural-plasticity
  layer to have gotten it right).

**`activate()`**:

1. `inputs` supplies this tick's normalized `SENSE` activations (already
   passed through `SensoryNormalizer` — `activate()` itself does not call
   the normalizer; that's the caller's job, keeping this method a pure
   function of its arguments, which is what makes determinism testable).
2. `previous` supplies the last tick's full activation frame for every
   node (defaults to all-zero for every node if omitted — the cold-start
   case, e.g. the very first tick).
3. For each non-`SENSE` node $j$, compute $u_j$ and $a_j = \tanh(u_j /
   \tau_j)$ per §3.1/§3.2's resolved rules, reading exclusively from
   `inputs` (for `SENSE`-sourced, `delay_ticks == 0` edges) and `previous`
   (for every `delay_ticks == 1` edge) — **never** from values computed
   earlier in this same `activate()` call, which is what makes the result
   independent of node/edge iteration order (double buffer: a fresh output
   dict, never mutating `previous` or reading back from itself mid-pass).
4. `SENSE` node activations in the returned frame are echoed directly from
   `inputs` (a `SENSE` node has no incoming edges by definition in this
   slice — nothing computes its $u_j$; enforced as a construction
   validation: a `SENSE` node with any incoming edge is rejected).
5. Every activation is `math.isfinite`-checked before being placed in the
   output frame; a non-finite result raises `GraphError` rather than
   silently propagating `nan`/`inf` (master doc §15 property: "para
   cualquier entrada finita, todo estado permanece finito y acotado").

## 5. Testing

- **Sensory normalization**: cold start (count=0) returns a defined value
  (not a division-by-zero crash); z-score clipping at `z_max`; output
  always in $(-1, 1)$ via `tanh`.
- **Graph construction — rejection matrix**: duplicate node id, dangling
  edge endpoint, node/edge/concept count exceeding `KernelLimits`, tau/
  weight/plasticity/delay out of range, `delay_ticks == 0` on a non-`SENSE`
  source, a `SENSE` node with an incoming edge, duplicate `(source,
  target, kind)` edge.
- **Activation determinism**: two `CognitiveGraph` instances built from
  the same nodes/edges (constructed via different insertion orders, e.g.
  reversed tuples) produce byte-identical `GraphFrame.activations` for the
  same `inputs`/`previous` — the master doc's own explicit invariant.
- **Gating**: a `GATING` edge with source activation near 0 suppresses a
  co-targeting `EXCITATORY` edge's contribution close to zero; near 1
  passes it through almost unchanged; two `GATING` edges targeting the
  same node combine by product (both must be "open" for full signal).
- **Delay**: a `delay_ticks=0` `SENSE`-sourced edge reacts to `inputs`
  immediately (same-tick); a `delay_ticks=1` edge reacts only on the
  *next* `activate()` call (echoes `previous`, ignores this tick's
  `inputs` change for that source).
- **Finiteness**: an extreme `inputs` value (e.g. `1e12`) and an extreme
  `bias`/`weight` combination never produce `nan`/`inf` in the output
  frame (tanh saturation handles this structurally; test it explicitly
  anyway per master doc §15's adversarial-input requirement).
- **Readouts**: `GraphFrame.readouts` contains exactly the `READOUT`-kind
  node activations, nothing else.
- **Cold start**: `activate()` with `previous=None` treats every
  `delay_ticks=1` source as activation `0.0` without raising.

## 6. Decisions

| Question | Decision |
| --- | --- |
| Gate semantics (doc gap) | GATING edge source activation, weight-scaled and clipped to [0,1], multiplies co-targeting edges by product; owner-confirmed |
| Delay semantics (doc gap) | `delay=0` valid only for `SENSE`-kind sources (fresh this tick); everything else must be `delay=1`; validated at construction |
| Genome-driven topology generation | Out of scope — not specified in the master doc; construction is explicit (caller supplies nodes/edges) until v0.58's structural creation rules exist |
| `PlasticEdge` mutability | Mutable, matching the master doc's exact `@dataclass(slots=True)` (not frozen) — future learning updates fields in place |
| `TAU_RANGE` | `(0.1, 10.0)`, a fixed conservative default (doc specifies "validated range" without numbers) |
| Runtime wiring | None yet — standalone engine, wired into `OrganismRuntime`'s tick cycle starting v0.57 once there's a learning signal to produce |
