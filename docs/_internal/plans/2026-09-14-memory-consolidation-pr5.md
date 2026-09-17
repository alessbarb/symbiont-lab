# Biological Memory Consolidation — PR5 (Adversarial Integration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `MemoryConsolidator` (built standalone in PR1, never connected since PR2/PR3 gave weights and host statistics their own dedicated consolidation paths) into `OrganismRuntime`'s real tick loop for salient-event detection, then verify the full P1-P13 adversarial property list and the three canonical scenarios (§22) end to end through the real organism, and close the milestone.

**Architecture:** `OrganismRuntime` gains an always-on `MemoryConsolidator` (matching `HostAcclimation`/`RhythmModel`, which are also always-on). Each tick, for every capability with a fresh `DriftObservation`, a `ConsolidationSignal` is built from signals the organism already computes — `novelty_from_drift_kind(observation.kind)`, `surprise_from_loss` against a matching cognitive predictor's loss (0.0 if none, never fabricated), `attention` from this tick's real allocation selection, `reliability` from the same `health * availability` computation `CognitiveBridge` already receives — and offered to `MemoryConsolidator.observe(..., kind=SALIENT_EVENT, ...)`. This is the one remaining piece connecting the design's "flame" scenario to a real, running organism.

**Tech Stack:** Python 3.11+ stdlib only, matching the rest of this arc.

**Spec:** `docs/design/biological-memory-consolidation.md` (§6 signal derivation, §16a reacclimation, §21 P1-P13, §22 scenarios, §23 PR5, §25 exit conditions)

## Global Constraints

