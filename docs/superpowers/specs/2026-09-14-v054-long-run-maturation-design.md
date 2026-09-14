# v0.54 — Long-run maturation (aging, forgetting, drift creep, checkpoint continuity)

**Status:** approved for implementation planning
**Base:** `main` at `b34fa65` (v0.53 organism self-model, merged)
**Roadmap entry:** "Aging/forgetting, rediscovery and bounded developmental
stability over long residence" (`docs/roadmap.md:61`, Milestone E, final
milestone — v0.50-v0.54)

## 1. Problem

A survey of `main@b34fa65` before designing this milestone found:

- **Rediscovery is already done.** `AdaptiveSenseModel.sampling_plan()`'s
  deterministic `probe_cursor` rotation through dormant/unknown senses
  already satisfies Milestone E exit condition 4 ("dormant senses retain a
  bounded chance of re-exploration"). Nothing to add here.
- **Aging/forgetting is not done.** `SenseSelfState.last_observed_tick`
  (added in v0.53) is write-only — set in `SelfModel.observe()` and never
  read anywhere. A sense that stops being sampled (goes dormant, or a
  provider silently drops it) keeps whatever health/confidence it last had
  forever, with no idle decay toward "I don't currently know."
- **`DriftAwareBaseline` has a documented, un-fixed gap** (its own
  docstring, `host/drift.py:53-60`): it detects a *sustained step*
  (`regime_run` consecutive large deviations) but never detects slow creep
  — a value drifting one small increment per tick never crosses `regime_z`
  on any single observation, so it is classified `NONE` forever and the
  baseline silently becomes wrong relative to the host's actual current
  behavior over long residence.
- **Checkpoint continuity is broken for the very idle-decay this milestone
  adds.** `SelfModel.restore()` (v0.53) does not persist
  `last_observed_tick` — every restored sense reads as "last observed at
  tick 0," which would make an idle-decay mechanism misfire on every
  restart, incorrectly treating a freshly-active sense as ancient. This
  must be fixed as part of adding idle decay, not after.

## 2. Goal

Three independent, additive fixes under one milestone theme (bounded
stability over long continuous residence):

1. **SelfModel idle decay** — health/confidence decay toward neutral for a
   sense that has gone idle for a bounded number of ticks, computed lazily
   at read time from `last_observed_tick`, never mutating stored EWMA state.
2. **Drift slow-creep detection** — a second, faster EWMA inside
   `DriftAwareBaseline` whose sustained divergence from the committed slow
   baseline confirms gradual creep as its own `DriftKind`, distinct from a
   sudden regime-shift step.
3. **Checkpoint continuity for `last_observed_tick`** — persist it per sense
   (checkpoint schema 3→4) so idle decay computed after a restart is exactly
   as accurate as if the organism had never stopped.

## 3. Non-goals

- No change to `AdaptiveSenseModel`'s existing eviction/rediscovery
  mechanism — it already satisfies the roadmap exit condition.
- No wall-clock/calendar time anywhere — ticks stay the only unit of
  elapsed "time," preserving the existing privacy discipline
  (`TimeBucket`/`saved_at_tick` precedent).
- No change to `RhythmModel` — surveyed and found to have no aging at all,
  but the user's scoping decision for this milestone was idle decay + drift
  creep + checkpoint continuity only; rhythm aging is a separate future gap,
  not silently folded in here.
- No new host permission, provider, or telemetry surface.
- No genome/learned-parameter system — every new threshold below is a fixed
  module-level constant, same discipline as v0.53.

## 4. Design

### 4.1 SelfModel idle decay (`core/selfmodel.py`)

`health(sense_id)` and `confidence(sense_id)` gain an optional
`current_tick: int | None = None` parameter. When `None` (the v0.53
default, used by every existing caller and test unless updated), behavior
is byte-for-byte unchanged — this is what makes the change additive rather
than a breaking API change.

When `current_tick` is supplied:

```python
IDLE_GRACE_TICKS = 20      # a sense skipped this many ticks is not yet "idle"
IDLE_DECAY_ALPHA = SELF_MODEL_EWMA_ALPHA  # same 0.06 as ordinary observation decay

def _idle_decayed(value: float, neutral: float, idle_ticks: int) -> float:
    steps = max(0, idle_ticks - IDLE_GRACE_TICKS)
    if steps == 0:
        return value
    return neutral + (value - neutral) * ((1 - IDLE_DECAY_ALPHA) ** steps)
```

`health()` decays toward `0.5` (the existing cold-start neutral), `confidence()`
toward `0.0`. `idle_ticks = max(0, current_tick - state.last_observed_tick)`.
This treats every idle tick past the grace period as an implicit "neutral"
observation at the same EWMA rate ordinary observations already use —
consistent with the rest of the module, not a new decay law.

`SelfModel.is_established()` and `relative_cost()` are **not** decayed —
"has this sense accumulated enough attempts to be established" and "what
did it cost when last measured" stay factual regardless of idleness; only
the two dimensions that represent *current trust* (health, confidence) fade
with disuse.

`core/runtime.py`'s two read sites (attention `relative_cost` reference
filtering stays as-is — cost is not decayed; the second-look health gate)
pass `current_tick=self._tick_count` so production behavior actually uses
the decay; existing `core/selfmodel.py` unit tests that call `health()`/
`confidence()` without a tick keep testing the undecayed EWMA directly.

