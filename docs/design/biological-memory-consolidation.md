# Biological memory consolidation — v0.59.5 design

Status: **approved design, not yet implemented**

Scope: resident individual only. No network, peer exchange, new permissions, identifying data, user content, autonomous actions or executable self-modification.

## 1. Purpose

Symbiont currently persists much of its learned state as a durable checkpoint. v0.59.4 hardened that checkpoint — bounded size, stricter validation, quantized cognitive weights, restart continuity — but the persistence model is still fundamentally a serialization model: several subsystems write precise aggregate state whenever `OrganismRuntime.checkpoint()` is called.

That leaves two problems.

1. **Checkpoint differencing.** Two precise aggregate checkpoints taken close together can reveal information about the observations between them. For a cumulative `(count, mean)` pair, a one-observation difference can algebraically recover that observation. The current host checkpoint documents this limitation explicitly.
2. **Wrong memory abstraction.** `eligibility`, `previous_frame`, precise recent statistics and other short-lived state are operational working state. Treating all of them as durable identity makes restart closer to restoring a process image than restoring an organism's long-term memory.

v0.59.5 changes the persistence model from **serialize learned state** to **persist consolidated memory**.

The biological analogy is architectural rather than literal: recent experience first changes a labile working state; only selected, sufficiently supported or sufficiently salient changes become durable. A single exceptionally strong event may create a durable trace, while statistical generalization still requires repeated independent evidence. Saving or shutting down never forces immature memory to consolidate.

## 2. Core invariant

> **A durable checkpoint must contain only bounded consolidated abstractions. No durable field may change in a form that attributes the change to one ordinary raw observation.**

The invariant has one deliberate exception in semantics, not in raw data: a single highly salient event may create a durable **abstract event trace**. That trace records that an exceptional transition occurred, never the exact source reading that caused it.

This design does **not** use differential-privacy noise. Privacy comes from state separation, aggregation, coarse classes, support gating and the fact that checkpoint timing is decoupled from consolidation timing.

## 3. Current implementation boundary

The change is deliberately built around existing classes rather than introducing a parallel runtime.

### 3.1 `OrganismRuntime`

Current behavior:

- samples/discovers senses;
- updates `AdaptiveSenseModel`, acclimation, rhythm, drift and `SelfModel` every tick;
- allocates attention;
- invokes `CognitiveBridge.tick()`;
- writes all exportable subsystem state from `checkpoint()`;
- writes that checkpoint atomically from `save()`.

v0.59.5 keeps the tick lifecycle, but inserts an explicit consolidation boundary before persistence.

### 3.2 `CognitiveBridge`

Current volatile state includes:

- live graph weights;
- edge eligibility traces;
- sensory normalizers;
- previous activation frame;
- structural-plasticity candidate state;
- safety state;
- topology revision.

Today `export_checkpoint()` includes both `eligibility` and `previous_frame`. v0.59.5 reclassifies both as labile.

### 3.3 Host models

Current durable host state includes exact aggregate statistics in multiple places:

- `HostAcclimation`: count/mean/variance;
- `RhythmModel`: count/mean/variance;
- `DriftAwareBaseline`: count/mean/variance;
- `AdaptiveSenseModel`: exact sample counts, means, second moments and relation accumulators;
- `SelfModel`: already mostly quantized classes, but still contains exact relative tick metadata.

These models remain precise in RAM. Their durable representation becomes a separate consolidated projection.

## 4. Three memory layers

```text
real observation
      |
      v
+-----------------------------+
| LABILE / WORKING MEMORY     |
| exact bounded runtime state |
| RAM only                    |
+-------------+---------------+
              |
        consolidation
              |
              v
+-----------------------------+
| CONSOLIDATION BUFFER        |
| evidence + salience         |
| bounded, RAM only           |
+-------------+---------------+
              |
    commit when eligible
              |
              v
+-----------------------------+
| CONSOLIDATED MEMORY         |
| coarse, stable abstractions |
| checkpointable              |
+-----------------------------+
```

