# Biological Memory Consolidation — PR1 (Memory Kernel & Executable Invariants) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone memory-consolidation kernel (`src/symbiont/core/consolidation.py`) — types, kernel limits, salience scoring, and the fast/slow consolidation decision — with P1, P2, P6, P7 and P10 (design §21) passing as real tests against it, with zero wiring into `OrganismRuntime`, `CognitiveBridge`, host models, or the checkpoint schema.

**Architecture:** One new module owns everything: closed `MemoryKind` enum, a bounded `ConsolidationSignal` (novelty/surprise/attention/reliability/coherence, each `[0,1]`) with a kernel-owned weighted `score()`, a `ConsolidationCandidate` working-buffer entry (RAM-only, epoch-gated independence), a `SalientEventTrace` durable record (coarse classes only), and `MemoryConsolidator` orchestrating both the fast path (one-shot salient trace commit) and the slow path (epoch-spaced statistical support). `MemoryConsolidator.export_checkpoint()` exports **only committed/durable state** — pending candidates never appear in it, which is what makes P1/P2 true by construction rather than by convention.

**Tech Stack:** Python 3.11+ stdlib only (`enum.StrEnum`, `dataclasses`, `collections.deque`) — matches the rest of `src/symbiont/cognition/`.

**Spec:** `docs/design/biological-memory-consolidation.md` (sections referenced below: §5-§10, §19, §21 P1/P2/P6/P7/P10, §23 PR1)

## Global Constraints

