# v0.54 Long-Run Maturation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add idle decay of self-model health/confidence, slow-creep detection to the drift baseline, and checkpoint continuity for the tick each sense was last observed — three additive fixes closing Milestone E's "aging/forgetting... bounded developmental stability over long residence" gap.

**Architecture:** `SelfModel.health()`/`confidence()` gain an optional `current_tick` parameter and decay lazily at read time from the already-existing (but currently unused) `last_observed_tick` field — no new per-tick sweep, no schema change needed for the decay itself. `DriftAwareBaseline` gains a free-running fast EWMA whose sustained divergence from the committed baseline confirms slow creep as a new `DriftKind`, subordinate to the existing regime-shift step detector. Checkpoint schema bumps 3→4 to persist `last_observed_tick` per sense, since v0.53 silently dropped it on restore — without this fix, idle decay would misfire on every restart.

**Tech Stack:** Python 3.11+, dataclasses, pytest. No new dependencies.

**Spec:** `docs/_internal/specs/2026-09-14-v054-long-run-maturation-design.md` — read both together.

## Global Constraints

- No wall-clock/calendar time anywhere — ticks are the only unit of elapsed time (spec §3).
- No change to `AdaptiveSenseModel`'s eviction/rediscovery mechanism — already satisfies the roadmap exit condition (spec §3).
- No new host permission, provider, or telemetry surface.
- No genome/learned-parameter system — every threshold below is a fixed module-level constant.
- `IDLE_GRACE_TICKS = 20`, `IDLE_DECAY_ALPHA = SELF_MODEL_EWMA_ALPHA` (0.06, from `core/selfmodel.py`) — spec §4.1.
- `fast_decay: float = 0.3`, `creep_z: float = 1.0`, `creep_run: int = 8` — spec §4.2.
- `CHECKPOINT_SCHEMA_VERSION` goes 3 → 4 — spec §4.3.

---

## Task 1: `SelfModel` idle decay

**Files:**

- Modify: `src/symbiont/core/selfmodel.py`
- Test: `tests/unit/core/test_selfmodel.py`

**Interfaces:**

- Consumes: existing `SenseSelfState.last_observed_tick`, `SELF_MODEL_EWMA_ALPHA`.
- Produces: `SelfModel.health(sense_id, current_tick: int | None = None) -> float`, `SelfModel.confidence(sense_id, current_tick: int | None = None) -> float`, module constant `IDLE_GRACE_TICKS = 20`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/core/test_selfmodel.py (append)
from symbiont.core.selfmodel import IDLE_GRACE_TICKS


def test_health_without_current_tick_is_unchanged_from_v053():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    assert model.health("sense-a") == model.health("sense-a", current_tick=None)


def test_health_within_grace_period_is_not_decayed():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    undecayed = model.health("sense-a")
    assert model.health("sense-a", current_tick=49 + IDLE_GRACE_TICKS) == pytest.approx(undecayed)


def test_health_decays_toward_neutral_past_grace_period():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    undecayed = model.health("sense-a")
    far_future = 49 + IDLE_GRACE_TICKS + 200
    decayed = model.health("sense-a", current_tick=far_future)
    assert decayed < undecayed
    assert decayed == pytest.approx(0.5, abs=0.05)


def test_confidence_decays_toward_zero_past_grace_period():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    far_future = 49 + IDLE_GRACE_TICKS + 200
    assert model.confidence("sense-a", current_tick=far_future) == pytest.approx(0.0, abs=0.05)


def test_idle_decay_is_computed_not_mutated():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    far_future = 49 + IDLE_GRACE_TICKS + 200
    first = model.health("sense-a", current_tick=far_future)
    second = model.health("sense-a", current_tick=far_future)
    assert first == second
    # And the raw, undecayed value underneath is untouched:
    assert model.health("sense-a") != pytest.approx(0.5, abs=0.01)


def test_is_established_and_relative_cost_are_never_decayed():
    model = SelfModel()
    for tick in range(50):
        model.observe(outcome=_outcome(), tick=tick)
    far_future = 49 + IDLE_GRACE_TICKS + 200
    assert model.is_established("sense-a")  # no current_tick parameter exists on this method
    cost_now = model.relative_cost("sense-a", reference_ids=("sense-a",))
    assert cost_now == pytest.approx(1.0)  # unaffected by any notion of "current tick"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_selfmodel.py -v -k "grace or decay or without_current_tick"`
