# v0.53 — Organism self-model (cost, health, confidence)

**Status:** approved for implementation planning (rev. 2, post-technical-review)
**Base:** `main` at `9a544a0` (v0.52.0)
**Roadmap entry:** "Learn resource cost, sensory health and confidence in its own
perceptual apparatus" (`docs/roadmap.md:60`, Milestone E)

Rev. 2 supersedes rev. 1 after a technical review found the original cost/health/
confidence/second-look/checkpoint design would corrupt the attention budget's
semantics and leak per-tick outcomes through the checkpoint. All eight findings
were verified against `main@9a544a0` before being folded in here.

## 1. Problem

The organism has no self-model. Three gaps, confirmed by reading the current
code (`core/attention.py`, `core/governor.py`, `host/adaptive.py`,
`core/metacognition.py`):

- **Cost**: `attention.attend_to_host()` uses a static `cost=1.0` default per
  capability. `GovernedOrganism` only tracks tick count/interval, never
  resource expense. No component measures what a sense actually costs to
  sample.
- **Health**: only implicit in `AdaptiveSenseModel.SenseState.availability`
  (ratio of successful to attempted samples). No explicit score that decays on
  provider failure and recovers on success.
- **Confidence**: `MetacognitionEngine` already computes a collective,
  population-level epistemic confidence from `Assessment`/`CollectiveMemory`.
  This is not a per-sense perceptual confidence and must not be duplicated.

## 2. Goal

Add a bounded, local, per-sense self-model (`cost`, `health`, `confidence`)
that composes existing signals, persists through checkpoints, and actively
feeds `attention` and `SecondLookSession` this milestone.

## 3. Non-goals

- No new host permission class, provider, or telemetry surface.
- No raw per-tick timing/outcome history persisted — checkpoint state is
  quantized into bins, not exact floats (§4.6).
- No change to `GovernedOrganism` hard limits.
- No genome/learned-parameter system — thresholds are fixed constants.
- No coupling to `MetacognitionEngine`: it works over synthetic pattern
  families with no established mapping to opaque resident `sense_id`s; adding
  one is out of scope for this milestone (dropped from rev. 1).

## 4. Design

### 4.1 Sampling outcome contract (new, load-bearing)

Confirmed gaps in `host/readings.py`: `ReadingFailure` carries only
`provider_id`/`reason` (no `capability_id`), and a provider silently returning
a partial batch produces no failure record at all for the missing
capabilities. Cost/health cannot be attributed correctly without knowing what
a provider *attempted*, not just what it returned.

```python
class SamplingOutcomeKind(StrEnum):
    SUCCEEDED = "succeeded"       # reading returned, quality NOMINAL/DEGRADED/STALE
    UNAVAILABLE = "unavailable"   # reading returned with quality UNAVAILABLE
    MISSING = "missing"           # capability requested, provider returned nothing for it
    PROVIDER_FAILED = "provider_failed"  # provider raised; every attempted capability gets this

@dataclass(slots=True, frozen=True)
class CapabilitySamplingOutcome:
    capability_id: str
    provider_id: str
    kind: SamplingOutcomeKind
    attributed_elapsed_s: float
    quality: ReadingQuality | None  # NOMINAL/DEGRADED/STALE/UNAVAILABLE from readings.py, None for MISSING/PROVIDER_FAILED
```

`HostSampler.sample()` (`host/readings.py`) wraps each
`provider.sample(available)` call with `time.perf_counter()`. The elapsed
time is divided evenly across every capability_id **attempted** in that call
(i.e. every id in `available` routed to that provider), not just the ones
that came back — an omitted or failed capability must not appear free. On a
provider exception, every attempted capability_id for that provider gets
`PROVIDER_FAILED` with the elapsed time up to the exception.

`HostSampler.sample()` return type gains a third element:

```python
@dataclass(slots=True, frozen=True)
class SamplingResult:
    readings: tuple[SensorReading, ...]
    failures: tuple[ReadingFailure, ...]
    outcomes: tuple[CapabilitySamplingOutcome, ...]
```

(Existing two-tuple callers are updated in the same change; this is an
internal framework type, not a public contract requiring a compat shim.)

### 4.2 Health — graduated, not binary

"Produced a reading" is not success/fail — `SensorReading` already carries
`ReadingQuality` with four levels. Health must not decay on omissions the
organism itself chose (dormant tier, backoff), only on genuine failure to
observe.

| Outcome                                  | Health observation |
| ----------------------------------------- | ------------------: |
| `SUCCEEDED` + `NOMINAL`                   |                 1.00 |
| `SUCCEEDED` + `DEGRADED`                  |                 0.60 |
| `SUCCEEDED` + `STALE`                     |                 0.25 |
| `UNAVAILABLE`                             |                 0.00 |
| `MISSING`                                 |                 0.00 |
| `PROVIDER_FAILED`                         |                 0.00 |
| Not sampled this tick (dormant/backoff)   |         no update    |

EWMA (α≈0.06, matching `RunningStat`) over these observations, seeded to 0.5
(neutral — neither trusted nor distrusted) on first contact.

### 4.3 Confidence — maturity × health × quality, no metacognition coupling

```python
maturity = min(1.0, log1p(successes) / log1p(MIN_MATURE_SUCCESSES))
confidence_target = clip(0.70 * health + 0.30 * quality_ewma, 0.0, 1.0) * maturity
```