A checkpoint request serializes **only consolidated memory plus durable immutable/configuration state**. It does not itself run consolidation.

## 5. Memory kinds

Different kinds of learning must not share one universal repetition threshold.

### 5.1 Statistical memory

Examples:

- sensory center/spread;
- rhythm;
- availability;
- correlations;
- learned edge strength;
- long-run self-model characteristics.

Rule: **slow consolidation**. It requires enough independent support and/or a stable accumulated consolidation score. One ordinary observation cannot update the durable statistical representation.

### 5.2 Salient event memory

Examples in Symbiont terms:

- an unusually large, reliable prediction error;
- an abrupt regime transition;
- a strong contradiction between an established belief and newly gathered evidence;
- a rare transition strongly selected by attention and observed through a healthy sense.

Rule: **one-shot consolidation is allowed**, but the durable form is categorical and abstract.

A one-shot event may establish:

```text
"an exceptional transition of this abstract pattern occurred"
```

It may not establish:

```text
"the raw sensor value was 97.3812"
```

### 5.3 Structural memory

Examples:

- new cognitive edge;
- new concept node;
- pruning/removal;
- durable topology revision.

Rule: structural change remains the most conservative class. Existing structural support/cooldown/lifecycle rules continue to apply; salience alone must **not** create or prune structure from one event.

### 5.4 Safety state

`SafetyState` is not biological memory. It is kernel/runtime protection. Its durable semantics remain explicit and may persist immediately because it does not encode host telemetry.

## 6. Consolidation signal

There is no external label such as `important=True`. Consolidation strength is derived only from signals the organism already produces.

Introduce:

```python
@dataclass(slots=True, frozen=True)
class ConsolidationSignal:
    novelty: float       # [0, 1]
    surprise: float      # [0, 1]
    attention: float     # [0, 1]
    reliability: float   # [0, 1]
    coherence: float     # [0, 1]
```

All fields are bounded and finite.

### 6.1 Novelty

Derived from already-existing descriptive state, never a threat label.

Candidate inputs:

- `DriftObservation.kind`;
- bounded absolute z-score class when available;
- first appearance / rediscovery of a developed sense;
- distance from the current consolidated class, not exact durable mean.

Suggested initial mapping:

```text
NONE          -> 0.00
GRADUAL       -> 0.35
CREEP         -> 0.50
ISOLATED      -> 0.70
REGIME_SHIFT  -> 0.90
```

This is a kernel mapping, not learned from host labels.

### 6.2 Surprise

Derived from cognition's own prediction error.

For each `PredictionError.loss`, transform into a bounded class using the same principle as Observatory's loss classes. A loss above the top threshold saturates at `1.0`; exact loss is never persisted as part of event memory.

No predictor means surprise contributes zero rather than being fabricated.

### 6.3 Attention

A sense selected by the bounded `AttentionBudget` contributes `1.0`; an unselected sense contributes `0.0` for fast consolidation. Statistical slow consolidation may still accumulate weak support from ordinary observations so attention does not permanently blind long-term learning.

Future implementations may use a graduated fraction of budget, but v0.59.5 should start binary because current allocation already exposes selected/not-selected semantics cleanly.

### 6.4 Reliability

Use the existing self-model and adaptive sense state:

```text
reliability = clamp(health * availability, 0, 1)
```

This mirrors the modulation already passed from `OrganismRuntime` into `CognitiveBridge` after v0.59.4. A broken or unavailable sense cannot manufacture a one-shot durable memory merely by producing a huge numerical deviation.

### 6.5 Coherence

Coherence means support from prior independent experience, not repetition count alone.

Initial implementation:

- `0.0` for a first unsupported pattern;
- rises by support **epochs**, not raw samples;
- repeated samples inside the same epoch contribute diminishing/no new independent support;
- reappearance after an epoch boundary contributes again;
- relation support from a distinct established sense may add one bounded corroboration increment.