- `MemoryConsolidator`'s `STATISTICAL` and `STRUCTURAL` kinds are **not** wired in this PR: statistical host memory already has its own dedicated path (`consolidated_baseline`, PR3) and structural mutation already has its own dedicated gate (`StructuralPlasticity`, pre-existing). Only `SALIENT_EVENT` is wired here — this is disclosed explicitly, not a silent gap, because it is the correct outcome of PR2/PR3's own design choices, not an oversight.
- `surprise_from_loss` receives a real predictor's loss only when one exists targeting that exact percept/node; absent a predictor, surprise contributes `0.0` (never fabricated) — matching `CognitiveBridgeResult.prediction_errors`' existing `target_id` field.
- The §16a reacclimation gate, added in PR2 for structural consolidation only (because the fast path didn't exist yet), is extended in this PR to also block `SALIENT_EVENT` fast-path commits during `reacclimation_ticks` after a restore — restart itself must never be misread as an extraordinary event.
- `OrganismRuntime.checkpoint()` exports `MemoryConsolidator`'s own bounded `export_checkpoint()` output (salient traces only — never a raw reading, per P3) under a new top-level `"memory"` key; restore seeds it back via `MemoryConsolidator.restore_checkpoint`.
- No `CHECKPOINT_SCHEMA_VERSION` bump needed: `"memory"` is a brand-new top-level key, so an older payload simply omits it and `.get("memory")` returns `None`, which `MemoryConsolidator.restore_checkpoint(None, ...)` already handles as "start empty" (`src/symbiont/core/consolidation.py:292-293`, `if payload is None: return consolidator`).
- After this PR, `src/symbiont/__init__.py`'s `__version__` becomes `"0.59.5"`, matching the design's own version numbering, per this project's established one-version-bump-per-completed-milestone convention.

---

### Task 1: Wire MemoryConsolidator into OrganismRuntime for salient-event detection

**Files:**

- Modify: `src/symbiont/core/runtime.py`
- Test: `tests/unit/core/test_organism_runtime.py`

**Interfaces:**

- Consumes: `MemoryConsolidator`, `MemoryKind`, `ConsolidationSignal`, `novelty_from_drift_kind`, `surprise_from_loss` (all from `src/symbiont/core/consolidation.py`, PR1).
- Produces: `OrganismRuntime.__init__` gains `memory_consolidator: MemoryConsolidator | None = None` (auto-created from `self._kernel_limits` if not given, matching `HostAcclimation`'s own always-on default); `OrganismRuntime.memory_consolidator` read-only property; `OrganismRuntime.checkpoint()`/`.from_checkpoint()` round-trip a new `"memory"` key.

Real API check (read `src/symbiont/core/consolidation.py` and `src/symbiont/host/drift.py` in full before writing this step): `MemoryConsolidator(kernel_limits=...)`, `.observe(key, kind, signal, *, tick=...)` returns `ConsolidationOutcome(path="fast"|"slow", ...)`, `.export_checkpoint()` returns `{"statistical": {...}, "salient_events": [{"pattern_id", "novelty_class", "surprise_class", "reliability_class", "context_class", "recurrence_class"}, ...]}`, `.restore_checkpoint(None, kernel_limits=...)` returns an empty consolidator. `DriftAwareBaseline` has no `min_samples=` kwarg on `.restore()` and no way to force a class synthetically — a real `REGIME_SHIFT` must come from real `.observe()` calls with constructed values, exactly the way `tests/unit/core/test_organism_runtime.py:224-226` already forces deterministic snapshots via `runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: snapshot)`. `KernelLimits()` defaults: `fast_consolidation_threshold=0.80`, `fast_min_reliability=0.60`. Given the score weights (novelty 0.20, surprise 0.30, attention 0.20, reliability 0.20, coherence 0.10, and this PR pins coherge=0.0), a `REGIME_SHIFT` alone (novelty=0.90) with full attention and reliability=1.0 but **no** cognitive-bridge surprise caps at `0.58` — below threshold. This is by design (surprise carries the largest weight, matching the design's own emphasis on prediction error over raw drift) but means Scenario A's test must supply a real prediction error, not just a drift class. `CognitiveBridgeResult` (`src/symbiont/core/cognition_bridge.py`) is `@dataclass(slots=True, frozen=True)`, so `dataclasses.replace(result, prediction_errors=(...))` works to inject an extra `PredictionError(predictor_id, target_id, error, loss)` (`src/symbiont/cognition/learning.py`) onto a real bridge's output without hand-rolling the rest of the result.

- [ ] **Step 1: Write the failing tests**

Add this shared helper and the four tests to `tests/unit/core/test_organism_runtime.py`:

```python
def _drive_regime_shift_with_surprise(runtime, *, capability_id="compute.logical_cpu", stable_value=10.0, extreme_value=1000.0, extra_loss=1.0, stable_ticks=5, extreme_ticks=3):
    """Deterministically forces a real DriftKind.REGIME_SHIFT on `capability_id`
    (percept name "system_load" via DEFAULT_PERCEPT_NAMES) while also injecting
    a high-loss PredictionError for that same node, so the combined signal's
    score can cross fast_consolidation_threshold -- exactly the scenario the
    design calls "flame" (§22). Uses the same _lifecycle-override pattern as
    test_attention_always_allocates_at_least_one_capability_once_known (this
    file, line ~217), not scripted drift-baseline internals."""
    from types import SimpleNamespace
    import dataclasses

    from symbiont.cognition.learning import PredictionError
    from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
    from symbiont.host.lifecycle import LifecycleSnapshot
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

    def reading(value):
        return SensorReading(
            capability_id=capability_id, source="fixture", value=value, unit=Unit.COUNT,
            monotonic_timestamp_ns=1, quality=ReadingQuality.NOMINAL, privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    manifest = HostManifest(1, (Capability(capability_id, CapabilityKind.SIGNAL, "fixture"),), ())
    stable_snapshot = LifecycleSnapshot(1, manifest, (reading(stable_value),), (), (), (capability_id,))
    extreme_snapshot = LifecycleSnapshot(1, manifest, (reading(extreme_value),), (), (), (capability_id,))

    real_bridge = runtime.cognitive_bridge
    if real_bridge is not None:
        original_tick = real_bridge.tick

        def boosted_tick(*args, **kwargs):
            result = original_tick(*args, **kwargs)
            boosted = result.prediction_errors + (
                PredictionError(predictor_id="synthetic", target_id="system_load", error=extra_loss, loss=extra_loss),
            )
            return dataclasses.replace(result, prediction_errors=boosted)

        runtime._cognitive_bridge = SimpleNamespace(tick=boosted_tick, restore=real_bridge.restore, export_checkpoint=real_bridge.export_checkpoint, graph=real_bridge.graph)
    else:
        fake_result = SimpleNamespace(
            prediction_errors=(PredictionError(predictor_id="synthetic", target_id="system_load", error=extra_loss, loss=extra_loss),),
        )
        runtime._cognitive_bridge = SimpleNamespace(tick=lambda *a, **k: fake_result)

    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: stable_snapshot)
    for _ in range(stable_ticks):
        runtime.tick()

    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: extreme_snapshot)
    result = None
    for _ in range(extreme_ticks):
        result = runtime.tick()
    return result


def test_a_single_extraordinary_regime_shift_creates_a_durable_salient_trace():
    """Scenario A ('flame'), design §22: a real regime shift combined with a
    real high-loss prediction error commits a SalientEventTrace, verified
    through the actual OrganismRuntime.tick() wiring, not a bare consolidator
    call."""
    from symbiont.host.drift import DriftKind

    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    result = _drive_regime_shift_with_surprise(runtime)

    assert result.drift_observations["system_load"].kind == DriftKind.REGIME_SHIFT
    checkpoint = runtime.checkpoint()
    assert len(checkpoint["memory"]["salient_events"]) == 1
    assert checkpoint["memory"]["salient_events"][0]["pattern_id"] == "system_load"


def test_p3_salient_trace_never_contains_a_raw_reading():
    """P3: a fast salient event may change durable memory after one tick,
    but persisted fields are only bounded categorical classes and safe ids
    -- never the extreme raw value (1000.0) or exact loss (1.0) that
    triggered it."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    _drive_regime_shift_with_surprise(runtime)

    checkpoint = runtime.checkpoint()
    traces = checkpoint["memory"]["salient_events"]
    assert traces  # the scenario above is proven to commit at least one trace
    for trace in traces:
        for key, value in trace.items():
            if key == "pattern_id":
                continue
            assert isinstance(value, int) and 0 <= value <= 15
    encoded = str(checkpoint["memory"])
    assert "1000.0" not in encoded
    assert "1000" not in encoded


def test_p8_low_reliability_sense_cannot_create_a_one_shot_trace():
    """Scenario C ('noisy sensor'), design §21 P8: a signal whose reliability
    sits below fast_min_reliability must never commit a fast trace even when
    the other four dimensions alone would already clear the score
    threshold -- proving the explicit reliability gate does real work beyond
    what the weighted score already enforces."""
    from symbiont.core.consolidation import ConsolidationSignal, MemoryKind

    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    borderline_unreliable = ConsolidationSignal(novelty=1.0, surprise=1.0, attention=1.0, reliability=0.59, coherence=1.0)
    assert borderline_unreliable.score() >= runtime._kernel_limits.fast_consolidation_threshold
    outcome = runtime.memory_consolidator.observe("noisy_percept", MemoryKind.SALIENT_EVENT, borderline_unreliable, tick=1)
    assert outcome.path == "slow"
    assert runtime.memory_consolidator.salient_events == ()


def test_reacclimation_gate_blocks_salient_fast_path_after_restore():
    """§16a extended: the exact scenario A signal, replayed immediately
    after a restore, must NOT commit while reacclimation is active, and
    MUST commit once the reacclimation window has elapsed -- proving the
    gate is real, not merely absent evidence of firing."""
    from symbiont.cognition.limits import KernelLimits

    limits = KernelLimits(reacclimation_ticks=20)
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0, kernel_limits=limits)
    checkpoint = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0, kernel_limits=limits)

    _drive_regime_shift_with_surprise(restored, stable_ticks=1, extreme_ticks=3)
    gated_checkpoint = restored.checkpoint()
    assert gated_checkpoint["memory"]["salient_events"] == []

    for _ in range(20):
        restored.tick()
    _drive_regime_shift_with_surprise(restored, capability_id="compute.logical_cpu", stable_value=10.0, extreme_value=2000.0, stable_ticks=1, extreme_ticks=3)
    reacclimated_checkpoint = restored.checkpoint()
    assert len(reacclimated_checkpoint["memory"]["salient_events"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k "salient or p3_salient or p8_low_reliability or reacclimation_gate_blocks_salient"`
Expected: FAIL — `AttributeError: 'OrganismRuntime' object has no attribute 'memory_consolidator'`, and `"memory" in checkpoint` is `False`

- [ ] **Step 3: Implement in `src/symbiont/core/runtime.py`**

Add the import:

```python
from ..core.consolidation import ConsolidationSignal, MemoryConsolidator, MemoryKind, novelty_from_drift_kind, surprise_from_loss
```

(Use a relative import matching this file's own existing style, e.g. `from .consolidation import ...` since `consolidation.py` lives in the same `core/` package as `runtime.py` -- check the exact existing import style for same-package siblings in this file before finalizing, and match it exactly.)

In `__init__`, add the parameter `memory_consolidator: MemoryConsolidator | None = None` to the signature, and after `self._genome = genome` (or any similarly early, always-executed line), add:

```python
        self._memory_consolidator = (
            memory_consolidator if memory_consolidator is not None else MemoryConsolidator(kernel_limits=self._kernel_limits)
        )
        self._reacclimation_remaining = 0  # matches CognitiveBridge's own §16a semantics
```

Add the property:

```python
    @property
    def memory_consolidator(self) -> MemoryConsolidator:
        return self._memory_consolidator
```

Find wherever this class already exposes a `restore`-driven reacclimation concept for `CognitiveBridge` (there is none at the `OrganismRuntime` level yet -- this PR introduces the runtime's own copy of the same concept, independent of `CognitiveBridge`'s, since salient-event detection is a sensory-layer concern that exists even without cognition wired up). Add a small helper:

```python
    def _reacclimation_ticks_remaining(self) -> int:
        return self._reacclimation_remaining
```

In `tick()`, add near the top (mirroring `CognitiveBridge.tick()`'s own decrement):

```python
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1
```

Locate the block computing `availability_by_capability` (currently defined only inside `if self._cognitive_bridge is not None:`). Move that computation out to always run (it is a cheap dict comprehension over already-available `self._adaptive_senses.states`), immediately before the `cognition_result: CognitiveBridgeResult | None = None` line:

```python
        availability_by_capability = {
            state.capability_id: state.availability for state in self._adaptive_senses.states
        }
```

Remove the now-duplicate inner definition inside the `if self._cognitive_bridge is not None:` block.

After the `cognition_result = ...` assignment (both the `if` branch and falling through when `self._cognitive_bridge is None`), add the salient-event detection pass, before the `investigated_capability: str | None = None` line:

```python
        if not self._reacclimation_remaining:
            attended_capability_ids = {allocation.name for allocation in allocations}
            capability_by_percept_name = {name: capability_id for capability_id, name in percept_names.items()}
            prediction_loss_by_node: dict[str, float] = {}
            if cognition_result is not None:
                for error in cognition_result.prediction_errors:
                    prediction_loss_by_node[error.target_id] = error.loss

            for percept_name, observation in drift_observations.items():
                capability_id = capability_by_percept_name.get(percept_name)
                novelty = novelty_from_drift_kind(observation.kind)
                surprise = surprise_from_loss(prediction_loss_by_node.get(percept_name))
                attention = 1.0 if capability_id in attended_capability_ids else 0.0
                availability = availability_by_capability.get(capability_id, 1.0) if capability_id else 1.0
                health = (
                    self._self_model.health(capability_id, current_tick=self._tick_count)
                    if capability_id is not None
                    else 0.5
                )
                reliability = max(0.0, min(1.0, availability * health))
                signal = ConsolidationSignal(
                    novelty=novelty, surprise=surprise, attention=attention, reliability=reliability, coherence=0.0
                )
                self._memory_consolidator.observe(
                    percept_name, MemoryKind.SALIENT_EVENT, signal, tick=self._tick_count + 1
                )
```

`coherence=0.0` is a disclosed simplification: design §6.5's epoch-spaced independent-support model for coherence is not wired to any real cross-tick bookkeeping in this PR (only the fast path is exercised here; coherence only affects the slow path's score, which nothing in this PR routes through `STATISTICAL`/`STRUCTURAL` kinds anyway per this PR's own Global Constraints).

In `checkpoint()`, add:

```python
        payload["memory"] = self._memory_consolidator.export_checkpoint()
```

In `from_checkpoint`, after the existing model-restoration calls, add:

```python
        memory_consolidator = MemoryConsolidator.restore_checkpoint(normalized.get("memory"), kernel_limits=kernel_limits)
```

and pass `memory_consolidator=memory_consolidator` into the final `cls(...)` constructor call. Also set the newly-restored runtime's reacclimation window the same way `CognitiveBridge.restore` does -- after the `cls(...)` call returns (assign to the local variable holding the constructed runtime before it is returned), set:

```python
        runtime._reacclimation_remaining = kernel_limits.reacclimation_ticks
```

(match whatever the constructed-and-about-to-be-returned local variable is actually named in this method -- check the real code before writing this line, since it must assign onto the actual returned instance, not a throwaway.)

- [ ] **Step 4: Run tests to verify they pass, rewriting the reacclimation test's final assertion per Step 1's own note**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k "salient or p3_salient or p8_low_reliability or reacclimation_gate_blocks_salient"`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/runtime.py tests/unit/core/test_organism_runtime.py
git commit -m "$(cat <<'COMMIT'
feat(core): wire MemoryConsolidator into OrganismRuntime for salient-event detection

The one remaining unwired piece from PR1: MemoryConsolidator's
STATISTICAL and STRUCTURAL kinds are correctly superseded by PR3's
consolidated_baseline and the pre-existing StructuralPlasticity gate,
but SALIENT_EVENT had no real caller anywhere. Every tick, each
percept with a fresh DriftObservation gets a ConsolidationSignal built
from signals the organism already computes -- novelty from drift kind,
surprise from a matching predictor's loss (0.0 if none), attention
from this tick's real allocation, reliability from the same
health*availability CognitiveBridge already receives -- offered to the
consolidator's fast path. Checkpoint exports/restores the consolidator
via a new top-level "memory" key. The §16a reacclimation gate (PR2,
structural-only until now) is extended to also block the salient
fast path after a restore.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

### Task 2: Scenario B (street name) and remaining adversarial properties end to end

**Files:**

- Test: `tests/unit/core/test_organism_runtime.py`

**Interfaces:**

- Consumes: `OrganismRuntime.memory_consolidator` (Task 1).

- [ ] **Step 1: Write the tests**

```python
def test_scenario_b_ordinary_operation_never_fast_paths_without_a_predictor():
    """Scenario B ('street name'), design §22: an ordinary residence with no
    cognitive predictor wired can only ever contribute novelty+attention+
    reliability to the score (surprise pinned to 0 absent a predictor,
    coherence pinned to 0 per this PR's Global Constraints). Given the score
    weights (0.20/0.30/0.20/0.20/0.10), the maximum reachable score without
    a predictor is 0.20*1 + 0.20*1 + 0.20*1 = 0.60, always below
    fast_consolidation_threshold (0.80) -- so ordinary drift, however
    extreme, can never fast-path on its own. This is a real, falsifiable
    consequence of the weights, not a tautology of MemoryConsolidator's own
    bound (see test_p10 below for that one)."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    for _ in range(60):
        runtime.tick()
    checkpoint = runtime.checkpoint()
    assert checkpoint["memory"]["salient_events"] == []


def test_p9_salient_trace_never_mutates_structure_by_itself():
    """P9: driving the exact scenario-A fast-path commit through the real
    OrganismRuntime.tick() wiring, with a real genome/graph attached, must
    never add or remove a graph edge or node -- MemoryConsolidator has no
    structural API to call, so this guards against a future wiring mistake
    that accidentally connects the two."""
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind

    genome_payload = {
        "schema_version": 1, "genome_id": "genome_p9test0000000000000000000", "parent_ids": [],
        "kernel_compatibility": ">=0.55,<0.60",
        "development": {"initial_concepts": 4, "soft_node_budget": 64, "soft_edge_budget": 384, "consolidation_interval_ticks": 4},
        "plasticity": {"learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08}, "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005}, "eligibility_decay": 0.9},
        "structure": {"grow_threshold": 0.18, "prune_threshold": 0.01, "minimum_support": 16, "tentative_lifetime_ticks": 128},
        "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
    }
    limits = KernelLimits()
    genome = GenomeCodec().load(genome_payload)
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="system_load", kind=NodeKind.SENSE), PlasticNode(node_id="c", kind=NodeKind.CONCEPT)),
        edges=(PlasticEdge(source_id="system_load", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),),
        kernel_limits=limits,
    )
    runtime = OrganismRuntime(
        discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0,
        genome=genome, kernel_limits=limits, cognitive_graph=graph,
    )
    edge_count_before = len(runtime.cognitive_bridge.graph.edges)
    node_count_before = len(runtime.cognitive_bridge.graph.nodes)

    _drive_regime_shift_with_surprise(runtime)
    assert runtime.memory_consolidator.salient_events  # the commit really happened

    assert len(runtime.cognitive_bridge.graph.edges) == edge_count_before
    assert len(runtime.cognitive_bridge.graph.nodes) == node_count_before


def test_p10_memory_stays_bounded_over_a_long_real_residence():
    """P10 end to end: candidates, salient traces and all durable
    projections respect kernel limits under a long real run, not just the
    standalone consolidator (already covered in PR1)."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    for _ in range(300):
        runtime.tick()
    checkpoint = runtime.checkpoint()
    assert len(checkpoint["memory"]["salient_events"]) <= runtime._kernel_limits.max_salient_event_traces
    assert len(checkpoint["memory"]["statistical"]) <= runtime._kernel_limits.max_consolidation_candidates
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k "scenario_b or p9_salient or p10_memory_stays_bounded"`
Expected: PASS (these exercise Task 1's wiring against real, longer runs -- if any fails, it is a real bug in Task 1's integration, not a plan error, since all three properties are load-bearing exit conditions)

- [ ] **Step 3: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/unit/core/test_organism_runtime.py
git commit -m "test(core): verify scenario B, P9 and P10 end to end through a real OrganismRuntime"
```

---

### Task 3: Close the milestone — version bump and documentation

**Files:**

- Modify: `src/symbiont/__init__.py`
- Modify: `pyproject.toml`
- Modify: `docs/roadmap.md`
- Modify: `README.md`
- Modify: `ORGANISM.md`

**Interfaces:**

- Produces: `__version__ = "0.59.5"`; `docs/roadmap.md`'s Milestone E2 exit-condition checklist confirmed complete; `README.md`/`ORGANISM.md` changelog entries for v0.59.5.

- [ ] **Step 1: Bump the version**

In `src/symbiont/__init__.py`, change `__version__ = "0.59.4"` to `__version__ = "0.59.5"`.

In `pyproject.toml`, change `version = "0.59.4"` to `version = "0.59.5"` under `[project]`.

- [ ] **Step 2: Run the full suite to confirm the version bump breaks nothing**

Run: `pytest -q`
Expected: PASS (check specifically for any test asserting the exact version string, e.g. `grep -rn '0\.59\.4' tests/`, and update any that hardcode the old version)

- [ ] **Step 3: Update `docs/roadmap.md`**

Find the "## Milestone E2 — Endogenous plasticity" section's exit conditions list (already present from this session's earlier work) and add a note that v0.59.5 (biological memory consolidation) is a completed follow-on hardening pass, listing its own exit conditions from `docs/design/biological-memory-consolidation.md` §25 as satisfied. Follow this file's existing prose style (see how "Post-milestone hardening" language was used for v0.59.1-v0.59.3 in `README.md`/`ORGANISM.md` earlier this session) rather than inventing a new format.

- [ ] **Step 4: Update `README.md` and `ORGANISM.md`**

Both files currently end their organism changelog at "Post-milestone hardening (v0.59.1-v0.59.3)" (per this session's earlier README rewrite). Add a new paragraph, in the same narrative style as the existing changelog entries (see the existing Milestone E2 paragraph for the expected voice and level of technical detail), covering v0.59.5: the shift from "serialize learned state" to "persist consolidated memory" (design `docs/design/biological-memory-consolidation.md`), `WeightStabilityTracker`'s epoch-spaced class stability, the deliberate supersession of PR #76's microstate-continuity guarantee (§2.1), the consolidated-baseline codec for host statistics, `SelfModel`'s `RecencyClass`, checkpoint schema v6, and `MemoryConsolidator`'s salient-event fast path finally wired into the real tick loop. Keep it to one paragraph per file, matching the existing density (see the v0.55-v0.59 paragraphs for length/tone).

`ORGANISM.md` and `README.md` should carry the same substantive content (the user asked for `ORGANISM.md` to be kept in sync when it was split out from `README.md` earlier this session) -- write the paragraph once and place equivalent text in both files, adjusting only cross-reference links if the two files' relative paths to `docs/design/...` differ.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/__init__.py pyproject.toml docs/roadmap.md README.md ORGANISM.md
git commit -m "$(cat <<'COMMIT'
chore(release): advance Symbiont to v0.59.5 (biological memory consolidation)

Closes the design docs/design/biological-memory-consolidation.md arc:
checkpoint schema v6, consolidated host statistics, WeightStabilityTracker,
SelfModel RecencyClass, and MemoryConsolidator's salient-event fast path
wired into the real tick loop. Updates README.md/ORGANISM.md/roadmap.md
to reflect the completed milestone.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

## Self-Review Notes

**Spec coverage:** §22 Scenario A -> Task 1. Scenario B -> Task 2. Scenario C / P8 -> Task 1. P3 -> Task 1. P9 -> Task 2. P10 (end to end) -> Task 2. §16a extended reacclimation -> Task 1. §25 exit conditions -> Task 3 (documentation confirms each is now demonstrably true given PR1-5's cumulative work).

**Explicitly out of scope, disclosed, not silently dropped:** `MemoryConsolidator`'s `STATISTICAL`/`STRUCTURAL` kinds stay unwired (superseded by dedicated mechanisms built in PR2/PR3/pre-existing `StructuralPlasticity`); `coherence` stays pinned at `0.0` in the wired signal (no real epoch-spaced independent-support bookkeeping connected in this PR); an Observatory projection of memory commit counts, explicitly marked *optional* in the design's own PR5 bullet, is skipped in this plan to avoid colliding with concurrent, unrelated Observatory frontend work already in progress in this repository.

**Type consistency check:** `ConsolidationSignal`/`MemoryKind`/`novelty_from_drift_kind`/`surprise_from_loss` (Task 1's import) are the exact names defined in `src/symbiont/core/consolidation.py` since PR1 -- no renaming has occurred across PR1-4. `OrganismRuntime.memory_consolidator` (Task 1) is consumed identically in Task 2's tests.
