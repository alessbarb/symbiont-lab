# Biological Memory Consolidation — PR3 (Host Consolidated Projection) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace exact `(count, mean, variance)` persistence for `HostAcclimation`/`RhythmModel`/`DriftAwareBaseline` with one shared coarse-class codec (`center_class`/`scale_class`/`maturity_class`), and replace `SelfModel`'s one remaining exact field (`last_observed_tick`) with a 5-level `RecencyClass`. Live RAM statistics are untouched — only what `host/checkpoint.py` reads and writes changes.

**Architecture:** One new module, `src/symbiont/host/consolidated_baseline.py`, owns a codec shared by all three `CapabilityBaseline` consumers: `center_class` is a signed-log encoding of the raw mean's own magnitude (never divided by scale, so it survives a near-zero-variance signal without collapsing or dividing by zero); `scale_class` is a `CONSTANT` sentinel plus 16 log-scale buckets of `stdev`; `maturity_class` reuses the same 8-bucket monotone shape already established in PR1, applied to observation count under a distinctly-named function so "count" and "epoch" maturity are never confused. Restoring seeds a **bounded, fixed prior weight** (never the real historical count) into a real `CapabilityBaseline`, so existing `HostAcclimation.restore`/`RhythmModel.restore`/`DriftAwareBaseline.restore`/`RunningStats.from_baseline` need no changes at all — only `host/checkpoint.py`'s `export_checkpoint`/`import_checkpoint` change what they read and write.

**Tech Stack:** Python 3.11+ stdlib only (`math.log10`), matching `src/symbiont/host/`.

**Spec:** `docs/design/biological-memory-consolidation.md` (§10.2 sensory statistics, §16 acclimation/rhythm/drift seeded restore, §17 self-model recency class, §23 PR3)

## Global Constraints