The exact independence model is intentionally simple in v0.59.5: tick spacing + distinct supporting senses. It must not attempt semantic causal reasoning.

## 7. Consolidation score and two-speed path

Use a bounded weighted sum, with kernel-owned weights:

```text
score =
    0.20 * novelty
  + 0.30 * surprise
  + 0.20 * attention
  + 0.20 * reliability
  + 0.10 * coherence
```

The weights are **not organism-learnable in v0.59.5**. They define persistence/privacy behavior and therefore belong to the immutable kernel side of the boundary.

Two paths:

```text
if score >= FAST_CONSOLIDATION_THRESHOLD
and reliability >= FAST_MIN_RELIABILITY:
    create/update abstract salient event trace
else:
    accumulate slow consolidation evidence
```

Initial constants:

```text
FAST_CONSOLIDATION_THRESHOLD = 0.80
FAST_MIN_RELIABILITY         = 0.60
SLOW_SUPPORT_EPOCHS          = 4
CONSOLIDATION_EPOCH_TICKS    = 8
```

These are deliberately **not** equivalent to "observe eight times".

An ordinary pattern generally needs support spread across at least four consolidation epochs. A sufficiently novel/surprising/reliable attended event can pass the fast threshold on its first occurrence.

The constants are implementation defaults to be preregistered and tested, not claims about human memory.

## 8. Independence and spacing

A single noisy burst must not masquerade as repeated independent evidence.

Introduce a per-memory-key epoch id:

```python
epoch_id = tick // CONSOLIDATION_EPOCH_TICKS
```

For slow statistical consolidation, at most one support increment per `(memory_key, epoch_id)` is counted.

Corroboration from another established sense may contribute separately but remains capped. This provides a minimal spacing effect without storing a history of observations.

Persisted memory never stores the list of epochs. Only the resulting maturity class is durable.

## 9. New runtime components

Add `src/symbiont/core/memory.py`.

### 9.1 `MemoryKind`

```python
class MemoryKind(StrEnum):
    STATISTICAL = "statistical"
    SALIENT_EVENT = "salient_event"
    STRUCTURAL = "structural"
```

### 9.2 `MemoryKey`

A closed internal key identifying the abstract thing being consolidated. It must use already-safe organism identifiers (`sense_*`, node ids, relation ids), never filesystem paths, provider names or host identity.

### 9.3 `ConsolidationCandidate`

```python
@dataclass(slots=True)
class ConsolidationCandidate:
    key: str
    kind: MemoryKind
    support_epochs: int
    last_support_epoch: int
    strength: float
    latest_signal: ConsolidationSignal
```

Bounded by `KernelLimits.max_consolidation_candidates`.

No raw observations are stored here.

### 9.4 `ConsolidatedMemory`

Owns the durable projection. It does not own live learning objects.

Conceptually:

```python
@dataclass(slots=True)
class ConsolidatedMemory:
    sensory: dict[str, ConsolidatedSensoryState]
    rhythms: dict[str, ConsolidatedRhythmState]
    drift: dict[str, ConsolidatedDriftState]
    cognition: ConsolidatedCognitionState
    salient_events: deque[SalientEventTrace]
```

Everything is bounded by kernel limits.

### 9.5 `MemoryConsolidator`

Responsibilities:

1. receive already-derived runtime/cognition signals;
2. update bounded candidates;
3. decide fast vs slow eligibility;
4. project live state into coarse durable classes only when eligible;
5. perform homeostatic projection for cognitive weights before durable quantization;
6. expose `export_checkpoint()` / `restore_checkpoint()`;
7. never sample the host itself;
8. never receive raw file paths, provider identity or external labels.

## 10. Durable representation

### 10.1 Maturity classes

Exact counts are not durable.

Use eight classes:

```text
0  trace
1  emerging
2  young
3  established
4  mature
5  stable
6  entrenched
7  saturated
```