- No raw observation, exact z-score, exact loss, exact tick, or provider/host identity may ever appear in `MemoryConsolidator.export_checkpoint()`'s output (design §2, §9.5 point 8).
- `ConsolidationSignal` fields are always finite and within `[0, 1]` (design §6).
- Consolidation score weights are fixed kernel constants, never genome-mutable or organism-learnable in this release (design §7, §19).
- `FAST_CONSOLIDATION_THRESHOLD = 0.80`, `FAST_MIN_RELIABILITY = 0.60`, `SLOW_SUPPORT_EPOCHS = 4`, `CONSOLIDATION_EPOCH_TICKS = 8` (design §7) — these become `KernelLimits` fields, not module constants, so they are validated the same way every other kernel limit is.
- At most one slow-support increment per `(memory_key, epoch_id)` pair; `epoch_id = tick // consolidation_epoch_ticks` (design §8).
- Structural memory (`MemoryKind.STRUCTURAL`) never takes the fast path regardless of score — only `MemoryKind.SALIENT_EVENT` can commit a `SalientEventTrace` in one shot (design §5.3, §5.2; P9 is verified end-to-end in PR5, but the gate must exist in PR1's decision logic already so PR5 has something real to test).
- `SalientEventTrace` caps at `KernelLimits.max_salient_event_traces` (default 64); eviction is deterministic — least-recently-reinforced trace, ties broken by `pattern_id` ascending (design §10.5).
- `ConsolidationCandidate` store caps at `KernelLimits.max_consolidation_candidates` (default 256); same eviction rule applies when a brand-new key arrives at capacity.
- This PR does **not** touch `OrganismRuntime`, `CognitiveBridge`, any host model, `CHECKPOINT_SCHEMA_VERSION`, or the genome schema.

---

### Task 1: Add new KernelLimits fields

**Files:**
- Modify: `src/symbiont/cognition/limits.py`
- Test: `tests/unit/cognition/test_limits.py` (create if it doesn't already exist — check first with `ls tests/unit/cognition/`)

**Interfaces:**
- Produces: `KernelLimits` gains eight new fields, all with the exact defaults below, consumed by Task 2 onward: `max_consolidation_candidates: int = 256`, `max_salient_event_traces: int = 64`, `consolidation_epoch_ticks: int = 8`, `slow_support_epochs: int = 4`, `fast_consolidation_threshold: float = 0.80`, `fast_min_reliability: float = 0.60`, `max_incoming_consolidated_weight_norm: float = 8.0`, `reacclimation_ticks: int = 32`.

- [ ] **Step 1: Check whether a limits test file already exists**

Run: `ls tests/unit/cognition/ 2>/dev/null | grep -i limit`

If a file exists, read it first and add to it in the same style. If not, create `tests/unit/cognition/test_limits.py`.

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits


def test_default_limits_include_memory_consolidation_fields():
    limits = KernelLimits()
    assert limits.max_consolidation_candidates == 256
    assert limits.max_salient_event_traces == 64
    assert limits.consolidation_epoch_ticks == 8
    assert limits.slow_support_epochs == 4
    assert limits.fast_consolidation_threshold == pytest.approx(0.80)
    assert limits.fast_min_reliability == pytest.approx(0.60)
    assert limits.max_incoming_consolidated_weight_norm == pytest.approx(8.0)
    assert limits.reacclimation_ticks == 32


def test_zero_or_negative_new_limits_are_rejected():
    with pytest.raises(ValueError):
        KernelLimits(max_consolidation_candidates=0)
    with pytest.raises(ValueError):
        KernelLimits(fast_consolidation_threshold=0.0)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/cognition/test_limits.py -v`
Expected: FAIL with `TypeError: KernelLimits.__init__() got an unexpected keyword argument 'max_consolidation_candidates'`

- [ ] **Step 4: Add the fields**

In `src/symbiont/cognition/limits.py`, add the eight fields to the `KernelLimits` dataclass body, after `max_plastic_checkpoint_bytes`:

```python
    max_plastic_checkpoint_bytes: int = 2 * 1024 * 1024
    max_consolidation_candidates: int = 256
    max_salient_event_traces: int = 64
    consolidation_epoch_ticks: int = 8
    slow_support_epochs: int = 4
    fast_consolidation_threshold: float = 0.80
    fast_min_reliability: float = 0.60
    max_incoming_consolidated_weight_norm: float = 8.0
    reacclimation_ticks: int = 32
```

The existing `__post_init__` already rejects any non-positive field via `fields(self)` iteration — no changes needed there, since all eight new fields are meant to be strictly positive (including the two float thresholds, which must never be exactly `0.0`).

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/cognition/test_limits.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS (same count as before plus the two new tests — this is a pure additive change, nothing else references these fields yet)

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/cognition/limits.py tests/unit/cognition/test_limits.py
git commit -m "feat(cognition): add memory consolidation kernel limits"
```

---

### Task 2: ConsolidationSignal, MemoryKind, and the salience score

**Files:**
- Create: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: nothing yet (pure types).
- Produces: `MemoryKind(StrEnum)` with values `STATISTICAL = "statistical"`, `SALIENT_EVENT = "salient_event"`, `STRUCTURAL = "structural"`; `MemoryError(Exception)`; `ConsolidationSignal` frozen dataclass with `novelty: float`, `surprise: float`, `attention: float`, `reliability: float`, `coherence: float`, validated finite-and-`[0,1]` in `__post_init__`, and a `.score() -> float` method. These are consumed by every later task in this plan.

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import math

import pytest

from symbiont.core.consolidation import ConsolidationSignal, MemoryError, MemoryKind


def test_memory_kind_is_closed_and_has_exactly_three_values():
    assert {kind.value for kind in MemoryKind} == {"statistical", "salient_event", "structural"}


def test_consolidation_signal_rejects_out_of_range_fields():
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=1.5, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=0.0, surprise=-0.1, attention=0.0, reliability=0.0, coherence=0.0)
    with pytest.raises(MemoryError):
        ConsolidationSignal(novelty=math.nan, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)


def test_consolidation_signal_score_matches_the_kernel_weighted_sum():
    signal = ConsolidationSignal(novelty=1.0, surprise=1.0, attention=1.0, reliability=1.0, coherence=1.0)
    assert signal.score() == pytest.approx(1.0)

    signal = ConsolidationSignal(novelty=0.0, surprise=1.0, attention=0.0, reliability=0.0, coherence=0.0)
    assert signal.score() == pytest.approx(0.30)  # only the surprise term contributes

    signal = ConsolidationSignal(novelty=0.0, surprise=0.0, attention=0.0, reliability=0.0, coherence=0.0)
    assert signal.score() == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'symbiont.core.consolidation'`

- [ ] **Step 3: Create `src/symbiont/core/consolidation.py`**

```python
"""Biological memory consolidation kernel (design: docs/design/biological-memory-consolidation.md).

Changes the persistence model from "serialize learned state" to "persist
consolidated memory": labile working state (RAM only) feeds a bounded
consolidation buffer, which commits into durable, coarse, checkpointable
memory only when independently supported or exceptionally salient. No raw
observation, exact tick, or host/provider identity is ever durable here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class MemoryError(Exception):
    """Raised for any invalid memory-consolidation input or state."""


class MemoryKind(StrEnum):
    """Closed set of memory kinds -- each has its own consolidation rule
    (design §5). Never extended by a genome or by learned behavior."""

    STATISTICAL = "statistical"
    SALIENT_EVENT = "salient_event"
    STRUCTURAL = "structural"


_SIGNAL_FIELDS = ("novelty", "surprise", "attention", "reliability", "coherence")

# Kernel-owned, not organism-learnable in this release (design §7, §19).
_NOVELTY_WEIGHT = 0.20
_SURPRISE_WEIGHT = 0.30
_ATTENTION_WEIGHT = 0.20
_RELIABILITY_WEIGHT = 0.20
_COHERENCE_WEIGHT = 0.10


@dataclass(slots=True, frozen=True)
class ConsolidationSignal:
    """Every field is derived only from signals the organism already
    produces (drift kind, prediction error, attention selection, self-model
    health/availability, epoch-spaced support) -- never an external label
    (design §6)."""

    novelty: float
    surprise: float
    attention: float
    reliability: float
    coherence: float

    def __post_init__(self) -> None:
        for name in _SIGNAL_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise MemoryError(f"{name} must be a number")
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise MemoryError(f"{name} must be finite and within [0, 1]")

    def score(self) -> float:
        return (
            _NOVELTY_WEIGHT * self.novelty
            + _SURPRISE_WEIGHT * self.surprise
            + _ATTENTION_WEIGHT * self.attention
            + _RELIABILITY_WEIGHT * self.reliability
            + _COHERENCE_WEIGHT * self.coherence
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add MemoryKind and bounded ConsolidationSignal with kernel-weighted score"
```

---

### Task 3: novelty_from_drift_kind and surprise_from_loss

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: `DriftKind` from `src/symbiont/host/drift.py` (values: `NONE`, `ISOLATED`, `GRADUAL`, `CREEP`, `REGIME_SHIFT`).
- Produces: `novelty_from_drift_kind(kind: DriftKind | None) -> float` and `surprise_from_loss(loss: float | None) -> float`, both pure kernel-mapping functions (design §6.1, §6.2). Consumed by later tasks' tests and eventually by PR3's real wiring (not in this PR).

- [ ] **Step 1: Write the failing tests**

```python
from symbiont.core.consolidation import novelty_from_drift_kind, surprise_from_loss
from symbiont.host.drift import DriftKind


def test_novelty_from_drift_kind_matches_the_kernel_mapping():
    assert novelty_from_drift_kind(DriftKind.NONE) == pytest.approx(0.00)
    assert novelty_from_drift_kind(DriftKind.GRADUAL) == pytest.approx(0.35)
    assert novelty_from_drift_kind(DriftKind.CREEP) == pytest.approx(0.50)
    assert novelty_from_drift_kind(DriftKind.ISOLATED) == pytest.approx(0.70)
    assert novelty_from_drift_kind(DriftKind.REGIME_SHIFT) == pytest.approx(0.90)
    assert novelty_from_drift_kind(None) == pytest.approx(0.0)


def test_surprise_from_loss_is_bounded_and_saturating():
    assert surprise_from_loss(None) == pytest.approx(0.0)  # no predictor -> zero, never fabricated
    assert surprise_from_loss(0.0) == pytest.approx(0.0)
    assert surprise_from_loss(0.5) == pytest.approx(0.5)
    assert surprise_from_loss(1.0) == pytest.approx(1.0)
    assert surprise_from_loss(50.0) == pytest.approx(1.0)  # saturates, never exceeds 1.0
    assert surprise_from_loss(float("nan")) == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `ImportError: cannot import name 'novelty_from_drift_kind'`

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Add near the top, after the imports (add `from .host_types import DriftKind` — no: use the real import path `from ..host.drift import DriftKind`):

```python
from ..host.drift import DriftKind
```

Add after `ConsolidationSignal`:

```python
_NOVELTY_BY_DRIFT_KIND: dict[DriftKind, float] = {
    DriftKind.NONE: 0.00,
    DriftKind.GRADUAL: 0.35,
    DriftKind.CREEP: 0.50,
    DriftKind.ISOLATED: 0.70,
    DriftKind.REGIME_SHIFT: 0.90,
}


def novelty_from_drift_kind(kind: DriftKind | None) -> float:
    """Kernel mapping (design §6.1), not learned from any host label."""
    if kind is None:
        return 0.0
    return _NOVELTY_BY_DRIFT_KIND.get(kind, 0.0)


_SURPRISE_SATURATION_LOSS = 1.0  # loss at/above this saturates surprise to 1.0


def surprise_from_loss(loss: float | None) -> float:
    """No predictor means surprise contributes zero rather than being
    fabricated (design §6.2). Exact loss is never itself persisted --
    only this bounded transform ever reaches a ConsolidationSignal."""
    if loss is None or not isinstance(loss, (int, float)) or isinstance(loss, bool):
        return 0.0
    if not math.isfinite(loss) or loss < 0:
        return 0.0
    return max(0.0, min(1.0, loss / _SURPRISE_SATURATION_LOSS))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add kernel-owned novelty/surprise signal mappings"
```

---

### Task 4: ConsolidationCandidate and maturity classes

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: `ConsolidationSignal` (Task 2).
- Produces: `ConsolidationCandidate` mutable dataclass (`key: str`, `kind: MemoryKind`, `support_epochs: int = 0`, `last_support_epoch: int | None = None`, `strength: float = 0.0`, `latest_signal: ConsolidationSignal | None = None`); `maturity_class_from_support_epochs(support_epochs: int) -> int` returning one of the 8 classes from design §10.1 (`0` trace .. `7` saturated). Consumed by `MemoryConsolidator` in Task 5.

- [ ] **Step 1: Write the failing tests**

```python
from symbiont.core.consolidation import ConsolidationCandidate, MemoryKind, maturity_class_from_support_epochs


def test_consolidation_candidate_defaults():
    candidate = ConsolidationCandidate(key="sense_a", kind=MemoryKind.STATISTICAL)
    assert candidate.support_epochs == 0
    assert candidate.last_support_epoch is None
    assert candidate.strength == 0.0
    assert candidate.latest_signal is None


def test_maturity_class_is_monotone_and_coarse():
    assert maturity_class_from_support_epochs(0) == 0    # trace
    assert maturity_class_from_support_epochs(1) == 1    # emerging
    assert maturity_class_from_support_epochs(3) == 2    # young
    assert maturity_class_from_support_epochs(4) == 3    # established (matches SLOW_SUPPORT_EPOCHS default)
    assert maturity_class_from_support_epochs(10) == 4   # mature
    assert maturity_class_from_support_epochs(20) == 5   # stable
    assert maturity_class_from_support_epochs(40) == 6   # entrenched
    assert maturity_class_from_support_epochs(1000) == 7  # saturated, never exceeds 7

    # monotone: more support never produces a lower class
    classes = [maturity_class_from_support_epochs(n) for n in range(0, 200, 3)]
    assert classes == sorted(classes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `ImportError: cannot import name 'ConsolidationCandidate'`

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Add `from dataclasses import dataclass, field` (update the existing `from dataclasses import dataclass` import line to also bring in `field`), then add after the `surprise_from_loss` function:

```python
_MATURITY_THRESHOLDS = (0, 1, 2, 4, 8, 16, 32, 64)  # support_epochs lower bound per class


def maturity_class_from_support_epochs(support_epochs: int) -> int:
    """Coarse, monotone class (design §10.1) -- no exact support_epochs
    count can be reconstructed from it. Eight classes: 0 trace .. 7
    saturated."""
    if support_epochs < 0:
        support_epochs = 0
    matured_class = 0
    for index, threshold in enumerate(_MATURITY_THRESHOLDS):
        if support_epochs >= threshold:
            matured_class = index
    return matured_class


@dataclass(slots=True)
class ConsolidationCandidate:
    """RAM-only working buffer entry (design §9.3). No raw observation is
    stored here -- only bounded epoch/strength bookkeeping."""

    key: str
    kind: MemoryKind
    support_epochs: int = 0
    last_support_epoch: int | None = None
    strength: float = 0.0
    latest_signal: ConsolidationSignal | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add ConsolidationCandidate and maturity class mapping"
```

---

### Task 5: SalientEventTrace

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `SalientEventTrace` frozen dataclass (`pattern_id: str`, `novelty_class: int`, `surprise_class: int`, `reliability_class: int`, `context_class: int`, `recurrence_class: int`), each class field validated to `0..15` inclusive (design §10.5 specifies `0..15` for novelty/surprise/reliability; this plan applies the same 16-class bound to `context_class`/`recurrence_class` for consistency, since the design leaves their exact bit-width unspecified beyond "coarse"); `quantize_unit(value: float, num_classes: int) -> int` mapping a `[0,1]` float to a class id. Consumed by `MemoryConsolidator` in Task 6.

- [ ] **Step 1: Write the failing tests**

```python
from symbiont.core.consolidation import SalientEventTrace, quantize_unit


def test_quantize_unit_is_bounded_and_monotone():
    assert quantize_unit(0.0, 16) == 0
    assert quantize_unit(1.0, 16) == 15
    assert quantize_unit(0.5, 16) == 8
    assert quantize_unit(-1.0, 16) == 0   # clipped
    assert quantize_unit(2.0, 16) == 15   # clipped


def test_salient_event_trace_rejects_out_of_range_classes():
    SalientEventTrace(
        pattern_id="sense_a", novelty_class=15, surprise_class=15,
        reliability_class=15, context_class=0, recurrence_class=0,
    )  # must not raise
    with pytest.raises(MemoryError):
        SalientEventTrace(
            pattern_id="sense_a", novelty_class=16, surprise_class=0,
            reliability_class=0, context_class=0, recurrence_class=0,
        )
    with pytest.raises(MemoryError):
        SalientEventTrace(
            pattern_id="sense_a", novelty_class=0, surprise_class=-1,
            reliability_class=0, context_class=0, recurrence_class=0,
        )
```

Add `from symbiont.core.consolidation import MemoryError` to the existing import line at the top of `tests/unit/core/test_consolidation.py` if not already imported there (it is, from Task 2 — just confirm before adding a duplicate import).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `ImportError: cannot import name 'SalientEventTrace'`

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Add after `ConsolidationCandidate`:

```python
_TRACE_CLASS_COUNT = 16


def quantize_unit(value: float, num_classes: int) -> int:
    """Maps a [0, 1] float to a class id in [0, num_classes - 1], clipping
    out-of-range input rather than raising -- this is a display/durable
    transform applied to already-validated signal values, not a boundary
    check in its own right."""
    clipped = max(0.0, min(1.0, value))
    return round(clipped * (num_classes - 1))


def _require_trace_class(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MemoryError(f"{field_name} must be an integer class id")
    if not 0 <= value < _TRACE_CLASS_COUNT:
        raise MemoryError(f"{field_name} must be within [0, {_TRACE_CLASS_COUNT - 1}]")


@dataclass(slots=True, frozen=True)
class SalientEventTrace:
    """Bounded durable record of one exceptional transition (design §10.5).
    No raw reading, exact z-score, exact prediction error, timestamp or
    provider identity -- only coarse categorical classes and a safe id."""

    pattern_id: str
    novelty_class: int
    surprise_class: int
    reliability_class: int
    context_class: int
    recurrence_class: int

    def __post_init__(self) -> None:
        if not isinstance(self.pattern_id, str) or not self.pattern_id:
            raise MemoryError("pattern_id must be a non-empty string")
        for field_name in ("novelty_class", "surprise_class", "reliability_class", "context_class", "recurrence_class"):
            _require_trace_class(getattr(self, field_name), field_name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add bounded SalientEventTrace and unit quantization"
```

---

### Task 6: MemoryConsolidator — slow path, epoch independence (P6, P7)

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: `KernelLimits` (Task 1), `ConsolidationCandidate`/`maturity_class_from_support_epochs` (Task 4), `ConsolidationSignal` (Task 2).
- Produces: `ConsolidationOutcome` frozen dataclass (`key: str`, `kind: MemoryKind`, `path: str` — `"fast"` or `"slow"`, `committed: bool`, `support_epochs: int`, `score: float`); `MemoryConsolidator` class with `__init__(self, *, kernel_limits: KernelLimits)` and `.observe(self, key: str, kind: MemoryKind, signal: ConsolidationSignal, *, tick: int) -> ConsolidationOutcome`, implementing only the slow path in this task (fast path added in Task 7). Consumed by Task 7 (fast path) and Task 8 (checkpoint export).

- [ ] **Step 1: Write the failing tests**

```python
from symbiont.core.consolidation import ConsolidationOutcome, MemoryConsolidator
from symbiont.cognition.limits import KernelLimits


def _weak_signal() -> ConsolidationSignal:
    # deliberately far below the fast-path threshold
    return ConsolidationSignal(novelty=0.1, surprise=0.1, attention=0.0, reliability=0.5, coherence=0.0)


def test_burst_repetition_is_not_independent_support_p6():
    """P6: many identical observations in one consolidation epoch produce
    at most one slow-support increment."""
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    for _ in range(100):
        outcome = consolidator.observe("sense_a", MemoryKind.STATISTICAL, _weak_signal(), tick=3)
    assert outcome.support_epochs == 1
    assert outcome.committed is False  # slow_support_epochs default is 4


def test_spaced_recurrence_can_consolidate_p7():
    """P7: the same coherent pattern across enough distinct epochs
    eventually becomes durable even if no single event crosses the fast
    threshold."""
    limits = KernelLimits()
    consolidator = MemoryConsolidator(kernel_limits=limits)
    last_outcome = None
    for epoch in range(limits.slow_support_epochs):
        tick = epoch * limits.consolidation_epoch_ticks + 1
        last_outcome = consolidator.observe("sense_a", MemoryKind.STATISTICAL, _weak_signal(), tick=tick)
    assert last_outcome.support_epochs == limits.slow_support_epochs
    assert last_outcome.committed is True
    assert last_outcome.path == "slow"


def test_structural_kind_never_takes_the_fast_path_regardless_of_epoch_count():
    limits = KernelLimits()
    consolidator = MemoryConsolidator(kernel_limits=limits)
    outcome = None
    for epoch in range(limits.slow_support_epochs):
        tick = epoch * limits.consolidation_epoch_ticks + 1
        outcome = consolidator.observe("edge_a->b", MemoryKind.STRUCTURAL, _weak_signal(), tick=tick)
    assert outcome.path == "slow"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `ImportError: cannot import name 'ConsolidationOutcome'`

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Add after `SalientEventTrace`:

```python
@dataclass(slots=True, frozen=True)
class ConsolidationOutcome:
    key: str
    kind: MemoryKind
    path: str  # "fast" or "slow"
    committed: bool
    support_epochs: int
    score: float


class MemoryConsolidator:
    """Orchestrates fast/slow consolidation (design §7, §9.5). Owns the
    RAM-only candidate buffer and the durable salient-trace/statistical
    projections. export_checkpoint() below (Task 8) exports only what has
    actually committed -- pending candidates never leave this class."""

    def __init__(self, *, kernel_limits: KernelLimits) -> None:
        self._kernel_limits = kernel_limits
        self._candidates: dict[str, ConsolidationCandidate] = {}
        self._committed_statistical: dict[str, int] = {}  # key -> maturity_class

    def observe(
        self, key: str, kind: MemoryKind, signal: ConsolidationSignal, *, tick: int
    ) -> ConsolidationOutcome:
        epoch_id = tick // self._kernel_limits.consolidation_epoch_ticks
        score = signal.score()

        candidate = self._candidates.get(key)
        if candidate is None:
            if len(self._candidates) >= self._kernel_limits.max_consolidation_candidates:
                self._evict_one_candidate()
            candidate = ConsolidationCandidate(key=key, kind=kind)
            self._candidates[key] = candidate

        if candidate.last_support_epoch != epoch_id:
            candidate.support_epochs += 1
            candidate.last_support_epoch = epoch_id
        candidate.strength = score
        candidate.latest_signal = signal

        committed = candidate.support_epochs >= self._kernel_limits.slow_support_epochs
        if committed and kind is MemoryKind.STATISTICAL:
            self._committed_statistical[key] = maturity_class_from_support_epochs(candidate.support_epochs)

        return ConsolidationOutcome(
            key=key, kind=kind, path="slow", committed=committed,
            support_epochs=candidate.support_epochs, score=score,
        )

    def _evict_one_candidate(self) -> None:
        # least-recently-reinforced, ties by key ascending (design §10.5's
        # eviction rule, applied the same way to the candidate buffer)
        victim_key = min(
            self._candidates,
            key=lambda k: (self._candidates[k].last_support_epoch or -1, k),
        )
        del self._candidates[victim_key]
```

`quantize_unit`, `MemoryKind`, `MemoryError`, `maturity_class_from_support_epochs` are already imported at module scope from earlier tasks (same file) — no new imports needed for this step.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add MemoryConsolidator slow path with epoch-gated independence (P6, P7)"
```

---

### Task 7: MemoryConsolidator — fast path and salient trace store

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: `SalientEventTrace`/`quantize_unit` (Task 5), `MemoryConsolidator.observe` (Task 6).
- Produces: `MemoryConsolidator.observe` now also implements the fast path for `MemoryKind.SALIENT_EVENT`; `MemoryConsolidator.salient_events -> tuple[SalientEventTrace, ...]` property (ordered, most-recently-reinforced last). Consumed by Task 8 (checkpoint export).

- [ ] **Step 1: Write the failing tests**

```python
def _strong_reliable_signal() -> ConsolidationSignal:
    return ConsolidationSignal(novelty=0.9, surprise=0.9, attention=1.0, reliability=0.9, coherence=0.0)


def test_salient_event_one_shot_fast_path_commits_immediately():
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    outcome = consolidator.observe("thermal_spike", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=1)
    assert outcome.path == "fast"
    assert outcome.committed is True
    assert len(consolidator.salient_events) == 1
    trace = consolidator.salient_events[0]
    assert trace.pattern_id == "thermal_spike"
    assert 0 <= trace.novelty_class <= 15
    assert trace.recurrence_class == 0


def test_reinforcing_the_same_pattern_updates_rather_than_duplicates():
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    consolidator.observe("thermal_spike", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=1)
    consolidator.observe("thermal_spike", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=2)
    assert len(consolidator.salient_events) == 1
    assert consolidator.salient_events[0].recurrence_class == 1


def test_unreliable_strong_signal_does_not_reach_the_fast_path():
    """Precursor to P8 (full end-to-end version lands in PR5): a low-
    reliability signal must fail the fast-path gate even with high
    novelty/surprise."""
    unreliable = ConsolidationSignal(novelty=0.9, surprise=0.9, attention=1.0, reliability=0.1, coherence=0.0)
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    outcome = consolidator.observe("noisy_sense", MemoryKind.SALIENT_EVENT, unreliable, tick=1)
    assert outcome.path == "slow"
    assert consolidator.salient_events == ()


def test_salient_trace_store_is_bounded_and_evicts_least_recently_reinforced():
    limits = KernelLimits(max_salient_event_traces=2)
    consolidator = MemoryConsolidator(kernel_limits=limits)
    consolidator.observe("pattern_a", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=1)
    consolidator.observe("pattern_b", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=2)
    consolidator.observe("pattern_c", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=3)
    pattern_ids = {trace.pattern_id for trace in consolidator.salient_events}
    assert pattern_ids == {"pattern_b", "pattern_c"}  # pattern_a evicted, least-recently-reinforced
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `AssertionError` (fast path not implemented yet — `outcome.path` is currently always `"slow"`)

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Replace the `MemoryConsolidator.__init__` and `.observe` bodies:

```python
    def __init__(self, *, kernel_limits: KernelLimits) -> None:
        self._kernel_limits = kernel_limits
        self._candidates: dict[str, ConsolidationCandidate] = {}
        self._committed_statistical: dict[str, int] = {}  # key -> maturity_class
        self._salient_traces: dict[str, SalientEventTrace] = {}
        self._salient_reinforced_epoch: dict[str, int] = {}

    @property
    def salient_events(self) -> tuple[SalientEventTrace, ...]:
        ordered_ids = sorted(self._salient_traces, key=lambda pattern_id: self._salient_reinforced_epoch[pattern_id])
        return tuple(self._salient_traces[pattern_id] for pattern_id in ordered_ids)

    def observe(
        self, key: str, kind: MemoryKind, signal: ConsolidationSignal, *, tick: int
    ) -> ConsolidationOutcome:
        epoch_id = tick // self._kernel_limits.consolidation_epoch_ticks
        score = signal.score()

        if (
            kind is MemoryKind.SALIENT_EVENT
            and score >= self._kernel_limits.fast_consolidation_threshold
            and signal.reliability >= self._kernel_limits.fast_min_reliability
        ):
            self._commit_salient_trace(key, signal, epoch_id=epoch_id)
            return ConsolidationOutcome(key=key, kind=kind, path="fast", committed=True, support_epochs=0, score=score)

        candidate = self._candidates.get(key)
        if candidate is None:
            if len(self._candidates) >= self._kernel_limits.max_consolidation_candidates:
                self._evict_one_candidate()
            candidate = ConsolidationCandidate(key=key, kind=kind)
            self._candidates[key] = candidate

        if candidate.last_support_epoch != epoch_id:
            candidate.support_epochs += 1
            candidate.last_support_epoch = epoch_id
        candidate.strength = score
        candidate.latest_signal = signal

        committed = candidate.support_epochs >= self._kernel_limits.slow_support_epochs
        if committed and kind is MemoryKind.STATISTICAL:
            self._committed_statistical[key] = maturity_class_from_support_epochs(candidate.support_epochs)

        return ConsolidationOutcome(
            key=key, kind=kind, path="slow", committed=committed,
            support_epochs=candidate.support_epochs, score=score,
        )

    def _commit_salient_trace(self, key: str, signal: ConsolidationSignal, *, epoch_id: int) -> None:
        existing = self._salient_traces.get(key)
        recurrence_class = min(15, (existing.recurrence_class + 1) if existing is not None else 0)
        trace = SalientEventTrace(
            pattern_id=key,
            novelty_class=quantize_unit(signal.novelty, _TRACE_CLASS_COUNT),
            surprise_class=quantize_unit(signal.surprise, _TRACE_CLASS_COUNT),
            reliability_class=quantize_unit(signal.reliability, _TRACE_CLASS_COUNT),
            context_class=existing.context_class if existing is not None else 0,
            recurrence_class=recurrence_class,
        )
        if key not in self._salient_traces and len(self._salient_traces) >= self._kernel_limits.max_salient_event_traces:
            self._evict_one_salient_trace()
        self._salient_traces[key] = trace
        self._salient_reinforced_epoch[key] = epoch_id

    def _evict_one_salient_trace(self) -> None:
        victim_id = min(self._salient_reinforced_epoch, key=lambda pattern_id: (self._salient_reinforced_epoch[pattern_id], pattern_id))
        del self._salient_traces[victim_id]
        del self._salient_reinforced_epoch[victim_id]

    def _evict_one_candidate(self) -> None:
        victim_key = min(
            self._candidates,
            key=lambda k: (self._candidates[k].last_support_epoch or -1, k),
        )
        del self._candidates[victim_key]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add MemoryConsolidator fast path and bounded salient trace store"
```

---

### Task 8: export_checkpoint()/restore_checkpoint() and P1, P2, P10

**Files:**
- Modify: `src/symbiont/core/consolidation.py`
- Test: `tests/unit/core/test_consolidation.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `MemoryConsolidator.export_checkpoint(self) -> dict[str, object]` (only committed state: `{"statistical": {key: maturity_class}, "salient_events": [trace_dict, ...]}`); `MemoryConsolidator.restore_checkpoint(payload: dict | None, *, kernel_limits: KernelLimits) -> MemoryConsolidator` classmethod. This is the module's complete PR1 surface — later PRs (PR2+) wire this into `OrganismRuntime`.

- [ ] **Step 1: Write the failing tests**

```python
def test_p1_checkpoint_spam_does_not_increase_resolution():
    """P1: one ordinary observation followed by 100 checkpoint calls
    produces the same durable statistical memory until a genuine
    consolidation event occurs."""
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    consolidator.observe("sense_a", MemoryKind.STATISTICAL, _weak_signal(), tick=1)
    first_export = consolidator.export_checkpoint()
    for _ in range(100):
        assert consolidator.export_checkpoint() == first_export
    assert first_export["statistical"] == {}  # one observation, one epoch: not committed yet


def test_p2_a_pending_candidate_never_appears_in_the_export():
    """P2: there is no exact count/mean/variance update pair in the export
    from which an ordinary observation can be solved, because a pending
    (uncommitted) candidate simply never appears in export_checkpoint()."""
    consolidator = MemoryConsolidator(kernel_limits=KernelLimits())
    before = consolidator.export_checkpoint()
    consolidator.observe("sense_a", MemoryKind.STATISTICAL, _weak_signal(), tick=1)
    after = consolidator.export_checkpoint()
    assert before == after == {"statistical": {}, "salient_events": []}


def test_export_includes_committed_statistical_memory_and_salient_traces():
    limits = KernelLimits()
    consolidator = MemoryConsolidator(kernel_limits=limits)
    for epoch in range(limits.slow_support_epochs):
        consolidator.observe("sense_a", MemoryKind.STATISTICAL, _weak_signal(), tick=epoch * limits.consolidation_epoch_ticks + 1)
    consolidator.observe("thermal_spike", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=1)

    payload = consolidator.export_checkpoint()
    assert payload["statistical"] == {"sense_a": 3}  # maturity_class_from_support_epochs(4) == 3
    assert len(payload["salient_events"]) == 1
    assert payload["salient_events"][0]["pattern_id"] == "thermal_spike"


def test_restore_checkpoint_round_trips_committed_memory():
    limits = KernelLimits()
    consolidator = MemoryConsolidator(kernel_limits=limits)
    consolidator.observe("thermal_spike", MemoryKind.SALIENT_EVENT, _strong_reliable_signal(), tick=1)
    payload = consolidator.export_checkpoint()

    restored = MemoryConsolidator.restore_checkpoint(payload, kernel_limits=limits)
    assert restored.export_checkpoint() == payload
    assert restored.salient_events[0].pattern_id == "thermal_spike"


def test_restore_of_none_payload_returns_an_empty_consolidator():
    restored = MemoryConsolidator.restore_checkpoint(None, kernel_limits=KernelLimits())
    assert restored.export_checkpoint() == {"statistical": {}, "salient_events": []}


def test_p10_memory_remains_bounded_over_a_long_synthetic_run():
    """P10: candidates, salient traces and all durable projections respect
    kernel limits under arbitrarily long synthetic runs."""
    limits = KernelLimits(max_consolidation_candidates=8, max_salient_event_traces=4)
    consolidator = MemoryConsolidator(kernel_limits=limits)
    for tick in range(1, 5000):
        key = f"pattern_{tick % 50}"
        kind = MemoryKind.SALIENT_EVENT if tick % 7 == 0 else MemoryKind.STATISTICAL
        signal = _strong_reliable_signal() if kind is MemoryKind.SALIENT_EVENT else _weak_signal()
        consolidator.observe(key, kind, signal, tick=tick)
    assert len(consolidator._candidates) <= limits.max_consolidation_candidates
    assert len(consolidator.salient_events) <= limits.max_salient_event_traces
    payload = consolidator.export_checkpoint()
    assert len(payload["statistical"]) <= limits.max_consolidation_candidates
    assert len(payload["salient_events"]) <= limits.max_salient_event_traces
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: FAIL with `AttributeError: 'MemoryConsolidator' object has no attribute 'export_checkpoint'`

- [ ] **Step 3: Implement in `src/symbiont/core/consolidation.py`**

Add these two methods to `MemoryConsolidator` (after `salient_events` property):

```python
    def export_checkpoint(self) -> dict[str, object]:
        """Only committed/durable state -- pending candidates never appear
        here (design §4, §12.1). This is what makes P1/P2 true by
        construction: nothing here changes except at a real commit."""
        return {
            "statistical": dict(self._committed_statistical),
            "salient_events": [
                {
                    "pattern_id": trace.pattern_id,
                    "novelty_class": trace.novelty_class,
                    "surprise_class": trace.surprise_class,
                    "reliability_class": trace.reliability_class,
                    "context_class": trace.context_class,
                    "recurrence_class": trace.recurrence_class,
                }
                for trace in self.salient_events
            ],
        }

    @classmethod
    def restore_checkpoint(cls, payload: dict[str, object] | None, *, kernel_limits: KernelLimits) -> "MemoryConsolidator":
        consolidator = cls(kernel_limits=kernel_limits)
        if payload is None:
            return consolidator
        if not isinstance(payload, dict):
            raise MemoryError("memory checkpoint payload must be an object")
        statistical = payload.get("statistical", {})
        if not isinstance(statistical, dict):
            raise MemoryError("memory checkpoint 'statistical' must be an object")
        consolidator._committed_statistical = {str(key): int(value) for key, value in statistical.items()}
        salient_events = payload.get("salient_events", [])
        if not isinstance(salient_events, list):
            raise MemoryError("memory checkpoint 'salient_events' must be an array")
        for epoch, entry in enumerate(salient_events):
            trace = SalientEventTrace(
                pattern_id=str(entry["pattern_id"]),
                novelty_class=int(entry["novelty_class"]),
                surprise_class=int(entry["surprise_class"]),
                reliability_class=int(entry["reliability_class"]),
                context_class=int(entry["context_class"]),
                recurrence_class=int(entry["recurrence_class"]),
            )
            consolidator._salient_traces[trace.pattern_id] = trace
            consolidator._salient_reinforced_epoch[trace.pattern_id] = epoch
        return consolidator
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/consolidation.py tests/unit/core/test_consolidation.py
git commit -m "feat(core): add MemoryConsolidator checkpoint export/restore (P1, P2, P10)"
```

---

## Self-Review Notes

**Spec coverage:** §6.1/§6.2 kernel mappings -> Task 3. §7 score/thresholds -> Task 2 + KernelLimits (Task 1). §8 epoch independence -> Task 6. §9.1-§9.5 types -> Tasks 2, 4, 5, 6. §10.1 maturity classes -> Task 4. §10.5 salient trace -> Task 5. §19 kernel limits -> Task 1. P1, P2, P6, P7, P10 (§21) -> Tasks 6, 7, 8, each with a named test. P9's *gate* (structural never fast-paths) is exercised in Task 6's `test_structural_kind_never_takes_the_fast_path...`, though the full adversarial P9 property (verified through real `apply_mutations`) is PR5's job per the design's revised sequencing. P8's *gate* (reliability) is exercised in Task 7's `test_unreliable_strong_signal_does_not_reach_the_fast_path`, full end-to-end P8 is PR5.

**Explicitly out of scope for PR1** (confirmed against Global Constraints): `OrganismRuntime` wiring, `CognitiveBridge` wiring, host model changes, checkpoint schema_version bump, genome changes, coherence-signal computation from real epoch/relation data (PR1's tests supply `coherence` directly as part of a hand-built `ConsolidationSignal` — computing it from real independent-support history is PR2/PR3's job once `MemoryConsolidator` is wired into the tick loop).

**Type consistency check:** `ConsolidationOutcome.path` is the string literal `"fast"` or `"slow"` everywhere (Tasks 6, 7) — no later task introduces a third spelling. `MemoryConsolidator.observe`'s signature (`key, kind, signal, *, tick`) is identical across Tasks 6 and 7 (Task 7 replaces the whole method body, not just adds to it — the plan text says so explicitly to avoid an ambiguous partial-edit). `_TRACE_CLASS_COUNT = 16` (Task 5) is reused by Task 7's `_commit_salient_trace` rather than a re-declared literal.