`quality_ewma` is the same graduated signal as health but tracks reading
quality specifically (so a sense that's *available* but chronically
`DEGRADED`/`STALE` doesn't read as fully confident even with perfect health).
EWMA-smoothed into `confidence_ewma` at the same α as health.

`SenseState.utility` (availability × variability/motion) remains a separate,
independent dimension — it answers "is this worth observing", not "do I
trust it". The four self-model dimensions stay conceptually distinct:
utility (worth watching), health (is it working), confidence (how much
trustworthy evidence exists), cost (what does it take).

### 4.4 Cost — split allocation cost from ranking cost

Verified in `core/attention.py`: `AttentionCandidate.cost` is used for both
`uncertainty / cost` ranking *and* consumed against the hard `budget` in
`AttentionBudget.allocate()`. Replacing that single field with a raw
wall-clock second value breaks the budget's semantics — a candidate costing
`0.003s` against a `budget=1.0` could pass ~333 candidates instead of ~1,
silently defeating the attention limit.

Fix: keep `AttentionCandidate.cost` as the existing, semantically-unchanged
allocation cost (default `1.0`, budget-consuming). Add a separate relative
cost factor used only to bias ranking, derived from the self-model:

```python
def relative_cost(self, sense_id: str, *, reference_ids: Iterable[str]) -> float:
    # median cost_ewma_s over reference_ids (established senses only); 1.0 if none established
    return clip(self.cost_ewma_s(sense_id) / reference_median, 0.25, 4.0)
```

`attend_to_host()` ranks by `uncertainty / (allocation_cost * relative_cost)`
but still consumes `allocation_cost` (unchanged `1.0` default) from the
budget. This preserves the existing budget contract exactly for a fresh
organism (no self-model data yet ⇒ `relative_cost == 1.0` ⇒ identical
ranking to v0.52) while letting learned relative expense reorder ties.

### 4.5 Second-look integration — confidence gates viability, not skip-on-trust

Rev. 1's "skip second look above confidence 0.85" was inverted: a
well-understood, healthy sense with currently uncertain behavior is exactly
the best candidate for higher-resolution investigation (`core/runtime.py`'s
existing ranking is uncertainty-driven, `runtime.py:186-224`). High
confidence must not veto that.

Corrected rule: confidence/health only exclude a candidate when health is
*persistently very low* (repeatedly broken sense — investigating it further
wastes the bounded `investigate_ticks` budget), not when confidence is high:

```python
for allocation in allocations:
    candidate = allocation.name
    if candidate not in selected_ids or not snapshot.manifest.supports(candidate):
        continue
    if self_model.is_established(candidate) and self_model.health(candidate) < 0.15:
        continue  # chronically broken, don't spend investigation budget on it
    # existing SecondLookSession flow, unchanged
```

An unestablished (cold-start) sense is never excluded by this check —
`is_established()` requires a minimum attempt count first, so new senses get
a chance to be investigated before health has enough samples to judge.

`SecondLookSession` also needs to report its own attributed cost so the
self-model learns the cost of investigation itself, not only of ordinary
sampling (`host/second_look.py`'s current `SecondLookResult` has no cost/
outcome fields — verified). Extend `SecondLookResult` with an
`outcomes: tuple[CapabilitySamplingOutcome, ...]` field from its internal
`HostSampler` calls; `OrganismRuntime.tick()` feeds these into
`self_model.observe(...)` after the session completes, so cost learned from a
second look affects **only future ticks' rankings**, never the selection
already made this tick.

### 4.6 New module: `core/selfmodel.py`

```python
@dataclass(slots=True)
class SenseSelfState:
    cost_ewma_s: float = 0.0
    health_ewma: float = 0.5
    quality_ewma: float = 0.5
    confidence_ewma: float = 0.0
    attempts: int = 0
    successes: int = 0
    last_observed_tick: int = 0

    @property
    def established(self) -> bool:
        return self.attempts >= MIN_SELF_MODEL_ATTEMPTS

class SelfModel:
    MAX_SENSES = 256

    def observe(self, *, outcome: CapabilitySamplingOutcome,
                sense_state: SenseState | None, tick: int) -> None: ...
    def health(self, sense_id: str) -> float: ...
    def confidence(self, sense_id: str) -> float: ...
    def is_established(self, sense_id: str) -> bool: ...
    def relative_cost(self, sense_id: str, *, reference_ids: Iterable[str]) -> float: ...
    def reconcile(self, allowed_sense_ids: Collection[str]) -> None: ...
    def export(self) -> dict[str, Any]: ...
    @classmethod
    def restore(cls, payload: dict[str, Any] | None, *, allowed_sense_ids: Collection[str]) -> "SelfModel": ...
```

**Bound enforcement is explicit, not assumed.** Rev. 1 assumed the
`AdaptiveSenseModel`'s own cap was sufficient; verified this doesn't hold:
`drain_evicted_percept_names()` returns percept names, not necessarily
`capability_id`s, and `bootstrap_semantic_senses=True` with
`discover_senses=False` runs semantic senses entirely outside the adaptive
repertoire (`runtime.py:79-89`). `SelfModel.reconcile()` is called every tick
with the current union of adaptive + enabled bootstrap sense ids and drops
any tracked state outside that set. `restore()` takes the same
`allowed_sense_ids` and **rejects** (not silently truncates) a payload
exceeding `MAX_SENSES` or containing non-finite floats, out-of-range values,
or malformed keys — a restore failure here should be loud, not a silent
partial load that could hide corruption.

### 4.7 Checkpoint — quantized bins, not raw floats

Rev. 1 proposed persisting raw EWMA floats "at existing precision
convention" — verified there is no such convention (`host/checkpoint.py`
persists means/variances as unquantized floats today). More importantly, an
exact EWMA is invertible: comparing two consecutive checkpoints lets you
solve for the exact last observation (`x_t = (EWMA_t - (1-α)EWMA_{t-1}) / α`),
which would leak per-tick outcome data through checkpoint diffs — the kind of
raw-telemetry leak `CLAUDE.md` explicitly prohibits persisting.

`CHECKPOINT_SCHEMA_VERSION` 2 → 3. New top-level key `self_model`:

```python
{sense_id: {"cost_class": 0-15, "health_class": 0-15,
            "confidence_class": 0-15, "maturity_class": 0-7}}
```

Quantization: `class_id = round(value * (N-1))` on restore,
`value = class_id / (N-1)`; `cost_class` uses a log-scaled bucket (cost is
unbounded above) rather than linear. Senses below `MIN_SELF_MODEL_ATTEMPTS`
are not exported at all (matches `AdaptiveSenseModel`'s existing
min-support-before-export pattern). `_migrate_2_to_3` fills
`self_model: {}` for old checkpoints, same pattern as the existing `1 → 2`
migration.

## 5. Testing

- Sampling outcome attribution: a 10ms provider call over 10 capabilities
  attributes 1ms attempted-cost to each; a capability silently missing from
  the provider's return gets `MISSING`, not zero cost; an exception mid-call
  attributes elapsed time as `PROVIDER_FAILED` to every attempted capability.
- Health: dormant/backoff (not sampled) leaves health unchanged; `STALE`
  degrades health but less than `UNAVAILABLE`; a provider recovering after
  failure climbs back via EWMA, not instantly.
- Confidence: bounded [0,1] and finite under extreme/adversarial inputs;
  cold-start (`attempts < MIN_SELF_MODEL_ATTEMPTS`) always reads as low
  regardless of a lucky first sample (maturity gating).
- Attention: with no self-model data, ranking and allocation are byte-for-
  byte identical to v0.52 (regression guard — `relative_cost == 1.0`
  default); a sense with high learned relative cost is deprioritized in
  ranking but the allocation-cost/budget arithmetic is unaffected.
- Second look: a health<0.15 established sense is skipped and the next
  ranked candidate is tried, preserving the existing "unsupported by
  manifest" fallthrough (`runtime.py:202-224`, finding A05 regression
  guard); a high-confidence but currently-uncertain sense is *not* skipped;
  an unestablished (cold) sense is never skipped by this rule; a second
  look's own attributed cost affects only the next tick, never the
  already-made selection.
- Checkpoint: `_migrate_2_to_3` round-trip on a v2 payload; quantize/
  dequantize round-trip stays within one bin's tolerance; two consecutive
  checkpoints cannot be differenced to recover the exact last raw
  observation (explicit adversarial test); a payload over `MAX_SENSES` or
  with non-finite/out-of-range/malformed values is rejected, not truncated.
- `SelfModel.reconcile()`: evicting a sense from `AdaptiveSenseModel` removes
  its self-model entry; a bootstrap-only sense (adaptive discovery disabled)
  keeps its self-model entry.
- Full `OrganismRuntime` integration across several ticks with one provider
  deliberately failing: health drops only for that provider's capabilities,
  others unaffected; injected fake clock produces deterministic cost values
  across repeated runs.

## 6. Decisions from review (rev. 2)

| Aspect             | Rev. 1                              | Rev. 2                                              |
| ------------------ | ------------------------------------ | ---------------------------------------------------- |
| Attention cost      | Raw seconds replace `1.0`            | `cost` (allocation, unchanged) + separate `relative_cost` (ranking only) |
| Failure attribution | Per-provider, no capability link     | Explicit per-capability `CapabilitySamplingOutcome`  |
| Health              | Binary success/fail                  | Graduated by `ReadingQuality`; no update when not sampled |
| Confidence          | `utility + health + metacognition`   | `maturity × (health, quality)`; no metacognition coupling |
| Second look         | Skip when confidence high            | Skip only when health persistently very low (established senses only) |
| Second-look cost    | Not measured                         | Measured via extended `SecondLookResult`, feeds next tick only |
| Checkpoint          | Assumed float precision convention   | Explicit quantized bins; differencing-attack tested |
| Bound enforcement   | Assumed via `AdaptiveSenseModel` cap | Explicit `reconcile()` + strict `restore()` rejection |