The mapping from internal support to class is monotone and coarse. No exact sample count can be reconstructed from it.

### 10.2 Sensory statistics

Live RAM keeps exact statistics.

Durable state uses bounded classes relative to the sense's own learned scale. v0.59.5 must not persist an exact dequantized raw-unit center merely under a different field name.

Persist, for example:

```json
{
  "center_class": 17,
  "spread_class": 6,
  "motion_class": 4,
  "availability_class": 13,
  "maturity_class": 5
}
```

Recommended classes:

```text
center          32
spread          16
motion          16
availability    16
maturity         8
```

The center class is defined against a durable scale/anchor class, not an exact raw host value. Implementation must test that two checkpoints cannot be used as a one-equation recovery of a single new observation.

### 10.3 Cognitive graph

Durable:

- node identity/kind/bounded declarative parameters;
- topology;
- **consolidated** edge weight class;
- edge plasticity class or current bounded declarative value if it is not derived from a raw observation;
- coarse lifecycle/maturity metadata required for structural continuity;
- topology revision;
- safety state.

Labile only:

- `edge.eligibility`;
- current activation;
- `previous_frame`;
- pending prediction errors;
- per-tick Oja delta.

On restore:

```text
eligibility = 0
previous_frame = {}
activations = resting/cold state
```

This means a restart intentionally loses immediate temporal context while retaining learned structure and consolidated weights.

### 10.4 Structural-plasticity state

Do not persist raw recent coactivation detail merely to preserve an in-progress structural candidate.

Persist only candidates that have themselves crossed the slow structural consolidation threshold, using coarse support/maturity classes. Immature candidates disappear on restart.

### 10.5 Salient event trace

Bounded record:

```python
@dataclass(slots=True, frozen=True)
class SalientEventTrace:
    pattern_id: str
    novelty_class: int       # 0..15
    surprise_class: int      # 0..15
    reliability_class: int   # 0..15
    context_class: int       # coarse organism-relative context, no wall clock
    recurrence_class: int    # coarse re-encounter count/maturity
```

No raw reading, exact z-score, exact prediction error, timestamp or provider identity.

Cap with a small kernel limit, initially 64 traces. Eviction is deterministic: least-recently-reinforced durable trace, with ties by `pattern_id`. "Recent" uses coarse organism-relative consolidation epoch, not wall-clock time.

A fast one-shot trace is therefore possible without making one raw observation reconstructible.

## 11. Homeostatic weight consolidation

The live graph may adapt continuously; durable weights should represent a stable phenotype, not every latest Oja micro-update.

Maintain a separate consolidated weight class per durable edge. At consolidation time:

1. collect the current live candidate weight;
2. require slow support unless the edge already exists structurally and the update is only strengthening/weakening an established relation;
3. apply bounded homeostatic normalization over incoming plastic edges of each target;
4. quantize to the durable weight class;
5. change the stored class only if the projected class differs.

Initial homeostasis should be simple and deterministic. Recommended rule:

```text
if L1 norm of incoming plastic weights > target budget:
    scale all plastic incoming weights proportionally to the budget
```

The target budget is kernel-owned and bounded. Gating/non-plastic semantics must not be silently reinterpreted.

This projection affects the **durable representation**, not necessarily the live graph in the same tick. The organism may continue to explore labile weight changes between consolidations.

## 12. Checkpoint semantics

### 12.1 Saving is not consolidation

`OrganismRuntime.checkpoint()` becomes a pure export of the latest consolidated state.

It must **not** call `consolidate()`.

Therefore:

```text
observe -> checkpoint -> checkpoint -> checkpoint
```

without a consolidation transition produces no progressively more precise durable view of that observation.

### 12.2 Shutdown is not a bypass

A clean `SIGTERM`/resident shutdown persists only what had already consolidated. It does not lower thresholds or force pending candidates through.

Labile experience may be lost on restart. That is intentional.