### 4.2 Drift slow-creep detection (`host/drift.py`)

Add a second EWMA, faster than the committed baseline's own `decay`, that
free-runs on every observation regardless of the existing large-deviation
branching:

```python
def __init__(self, *, ..., fast_decay: float = 0.3, creep_z: float = 1.0, creep_run: int = 8) -> None:
    ...
    if fast_decay <= self._decay:
        raise ValueError("fast_decay must be faster (greater) than decay")
    ...
    self._fast_mean = 0.0
    self._creep_streak = 0
    self._creep_direction = 0
```

`creep_z` (default `1.0`) is deliberately smaller than `regime_z` (`2.0`) —
creep is a subtler signal than a step — and `creep_run` (default `8`) is
longer than `regime_run` (`3`) to compensate, so creep still requires
sustained evidence before confirming, not a single noisy tick.

On every `observe()` call (once established), after computing the existing
`z_score`/`large_deviation` step-detection path:

```python
# Free-running fast EWMA, same cold-start-then-decay rule _apply_direct
# already uses for the slow mean, just at fast_decay's higher rate:
if self._count == 0:
    self._fast_mean = value
else:
    self._fast_mean += fast_decay * (value - self._fast_mean)

creep_z_score = self._z_score(self._fast_mean, self._mean, self.stdev)
creep_direction = 1 if creep_z_score > 0 else -1 if creep_z_score < 0 else 0
if abs(creep_z_score) >= self._creep_z and creep_direction == self._creep_direction and self._creep_streak > 0:
    self._creep_streak += 1
elif abs(creep_z_score) >= self._creep_z:
    self._creep_streak = 1
    self._creep_direction = creep_direction
else:
    self._creep_streak = 0
    self._creep_direction = 0
```

`DriftKind` gains `CREEP = "creep"`. Confirmation rule and precedence:
creep is checked and can confirm **only when the existing step-detection
path this tick classified `NONE`** — a value large enough to already be
`ISOLATED`/`GRADUAL`/`REGIME_SHIFT` this tick is not additionally reported
as creeping; the two mechanisms answer different questions (a sudden jump
vs. a slow trend) and must not both fire on the same observation. On creep
confirmation (`_creep_streak >= creep_run`), the baseline gently re-centers
by blending toward the fast mean rather than the regime-shift's hard
recompute-from-buffer: `self._mean = self._fast_mean` (variance is left as
the ordinary EWMA-updated value from `_apply_direct`, which has been
tracking every observation the whole time since creep, unlike
regime-shift's frozen-during-streak variance — creep never freezes the
committed baseline, it only adds a second read on the side). The creep
streak then resets so the next creep episode starts clean.

`_apply_direct()` is unchanged and still runs on every `NONE`/creep-tracked
observation (creep does not suppress the ordinary slow-EWMA update — it is
an additional signal computed alongside it, not a replacement path).

`restore()` resets `_fast_mean` to the restored `mean` (not persisted
separately — see §4.3, this field is deliberately **not** checkpointed:
losing a few ticks of fast-EWMA warm-up after a restart is bounded and
harmless, unlike losing `last_observed_tick`, which would misfire idle
decay by definition).

### 4.3 Checkpoint continuity for `last_observed_tick`

