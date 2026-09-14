# v0.53 — Organism self-model (cost, health, confidence)

**Status:** approved for implementation planning
**Base:** `main` at `9a544a0` (v0.52.0)
**Roadmap entry:** "Learn resource cost, sensory health and confidence in its own
perceptual apparatus" (`docs/roadmap.md:60`, Milestone E)

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
  population-level epistemic confidence (`self_confidence`,
  `epistemic_pressure`, ...) from `Assessment`/`CollectiveMemory`. This is not
  a per-sense perceptual confidence and must not be duplicated, only composed
  with.

## 2. Goal

Add a bounded, local, per-sense self-model (`cost`, `health`, `confidence`)
that composes existing signals, persists through checkpoints, and actively
feeds `attention` and `SecondLookSession` this milestone (not deferred to a
later version).

## 3. Non-goals

- No new host permission class, provider, or telemetry surface.
- No raw per-tick timing history persisted (aggregate/EWMA only, matching the
  "raw telemetry is not persisted" invariant in `CLAUDE.md`).
- No change to `GovernedOrganism` hard limits (consent, tick budget, rate
  limit stay non-adjustable).
- No genome/learned-parameter system — thresholds here are fixed constants,
  same pattern as existing `conflict_z`, `min_samples` constructor args.

## 4. Design

### 4.1 Cost — measured at provider-call granularity

Providers batch-sample: `ReadingProvider.sample(capabilities)` returns
readings for many capabilities in one call (`host/readings.py:128`). There is
no native per-capability timing seam without touching provider internals,
which the project boundary discourages (`host/providers/` stays a thin
platform seam).

`HostSampler.sample()` (`host/readings.py`) wraps each
`provider.sample(available)` call with `time.perf_counter()`. The elapsed
time is divided evenly across the `capability_id`s the provider actually
returned readings for in that call, and reported to `SelfModel` alongside the
existing return value (new field on the return, or a companion mapping —
implementation detail for the plan). This is a per-provider-call cost
attributed to capabilities, not a true isolated per-sense cost — documented
as an approximation.

### 4.2 Health

Per sense_id, EWMA (same α family as `RunningStat`, α≈0.06) of a binary
success signal: 1.0 when the sense produced a reading this tick, 0.0 when a
`ReadingFailure` was recorded for it. Seeded from
`AdaptiveSenseModel.SenseState.availability` on first observation so cold
start isn't zero. Health isolated per sense_id — one provider's failure never
touches another sense's health (preserves "failure of one provider cannot
stop the organism").

### 4.3 Confidence

```
confidence(sense) = clip(
    0.5 * sense_state.utility
  + 0.3 * health(sense)
  + 0.2 * metacognition_bonus(sense),   # 0 if no family match found
  0.0, 1.0
)
```

`metacognition_bonus` looks up whether `MetacognitionEngine`'s last
`Assessment`-derived status for a matching pattern family is `stable`/`novel`
(bonus) vs `contested`/`uncertain` (penalty), defaulting to 0 when no mapping
exists yet — the two systems are not always aligned 1:1 today, so absence of
a match must not crash or silently zero confidence.

EWMA-smoothed across ticks (same α as health) so attention/second-look don't
thrash on single-tick noise.

### 4.4 New module: `core/selfmodel.py`

```python
@dataclass(slots=True)
class SenseSelfState:
    cost_ewma: float = 1.0       # seconds, cold-start = attention's old default
    health: float = 0.5          # cold-start = unknown, neither trusted nor distrusted
    confidence: float = 0.0
    sample_count: int = 0

class SelfModel:
    def observe(self, *, sense_id: str, elapsed_s: float, succeeded: bool,
                sense_state: SenseState | None, metacognition_bonus: float) -> None: ...
    def cost_estimate(self, sense_id: str) -> float: ...      # attention cost input
    def confidence(self, sense_id: str) -> float: ...          # second-look gating input
    def export(self) -> dict[str, Any]: ...                    # checkpoint sub-blob
    @classmethod
    def restore(cls, payload: dict[str, Any] | None) -> "SelfModel": ...
```

Bounded by construction: only sense_ids already tracked by
`AdaptiveSenseModel` (itself capacity-bounded) ever get an entry — no
independent unbounded growth path.

### 4.5 Feedback wiring

- `core/attention.py::attend_to_host()`: cost parameter for each capability
  becomes `self_model.cost_estimate(capability_id)` instead of the hardcoded
  `1.0`. Unknown/unseen senses keep the `1.0` cold-start default (no behavior
  change for a fresh organism).
- `core/runtime.py::tick()`: after `SecondLookSession` candidates are ranked
  by `attend_to_host`, skip a candidate whose `self_model.confidence(id)`
  already exceeds a fixed threshold (`0.85`) — that sense doesn't need
  higher-resolution investigation this tick. Falls through to the next
  ranked candidate, preserving existing "one candidate unsupported by
  manifest" fallthrough logic (`runtime.py:202-224`).

### 4.6 Checkpoint

`host/checkpoint.py`: `CHECKPOINT_SCHEMA_VERSION` 2 → 3. New top-level key
`self_model`: `{sense_id: {cost_ewma, health, confidence, sample_count}}`,
values quantized to existing checkpoint float precision convention. Add
`_migrate_2_to_3` filling `self_model: {}` for old checkpoints (same pattern
as the existing `1 → 2` migration). `OrganismRuntime.checkpoint()` /
`from_checkpoint()` wire `self._self_model.export()` /
`SelfModel.restore(payload.get("self_model"))`, alongside the existing
`sensory_development` sub-blob pattern.

## 5. Testing

- `SenseSelfState`/`SelfModel` unit tests: EWMA cost update arithmetic,
  health decay on simulated `ReadingFailure` and recovery on success streak,
  confidence composition bounds ([0,1], no NaN/inf on extreme inputs),
  cold-start defaults.
- Checkpoint: `_migrate_2_to_3` round-trip on a v2 payload; export/restore
  round-trip preserves values within quantization tolerance; size stays
  bounded for a saturated sense set.
- Attention integration: a sense with high learned cost gets deprioritized
  in `attend_to_host()` versus the old static-1.0 baseline, on a fixed
  fixture.
- Second-look integration: a high-confidence sense is skipped in favor of the
  next ranked candidate; falls through correctly when the skipped sense
  wasn't manifest-supported anyway (regression guard on existing A05 fix).
- Full `OrganismRuntime` integration test across several ticks with one
  provider deliberately failing, confirming health drops only for affected
  sense_ids and other senses are unaffected.

## 6. Open questions resolved during brainstorming

- Cost metric: wall-clock via `perf_counter`, not sample-count proxy.
- Feedback loop: wired into attention + second-look this milestone, not
  deferred.
- Confidence: composed from existing `SenseState`/`MetacognitionEngine`
  signals, not an independent model.
- Persistence: checkpoint schema bump 2→3 with explicit migration, following
  the main schema chain rather than a bolt-on sub-blob like
  `sensory_development` (chosen since self-model logically belongs to core
  runtime state, not the adaptive-sense subsystem).