### 12.3 Consolidation occurs in the tick lifecycle

At the end of a successful cognitive tick, after attention/evidence/cognition outputs are known:

```text
sample
  -> perceive
  -> drift
  -> attend
  -> cognition
  -> second look / evidence revision
  -> derive consolidation signals
  -> MemoryConsolidator.observe_tick(...)
  -> possibly commit eligible memory
  -> return RuntimeTickResult
```

Checkpoint timing is orthogonal.

## 13. Runtime API changes

### 13.1 `OrganismRuntime.__init__`

Add:

```python
memory_consolidator: MemoryConsolidator | None = None
```

If absent, create one from kernel defaults.

### 13.2 `RuntimeTickResult`

Optionally expose bounded introspection:

```python
memory: MemoryConsolidationResult | None
```

with only:

- candidates_considered;
- statistical_commits;
- salient_commits;
- structural_commits;
- durable_revision.

No raw values.

This can later feed Observatory without exposing labile memory.

### 13.3 `checkpoint()`

New top-level durable shape:

```json
{
  "schema_version": 6,
  "saved_at_tick": 12345,
  "genome": {...},
  "memory": {
    "schema_version": 1,
    "revision": 42,
    "sensory": {...},
    "rhythms": [...],
    "drift": {...},
    "self_model": {...},
    "dissent": {...},
    "cognition": {...},
    "salient_events": [...]
  }
}
```

Legacy top-level exact aggregate namespaces are no longer emitted by v6.

`saved_at_tick` may remain exact because it is organism-relative process age, not a host reading; however it must not be used as the consolidation support counter.

## 14. Migration from checkpoint schema v5 to v6

Migration is the hardest compatibility point because old v5 contains information that v6 deliberately refuses to continue persisting exactly.

The v5->v6 migration therefore performs a **privacy-reducing projection**, not a lossless migration.

Rules:

1. load and validate v5 exactly as today;
2. convert mature exact aggregates into coarse consolidated classes;
3. discard `previous_frame`;
4. restore all edge eligibility as zero;
5. quantize/normalize durable edge weights into the new consolidated representation;
6. convert exact counts into maturity classes;
7. drop immature structural candidates;
8. preserve topology, genome identity, safety state and abstract dissent continuity;
9. write future saves only as v6.

The migration must never re-export the exact v5 aggregate after it has crossed into v6.

A v5 checkpoint can therefore start a v0.59.5 organism with slightly less precise internal state than before. This is intentional and should be documented as **memory consolidation on upgrade**, not corruption.

## 15. Adaptive sensory model changes

`AdaptiveSenseModel` may continue using exact Welford accumulators in RAM.

Its existing `export()` should stop being the durable checkpoint format. Split the responsibilities:

```text
AdaptiveSenseModel.export_runtime_state()       # if ever needed for tests only; not durable
MemoryConsolidator.project_sensory_memory(...)  # durable path
```

Production checkpoint code must have no route to persist `SenseState.mean`, `m2`, exact `samples`, exact `available_samples` or exact `PairAccumulator` moments.

Durable sensory relations contain:

- correlation sign/strength class;
- lag-direction class;
- maturity class;
- stable/dormant relation class if needed.

No exact accumulator state.

## 16. Acclimation, rhythm and drift after restart

A durable coarse memory cannot simply be stuffed back into `CapabilityBaseline(count, mean, variance)` and pretended to be exact history.

Introduce explicit seeded restore semantics:

```python
HostAcclimation.seed_from_consolidated(...)
RhythmModel.seed_from_consolidated(...)
DriftAwareBaseline.seed_from_consolidated(...)
```

A seed creates a prior/anchor, not fabricated samples.

After restart:

- models know the broad learned regime;
- confidence/maturity starts from the durable maturity class;
- new exact runtime statistics accumulate afresh around that prior;
- no fake exact count is invented;
- early post-restart observations can adjust the live model without retroactively revealing the old aggregate.