Expected: FAIL — `TypeError: health() got an unexpected keyword argument 'current_tick'`.

- [ ] **Step 3: Implement in `src/symbiont/core/selfmodel.py`**

Add the constant near the other module constants:

```python
IDLE_GRACE_TICKS = 20
```

Add a helper function near `_ewma`/`_clip`:

```python
def _idle_decayed(value: float, neutral: float, idle_ticks: int) -> float:
    steps = max(0, idle_ticks - IDLE_GRACE_TICKS)
    if steps == 0:
        return value
    return neutral + (value - neutral) * ((1 - SELF_MODEL_EWMA_ALPHA) ** steps)
```

Replace the `health`/`confidence` methods:

```python
    def health(self, sense_id: str, current_tick: int | None = None) -> float:
        state = self._state(sense_id)
        if state is None:
            return 0.5
        if current_tick is None:
            return state.health_ewma
        idle_ticks = max(0, current_tick - state.last_observed_tick)
        return _idle_decayed(state.health_ewma, 0.5, idle_ticks)

    def confidence(self, sense_id: str, current_tick: int | None = None) -> float:
        state = self._state(sense_id)
        if state is None:
            return 0.0
        if current_tick is None:
            return state.confidence_ewma
        idle_ticks = max(0, current_tick - state.last_observed_tick)
        return _idle_decayed(state.confidence_ewma, 0.0, idle_ticks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_selfmodel.py -v`
Expected: PASS, all tests including every pre-existing v0.53 test (none of them pass `current_tick`, so they exercise the unchanged `None` path).

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/core/selfmodel.py tests/unit/core/test_selfmodel.py
git commit -m "$(cat <<'EOF'
feat(core): decay self-model health/confidence for idle senses

health()/confidence() gain an optional current_tick parameter; past a
20-tick grace period a sense that has not been observed decays toward
neutral (0.5 health, 0.0 confidence) at the same EWMA rate ordinary
observations already use. Computed lazily at read time from the
existing (previously write-only) last_observed_tick field -- no
mutation, no extra per-tick sweep. Omitting current_tick preserves
the exact v0.53 undecayed behavior.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: Checkpoint continuity for `last_observed_tick`

**Files:**

- Modify: `src/symbiont/core/selfmodel.py`, `src/symbiont/host/checkpoint.py`
- Test: `tests/unit/core/test_selfmodel.py`, `tests/unit/host/test_checkpoint.py`

**Interfaces:**