`CHECKPOINT_SCHEMA_VERSION` 3 → 4. Each `self_model` entry gains
`last_observed_tick: int` (exact, non-negative — same precedent as the
existing top-level `saved_at_tick`, which is already an exact organism-tick
integer, not wall-clock time, so this is not a new privacy surface).

`SelfModel.export()` adds the field per established sense;
`SelfModel.restore()` reads it (defaulting to `0` only for a genuinely
missing key, via `_migrate_v3_to_v4` filling absent per-sense values — see
below — never for a present-but-malformed one, which is rejected like every
other field). `_require_class_range`-style validation extends to this field:
must be a non-negative int, no upper bound needed (ticks are unbounded over
long residence by design).

```python
def _migrate_v3_to_v4(payload: dict[str, Any]) -> dict[str, Any]:
    """v3 self_model entries predate per-sense last_observed_tick (roadmap
    v0.54) -- v4 backfills it to saved_at_tick (or 0) for every existing
    entry, the most conservative assumption (as if every sense was observed
    at the moment of the last save, so nothing decays as artificially idle
    immediately after migrating an old checkpoint)."""
    migrated = dict(payload)
    migrated["schema_version"] = 4
    fallback_tick = migrated.get("saved_at_tick") or 0
    self_model = dict(migrated.get("self_model", {}))
    for sense_id, entry in self_model.items():
        if isinstance(entry, dict) and "last_observed_tick" not in entry:
            entry = dict(entry)
            entry["last_observed_tick"] = fallback_tick
            self_model[sense_id] = entry
    migrated["self_model"] = self_model
    return migrated
```

## 5. Testing

- **Idle decay**: `health(sense_id, current_tick=...)` within grace period
  equals the undecayed value; past grace period, decays monotonically
  toward `0.5`/`0.0` as `current_tick` increases; passing `current_tick=None`
  (or omitting it) after the change still returns the exact v0.53 undecayed
  value — an explicit regression guard, run against the full v0.53 test
  file unmodified where it doesn't pass a tick.
- **Idle decay never mutates stored state**: two consecutive `health()`
  calls with the same large `current_tick` return the same value (proving
  it's computed, not applied-and-forgotten).
- **Drift creep**: a synthetic series incrementing by a fraction of a
  stdev per tick, never crossing `regime_z` on any single step, eventually
  classifies `CREEP` after `creep_run` sustained ticks, and the baseline's
  `mean` moves toward the true post-creep level; a single isolated spike
  does not trigger creep; an established `REGIME_SHIFT` step in the same
  tick suppresses a simultaneous creep classification (precedence test);
  variance is never frozen during a creep streak (regression guard against
  the exact bug regime-shift already had to work around, verified not
  reintroduced for creep).
- **Checkpoint v3→v4 migration**: an old `self_model` entry backfills
  `last_observed_tick` to `saved_at_tick`; a payload already at v4 is
  untouched; malformed `last_observed_tick` (negative, non-int, non-finite)
  is rejected on restore, not silently coerced.
- **End-to-end**: an `OrganismRuntime` runs, checkpoints, restores, and a
  sense observed just before the checkpoint reads as non-idle immediately
  after restore (the bug this milestone exists to prevent — a naive
  restore that lost `last_observed_tick` would instead read it as
  maximally idle and instantly decay health/confidence to neutral on the
  very next tick).

## 6. Decisions

| Question | Decision |
| --- | --- |
| Idle decay applies to which self-model fields | health, confidence only — not `is_established`, not `relative_cost` (cost is fact, not trust) |
| Idle decay computed how | Lazily at read time from `last_observed_tick`, never mutates stored EWMA — no extra per-tick sweep over all senses needed |
| Drift creep vs. regime-shift precedence | Regime-shift (a real step) takes precedence in the same tick; creep only classifies when the step-detector said `NONE` |
| Creep re-centering | Soft blend to the fast EWMA (`mean = fast_mean`), unlike regime-shift's hard recompute-from-buffer — creep never freezes variance |
| Checkpoint schema | Bump 3→4, migration backfills `last_observed_tick` to `saved_at_tick` (conservative: assume no idle time accrued across an old checkpoint) |
| `_fast_mean` persistence | Not persisted — losing fast-EWMA warm-up across a restart is bounded/harmless, unlike losing `last_observed_tick` |