This distinction is mandatory. Do not encode `maturity_class=5` as an arbitrary fake `count=128` and feed it into existing exact formulas.

## 17. Self-model

`SelfModel` is already closer to the target design because cost/health/confidence/maturity are quantized before persistence.

v0.59.5 changes:

- replace exact `last_observed_tick` with a coarse recency/idle class, or derive a fresh restart age policy;
- preserve established cost/health/confidence classes;
- do not reconstruct exact attempt/success counts;
- restore as a seeded mature state with an explicit `restored_from_memory` path rather than inventing counts that happen to satisfy `established`.

This removes another place where durable class state currently expands back into fabricated exact history.

## 18. Dissent memory

v0.59.4 already moved dissent toward bounded abstract persistence. Keep it abstract.

A contradiction itself is naturally salient and may use the fast path when:

- the prior belief was established;
- new evidence is reliable;
- disagreement exceeds the existing conflict rule.

Persist that a contradiction occurred and its coarse strength/maturity, not the exact evidence mean or exact z-score.

## 19. Kernel limits

Add immutable limits to `KernelLimits`:

```python
max_consolidation_candidates: int = 256
max_salient_event_traces: int = 64
consolidation_epoch_ticks: int = 8
slow_support_epochs: int = 4
fast_consolidation_threshold: float = 0.80
fast_min_reliability: float = 0.60
max_incoming_consolidated_weight_norm: float = 8.0
```

All must be validated finite/positive/in-range as appropriate and must not be learnable or genome-mutable in v0.59.5.

The genome may later evolve bounded consolidation tendencies only after a separate design proves that this cannot learn around the privacy boundary. That is explicitly out of scope now.

## 20. Failure semantics

Consolidation must be transactional.

If projection/validation fails:

- live labile learning for the tick is not destroyed;
- durable memory remains at the previous revision;
- `MemoryConsolidator` records one bounded failure counter;
- checkpoint still exports the last valid consolidated memory;
- repeated consolidation failures may freeze **consolidation** without freezing perception/cognition.

Do not reuse `SafetyState.frozen` blindly: cognition plasticity failure and persistence-projection failure are different failure domains. Introduce a small `ConsolidationSafetyState` if needed.

## 21. Privacy properties to test

The implementation is accepted only if these adversarial properties hold.

### P1 — checkpoint spam does not increase temporal resolution

One ordinary observation followed by 100 checkpoint calls produces the same durable statistical memory until a genuine consolidation event occurs.

### P2 — one ordinary observation is not algebraically recoverable

Given checkpoint A, one ordinary new observation, and checkpoint B, there is no exact count/mean/variance update pair from which the observation can be solved.

### P3 — one-shot memory does not contain the raw event

A fast salient event may change durable memory after one tick, but persisted fields are only bounded categorical classes and safe ids.

### P4 — shutdown cannot force consolidation

A pending weak candidate remains absent after `save()` or clean resident shutdown.

### P5 — labile cognition resets

After restart:

```text
eligibility == 0
previous_frame == {}
```

while topology and consolidated weight classes survive.

### P6 — burst repetition is not independent support

Many identical observations in one consolidation epoch produce at most one slow-support increment.

### P7 — spaced recurrence can consolidate

The same coherent pattern across enough distinct epochs eventually becomes durable even if no single event crosses the fast threshold.

### P8 — unreliable surprise cannot create one-shot memory

Huge prediction error from a low-health/unavailable sense fails the fast reliability gate.

### P9 — structural one-shot mutation is impossible

One salient event may create a salient trace but cannot by itself add/remove a graph edge or node.

### P10 — memory remains bounded forever

Candidates, salient traces and all durable projections respect kernel limits under arbitrarily long synthetic runs.

## 22. Functional tests

Add deterministic tests around three canonical scenarios.

### Scenario A — "flame"

Synthetic sense is stable, then produces one reliable attended transition with top-class novelty and surprise.