- Consumes: `SenseSelfState.last_observed_tick` (Task 1's target field).
- Produces: `SelfModel.export()` includes `last_observed_tick` per entry; `SelfModel.restore()` reads and validates it; `CHECKPOINT_SCHEMA_VERSION = 4`; `_migrate_v3_to_v4`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/core/test_selfmodel.py (append)
def test_export_includes_last_observed_tick():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export()
    assert exported["sense-a"]["last_observed_tick"] == 9


def test_restore_preserves_last_observed_tick_for_idle_decay():
    model = SelfModel()
    for tick in range(10):
        model.observe(outcome=_outcome(), tick=tick)
    exported = model.export()

    restored = SelfModel.restore(exported, allowed_sense_ids={"sense-a"})

    # A sense observed at tick 9, restored, then read many ticks later
    # must decay from tick 9 -- not from a lost/zeroed last_observed_tick,
    # which would make it read as maximally idle immediately.
    close_tick_health = restored.health("sense-a", current_tick=9 + IDLE_GRACE_TICKS)
    assert close_tick_health == pytest.approx(model.health("sense-a"), abs=0.05)


def test_restore_rejects_negative_last_observed_tick():
    with pytest.raises(ValueError):
        SelfModel.restore(
            {
                "sense-a": {
                    "cost_class": 0,
                    "health_class": 8,
                    "confidence_class": 8,
                    "maturity_class": 4,
                    "last_observed_tick": -1,
                }
            },
            allowed_sense_ids={"sense-a"},
        )
```

```python
# tests/unit/host/test_checkpoint.py (append)
def test_current_schema_version_is_four():
    assert CHECKPOINT_SCHEMA_VERSION == 4


def test_v3_checkpoint_migrates_to_v4_backfilling_last_observed_tick():
    from symbiont.host.checkpoint import _migrate_to_current

    v3_payload = {
        "schema_version": 3,
        "saved_at_tick": 42,
        "self_model": {"sense-a": {"cost_class": 0, "health_class": 8, "confidence_class": 8, "maturity_class": 4}},
    }
    migrated = _migrate_to_current(dict(v3_payload))
    assert migrated["schema_version"] == 4
    assert migrated["self_model"]["sense-a"]["last_observed_tick"] == 42


def test_v1_checkpoint_migrates_all_the_way_to_v4():
    from symbiont.host.checkpoint import _migrate_to_current

    migrated = _migrate_to_current({"schema_version": 1})
    assert migrated["schema_version"] == 4
    assert migrated["self_model"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_selfmodel.py tests/unit/host/test_checkpoint.py -v -k "last_observed_tick or schema_version_is_four or v3_checkpoint or v1_checkpoint_migrates_all"`
Expected: FAIL — `KeyError: 'last_observed_tick'` / `assert 3 == 4`.

- [ ] **Step 3: Implement**

In `src/symbiont/core/selfmodel.py`, update `export()`:

```python
    def export(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for sense_id, state in self._states.items():
            if not state.established:
                continue
            payload[sense_id] = {
                "cost_class": _quantize_cost(state.cost_ewma_s),
                "health_class": _quantize(state.health_ewma, _HEALTH_CLASSES),
                "confidence_class": _quantize(state.confidence_ewma, _CONFIDENCE_CLASSES),
                "maturity_class": _quantize(_maturity(state.successes), _MATURITY_CLASSES),
                "last_observed_tick": state.last_observed_tick,
            }
        return payload
```

Update `restore()` to read and validate the new field, inserting after the existing `maturity_class` validation:

```python
            maturity_class = entry["maturity_class"]
            last_observed_tick = entry["last_observed_tick"]
            _require_class_range(cost_class, _COST_CLASSES, "cost_class")
            _require_class_range(health_class, _HEALTH_CLASSES, "health_class")
            _require_class_range(confidence_class, _CONFIDENCE_CLASSES, "confidence_class")
            _require_class_range(maturity_class, _MATURITY_CLASSES, "maturity_class")
            if isinstance(last_observed_tick, bool) or not isinstance(last_observed_tick, int):
                raise ValueError("last_observed_tick must be an int")
            if last_observed_tick < 0:
                raise ValueError("last_observed_tick must be non-negative")
```

and pass it into the reconstructed state:

```python
            state = SenseSelfState(
                cost_ewma_s=_dequantize_cost(cost_class),
                health_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                quality_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                confidence_ewma=_dequantize(confidence_class, _CONFIDENCE_CLASSES),
                attempts=max(successes, MIN_SELF_MODEL_ATTEMPTS),
                successes=successes,
                last_observed_tick=last_observed_tick,
            )
```

In `src/symbiont/host/checkpoint.py`:

```python
CHECKPOINT_SCHEMA_VERSION = 4
```

```python
def _migrate_v3_to_v4(payload: dict[str, Any]) -> dict[str, Any]:
    """v3 self_model entries predate per-sense last_observed_tick (roadmap
    v0.54) -- v4 backfills it to saved_at_tick (or 0) for every existing
    entry, the most conservative assumption: as if every sense was observed
    at the moment of the last save, so nothing decays as artificially idle
    immediately after migrating an old checkpoint."""
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


_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_selfmodel.py tests/unit/host/test_checkpoint.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/core/selfmodel.py src/symbiont/host/checkpoint.py tests/unit/core/test_selfmodel.py tests/unit/host/test_checkpoint.py
git commit -m "$(cat <<'EOF'
feat(host,core): persist last_observed_tick through checkpoint v4

v0.53's SelfModel.restore() silently dropped last_observed_tick,
which would have made Task 1's idle decay misfire on every restart --
a freshly-active sense would read as maximally idle immediately after
loading a checkpoint. Schema bumps 3->4; the migration backfills the
field to saved_at_tick for old checkpoints, the conservative
assumption that no idle time accrued before this milestone existed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

Also check `tests/smoke/test_cli.py` for hard-coded `schema_version == 3` assertions (the same pattern that needed fixing from 2→3 during v0.53) and update them to `4` if present:

```bash
grep -n "schema_version.*== 3" tests/smoke/test_cli.py
```

If any match, update each to `== 4` and re-run `pytest tests/smoke/test_cli.py -q` before committing (fold this fix into this task's commit, same as the v0.53 precedent).

---

## Task 3: Wire `OrganismRuntime`'s second-look gate to use idle decay

**Files:**

- Modify: `src/symbiont/core/runtime.py`
- Test: `tests/unit/core/test_organism_runtime.py`

**Interfaces:**

- Consumes: `SelfModel.health(sense_id, current_tick=...)` (Task 1).
- Produces: no new public interface — behavior change only.

- [ ] **Step 1: Write the failing test**

```python
def test_second_look_gate_uses_idle_decayed_health_not_raw_health():
    from symbiont.core.selfmodel import IDLE_GRACE_TICKS, MIN_SELF_MODEL_ATTEMPTS, SelfModel
    from symbiont.host.readings import CapabilitySamplingOutcome, ReadingQuality, SamplingOutcomeKind

    self_model = SelfModel()
    # Establish "stale" with good health, then let it go idle for a long
    # time without further observation -- idle decay should pull its
    # *read* health down toward neutral (0.5), which sits above the 0.15
    # gate threshold, so this alone must not block investigation on idle
    # grounds. This test's purpose is documentation-as-regression: idle
    # decay must never be confused with the "chronically broken" gate,
    # which is Task 1's design boundary (spec 4.1: only two fields decay,
    # and 0.5 neutral health never itself crosses the 0.15 gate).
    for tick in range(40):
        self_model.observe(
            outcome=CapabilitySamplingOutcome(
                capability_id="stale-but-was-healthy",
                provider_id="fixture",
                kind=SamplingOutcomeKind.SUCCEEDED,
                attributed_elapsed_s=0.01,
                quality=ReadingQuality.NOMINAL,
            ),
            tick=tick,
        )
    assert self_model.health("stale-but-was-healthy", current_tick=39 + IDLE_GRACE_TICKS + 500) == pytest.approx(
        0.5, abs=0.05
    )
```

This step only re-confirms Task 1's own guarantee from `runtime.py`'s perspective; it does not yet prove the runtime *calls* `health()` with `current_tick`. Add a second, sharper test using the existing monkeypatch pattern from `test_established_but_persistently_unhealthy_sense_is_skipped_for_second_look`:

```python
def test_runtime_passes_current_tick_to_self_model_health_for_second_look_gate(monkeypatch):
    calls = []

    runtime = OrganismRuntime(min_samples=1, investigate_ticks=1)

    real_health = runtime.self_model.health

    def spy_health(sense_id, current_tick=None):
        calls.append(current_tick)
        return real_health(sense_id, current_tick=current_tick)

    monkeypatch.setattr(runtime.self_model, "health", spy_health)
    runtime.tick()

    assert any(tick_arg is not None for tick_arg in calls)
```

- [ ] **Step 2: Run tests to verify the second one fails**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k passes_current_tick`
Expected: FAIL — `calls` only ever recorded `None`, since the runtime currently calls `health(candidate)` with no `current_tick`.

- [ ] **Step 3: Implement**

In `src/symbiont/core/runtime.py`, find the second-look health gate (added in v0.53):

```python
                if (
                    self._self_model.is_established(candidate)
                    and self._self_model.health(candidate) < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
```

Change to:

```python
                if (
                    self._self_model.is_established(candidate)
                    and self._self_model.health(candidate, current_tick=self._tick_count)
                    < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_organism_runtime.py tests/unit/core/test_selfmodel.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/core/runtime.py tests/unit/core/test_organism_runtime.py
git commit -m "$(cat <<'EOF'
feat(core): apply idle decay to the runtime's second-look health gate

The chronically-low-health second-look skip now reads health() with
current_tick, so a sense that was unhealthy long ago but has since
gone idle correctly fades toward neutral (0.5) rather than
permanently reading as broken from a stale EWMA value.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: Drift slow-creep detection

**Files:**

- Modify: `src/symbiont/host/drift.py`
- Test: `tests/unit/host/test_host_drift.py`

**Interfaces:**

- Consumes: nothing new.
- Produces: `DriftKind.CREEP`, `DriftAwareBaseline(fast_decay=0.3, creep_z=1.0, creep_run=8, ...)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_slow_creep_confirms_after_creep_run_without_ever_triggering_regime_shift():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_z=2.0, creep_z=1.0, creep_run=6, fast_decay=0.4)
    _seed(baseline, [1.0, 1.0, 1.0, 1.0, 1.0])

    kinds = []
    value = 1.0
    for _ in range(30):
        value += 0.05  # small enough that no single step ever reads as a regime_z jump
        kinds.append(baseline.observe(value).kind)

    assert DriftKind.REGIME_SHIFT not in kinds
    assert DriftKind.CREEP in kinds


def test_creep_moves_the_baseline_toward_the_true_level():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, creep_z=1.0, creep_run=6, fast_decay=0.4)
    _seed(baseline, [1.0, 1.0, 1.0, 1.0, 1.0])
    mean_before = baseline.mean

    value = 1.0
    for _ in range(30):
        value += 0.05
        baseline.observe(value)

    assert baseline.mean > mean_before


def test_isolated_spike_does_not_trigger_creep():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, creep_z=1.0, creep_run=6, fast_decay=0.4)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    obs = baseline.observe(10.0)
    assert obs.kind == DriftKind.ISOLATED


def test_regime_shift_takes_precedence_over_creep_in_the_same_tick():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3, creep_z=1.0, creep_run=3, fast_decay=0.4)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    kinds = [baseline.observe(5.0).kind for _ in range(3)]

    assert kinds[-1] == DriftKind.REGIME_SHIFT
    assert DriftKind.CREEP not in kinds


def test_creep_never_freezes_variance():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, creep_z=1.0, creep_run=6, fast_decay=0.4)
    _seed(baseline, [1.0, 1.0, 1.0, 1.0, 1.0])
    variance_before = baseline.variance

    value = 1.0
    for _ in range(6):
        value += 0.05
        baseline.observe(value)

    assert baseline.variance != pytest.approx(variance_before)


def test_creep_and_regime_are_independently_configurable():
    baseline = DriftAwareBaseline(creep_z=1.0, fast_decay=0.5)
    assert baseline is not None


@pytest.mark.parametrize("kwargs", [{"fast_decay": 0.1, "decay": 0.2}, {"fast_decay": 0.2, "decay": 0.2}])
def test_fast_decay_must_exceed_decay(kwargs):
    with pytest.raises(ValueError):
        DriftAwareBaseline(**kwargs)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/host/test_host_drift.py -v -k "creep or fast_decay"`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'creep_z'`.

- [ ] **Step 3: Implement in `src/symbiont/host/drift.py`**

Add to `DriftKind`:

```python
class DriftKind(StrEnum):
    NONE = "none"
    ISOLATED = "isolated"
    GRADUAL = "gradual"
    CREEP = "creep"
    REGIME_SHIFT = "regime_shift"
```

Update `__init__`:

```python
    def __init__(
        self,
        *,
        decay: float = 0.1,
        isolated_z: float = 3.0,
        regime_z: float = 2.0,
        regime_run: int = 3,
        min_samples: int = 5,
        fast_decay: float = 0.3,
        creep_z: float = 1.0,
        creep_run: int = 8,
    ) -> None:
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be between 0 (exclusive) and 1 (inclusive)")
        if isolated_z <= 0.0:
            raise ValueError("isolated_z must be positive")
        if regime_z <= 0.0:
            raise ValueError("regime_z must be positive")
        if isolated_z < regime_z:
            raise ValueError("isolated_z must be at least regime_z")
        if regime_run < 1:
            raise ValueError("regime_run must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if not 0.0 < fast_decay <= 1.0:
            raise ValueError("fast_decay must be between 0 (exclusive) and 1 (inclusive)")
        if fast_decay <= decay:
            raise ValueError("fast_decay must be faster (greater) than decay")
        if creep_z <= 0.0:
            raise ValueError("creep_z must be positive")
        if creep_run < 1:
            raise ValueError("creep_run must be at least 1")

        self._decay = decay
        self._isolated_z = isolated_z
        self._regime_z = regime_z
        self._regime_run = regime_run
        self._min_samples = min_samples
        self._fast_decay = fast_decay
        self._creep_z = creep_z
        self._creep_run = creep_run

        self._count = 0
        self._mean = 0.0
        self._variance = 0.0
        self._deviation_streak = 0
        self._streak_direction = 0
        self._buffer: list[float] = []
        self._fast_mean = 0.0
        self._creep_streak = 0
        self._creep_direction = 0
```

Update `restore()` to also reset the creep-tracking state (mirroring the existing streak reset):

```python
        self._deviation_streak = 0
        self._streak_direction = 0
        self._buffer = []
        self._fast_mean = mean
        self._creep_streak = 0
        self._creep_direction = 0
```

Update `observe()` — insert the fast-EWMA update and creep tracking, checked only when the existing step-detector classified `NONE` this tick:

```python
    def observe(self, value: float) -> DriftObservation:
        if not self.is_established:
            kind = DriftKind.NONE
            z_score = None
            self._apply_direct(value)
            self._fast_mean = value
            self._count += 1
            return DriftObservation(kind=kind, z_score=z_score)

        z_score = self._z_score(value, self._mean, self.stdev)
        magnitude = abs(z_score)
        large_deviation = magnitude >= self._regime_z
        direction = 1 if z_score > 0 else -1 if z_score < 0 else 0

        if large_deviation and direction == self._streak_direction and self._deviation_streak > 0:
            self._deviation_streak += 1
            self._buffer.append(value)
        elif large_deviation:
            self._deviation_streak = 1
            self._streak_direction = direction
            self._buffer = [value]
        else:
            self._deviation_streak = 0
            self._streak_direction = 0
            self._buffer = []

        if large_deviation and self._deviation_streak >= self._regime_run:
            self._recompute_from_buffer()
            kind = DriftKind.REGIME_SHIFT
            self._deviation_streak = 0
            self._streak_direction = 0
            self._buffer = []
            self._fast_mean = self._mean
            self._creep_streak = 0
            self._creep_direction = 0
        else:
            if not large_deviation:
                self._apply_direct(value)
            self._fast_mean += self._fast_decay * (value - self._fast_mean)

            if magnitude >= self._isolated_z:
                kind = DriftKind.ISOLATED
                self._creep_streak = 0
                self._creep_direction = 0
            elif large_deviation:
                kind = DriftKind.GRADUAL
                self._creep_streak = 0
                self._creep_direction = 0
            else:
                creep_z_score = self._z_score(self._fast_mean, self._mean, self.stdev)
                creep_direction = 1 if creep_z_score > 0 else -1 if creep_z_score < 0 else 0
                creeping = abs(creep_z_score) >= self._creep_z
                if creeping and creep_direction == self._creep_direction and self._creep_streak > 0:
                    self._creep_streak += 1
                elif creeping:
                    self._creep_streak = 1
                    self._creep_direction = creep_direction
                else:
                    self._creep_streak = 0
                    self._creep_direction = 0

                if creeping and self._creep_streak >= self._creep_run:
                    self._mean = self._fast_mean
                    kind = DriftKind.CREEP
                    self._creep_streak = 0
                    self._creep_direction = 0
                else:
                    kind = DriftKind.NONE

        self._count += 1
        return DriftObservation(kind=kind, z_score=z_score)
```

Update the class docstring's "Known limitation" paragraph (lines ~53-60) to state creep detection now exists instead of being an open gap — replace:

```
    Known limitation: this detects a *sustained step* ...
```

with:

```
    Slow creep — a value drifting a small increment per tick, never
    crossing ``regime_z`` on any single observation — is detected
    separately (roadmap v0.54) by a free-running fast EWMA (``fast_decay``,
    faster than ``decay``) whose sustained divergence from the committed
    mean confirms ``DriftKind.CREEP`` after ``creep_run`` consecutive
    ticks past ``creep_z``. Creep only classifies when the step-detector
    above found ``NONE`` this tick — a value already large enough to be
    ``ISOLATED``/``GRADUAL``/``REGIME_SHIFT`` is not also reported as
    creeping. Unlike a regime shift's hard recompute-from-buffer, creep
    re-centers gently (``mean = fast_mean``) and never freezes variance.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/host/test_host_drift.py -v`
Expected: PASS, all tests including every pre-existing test (creep only ever classifies where the old code classified `NONE`, and the fast EWMA never touches `_mean`/`_variance` except on its own confirmation).

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/host/drift.py tests/unit/host/test_host_drift.py
git commit -m "$(cat <<'EOF'
feat(host): detect slow creep in DriftAwareBaseline

Fixes the baseline's own documented gap: a value drifting a small
increment per tick never crossed regime_z and was classified NONE
forever. A free-running fast EWMA now tracks recent values; sustained
divergence from the committed baseline confirms DriftKind.CREEP after
creep_run ticks, subordinate to the existing regime-shift step
detector (a real step in the same tick takes precedence). Creep
re-centers gently toward the fast mean rather than regime-shift's
hard recompute, and never freezes variance.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 5: End-to-end restart regression

**Files:**

- Test: `tests/unit/core/test_organism_runtime.py`

**Interfaces:**

- Consumes: everything above.

- [ ] **Step 1: Write the failing test**

```python
def test_a_sense_observed_just_before_checkpoint_is_not_idle_immediately_after_restore():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    for _ in range(10):
        runtime.tick()

    established = [
        capability_id for capability_id in DEFAULT_PERCEPT_NAMES if runtime.self_model.is_established(capability_id)
    ]
    assert established

    payload = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)

    sense_id = established[0]
    pre_checkpoint_health = runtime.self_model.health(sense_id)
    # Reading immediately at the restored tick count must not have decayed
    # at all -- this is the exact bug a lost last_observed_tick would cause
    # (it would read as idle since tick 0, decaying instantly).
    post_restore_health = restored.self_model.health(sense_id, current_tick=restored.tick_count)
    assert post_restore_health == pytest.approx(pre_checkpoint_health, abs=0.02)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k not_idle_immediately_after_restore`
Expected: PASS already if Tasks 1-3 are correctly implemented — this task adds no new production code, it is a dedicated end-to-end regression guard tying the whole milestone together. Run it to confirm it actually passes rather than accidentally vacuously succeeding (e.g. because `established` was empty) — assert `established` is non-empty is already in the test body for exactly this reason.

- [ ] **Step 3: N/A — test-only task, no implementation change expected**

- [ ] **Step 4: Run the full suite**

Run: `pytest -q`
Expected: every test in the repository passes, including this one and everything from v0.50-v0.53.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/core/test_organism_runtime.py
git commit -m "$(cat <<'EOF'
test(core): guard idle decay against a lost last_observed_tick

End-to-end regression across a real checkpoint/restore cycle: a sense
observed just before saving reads with unchanged health immediately
after restore, at the restored tick count -- the exact failure mode
Task 2's checkpoint fix exists to prevent.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**

- §4.1 SelfModel idle decay (lazy, grace period, health/confidence only) → Task 1.
- §4.2 Drift slow-creep detection, precedence over/subordinate to regime-shift, gentle re-centering, variance never frozen → Task 4.
- §4.3 Checkpoint schema 3→4, `last_observed_tick` persistence, migration backfill → Task 2.
- Runtime actually using the decay in production (not just available as an API) → Task 3.
- End-to-end restart correctness (the specific bug this milestone exists to prevent) → Task 5.
- Non-goals (no `AdaptiveSenseModel`/`RhythmModel` changes, no wall-clock time, no genome) — respected: no task touches those files.

**Type consistency check:** `health`/`confidence` signatures in Task 1 (`current_tick: int | None = None`) are used identically in Task 3's runtime call site and Task 5's end-to-end test. `DriftKind.CREEP` from Task 4 matches the spec's exact naming. `_migrate_v3_to_v4` in Task 2 follows the exact naming/registration pattern of the existing `_migrate_v2_to_v3` it sits beside.