- `center_class` is `sign(mean) * log10(1 + |mean|)`, quantized to 32 classes over range `[-6, 6]` — never `mean / stdev` (owner-rejected: divides by zero at `stdev == 0`, and saturates immediately whenever `|mean| >> stdev`, which is common for a positive signal with low relative variance).
- `scale_class` is `0` (`CONSTANT`) when `stdev <= 1e-9`, else `1 + quantize(log10(stdev), [-6, 6], 16)` (17 total states, per the owner's own count).
- `maturity_class_from_observation_support(count: int) -> int` is a distinctly-named function from PR1's `maturity_class_from_support_epochs` even though both delegate to the same internal threshold table — count and epoch-count are different magnitudes and must never read as the same concept later.
- Restoring a consolidated baseline seeds a **small, fixed, maturity-scaled prior weight** (`_PRIOR_WEIGHTS_BY_MATURITY`, capped at `8`) as the synthetic `count`, never a number that could be mistaken for real historical sample count (owner: "no fabricar count... internamente el modelo podría tener prior + nueva evidencia"). A small fixed cap means real post-restart observations dominate quickly — the durable memory is a soft anchor, not fabricated operational history.
- `SelfModel.export`/`SelfModel.restore` gain a `current_tick`/`saved_at_tick` parameter and persist `recency_class` (5 levels: `CURRENT`, `SHORT_IDLE`, `IDLE`, `LONG_IDLE`, `DORMANT`) instead of `last_observed_tick`. Restore seeds `last_observed_tick` from a **fixed per-class representative idle-tick table**, never a per-organism-derived exact offset.
- No `CHECKPOINT_SCHEMA_VERSION` bump in this PR (PR4's job); `host/checkpoint.py`'s own payload shape for `acclimation`/`rhythms`/`drift`/`self_model` changes, which PR4's v5->v6 migration will need to account for.
- **Explicitly out of scope, disclosed, not silently dropped:** `AdaptiveSenseModel`'s `SenseState`/`PairAccumulator` still persist exact `mean`/`m2`/correlation moments. This is a known, deferred gap — the same disclosed-gap pattern already used for P8/P9 in PR1 — left for a follow-up PR rather than expanding this one further.

---

### Task 1: Shared consolidated-baseline codec

**Files:**
- Create: `src/symbiont/host/consolidated_baseline.py`
- Test: `tests/unit/host/test_consolidated_baseline.py`

**Interfaces:**
- Consumes: `CapabilityBaseline` from `src/symbiont/host/acclimation.py`.
- Produces: `ConsolidatedBaselineSeed` frozen dataclass (`center_class: int`, `scale_class: int`, `maturity_class: int`); `consolidate_baseline(baseline: CapabilityBaseline) -> ConsolidatedBaselineSeed`; `seed_capability_baseline(seed: ConsolidatedBaselineSeed) -> CapabilityBaseline`; `maturity_class_from_observation_support(count: int) -> int`. Consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import math

import pytest

from symbiont.host.acclimation import CapabilityBaseline
from symbiont.host.consolidated_baseline import (
    ConsolidatedBaselineSeed,
    consolidate_baseline,
    maturity_class_from_observation_support,
    seed_capability_baseline,
)


def test_maturity_class_from_observation_support_is_monotone_and_coarse():
    assert maturity_class_from_observation_support(0) == 0
    assert maturity_class_from_observation_support(1) == 1
    assert maturity_class_from_observation_support(1000) == 7
    classes = [maturity_class_from_observation_support(n) for n in range(0, 300, 3)]
    assert classes == sorted(classes)


def test_constant_signal_gets_the_constant_scale_sentinel():
    baseline = CapabilityBaseline(count=50, mean=700.0, variance=0.0)
    seed = consolidate_baseline(baseline)
    assert seed.scale_class == 0  # CONSTANT sentinel, never a fabricated tiny stdev

    restored = seed_capability_baseline(seed)
    assert restored.variance == pytest.approx(0.0)
    assert restored.mean == pytest.approx(700.0, rel=0.15)


def test_high_mean_low_variance_signal_does_not_saturate_center():
    """Owner-rejected failure mode of the first proposal: mean=1000,
    stdev=5 must not collapse to the same class as mean=1e9, stdev=5."""
    moderate = consolidate_baseline(CapabilityBaseline(count=20, mean=1000.0, variance=25.0))
    extreme = consolidate_baseline(CapabilityBaseline(count=20, mean=1_000_000_000.0, variance=25.0))
    assert moderate.center_class != extreme.center_class


def test_center_and_scale_round_trip_approximately_and_never_fabricate_count():
    baseline = CapabilityBaseline(count=123, mean=517.4, variance=63.2 * 63.2)
    seed = consolidate_baseline(baseline)
    restored = seed_capability_baseline(seed)

    assert restored.mean == pytest.approx(517.4, rel=0.2)
    assert restored.stdev == pytest.approx(63.2, rel=0.5)
    # Never the real historical count -- a small, fixed, maturity-scaled prior weight.
    assert restored.count <= 8
    assert restored.count != 123


def test_two_baselines_one_ordinary_observation_apart_are_not_differenced_to_the_same_precision():
    """P2-style guarantee applied to host statistics."""
    before = consolidate_baseline(CapabilityBaseline(count=100, mean=50.0, variance=4.0))
    after = consolidate_baseline(CapabilityBaseline(count=101, mean=50.0049, variance=4.0))
    assert before == after  # a single ordinary observation must not move any durable class
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/host/test_consolidated_baseline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'symbiont.host.consolidated_baseline'`

- [ ] **Step 3: Create `src/symbiont/host/consolidated_baseline.py`**

```python
"""Shared coarse-class codec for HostAcclimation/RhythmModel/DriftAwareBaseline
statistics (design docs/design/biological-memory-consolidation.md §10.2, §16).

center_class is a signed-log encoding of the mean's own magnitude -- never
mean/stdev, which divides by zero at stdev==0 and saturates whenever
|mean| >> stdev (owner-rejected failure mode, 2026-09-14). scale_class is a
CONSTANT sentinel plus log-scale buckets of stdev. Restoring seeds a small,
fixed, maturity-scaled prior weight as the synthetic count -- never the real
historical sample count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .acclimation import CapabilityBaseline

_CENTER_CLASSES = 32
_CENTER_LOG_RANGE = (-6.0, 6.0)
_SCALE_LOG_CLASSES = 16
_SCALE_LOG_RANGE = (-6.0, 6.0)
_SCALE_EPSILON = 1e-9
_MATURITY_THRESHOLDS = (0, 1, 2, 4, 8, 16, 32, 64)
_PRIOR_WEIGHTS_BY_MATURITY = (1, 1, 2, 3, 4, 6, 8, 8)


def _quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int:
    low, high = bounds
    clipped = max(low, min(high, value))
    ratio = (clipped - low) / (high - low)
    return round(ratio * (num_classes - 1))


def _dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float:
    low, high = bounds
    ratio = class_id / (num_classes - 1)
    return low + ratio * (high - low)


def maturity_class_from_observation_support(count: int) -> int:
    """Coarse, monotone class over a real sample count -- distinctly named
    from PR1's maturity_class_from_support_epochs even though both delegate
    to the same threshold shape, since count and epoch-count are different
    magnitudes."""
    if count < 0:
        count = 0
    matured_class = 0
    for index, threshold in enumerate(_MATURITY_THRESHOLDS):
        if count >= threshold:
            matured_class = index
    return matured_class


def _center_class(mean: float) -> int:
    magnitude = math.log10(1.0 + abs(mean))
    signed = math.copysign(magnitude, mean) if mean != 0 else 0.0
    return _quantize_signed(signed, _CENTER_LOG_RANGE, _CENTER_CLASSES)


def _center_representative(cls: int) -> float:
    signed = _dequantize_signed(cls, _CENTER_LOG_RANGE, _CENTER_CLASSES)
    magnitude = 10.0 ** abs(signed) - 1.0
    return math.copysign(magnitude, signed) if signed != 0 else 0.0


def _scale_class(stdev: float) -> int:
    if stdev <= _SCALE_EPSILON:
        return 0
    exponent = math.log10(stdev)
    return 1 + _quantize_signed(exponent, _SCALE_LOG_RANGE, _SCALE_LOG_CLASSES)


def _scale_representative(cls: int) -> float:
    if cls == 0:
        return 0.0
    exponent = _dequantize_signed(cls - 1, _SCALE_LOG_RANGE, _SCALE_LOG_CLASSES)
    return 10.0 ** exponent


@dataclass(slots=True, frozen=True)
class ConsolidatedBaselineSeed:
    center_class: int
    scale_class: int
    maturity_class: int


def consolidate_baseline(baseline: CapabilityBaseline) -> ConsolidatedBaselineSeed:
    return ConsolidatedBaselineSeed(
        center_class=_center_class(baseline.mean),
        scale_class=_scale_class(baseline.stdev),
        maturity_class=maturity_class_from_observation_support(baseline.count),
    )


def seed_capability_baseline(seed: ConsolidatedBaselineSeed) -> CapabilityBaseline:
    stdev = _scale_representative(seed.scale_class)
    mean = _center_representative(seed.center_class)
    weight = _PRIOR_WEIGHTS_BY_MATURITY[seed.maturity_class]
    return CapabilityBaseline(count=weight, mean=mean, variance=stdev * stdev)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/host/test_consolidated_baseline.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/host/consolidated_baseline.py tests/unit/host/test_consolidated_baseline.py
git commit -m "feat(host): add shared consolidated-baseline codec (center/scale/maturity classes)"
```

---

### Task 2: Wire the codec into host/checkpoint.py for acclimation/rhythm/drift

**Files:**
- Modify: `src/symbiont/host/checkpoint.py`
- Modify: `tests/unit/host/test_checkpoint.py` (read it first — check exact current assertions before editing)
- Test: same files

**Interfaces:**
- Consumes: `consolidate_baseline`/`seed_capability_baseline` (Task 1).
- Produces: `export_checkpoint`'s `"acclimation"`/`"rhythms"`/`"drift"` entries now carry `{"center_class", "scale_class", "maturity_class"}` instead of `{"count", "mean", "variance"}`; `import_checkpoint` reconstructs a `CapabilityBaseline` via `seed_capability_baseline` before calling the existing `.restore(...)` methods.

- [ ] **Step 1: Read the current test file**

Run: `grep -n "count\|mean\|variance" tests/unit/host/test_checkpoint.py`

Note every assertion that constructs a raw `{"count": ..., "mean": ..., "variance": ...}` dict as fixture input to `import_checkpoint`, or that asserts an exported payload's `"acclimation"`/`"rhythms"`/`"drift"` entries contain those exact keys. Each must be rewritten to use the new `{"center_class", "scale_class", "maturity_class"}` shape (fixture input) or assert approximate round-trip (assertions on exported shape).

- [ ] **Step 2: Write/update the failing tests**

Add near the existing acclimation/rhythm/drift round-trip tests in `tests/unit/host/test_checkpoint.py`:

```python
def test_acclimation_checkpoint_uses_consolidated_classes_not_exact_stats():
    acclimation = HostAcclimation(min_samples=1)
    for value in [10.0, 10.2, 9.8, 10.1, 9.9]:
        acclimation.observe([_reading("cpu", value)])  # use this file's existing reading-fixture helper

    payload = export_checkpoint(acclimation=acclimation)
    entry = payload["acclimation"]["cpu"]
    assert set(entry) == {"center_class", "scale_class", "maturity_class"}
    assert "mean" not in entry
    assert "variance" not in entry
    assert "count" not in entry

    restored_acclimation, _, _ = import_checkpoint(payload)
    restored_baseline = restored_acclimation.baseline("cpu")
    assert restored_baseline.mean == pytest.approx(10.0, rel=0.2)
    assert restored_baseline.count <= 8
```

Use whichever existing helper this test file already has for constructing a `SensorReading` fixture (check the top of the file — do not invent a new one if `_reading(...)` or similar already exists there).

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/host/test_checkpoint.py -v`
Expected: FAIL — the new test fails because the payload still has `"count"/"mean"/"variance"`, and/or the pre-existing tests you updated in Step 1 now fail because you changed their expectations ahead of the implementation

- [ ] **Step 4: Modify `src/symbiont/host/checkpoint.py`**

Add the import:

```python
from .consolidated_baseline import ConsolidatedBaselineSeed, consolidate_baseline, seed_capability_baseline
```

In `export_checkpoint`, change the three blocks:

```python
    if acclimation is not None:
        payload["acclimation"] = {
            capability_id: {"count": baseline.count, "mean": baseline.mean, "variance": baseline.variance}
            for capability_id in acclimation.acclimated_capabilities
            if (baseline := acclimation.baseline(capability_id)) is not None
        }
```

to:

```python
    if acclimation is not None:
        payload["acclimation"] = {
            capability_id: _seed_payload(consolidate_baseline(baseline))
            for capability_id in acclimation.acclimated_capabilities
            if (baseline := acclimation.baseline(capability_id)) is not None
        }
```

and equivalently for `rhythms` (keep `"percept_name"`/`"time_bucket"`, replace only the three stat fields) and `drift` (keep the `name` key, replace only the three stat fields). Add the small helper near the top of the file, after `_capability_fingerprint`:

```python
def _seed_payload(seed: ConsolidatedBaselineSeed) -> dict[str, int]:
    return {"center_class": seed.center_class, "scale_class": seed.scale_class, "maturity_class": seed.maturity_class}


def _seed_from_payload(entry: dict[str, Any]) -> ConsolidatedBaselineSeed:
    return ConsolidatedBaselineSeed(
        center_class=int(entry["center_class"]),
        scale_class=int(entry["scale_class"]),
        maturity_class=int(entry["maturity_class"]),
    )
```

In `import_checkpoint`, change:

```python
        acclimation = acclimation if acclimation is not None else HostAcclimation()
        for capability_id, stats in payload.get("acclimation", {}).items():
            acclimation.restore(
                capability_id,
                CapabilityBaseline(count=stats["count"], mean=stats["mean"], variance=stats["variance"]),
            )

        rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel()
        for entry in payload.get("rhythms", []):
            rhythm_model.restore(
                entry["percept_name"],
                TimeBucket(entry["time_bucket"]),
                CapabilityBaseline(count=entry["count"], mean=entry["mean"], variance=entry["variance"]),
            )

        drift_baselines: dict[str, DriftAwareBaseline] = {}
        for name, stats in payload.get("drift", {}).items():
            baseline = DriftAwareBaseline()
            baseline.restore(count=stats["count"], mean=stats["mean"], variance=stats["variance"])
            drift_baselines[name] = baseline
```

to:

```python
        acclimation = acclimation if acclimation is not None else HostAcclimation()
        for capability_id, stats in payload.get("acclimation", {}).items():
            acclimation.restore(capability_id, seed_capability_baseline(_seed_from_payload(stats)))

        rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel()
        for entry in payload.get("rhythms", []):
            rhythm_model.restore(
                entry["percept_name"],
                TimeBucket(entry["time_bucket"]),
                seed_capability_baseline(_seed_from_payload(entry)),
            )

        drift_baselines: dict[str, DriftAwareBaseline] = {}
        for name, stats in payload.get("drift", {}).items():
            seeded = seed_capability_baseline(_seed_from_payload(stats))
            baseline = DriftAwareBaseline()
            baseline.restore(count=seeded.count, mean=seeded.mean, variance=seeded.variance)
            drift_baselines[name] = baseline
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/host/test_checkpoint.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS (the v4->v5 migration test in `tests/unit/core/test_resident_continuity.py` and `tests/unit/host/test_checkpoint.py` construct v4-shaped fixture payloads that never reach `import_checkpoint`'s acclimation/rhythm/drift reading in a way that depends on the old key shape -- if any migration test does fail, it means a fixture payload hand-built the old `{"count","mean","variance"}` shape as if it were the CURRENT schema's acclimation entry rather than a v4 migration input; fix the fixture, not this task's production code, since migration inputs are versioned snapshots of the past, not required to match today's shape post-migration for keys this task didn't touch)

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/host/checkpoint.py tests/unit/host/test_checkpoint.py
git commit -m "$(cat <<'COMMIT'
feat(host): persist acclimation/rhythm/drift as consolidated classes, not exact stats

export_checkpoint/import_checkpoint now read and write
center_class/scale_class/maturity_class for every HostAcclimation,
RhythmModel and DriftAwareBaseline entry instead of exact
count/mean/variance -- closing the differencing weakness this
module's own docstring has documented since v0.37. The three models
themselves are unchanged; only what the checkpoint boundary persists
changes, since seed_capability_baseline() already returns a real
CapabilityBaseline their existing .restore() methods accept.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

### Task 3: SelfModel RecencyClass

**Files:**
- Modify: `src/symbiont/core/selfmodel.py`
- Modify: `src/symbiont/core/runtime.py`
- Test: `tests/unit/core/test_selfmodel.py` (check the exact filename first with `ls tests/unit/core/ | grep -i self`)

**Interfaces:**
- Produces: `RecencyClass` `IntEnum` (`CURRENT=0, SHORT_IDLE=1, IDLE=2, LONG_IDLE=3, DORMANT=4`); `SelfModel.export(self, *, current_tick: int) -> dict[str, Any]` (signature change: gains `current_tick`, payload's per-sense `"last_observed_tick"` key becomes `"recency_class"`); `SelfModel.restore(cls, payload, *, allowed_sense_ids, current_tick: int) -> SelfModel` (signature change: gains `current_tick`, seeds `last_observed_tick` from a fixed per-class representative idle-tick table, never a per-organism-derived exact offset).

- [ ] **Step 1: Find and read the current self-model test file**

Run: `ls tests/unit/core/ | grep -i self`, then read it in full before editing.

- [ ] **Step 2: Write/update the failing tests**

Add:

```python
from symbiont.core.selfmodel import RecencyClass


def test_export_uses_recency_class_not_exact_last_observed_tick():
    model = SelfModel()
    for _ in range(MIN_SELF_MODEL_ATTEMPTS):
        model.observe(outcome=_success_outcome("cpu"), tick=100)  # use this file's existing outcome fixture helper
    payload = model.export(current_tick=105)
    entry = payload["cpu"]
    assert "last_observed_tick" not in entry
    assert entry["recency_class"] == RecencyClass.CURRENT.value  # observed 5 ticks ago, well within grace


def test_restore_seeds_a_representative_idle_offset_never_the_real_one():
    model = SelfModel()
    for _ in range(MIN_SELF_MODEL_ATTEMPTS):
        model.observe(outcome=_success_outcome("cpu"), tick=100)
    payload = model.export(current_tick=500)  # 400 ticks idle -> DORMANT
    assert payload["cpu"]["recency_class"] == RecencyClass.DORMANT.value

    restored = SelfModel.restore(payload, allowed_sense_ids={"cpu"}, current_tick=1000)
    # The restored last_observed_tick must come from the fixed DORMANT
    # representative offset applied to the NEW current_tick (1000), not the
    # real original offset (400 ticks before tick 500).
    state = restored._states["cpu"]
    assert 1000 - state.last_observed_tick != 400
```

Use whichever existing helper this test file already has for constructing a successful sampling `outcome` (check the top of the file for the real fixture name — do not invent `_success_outcome` if a differently-named helper already exists).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_selfmodel.py -v` (or whatever the real filename is)
Expected: FAIL — `ImportError: cannot import name 'RecencyClass'`, and/or `TypeError: export() missing 1 required keyword-only argument: 'current_tick'`

- [ ] **Step 4: Implement in `src/symbiont/core/selfmodel.py`**

Add near the top (after the existing imports):

```python
from enum import IntEnum


class RecencyClass(IntEnum):
    CURRENT = 0
    SHORT_IDLE = 1
    IDLE = 2
    LONG_IDLE = 3
    DORMANT = 4


_RECENCY_REPRESENTATIVE_IDLE_TICKS = {
    RecencyClass.CURRENT: 0,
    RecencyClass.SHORT_IDLE: 10,
    RecencyClass.IDLE: 40,
    RecencyClass.LONG_IDLE: 120,
    RecencyClass.DORMANT: 400,
}
_RECENCY_THRESHOLDS = (
    (10, RecencyClass.CURRENT),
    (40, RecencyClass.SHORT_IDLE),
    (120, RecencyClass.IDLE),
    (400, RecencyClass.LONG_IDLE),
)


def _recency_class(idle_ticks: int) -> RecencyClass:
    for threshold, recency in _RECENCY_THRESHOLDS:
        if idle_ticks < threshold:
            return recency
    return RecencyClass.DORMANT
```

Change `export`:

```python
    def export(self, *, current_tick: int) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for sense_id, state in self._states.items():
            if not state.established:
                continue
            idle_ticks = max(0, current_tick - state.last_observed_tick)
            payload[sense_id] = {
                "cost_class": _quantize_cost(state.cost_ewma_s),
                "health_class": _quantize(state.health_ewma, _HEALTH_CLASSES),
                "confidence_class": _quantize(state.confidence_ewma, _CONFIDENCE_CLASSES),
                "maturity_class": _quantize(_maturity(state.successes), _MATURITY_CLASSES),
                "recency_class": _recency_class(idle_ticks).value,
            }
        return payload
```

Change `restore`'s signature and the `last_observed_tick`/`recency_class` handling:

```python
    @classmethod
    def restore(
        cls, payload: dict[str, Any] | None, *, allowed_sense_ids: Collection[str], current_tick: int
    ) -> "SelfModel":
        model = cls()
        if not payload:
            return model
        if not isinstance(payload, dict):
            raise ValueError("self_model payload must be a JSON object")
        if len(payload) > cls.MAX_SENSES:
            raise ValueError(f"self_model payload exceeds MAX_SENSES ({cls.MAX_SENSES})")
        allowed = set(allowed_sense_ids)
        for sense_id, entry in payload.items():
            if sense_id not in allowed:
                continue
            if not isinstance(entry, dict):
                raise ValueError(f"self_model entry for {sense_id!r} must be a JSON object")
            cost_class = entry["cost_class"]
            health_class = entry["health_class"]
            confidence_class = entry["confidence_class"]
            maturity_class = entry["maturity_class"]
            recency_class_raw = entry["recency_class"]
            _require_class_range(cost_class, _COST_CLASSES, "cost_class")
            _require_class_range(health_class, _HEALTH_CLASSES, "health_class")
            _require_class_range(confidence_class, _CONFIDENCE_CLASSES, "confidence_class")
            _require_class_range(maturity_class, _MATURITY_CLASSES, "maturity_class")
            _require_class_range(recency_class_raw, len(RecencyClass), "recency_class")
            representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_class_raw)]
            last_observed_tick = max(0, current_tick - representative_idle)
            maturity = maturity_class / (_MATURITY_CLASSES - 1)
            successes = int(round(math.expm1(maturity * math.log1p(MIN_SELF_MODEL_ATTEMPTS))))
            state = SenseSelfState(
                cost_ewma_s=_dequantize_cost(cost_class),
                health_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                quality_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                confidence_ewma=_dequantize(confidence_class, _CONFIDENCE_CLASSES),
                attempts=max(successes, MIN_SELF_MODEL_ATTEMPTS),
                successes=successes,
                last_observed_tick=last_observed_tick,
            )
            model._states[sense_id] = state
        return model
```

- [ ] **Step 5: Update the two call sites in `src/symbiont/core/runtime.py`**

Change `payload["self_model"] = self._self_model.export()` to:

```python
        payload["self_model"] = self._self_model.export(current_tick=self._tick_count)
```

Change the `SelfModel.restore(...)` call in `from_checkpoint` to pass `current_tick=normalized.get("saved_at_tick") or 0`:

```python
        self_model = SelfModel.restore(
            normalized.get("self_model"), allowed_sense_ids=allowed_sense_ids, current_tick=normalized.get("saved_at_tick") or 0
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_selfmodel.py -v` (real filename from Step 1)
Expected: PASS

- [ ] **Step 7: Run the full suite**

Run: `pytest -q`
Expected: PASS (any other test calling `SelfModel.export()`/`.restore()` without the new required keyword argument will fail loudly with a clear `TypeError` -- fix each call site the same way as Step 5, don't add a default that would silently let the old exact-tick behavior sneak back in for a caller that forgets to pass it)

- [ ] **Step 8: Commit**

```bash
git add src/symbiont/core/selfmodel.py src/symbiont/core/runtime.py tests/unit/core/test_selfmodel.py
git commit -m "$(cat <<'COMMIT'
feat(core): replace SelfModel's exact last_observed_tick with RecencyClass (design §17)

export()/restore() gain a required current_tick/saved_at_tick
parameter and persist a 5-level RecencyClass instead of an exact tick.
Restore seeds last_observed_tick from a fixed per-class representative
idle-tick table, never a reconstructed per-organism exact offset --
closing the last place SelfModel's otherwise-already-quantized
checkpoint expanded back into fabricated precise chronology.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

## Self-Review Notes

**Spec coverage:** §10.2/§16 acclimation/rhythm/drift consolidated projection + seeded restore -> Tasks 1-2. §17 self-model recency class -> Task 3.

**Explicitly deferred, disclosed in Global Constraints, not silently dropped:** `AdaptiveSenseModel`'s `SenseState.mean`/`.m2` and `PairAccumulator`'s correlation moments still persist exactly. The same codec from Task 1 (for `SenseState`, whose mean/variance are the same shape as `CapabilityBaseline`) and a simpler bounded quantization (for `PairAccumulator`'s already-`[-1,1]`-bounded correlation) would close this the same way -- left for a follow-up PR so this one stays reviewable at its current size, matching the P8/P9-deferred-to-PR5 pattern already used in PR1.

**Type consistency check:** `ConsolidatedBaselineSeed` (Task 1) is consumed identically by all three call sites in Task 2 (`acclimation`, `rhythms`, `drift`) via the same `_seed_payload`/`_seed_from_payload` helpers -- no per-subsystem variant shape. `SelfModel.export`/`.restore`'s new `current_tick` parameter name matches exactly between the class definition (Task 3) and both call sites in `runtime.py` (Task 3, Step 5).
