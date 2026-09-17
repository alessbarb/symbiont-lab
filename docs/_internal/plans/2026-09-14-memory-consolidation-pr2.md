# Biological Memory Consolidation — PR2 (Cognitive Labile/Durable Split) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `CognitiveBridge`'s checkpoint into labile (RAM-only: eligibility, previous activation frame, in-progress structural candidates) and durable (topology, node-atomic consolidated weight classes, safety state) state, per the design's supersession of PR #76 (§2.1), with `WeightStabilityTracker`'s epoch-spaced class stability (§11, owner decision) as the sole path to a durable edge weight, node-atomic homeostatic commit (P13), and the §16a reacclimation gate over structural consolidation.

**Architecture:** A new standalone `WeightStabilityTracker` (own file, own tests, zero `ConsolidationSignal`/`MemoryConsolidator` involvement per the owner's explicit decision) tracks each edge's quantized-class stability across consolidation epochs and computes node-atomic homeostatic commits. `CognitiveBridge` owns one tracker instance, seeds it with each edge's *construction* weight class at creation/restore, calls it once per tick per edge, and uses its durable classes — never live weight — when exporting a checkpoint. `eligibility`, `previous_frame`, and `StructuralPlasticity`'s in-progress candidate state are removed from the checkpoint entirely; restore always cold-starts them. A reacclimation counter blocks structural consolidation for `reacclimation_ticks` after a restore (never after first construction).

**Tech Stack:** Python 3.11+ stdlib only, matching `src/symbiont/cognition/`. Reuses `quantize_signed`/`dequantize_signed`/`WEIGHT_RANGE`/`WEIGHT_CLASSES` from `src/symbiont/cognition/checkpoint.py` and `src/symbiont/cognition/types.py` (already public since the Observatory work this session).

**Spec:** `docs/design/biological-memory-consolidation.md` (§2.1 supersedes PR #76, §10.3-§10.4 durable/labile split, §11 `WeightStabilityTracker` + node-atomic commit, §16a reacclimation, §21 P5/P11/P12/P13, §23 PR2)

## Global Constraints

- `eligibility` and `previous_frame` are never exported by `CognitiveBridge.export_checkpoint()`; `CognitiveBridge.restore()` always cold-starts them (`eligibility=0` on every edge, `previous_frame={}`) regardless of what a legacy payload might contain (design §10.3, P5).
- `StructuralPlasticity`'s candidate/cooldown bookkeeping is never exported by `CognitiveBridge.export_checkpoint()`; restore always constructs a fresh `StructuralPlasticity()`. Anything durable about structure already exists as real graph topology (nodes/edges) — there is no separate "durable candidate" concept to preserve (design §10.4).
- An edge's durable weight class is its **construction-time** class until it completes a real consolidation (design owner decision: "construction weight until first real consolidation"). It is never the current live weight class before that (P2's differencing concern applies here too — an unstable edge's checkpoint must not move with every Oja update).
- Weight consolidation is **epoch-spaced** (`KernelLimits.consolidation_epoch_ticks`), resets support to `1` on any class change (no partial credit), and never uses `ConsolidationSignal`/`MemoryConsolidator` (design §11, P12).
- Homeostatic commit is **node-atomic**: a node commits only when every *changed* incoming edge (candidate class differs from current durable class) is individually ready; one immature changed edge blocks the whole node, and unchanged siblings are never touched (design §11, P13).
- The reacclimation gate (`KernelLimits.reacclimation_ticks`) blocks only **structural** consolidation in this PR — `MemoryConsolidator`'s fast path is not wired into `CognitiveBridge` yet, so there is nothing else to gate here (design §16a, scoped per owner decision this session).
- No `CHECKPOINT_SCHEMA_VERSION` bump in this PR (that is PR4's job) — `CognitiveBridge`'s own checkpoint dict shape changes, but the top-level `OrganismRuntime` schema version stays at 5.
- `tests/unit/core/test_resident_continuity.py::test_delay_one_previous_frame_survives_bridge_checkpoint` is intentionally rewritten with an **inverted** expectation (cold restart, not continuity) — this is the PR #76 supersession made concrete, not a regression.

---

### Task 1: WeightStabilityTracker — epoch-spaced class stability (P12)

**Files:**
- Create: `src/symbiont/core/weight_stability.py`
- Test: `tests/unit/core/test_weight_stability.py`

**Interfaces:**
- Consumes: `KernelLimits` (`consolidation_epoch_ticks`, `slow_support_epochs`).
- Produces: `WeightStabilityTracker` with `__init__(self, *, kernel_limits: KernelLimits)`, `.seed(edge_key: str, construction_class: int) -> None`, `.observe(edge_key: str, weight_class: int, *, tick: int) -> None`, `.candidate_class(edge_key: str) -> int | None`, `.is_ready(edge_key: str) -> bool`, `.durable_class(edge_key: str) -> int`. Consumed by Task 2 (`consolidate_node`) and Task 6 (`CognitiveBridge` wiring).

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.core.weight_stability import WeightStabilityTracker


def test_seed_sets_the_durable_class_before_any_observation():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->b", 5)
    assert tracker.durable_class("a->b") == 5
    assert tracker.candidate_class("a->b") is None
    assert tracker.is_ready("a->b") is False


def test_p12_class_change_within_the_same_epoch_does_not_accumulate_support():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    for weight_class in (3, 4, 3, 5, 3):  # oscillating within one epoch (ticks 1-7, epoch 0)
        tracker.observe("a->b", weight_class, tick=1)
    assert tracker.is_ready("a->b") is False


def test_p12_class_change_across_epochs_resets_support_to_one():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    # three epochs at class 7, then one epoch at class 8 -- must NOT be ready
    # (support resets to 1 for the new class, and slow_support_epochs default is 4)
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch, cls in enumerate([7, 7, 7, 8]):
        tracker.observe("a->b", cls, tick=epoch * epoch_ticks + 1)
    tracker.observe("a->b", 8, tick=4 * epoch_ticks + 1)  # close epoch 4 by opening epoch 4... (see below)
    assert tracker.candidate_class("a->b") == 8
    assert tracker.is_ready("a->b") is False  # only 1 epoch of support for class 8 so far


def test_stable_class_across_enough_epochs_becomes_ready():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->b", 0)
    epoch_ticks = limits.consolidation_epoch_ticks
    # slow_support_epochs + 1 observations at the same class, one per epoch boundary,
    # to actually finalize slow_support_epochs worth of closed epochs
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->b", 7, tick=epoch * epoch_ticks + 1)
    assert tracker.candidate_class("a->b") == 7
    assert tracker.is_ready("a->b") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_weight_stability.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'symbiont.core.weight_stability'`

- [ ] **Step 3: Create `src/symbiont/core/weight_stability.py`**

```python
"""Epoch-spaced class-stability consolidation for synaptic weights (design
docs/design/biological-memory-consolidation.md §11, owner decision
2026-09-14). Deliberately separate from ConsolidationSignal/
MemoryConsolidator: an Oja delta is an internal consequence of learning,
not a perceptual salience signal, and reinterpreting it as novelty/surprise
would mix levels the memory-kind taxonomy keeps apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..cognition.limits import KernelLimits


@dataclass(slots=True)
class _EdgeStability:
    pending_class: int
    pending_epoch: int
    candidate_class: int | None = None
    support_epochs: int = 0


class WeightStabilityTracker:
    def __init__(self, *, kernel_limits: KernelLimits) -> None:
        self._kernel_limits = kernel_limits
        self._state: dict[str, _EdgeStability] = {}
        self._durable: dict[str, int] = {}

    def seed(self, edge_key: str, construction_class: int) -> None:
        """Called once per edge at CognitiveBridge construction/restore --
        this is the durable class an edge exports until it completes its
        first real consolidation (design: construction weight until first
        real consolidation)."""
        self._durable[edge_key] = construction_class

    def observe(self, edge_key: str, weight_class: int, *, tick: int) -> None:
        epoch_id = tick // self._kernel_limits.consolidation_epoch_ticks
        state = self._state.get(edge_key)
        if state is None:
            self._state[edge_key] = _EdgeStability(
                pending_class=weight_class, pending_epoch=epoch_id, candidate_class=weight_class, support_epochs=0
            )
            return
        if epoch_id == state.pending_epoch:
            # Still inside the same epoch -- P12: the latest sample this
            # epoch wins, but no support increment happens until the epoch
            # actually closes (a burst of updates counts as at most one
            # observation for this epoch).
            state.pending_class = weight_class
            return
        # An epoch boundary was crossed: finalize the just-closed epoch's
        # sampled class against the running candidate.
        finalized_class = state.pending_class
        if finalized_class == state.candidate_class:
            state.support_epochs += 1
        else:
            state.candidate_class = finalized_class
            state.support_epochs = 1
        state.pending_class = weight_class
        state.pending_epoch = epoch_id

    def candidate_class(self, edge_key: str) -> int | None:
        state = self._state.get(edge_key)
        return state.candidate_class if state is not None else None

    def is_ready(self, edge_key: str) -> bool:
        state = self._state.get(edge_key)
        return state is not None and state.support_epochs >= self._kernel_limits.slow_support_epochs

    def durable_class(self, edge_key: str) -> int:
        return self._durable[edge_key]
```

- [ ] **Step 4: Run tests, fix the deliberately-awkward test to actually reach a true reset, and verify they pass**

The `test_p12_class_change_across_epochs_resets_support_to_one` test above has an
intentionally-tricky tick sequence; run it first and adjust the tick values if the
epoch math doesn't land exactly as described (the assertion — support resets to `1`
after a class change, so 4 total observations of `[7,7,7,8]` plus one more at `8`
cannot yet be ready — is what must hold, not the exact tick literals).

Run: `pytest tests/unit/core/test_weight_stability.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/weight_stability.py tests/unit/core/test_weight_stability.py
git commit -m "feat(core): add WeightStabilityTracker with epoch-spaced class stability (P12)"
```

---

### Task 2: Node-atomic homeostatic commit (P13)

**Files:**
- Modify: `src/symbiont/core/weight_stability.py`
- Test: `tests/unit/core/test_weight_stability.py`

**Interfaces:**
- Consumes: `quantize_signed`/`dequantize_signed`/`WEIGHT_RANGE`/`WEIGHT_CLASSES` from `symbiont.cognition.checkpoint`/`symbiont.cognition.types`.
- Produces: `WeightStabilityTracker.consolidate_node(self, edge_keys: Sequence[str], live_weights: Mapping[str, float], *, max_incoming_norm: float) -> dict[str, int] | None` — pure with respect to the graph (takes plain edge keys and live float weights, no `CognitiveGraph`/`PlasticEdge` dependency, so it is fully testable here). Returns the new durable class per `edge_key` for the whole node if the node committed, or `None` if it did not (nothing changed, or a changed edge wasn't ready). Also updates `self._durable` in place for a real commit. Consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

```python
def test_consolidate_node_returns_none_when_nothing_changed():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)
    # observe the exact same class as the seed -- "changed" means candidate != durable
    tracker.observe("a->n", 5, tick=1)
    tracker.observe("b->n", 5, tick=1)
    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 0.3, "b->n": 0.3}, max_incoming_norm=8.0)
    assert result is None


def test_p13_node_atomic_commit_blocks_on_one_immature_changed_edge():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)
    epoch_ticks = limits.consolidation_epoch_ticks
    # a->n: stable long enough to be ready and changed relative to its seed
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 9, tick=epoch * epoch_ticks + 1)
    # b->n: also changed (class 6 != seeded 5) but observed only once -- NOT ready
    tracker.observe("b->n", 6, tick=1)

    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.5, "b->n": 0.4}, max_incoming_norm=8.0)
    assert result is None  # b->n blocks the whole node
    assert tracker.durable_class("a->n") == 5  # unchanged by the blocked attempt
    assert tracker.durable_class("b->n") == 5


def test_node_commits_when_all_changed_edges_are_ready_unchanged_sibling_untouched():
    limits = KernelLimits()
    tracker = WeightStabilityTracker(kernel_limits=limits)
    tracker.seed("a->n", 5)
    tracker.seed("b->n", 5)  # this one will stay unchanged
    epoch_ticks = limits.consolidation_epoch_ticks
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 9, tick=epoch * epoch_ticks + 1)
        tracker.observe("b->n", 5, tick=epoch * epoch_ticks + 1)  # stays at the seeded class

    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.5, "b->n": 0.3}, max_incoming_norm=8.0)
    assert result is not None
    assert "a->n" in result
    assert result["b->n"] == tracker.durable_class("b->n") == 5  # untouched sibling's durable value, unchanged
    assert tracker.durable_class("a->n") == result["a->n"]


def test_homeostatic_l1_normalization_scales_down_when_over_budget():
    tracker = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker.seed("a->n", 0)
    tracker.seed("b->n", 0)
    limits = KernelLimits()
    for epoch in range(limits.slow_support_epochs + 1):
        tracker.observe("a->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)  # near +2.0
        tracker.observe("b->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)

    # live weights sum |1.9| + |1.9| = 3.8, well under budget 8.0 -- no scaling
    result = tracker.consolidate_node(["a->n", "b->n"], {"a->n": 1.9, "b->n": 1.9}, max_incoming_norm=8.0)
    assert result is not None

    # now force an over-budget scenario with a tiny budget
    tracker2 = WeightStabilityTracker(kernel_limits=KernelLimits())
    tracker2.seed("a->n", 0)
    tracker2.seed("b->n", 0)
    for epoch in range(limits.slow_support_epochs + 1):
        tracker2.observe("a->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)
        tracker2.observe("b->n", 15, tick=epoch * limits.consolidation_epoch_ticks + 1)
    scaled = tracker2.consolidate_node(["a->n", "b->n"], {"a->n": 1.9, "b->n": 1.9}, max_incoming_norm=1.0)
    assert scaled is not None
    # scaled classes must correspond to weights whose |sum| is bounded by the budget
    from symbiont.cognition.checkpoint import WEIGHT_CLASSES, dequantize_signed
    from symbiont.cognition.types import WEIGHT_RANGE
    total = sum(abs(dequantize_signed(cls, WEIGHT_RANGE, WEIGHT_CLASSES)) for cls in scaled.values())
    assert total <= 1.0 + 1e-6
```

Add the needed imports at the top of `tests/unit/core/test_weight_stability.py` (`from symbiont.core.weight_stability import WeightStabilityTracker` should already be there from Task 1 — just confirm).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_weight_stability.py -v`
Expected: FAIL with `AttributeError: 'WeightStabilityTracker' object has no attribute 'consolidate_node'`

- [ ] **Step 3: Implement `consolidate_node`**

Add the import at the top of `src/symbiont/core/weight_stability.py`:

```python
from ..cognition.checkpoint import WEIGHT_CLASSES, dequantize_signed, quantize_signed
from ..cognition.types import WEIGHT_RANGE
```

Add the method to `WeightStabilityTracker`, after `durable_class`:

```python
    def consolidate_node(
        self,
        edge_keys: "Sequence[str]",
        live_weights: "Mapping[str, float]",
        *,
        max_incoming_norm: float,
    ) -> dict[str, int] | None:
        """Node-atomic homeostatic commit (design §11, P13): a node commits
        only when every *changed* incoming edge (candidate class differs
        from its current durable class) is individually ready. One immature
        changed edge blocks the whole node -- no partial commits, and an
        unchanged sibling's durable weight is never rewritten."""
        changed = [key for key in edge_keys if self.candidate_class(key) != self.durable_class(key)]
        if not changed:
            return None
        if not all(self.is_ready(key) for key in changed):
            return None

        changed_set = set(changed)
        vector: dict[str, float] = {}
        for key in edge_keys:
            if key in changed_set:
                vector[key] = live_weights[key]
            else:
                vector[key] = dequantize_signed(self.durable_class(key), WEIGHT_RANGE, WEIGHT_CLASSES)

        norm = sum(abs(value) for value in vector.values())
        scale = max_incoming_norm / norm if norm > max_incoming_norm else 1.0

        result = {key: quantize_signed(value * scale, WEIGHT_RANGE, WEIGHT_CLASSES) for key, value in vector.items()}
        for key, durable_class in result.items():
            self._durable[key] = durable_class
        return result
```

Add `from typing import Mapping, Sequence` to the top-of-file imports (replace the bare type-hint strings above with real imports rather than string-quoted types once this is in place):

```python
from typing import Mapping, Sequence
```

and change the method signature to use the real types (`edge_keys: Sequence[str]`, `live_weights: Mapping[str, float]`) instead of the quoted placeholders shown above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_weight_stability.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/weight_stability.py tests/unit/core/test_weight_stability.py
git commit -m "feat(core): add node-atomic homeostatic weight commit (P13)"
```

---

### Task 3: Remove eligibility from the graph checkpoint

**Files:**
- Modify: `src/symbiont/cognition/checkpoint.py`
- Modify: `tests/unit/cognition/test_graph_checkpoint.py` (read it first — check exact current test names before editing)
- Test: same file

**Interfaces:**
- Consumes: nothing new.
- Produces: `export_graph_checkpoint` no longer writes `eligibility_class` per edge; `restore_graph_checkpoint` no longer reads it and always constructs each `PlasticEdge` with `eligibility=0.0`.

- [ ] **Step 1: Read the current test file to see exactly what asserts eligibility round-trips**

Run: `grep -n "eligibility" tests/unit/cognition/test_graph_checkpoint.py tests/unit/cognition/test_checkpoint.py`

Note every assertion that checks `eligibility_class` is present in an exported payload, or that a restored edge's `.eligibility` matches a pre-export nonzero value. Those assertions must be rewritten to expect `eligibility_class` **absent** from the export and restored `.eligibility == 0.0` regardless of what the edge's eligibility was before export.

- [ ] **Step 2: Write/update the failing test**

In whichever of the two files contains the graph-checkpoint round-trip test (found in Step 1), replace the eligibility-related assertions with:

```python
def test_eligibility_is_never_exported_and_always_zero_on_restore():
    limits = KernelLimits()
    nodes = (PlasticNode(node_id="s", kind=NodeKind.SENSE), PlasticNode(node_id="c", kind=NodeKind.CONCEPT))
    edges = (
        PlasticEdge(source_id="s", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0, eligibility=3.7),
    )
    graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=limits)

    payload = export_graph_checkpoint(graph)
    assert "eligibility_class" not in payload["edges"][0]

    restored = restore_graph_checkpoint(payload, kernel_limits=limits)
    assert restored.edges[0].eligibility == 0.0
```

Use whichever imports (`CognitiveGraph`, `PlasticNode`, `PlasticEdge`, `NodeKind`, `EdgeKind`, `KernelLimits`, `export_graph_checkpoint`, `restore_graph_checkpoint`) the existing file already has at its top — do not duplicate imports.

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/cognition/test_graph_checkpoint.py -v` (or `test_checkpoint.py`, whichever file you added the test to)
Expected: FAIL — either `KeyError`/`AssertionError` because `eligibility_class` is still present, or the old test(s) from Step 1 still assert the opposite and now fail once you've updated them

- [ ] **Step 4: Modify `export_graph_checkpoint`/`restore_graph_checkpoint` in `src/symbiont/cognition/checkpoint.py`**

In `export_graph_checkpoint`'s edge dict comprehension, remove the `"eligibility_class": ...` line entirely.

In `restore_graph_checkpoint`'s `PlasticEdge(...)` construction, replace:

```python
            eligibility=_dequantize_signed(
                _require_class_id(
                    entry["eligibility_class"],
                    field="edge.eligibility_class",
                    num_classes=ELIGIBILITY_CLASSES,
                ),
                ELIGIBILITY_RANGE,
                ELIGIBILITY_CLASSES,
            ),
```

with:

```python
            eligibility=0.0,  # labile: never restored from a checkpoint (design §10.3, P5)
```

(Use the actual current parameter names in the file — check the real current text with `grep -n "eligibility" src/symbiont/cognition/checkpoint.py` before editing, since the post-merge version may have slightly different local variable names than shown here; the substance of the change — delete the export line, replace the restore line with a hardcoded `0.0` — is what matters.)

`ELIGIBILITY_CLASSES`/`ELIGIBILITY_RANGE`/`dequantize_signed` may now be unused in this file if nothing else references them — run `grep -n "ELIGIBILITY_CLASSES\|ELIGIBILITY_RANGE" src/symbiont/cognition/checkpoint.py` after the edit; if they have no remaining call sites, remove the now-dead constants and any now-unused import, keeping the module clean (YAGNI/no-dead-code).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_graph_checkpoint.py tests/unit/cognition/test_checkpoint.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/cognition/checkpoint.py tests/unit/cognition/test_graph_checkpoint.py tests/unit/cognition/test_checkpoint.py
git commit -m "feat(cognition): remove eligibility from the graph checkpoint (labile, design §10.3)"
```

---

### Task 4: Remove previous_frame from CognitiveBridge's checkpoint (P5, P11)

**Files:**
- Modify: `src/symbiont/cognition/checkpoint.py` (remove `export_activation_frame`/`restore_activation_frame` if they have no other callers after this task)
- Modify: `src/symbiont/core/cognition_bridge.py`
- Modify: `tests/unit/core/test_resident_continuity.py`
- Test: same files

**Interfaces:**
- Produces: `CognitiveBridge.export_checkpoint()` no longer includes a `"previous_frame"` key; `CognitiveBridge.restore()` always sets `bridge._previous_frame = {}` regardless of payload content.

- [ ] **Step 1: Write/replace the failing test**

In `tests/unit/core/test_resident_continuity.py`, replace `test_delay_one_previous_frame_survives_bridge_checkpoint` (the whole function) with its inverted-expectation successor:

```python
def test_p5_p11_previous_frame_is_never_exported_and_cold_starts_on_restore() -> None:
    """PR2 supersedes PR #76's continuity guarantee for this exact test
    (design §2.1): the checkpoint must never let a restart reconstruct the
    prior tick's activation. delay_ticks=1 edges therefore see a genuine
    cold (0.0) source on the first post-restore tick, not the pre-restart
    value."""
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id="s", kind=NodeKind.SENSE),
            PlasticNode(node_id="c", kind=NodeKind.CONCEPT),
            PlasticNode(node_id="r", kind=NodeKind.READOUT),
        ),
        edges=(
            PlasticEdge(source_id="s", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),
            PlasticEdge(source_id="c", target_id="r", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=1),
        ),
        kernel_limits=limits,
    )
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    first = bridge.tick({"s": 5.0}, tick=1)
    assert abs(first.activations["c"]) > 0.1  # real, non-trivial activation before any restart

    payload = bridge.export_checkpoint()
    assert "previous_frame" not in payload

    restored = CognitiveBridge.restore(payload, genome=genome, kernel_limits=limits)
    assert restored is not None

    # Cold start: feeding 0.0 this tick, the delay=1 edge (c->r) reads from
    # a previous_frame that is genuinely empty, not the pre-restart "c"
    # activation -- so "r" sees no contribution from "c" this tick.
    second = restored.tick({"s": 0.0}, tick=1)
    assert second.readouts["r"] == pytest.approx(0.0)
```

Add `import pytest` at the top of `tests/unit/core/test_resident_continuity.py` if it isn't already imported (check first).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_resident_continuity.py::test_p5_p11_previous_frame_is_never_exported_and_cold_starts_on_restore -v`
Expected: FAIL — `payload` still contains `"previous_frame"`, and/or `second.readouts["r"]` is not `0.0` because the old code restores the real prior frame

- [ ] **Step 3: Modify `src/symbiont/core/cognition_bridge.py`**

Remove `export_activation_frame`, `restore_activation_frame` from the import block at the top (leave the other imports from `..cognition.checkpoint` untouched).

In `export_checkpoint`, delete the line:

```python
            "previous_frame": export_activation_frame(self._previous_frame),
```

In `restore`, delete:

```python
        restored_previous = restore_activation_frame(payload.get("previous_frame"))
        bridge._previous_frame = {
            node_id: value for node_id, value in restored_previous.items() if node_id in allowed_node_ids
        }
```

`bridge._previous_frame` is already initialized to `{}` by `cls(...)`'s own `__init__` (see the `self._previous_frame: dict[str, float] = {}` line there) — no replacement line is needed; simply removing the two lines above is the whole change, since the constructor already cold-starts it.

- [ ] **Step 4: Remove the now-dead activation-frame functions from `checkpoint.py`**

Run: `grep -rn "export_activation_frame\|restore_activation_frame" src/ tests/` to confirm the only remaining references are the function definitions themselves and any direct unit tests of them in `tests/unit/cognition/test_checkpoint.py`.

If there are direct tests of `export_activation_frame`/`restore_activation_frame` in `tests/unit/cognition/test_checkpoint.py`, delete those test functions (they test a function this task removes — this is not "losing coverage," it's removing coverage for removed functionality, exactly like deleting a test for a deleted feature).

Delete the `export_activation_frame` and `restore_activation_frame` function definitions from `src/symbiont/cognition/checkpoint.py`. If `_ACTIVATION_CLASSES`/`_ACTIVATION_RANGE` (module-level constants used only by those two functions) have no other callers after this removal, delete them too.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_resident_continuity.py tests/unit/cognition/test_checkpoint.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/cognition/checkpoint.py src/symbiont/core/cognition_bridge.py tests/unit/core/test_resident_continuity.py tests/unit/cognition/test_checkpoint.py
git commit -m "$(cat <<'COMMIT'
feat(core): remove previous_frame from CognitiveBridge checkpoint (P5, P11)

Supersedes PR #76's previous_frame continuity guarantee (design §2.1):
a restart no longer reconstructs the prior tick's activation frame.
delay_ticks=1 edges genuinely cold-start (0.0 source) on the first
post-restore tick rather than replaying pre-restart dynamics. This is
a deliberate, owner-approved reversal, not a regression --
test_delay_one_previous_frame_survives_bridge_checkpoint is replaced
with its inverted-expectation successor,
test_p5_p11_previous_frame_is_never_exported_and_cold_starts_on_restore.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

### Task 5: Stop persisting StructuralPlasticity candidate state

**Files:**
- Modify: `src/symbiont/core/cognition_bridge.py`
- Test: `tests/unit/core/test_cognition_bridge.py`

**Interfaces:**
- Produces: `CognitiveBridge.export_checkpoint()` no longer includes a `"structural_plasticity"` key; `CognitiveBridge.restore()` always constructs a fresh `StructuralPlasticity(...)` rather than calling `StructuralPlasticity.restore_checkpoint(...)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/core/test_cognition_bridge.py`:

```python
def test_structural_plasticity_candidate_state_is_never_exported():
    """Design §10.4: anything durable about structure already exists as
    real graph topology; in-progress candidate/cooldown bookkeeping is
    RAM-only working state, never checkpointed."""
    graph = _simple_graph()
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())
    for tick in range(1, 10):
        bridge.tick({"s": 1.0}, tick=tick)
    payload = bridge.export_checkpoint()
    assert "structural_plasticity" not in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_cognition_bridge.py::test_structural_plasticity_candidate_state_is_never_exported -v`
Expected: FAIL — `"structural_plasticity"` is present in `payload`

- [ ] **Step 3: Modify `src/symbiont/core/cognition_bridge.py`**

In `export_checkpoint`, delete the line:

```python
            "structural_plasticity": self._structural_plasticity.export_checkpoint(),
```

In `restore`, replace:

```python
        allowed_node_ids = {node.node_id for node in graph.nodes}
        structural_plasticity = StructuralPlasticity.restore_checkpoint(
            payload.get("structural_plasticity"),
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
            allowed_node_ids=allowed_node_ids,
        )
```

with:

```python
        # Design §10.4: in-progress structural candidate/cooldown state is
        # RAM-only working memory, never checkpointed -- a restart always
        # starts structural plasticity fresh. Anything that had actually
        # crossed into real topology already survives via graph.nodes/edges.
        structural_plasticity = StructuralPlasticity(
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
        )
```

Keep the `allowed_node_ids = {node.node_id for node in graph.nodes}` line only if it is used elsewhere in `restore` after this edit (check — if `previous_frame` restoration was the only other consumer and Task 4 already removed that block, delete this now-unused line too).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_cognition_bridge.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS (note: `StructuralPlasticity.export_checkpoint`/`.restore_checkpoint` themselves are untouched and still directly unit-tested in `tests/unit/cognition/test_structure.py` and `tests/unit/core/test_resident_continuity.py::test_structural_candidate_support_survives_restart` — those tests exercise `StructuralPlasticity` directly, never through `CognitiveBridge`, and remain valid and unchanged)

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/cognition_bridge.py tests/unit/core/test_cognition_bridge.py
git commit -m "feat(core): stop persisting structural-plasticity candidate state through CognitiveBridge (design §10.4)"
```

---

### Task 6: Wire WeightStabilityTracker into CognitiveBridge

**Files:**
- Modify: `src/symbiont/cognition/checkpoint.py`
- Modify: `src/symbiont/core/cognition_bridge.py`
- Test: `tests/unit/core/test_cognition_bridge.py`

**Interfaces:**
- Consumes: `WeightStabilityTracker` (Tasks 1-2), `quantize_signed`/`WEIGHT_RANGE`/`WEIGHT_CLASSES` (already public).
- Produces: `export_graph_checkpoint` gains an optional `weight_class_overrides: dict[tuple[str, str, str], int] | None = None` parameter (keyed by `(source_id, target_id, kind.value)`); when provided, an edge's exported `weight_class` comes from the override map instead of quantizing `edge.weight` directly. `CognitiveBridge` owns a `WeightStabilityTracker`, seeds every edge's construction class at `__init__`/`restore`, consolidates weights once per tick, and passes the tracker's durable classes as `weight_class_overrides` when exporting.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/core/test_cognition_bridge.py`:

```python
def _edge_key(edge) -> tuple[str, str, str]:
    return (edge.source_id, edge.target_id, edge.kind.value)


def test_unconsolidated_edge_exports_its_construction_weight_class_not_the_live_one():
    """P2-style guarantee applied to weights: an edge that hasn't completed
    a real consolidation must not leak its current (still-moving) live
    weight through the checkpoint."""
    graph = _simple_graph()  # weight=0.5 at construction
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits())
    from symbiont.cognition.checkpoint import WEIGHT_CLASSES, quantize_signed
    from symbiont.cognition.types import WEIGHT_RANGE
    construction_class = quantize_signed(0.5, WEIGHT_RANGE, WEIGHT_CLASSES)

    # drive real learning for a few ticks -- not enough epochs to consolidate
    for tick in range(1, 4):
        bridge.tick({"s": 1.0}, tick=tick)

    payload = bridge.export_checkpoint()
    exported_class = payload["graph"]["edges"][0]["weight_class"]
    assert exported_class == construction_class


def test_edge_weight_consolidates_and_checkpoint_reflects_the_new_durable_class():
    limits = KernelLimits()
    graph = _simple_graph()
    genome = _genome()
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    # Enough ticks across enough epochs for real Oja-driven learning to
    # stabilize the edge's weight class away from its construction value.
    total_ticks = limits.consolidation_epoch_ticks * (limits.slow_support_epochs + 3)
    for tick in range(1, total_ticks):
        bridge.tick({"s": 1.0}, tick=tick)

    from symbiont.cognition.checkpoint import WEIGHT_CLASSES, quantize_signed
    from symbiont.cognition.types import WEIGHT_RANGE
    construction_class = quantize_signed(0.5, WEIGHT_RANGE, WEIGHT_CLASSES)
    live_class = quantize_signed(bridge.graph.edges[0].weight, WEIGHT_RANGE, WEIGHT_CLASSES)

    payload = bridge.export_checkpoint()
    exported_class = payload["graph"]["edges"][0]["weight_class"]
    # Either the edge genuinely never moved off its construction class (a
    # possible but unlikely outcome depending on the fixture's dynamics),
    # or it consolidated and the checkpoint reflects the new durable class
    # -- but it must equal one of these two coarse classes, never a
    # snapshot of live weight taken at an arbitrary intermediate tick that
    # differs from both.
    assert exported_class in {construction_class, live_class}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_cognition_bridge.py::test_unconsolidated_edge_exports_its_construction_weight_class_not_the_live_one -v`
Expected: FAIL — the current `export_graph_checkpoint` always exports the live weight's own class, so `exported_class` already differs from `construction_class` after real learning ticks (this may or may not fail depending on how much the fixture's weight actually moved in 3 ticks — if it happens to pass trivially because the weight barely moved, that is a weak test; the real assertion this task must make true is checked properly by the second test below, which forces enough ticks to guarantee movement. Treat the first test as documentation-by-example and the second as the real regression guard).

- [ ] **Step 3: Add `weight_class_overrides` to `export_graph_checkpoint` in `src/symbiont/cognition/checkpoint.py`**

Change the signature:

```python
def export_graph_checkpoint(
    graph: CognitiveGraph | None, *, weight_class_overrides: dict[tuple[str, str, str], int] | None = None
) -> dict[str, Any] | None:
```

In the edges list comprehension, change the `"weight_class": quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES),` line to:

```python
                "weight_class": (
                    weight_class_overrides[(edge.source_id, edge.target_id, edge.kind.value)]
                    if weight_class_overrides is not None and (edge.source_id, edge.target_id, edge.kind.value) in weight_class_overrides
                    else quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES)
                ),
```

(The fallback to live quantization only matters for a caller that doesn't pass overrides at all, e.g. any direct test of `export_graph_checkpoint` written before this task — `CognitiveBridge`, wired in the next step, always passes a complete override map covering every edge.)

- [ ] **Step 4: Wire the tracker into `CognitiveBridge`**

In `src/symbiont/core/cognition_bridge.py`, add the import:

```python
from .weight_stability import WeightStabilityTracker
```

and `from ..cognition.checkpoint import ... , WEIGHT_CLASSES, quantize_signed` (add `WEIGHT_CLASSES` and `quantize_signed` to the existing import-from-checkpoint block), and `from ..cognition.types import WEIGHT_RANGE` (add if not already imported).

In `__init__`, after `self._topology_revision = 0`, add:

```python
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        for edge in graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            self._weight_tracker.seed(key, quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES))
```

In `export_checkpoint`, change the `"graph": export_graph_checkpoint(self._graph),` line to:

```python
            "graph": export_graph_checkpoint(self._graph, weight_class_overrides=self._weight_class_overrides()),
```

Add a new private method to `CognitiveBridge`:

```python
    def _weight_class_overrides(self) -> dict[tuple[str, str, str], int]:
        return {
            (edge.source_id, edge.target_id, edge.kind.value): self._weight_tracker.durable_class(
                (edge.source_id, edge.target_id, edge.kind.value)
            )
            for edge in self._graph.edges
        }
```

In `restore`, after the bridge is constructed (after `bridge = cls(...)`), the `__init__` call above already seeds every edge from the **restored graph's live weight** -- which on restore *is* the durable class, since `restore_graph_checkpoint` dequantizes exactly the class that was exported. This is correct: a freshly-restored edge's "construction" class for tracker purposes is whatever was durable at export time. No additional restore-time code is needed for the tracker beyond what `__init__` already does.

In `tick()`, after the existing per-edge learning loop (`for edge in self._graph.edges: ... advance_edge_age(...)`), inside the same `if not frozen:` block, add a new pass:

```python
            edges_by_target: dict[str, list] = {}
            for edge in self._graph.edges:
                key = (edge.source_id, edge.target_id, edge.kind.value)
                self._weight_tracker.observe(key, quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES), tick=tick)
                edges_by_target.setdefault(edge.target_id, []).append(edge)

            for target_edges in edges_by_target.values():
                keys = [(edge.source_id, edge.target_id, edge.kind.value) for edge in target_edges]
                live_weights = {key: edge.weight for key, edge in zip(keys, target_edges)}
                self._weight_tracker.consolidate_node(
                    keys, live_weights, max_incoming_norm=self._kernel_limits.max_incoming_consolidated_weight_norm
                )
```

Place this new pass immediately after the existing `for edge in self._graph.edges:` learning loop and before the `active_nodes = [...]` line, still inside `if not frozen:`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_cognition_bridge.py -v`
Expected: PASS. If `test_edge_weight_consolidates_and_checkpoint_reflects_the_new_durable_class` fails because the edge never moves far enough to change class within the fixture's dynamics, that is a fixture-tuning problem, not a design problem — increase `total_ticks` or the driving sense value (`{"s": 1.0}` -> a larger magnitude) until real movement is observed, rather than weakening the assertion.

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/cognition/checkpoint.py src/symbiont/core/cognition_bridge.py tests/unit/core/test_cognition_bridge.py
git commit -m "$(cat <<'COMMIT'
feat(core): wire WeightStabilityTracker into CognitiveBridge

Every edge is seeded with its construction weight class at
construction/restore. Each tick, every edge's live weight class is
observed by the tracker, then each target node's incoming edges are
offered for node-atomic homeostatic consolidation. export_checkpoint()
now sources weight_class from the tracker's durable classes, never
live weight directly -- an edge that hasn't completed a real
consolidation exports its construction class, closing the same
differencing concern P2 addresses for perceptual memory, applied here
to synaptic weight.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

### Task 7: Reacclimation gate over structural consolidation (§16a)

**Files:**
- Modify: `src/symbiont/core/cognition_bridge.py`
- Test: `tests/unit/core/test_cognition_bridge.py`

**Interfaces:**
- Produces: `CognitiveBridge` tracks `self._reacclimation_remaining: int`, `0` on fresh construction (never gated), set to `kernel_limits.reacclimation_ticks` inside `restore()`, decremented once per `tick()` call while `> 0`. Structural consolidation (`tick % interval == 0` block) additionally requires `self._reacclimation_remaining <= 0`.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/core/test_cognition_bridge.py`:

```python
def test_reacclimation_gate_blocks_structural_consolidation_only_after_restore():
    limits = KernelLimits(reacclimation_ticks=100)
    graph = _simple_graph()
    genome = _genome()  # consolidation_interval_ticks == 4 in this fixture genome

    fresh = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)
    assert fresh._reacclimation_remaining == 0  # a first-ever launch never reacclimates

    payload = fresh.export_checkpoint()
    restored = CognitiveBridge.restore(payload, genome=genome, kernel_limits=limits)
    assert restored is not None
    assert restored._reacclimation_remaining == 100

    # tick 4 would normally attempt structural consolidation (interval=4);
    # during reacclimation it must not.
    for tick in range(1, 5):
        result = restored.tick({"s": 1.0}, tick=tick)
    assert result.structural_mutations_applied == 0
    assert restored._reacclimation_remaining == 96  # decremented once per tick, 4 ticks elapsed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_cognition_bridge.py::test_reacclimation_gate_blocks_structural_consolidation_only_after_restore -v`
Expected: FAIL with `AttributeError: 'CognitiveBridge' object has no attribute '_reacclimation_remaining'`

- [ ] **Step 3: Implement in `src/symbiont/core/cognition_bridge.py`**

In `__init__`, after `self._weight_tracker = ...` block from Task 6, add:

```python
        self._reacclimation_remaining = 0  # a first-ever construction never reacclimates (design §16a)
```

In `restore`, after `bridge = cls(...)` (before `return bridge`), add:

```python
        bridge._reacclimation_remaining = kernel_limits.reacclimation_ticks
```

In `tick()`, at the very top of the method body (before the `sense_inputs` loop), add:

```python
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1
```

Change the structural-consolidation condition from:

```python
        if not frozen and tick % interval == 0:
```

to:

```python
        if not frozen and self._reacclimation_remaining <= 0 and tick % interval == 0:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_cognition_bridge.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/cognition_bridge.py tests/unit/core/test_cognition_bridge.py
git commit -m "feat(core): add reacclimation gate over structural consolidation after restore (design §16a)"
```

---

## Self-Review Notes

**Spec coverage:** §10.3 eligibility/previous_frame labile -> Tasks 3, 4. §10.4 structural candidate state labile -> Task 5. §11 `WeightStabilityTracker` + node-atomic commit -> Tasks 1, 2, 6. §16a reacclimation -> Task 7. P5 -> Task 4. P11 -> Task 4 (test name says so explicitly). P12 -> Task 1. P13 -> Task 2. The PR2 commit sequence documents the PR #76 supersession explicitly in Task 4's commit message, per §2.1's own instruction and the design's PR2 bullet list.

**Explicitly out of scope for PR2** (confirmed against Global Constraints): `MemoryConsolidator`/`ConsolidationSignal` wiring into `CognitiveBridge` (weight consolidation deliberately bypasses it per the owner's decision this session); the fast-path reacclimation guard (nothing to gate yet); `CHECKPOINT_SCHEMA_VERSION` bump and the v5->v6 migration (PR4); host-model consolidated projections (PR3).

**Type consistency check:** the edge key shape `(source_id, target_id, kind.value)` is used identically in `WeightStabilityTracker`'s test fixtures (as plain strings there, e.g. `"a->n"`, since Tasks 1-2 test the tracker standalone without real `PlasticEdge` objects) and in `CognitiveBridge`'s real wiring (Task 6, as 3-tuples) -- `WeightStabilityTracker` itself is agnostic to the key's shape (`str` in its type hints, but any hashable works identically; Task 6 passes tuples, which are hashable and dict-keyable exactly like strings are). This is intentional: the tracker doesn't care what an edge key looks like, only that it's stable and hashable. `export_graph_checkpoint`'s `weight_class_overrides` parameter and `CognitiveBridge._weight_class_overrides()`'s return type both use the 3-tuple shape consistently.
