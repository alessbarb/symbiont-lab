# v0.57 — Label-free learning

**Status:** approved for implementation planning
**Base:** `main` (v0.56.0, cognitive graph merged)
**Master design:** `docs/design/endogenous-plasticity.md` §6.1-§6.3.
**Roadmap entry:** master doc §17: "Aprendizaje sin etiqueta — Predicción
local, Oja, elegibilidad y adaptación de pesos."

## 1. Scope

Three learning mechanisms, each a pure, composable function operating on
the v0.56 graph's data structures — no runtime wiring, matching v0.56's
own precedent (a standalone, independently-testable module):

1. **Prediction error** (§6.1): compares a `PREDICTOR` node's *previous*
   activation (its prediction, made last tick) against its designated
   target's *current* activation, through a Huber loss.
2. **Eligibility traces** (§6.3): per-edge decaying trace of
   pre/post-synaptic coincidence, gating which edges are even eligible for
   a weight update.
3. **Bounded Oja weight update** (§6.2): the actual weight adaptation,
   applied only to eligible edges.

## 2. Non-goals (this slice)

- No metaplasticity (`learning_rate` stays a fixed, caller-supplied scalar
  this slice — genome-bounded *slow adaptation* of it is v0.58, per
  master doc §6.5 and the roadmap table assigning metaplasticity to v0.58).
- No composite Pareto objective (§6.4) — that feeds *growth* decisions,
  which are v0.58's structural-plasticity job.
- No structural creation/consolidation/pruning (v0.58).
- No wiring into `OrganismRuntime`'s tick loop (same non-goal v0.56 had;
  the self-model-derived modulation term `m(t)` and attention-derived
  eligibility gating are accepted as plain caller-supplied arguments here,
  not sourced from `SelfModel`/`attend_to_host` yet — that integration is
  a `core/runtime.py` wiring task better done once v0.58 exists too, so
  the tick loop changes once, not three times).

## 3. One design gap resolved

`PREDICTOR`'s master-doc description (§5.1: "Contexto previo → Predice una
activación futura") doesn't say *which* node's future a given predictor
predicts. `PlasticNode` gains `predicts_node_id: str | None = None` — a
disclosed addition (same pattern as v0.56's `delay_ticks`/gate
resolution): required and must reference a declared node when
`kind == NodeKind.PREDICTOR`, forbidden (must be `None`) for every other
kind. Validated at `CognitiveGraph` construction.

## 4. Design

### 4.1 `cognition/learning.py`

```python
def huber_loss(error: float, delta: float = 1.0) -> float:
    """0.5*e^2 for |e|<=delta, delta*(|e|-0.5*delta) beyond -- quadratic
    near zero, linear (robust to outliers) further out."""

@dataclass(slots=True, frozen=True)
class PredictionError:
    predictor_id: str
    target_id: str
    error: float   # target's current activation minus the predictor's previous activation
    loss: float    # huber_loss(error)

def compute_prediction_errors(
    graph: CognitiveGraph, *, current: Mapping[str, float], previous: Mapping[str, float]
) -> tuple[PredictionError, ...]:
    """One PredictionError per PREDICTOR node, in a stable (sorted by
    predictor_id) order. A predictor with no previous-tick activation
    (cold start) is skipped, not reported as a spurious large error."""
```

### 4.2 Eligibility trace update

$$q_{ij}(t)=\lambda q_{ij}(t-1)+a_i(t-1)a_j(t)$$

```python
def update_eligibility(edge: PlasticEdge, *, source_previous: float, target_current: float, decay: float) -> None:
    """Mutates edge.eligibility in place. decay (lambda) is genome.plasticity.eligibility_decay, caller-supplied."""
```

No clipping range is specified for eligibility in the master doc (§5.2
calls it "estado efímero o cuantizado," no bound given); it is bounded in
practice by the boundedness of $a_i, a_j \in (-1, 1)$ and $\lambda \in
[0,1]$ maintaining a convergent series — tested as a property, not
enforced by a hard clip.

### 4.3 Bounded Oja weight update

$$\Delta w_{ij}=\eta_{ij}\,m(t)\,[a_i a_j-a_j^2 w_{ij}]$$

```python
def apply_oja_update(
    edge: PlasticEdge, *, source_activation: float, target_activation: float,
    learning_rate: float, modulation: float, eligible: bool,
) -> None:
    """Mutates edge.weight in place, clipped to WEIGHT_RANGE. A no-op
    when eligible is False -- master doc §6.3: only edges within the
    causal window and selected by attention receive a full update.
    learning_rate and modulation are plain floats this slice (see §2 --
    no metaplasticity, no SelfModel wiring yet)."""
```

`modulation` stands in for master doc §6.2's $m(t)$ ("combina
disponibilidad, calidad, atención y salud perceptual") — a plain
caller-supplied float `[0.0, 1.0]` this slice, not yet computed from
`SelfModel`/attention (§2 non-goals).

### 4.4 `PlasticNode.predicts_node_id` and graph validation

`cognition/graph.py`: add the field; `CognitiveGraph.__init__` validates:
- `predicts_node_id is not None` iff `kind is NodeKind.PREDICTOR`.
- When set, it must reference a declared node id (dangling-reference
  check, same family as edge endpoint validation).

## 5. Testing

- **Huber loss**: quadratic region matches `0.5*e^2` for small `error`;
  linear region matches `delta*(|e|-0.5*delta)` beyond `delta`; symmetric
  in sign; zero at `error=0`.
- **Prediction error**: a predictor whose previous activation exactly
  matches the target's current activation yields `error=0.0`; cold start
  (predictor id absent from `previous`) is skipped, not reported.
- **Eligibility**: decays toward zero when co-activation stops; grows
  when source/target are both persistently active; a property test over
  many random `(a_i, a_j, decay)` triples in valid ranges confirms the
  trace stays finite and bounded within a derivable envelope
  ($|q| \le 1/(1-\lambda)$ for $\lambda < 1$).
- **Oja update**: `eligible=False` never changes `edge.weight`; repeated
  correlated `(source_activation, target_activation)` pairs move `weight`
  toward the Oja fixed point ($w \to a_i/a_j$ direction, bounded); weight
  never leaves `WEIGHT_RANGE` even under adversarial repeated updates;
  `modulation=0.0` never changes weight (a fully-suppressed tick).
- **`predicts_node_id` validation**: a `PREDICTOR` node without it is
  rejected; a non-`PREDICTOR` node with it set is rejected; a
  `predicts_node_id` referencing an undeclared node is rejected.
- **End-to-end demonstration** (roadmap's own bar: "v0.57 demostrará
  aprendizaje de pesos"): a small hand-built graph where a `PREDICTOR`
  tracks a periodic `SENSE` input over many `activate()` + eligibility +
  Oja update cycles shows `PredictionError.loss` trending down compared
  to its value in the first few ticks — the graph is measurably learning,
  not just mechanically updating numbers.

## 6. Decisions

| Question | Decision |
| --- | --- |
| Which node a `PREDICTOR` predicts | New `predicts_node_id` field, validated at construction (disclosed doc gap, same pattern as v0.56's delay/gate resolutions) |
| `learning_rate` source this slice | Plain caller-supplied float — no metaplasticity yet (v0.58) |
| `m(t)` modulation source this slice | Plain caller-supplied float — no `SelfModel`/attention wiring yet (that tick-loop integration lands once v0.58 exists too) |
| Eligibility bound | No hard clip (none specified); verified as a bounded property instead |
| Runtime wiring | None yet, matching v0.56's precedent |