Expected:

- one `SalientEventTrace` is committed immediately;
- no raw value appears anywhere in checkpoint JSON;
- statistical center/spread memory does not jump to encode that single sample;
- no structural mutation occurs solely because of this event.

### Scenario B — "street name"

Moderate coherent pattern reappears once per consolidation epoch, with ordinary surprise.

Expected:

- no fast trace on first observation;
- slow support grows once per epoch;
- durable statistical memory commits only after `SLOW_SUPPORT_EPOCHS`;
- repeated observations inside one epoch do not accelerate it.

### Scenario C — "noisy sensor"

Large deviations come from a sense whose self-model health/availability is below the reliability threshold.

Expected:

- no one-shot trace;
- weak/failed support does not poison durable memory;
- normal runtime learning can continue according to existing attention/plasticity rules.

## 23. Integration sequence

Implement as small reviewable steps.

### PR 1 — memory kernel and types

- `core/memory.py` types and bounded candidate store;
- kernel limits;
- salience calculation;
- deterministic fast/slow decision tests;
- no checkpoint changes yet.

### PR 2 — cognitive labile/durable split

- remove eligibility and previous frame from the new durable projection;
- consolidated weight classes;
- homeostatic projection;
- cold temporal state on restore;
- topology continuity.

### PR 3 — host consolidated projection

- sensory/acclimation/rhythm/drift coarse memory;
- seeded restore APIs;
- self-model recency-class restore;
- no exact aggregate statistics in production checkpoint path.

### PR 4 — schema v6 and migration

- v5->v6 privacy-reducing migration;
- `OrganismRuntime.checkpoint()` exports consolidated memory only;
- shutdown/save cannot force consolidation;
- checkpoint byte bound retained.

### PR 5 — adversarial integration and Observatory

- P1-P10 regression suite;
- long-run boundedness test;
- optional Observatory projection of memory commit counts/classes only;
- docs/roadmap/status update.

GitHub Actions are not a merge gate while private-repository minutes are exhausted; use deterministic local/structural review under the repository's existing merge policy.

## 24. Explicit non-goals

v0.59.5 does not add:

- human-like episodic narrative memory;
- semantic labels for host signals;
- fear/reward/pain concepts;
- external importance labels;
- reinforcement learning from operator approval;
- wall-clock autobiographical history;
- raw-event persistence;
- generated code;
- network sharing;
- autonomous action;
- learned privacy thresholds.

"Flame" and "street name" are test metaphors only. Symbiont's actual salience remains label-free and derived from its own novelty, prediction, attention, reliability and coherence signals.

## 25. Exit conditions for v0.59.5

The release is complete when all are true:

1. checkpoint v6 persists consolidated memory rather than precise runtime aggregates;
2. ordinary single-observation checkpoint differencing is no longer algebraically reversible;
3. a single reliable, highly salient event can produce an abstract durable trace;
4. ordinary statistical memory requires spaced/coherent support rather than a universal raw repetition count;
5. eligibility, previous activation and pending prediction state are RAM-only;
6. restart retains topology and consolidated phenotype but begins with cold temporal dynamics;
7. structural learning still requires repeated support and cannot one-shot mutate topology;
8. checkpoint/save/shutdown never forces immature memory to consolidate;
9. memory use remains kernel-bounded over indefinite residence;
10. no new permission, network, identity, user-content or action boundary is introduced.

## 26. Resulting organism model

After v0.59.5, Symbiont's durable identity is no longer "whatever happened to be in RAM at save time".

It becomes:

```text
perception
  -> working state
  -> attention + prediction + evidence
  -> labile plasticity
  -> salience/support evaluation
  -> selective consolidation
  -> bounded long-term memory
  -> checkpoint
```

A restart therefore behaves like interruption of short-term activity, not resurrection of the exact previous microstate: immediate context is lost, while sufficiently consolidated structure, tendencies and exceptional abstract memories survive.
