# Biological Memory Consolidation — PR4 (Schema v6 and Migration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize the consolidated-memory shape PR1-3 already built as `CHECKPOINT_SCHEMA_VERSION = 6`, add a real `_migrate_v5_to_v6` step that converts any real historical v5 checkpoint (exact acclimation/rhythm/drift stats, exact `self_model.last_observed_tick`) into the new consolidated shape, and retire PR3's temporary dual-read fallback now that migration handles the boundary properly.

**Architecture:** One new migration function, registered in the existing `_MIGRATIONS` chain exactly like `_migrate_v4_to_v5` before it. `host/checkpoint.py`'s `_baseline_from_stats_entry` goes back to single-path (only the new shape) since `normalize_checkpoint` now guarantees every payload reaching it is already v6-shaped.

**Tech Stack:** Python 3.11+ stdlib only, matching the existing migration chain's style.

**Spec:** `docs/design/biological-memory-consolidation.md` (§14 v5->v6 migration, §23 PR4)

## Global Constraints

- `CHECKPOINT_SCHEMA_VERSION` becomes `6`.
- Migration is a **privacy-reducing projection**, not lossless (design §14): a v5 payload's exact acclimation/rhythm/drift stats become consolidated classes; nothing exact is preserved through it.
- `self_model`'s `last_observed_tick` -> `recency_class` conversion in the migration uses the same `idle_ticks = max(0, saved_at_tick - last_observed_tick)` -> `RecencyClass` mapping `SelfModel.export()` itself uses, so a migrated entry's recency reads exactly as if it had been exported by the current code at the time it was actually saved (this is the one migration step in this PR that legitimately derives from real per-organism history, because it is converting the *same organism's own* prior real export, not inventing a new organism's history — unlike PR2/PR3's restore-time seeding, which intentionally does not do this for genuinely fresh restores).
- The migration must never re-export the exact v5 aggregate after it has crossed into v6 (design §14) — `_migrate_v5_to_v6` converts in place and only ever emits the new shape.
- `host/checkpoint.py`'s `_baseline_from_stats_entry` reverts to single-path (new shape only) once migration is in place — the temporary PR3 dual-read fallback is removed, not left as permanent dead weight.
- Every hardcoded literal schema-version assertion (`== 5`) across the test suite is updated to `== 6`; assertions already using the `CHECKPOINT_SCHEMA_VERSION` symbol need no change.

---

### Task 1: `_migrate_v5_to_v6` and the version bump

**Files:**
- Modify: `src/symbiont/host/checkpoint.py`
- Modify: `tests/unit/host/test_checkpoint.py`
- Modify: `tests/unit/core/test_resident_continuity.py`
- Modify: `tests/smoke/test_cli.py`
- Test: `tests/unit/host/test_checkpoint.py`

**Interfaces:**
- Produces: `CHECKPOINT_SCHEMA_VERSION = 6`; `_migrate_v5_to_v6(payload: dict[str, Any]) -> dict[str, Any]` registered in `_MIGRATIONS`; `_baseline_from_stats_entry` simplified to single-path.

- [ ] **Step 1: Write the failing regression test for the real self_model crash**

Add to `tests/unit/host/test_checkpoint.py`:

```python
def test_v5_self_model_with_exact_last_observed_tick_migrates_without_crashing():
    """Real regression: PR3 changed SelfModel.restore() to require
    recency_class, but no migration step existed for a genuine historical
    v5 checkpoint's exact last_observed_tick -- this crashed with a raw
    KeyError, not even a clean CheckpointError, before this task."""
    from symbiont.core.selfmodel import RecencyClass, SelfModel

    v5_payload = {
        "schema_version": 5,
        "saved_at_tick": 100,
        "self_model": {
            "cpu": {
                "cost_class": 0, "health_class": 8, "confidence_class": 8, "maturity_class": 4,
                "last_observed_tick": 90,
            },
        },
    }
    migrated = normalize_checkpoint(v5_payload)
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    entry = migrated["self_model"]["cpu"]
    assert "last_observed_tick" not in entry
    assert entry["recency_class"] == RecencyClass.CURRENT.value  # idle 10 ticks, within grace

    restored = SelfModel.restore(migrated["self_model"], allowed_sense_ids={"cpu"}, current_tick=100)
    assert restored.is_established("cpu")


def test_v5_acclimation_with_exact_stats_migrates_to_consolidated_classes():
    v5_payload = {
        "schema_version": 5,
        "acclimation": {"cpu": {"count": 20, "mean": 10.0, "variance": 0.04}},
        "rhythms": [{"percept_name": "cpu", "time_bucket": "night", "count": 10, "mean": 5.0, "variance": 1.0}],
        "drift": {"cpu": {"count": 30, "mean": 10.0, "variance": 0.04}},
    }
    migrated = normalize_checkpoint(v5_payload)
    assert set(migrated["acclimation"]["cpu"]) == {"center_class", "scale_class", "maturity_class"}
    assert set(migrated["rhythms"][0]) == {"percept_name", "time_bucket", "center_class", "scale_class", "maturity_class"}
    assert set(migrated["drift"]["cpu"]) == {"center_class", "scale_class", "maturity_class"}

    acclimation, rhythm_model, drift_baselines = import_checkpoint(migrated)
    assert acclimation.baseline("cpu") is not None
    assert drift_baselines["cpu"].is_established or drift_baselines["cpu"].count > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/host/test_checkpoint.py -v -k v5_self_model_or_v5_acclimation`
Expected: FAIL — `test_v5_self_model_with_exact_last_observed_tick_migrates_without_crashing` fails with the raw `KeyError: 'recency_class'` (or an unhandled exception from `normalize_checkpoint`/`SelfModel.restore`), and `test_v5_acclimation_with_exact_stats_migrates_to_consolidated_classes` fails because `migrated["acclimation"]["cpu"]` still has the old `{count, mean, variance}` shape (no migration step exists yet)

- [ ] **Step 3: Implement `_migrate_v5_to_v6` in `src/symbiont/host/checkpoint.py`**

Add the import:

```python
from .consolidated_baseline import consolidate_baseline
```

(This is likely already imported from Task 2 of PR3 — check first with `grep -n "consolidated_baseline" src/symbiont/host/checkpoint.py` and only add what's missing.)

Add near the top, after `CHECKPOINT_SCHEMA_VERSION`:

```python
from ..core.selfmodel import RecencyClass, _recency_class  # local import avoids a host->core cycle at module load
```

Actually place this import **inside** `_migrate_v5_to_v6` itself, not at module scope — `symbiont.core` imports from `symbiont.host` elsewhere (e.g. `core/runtime.py`), so a module-level `host -> core` import would create a real circular import. Confirm this by checking `grep -n "^from \.\.host\|^from symbiont.host" src/symbiont/core/*.py` before writing the import, and if `_recency_class` is not already accessible the way this snippet assumes, import `RecencyClass` and re-derive the idle-ticks-to-class mapping locally in this module instead of reaching into `core.selfmodel`'s private helper — whichever avoids the cycle and avoids duplicating logic unnecessarily; prefer importing the small set of public names (`RecencyClass`) and, if `_recency_class` truly must stay private, inline the same four-threshold comparison here with a one-line comment noting it mirrors `SelfModel`'s own mapping.

Change `CHECKPOINT_SCHEMA_VERSION`:

```python
CHECKPOINT_SCHEMA_VERSION = 6
```

Add after `_migrate_v4_to_v5`:

```python
def _migrate_acclimation_style_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if "center_class" in entry:
        return entry
    seed = consolidate_baseline(CapabilityBaseline(count=entry["count"], mean=entry["mean"], variance=entry["variance"]))
    return _seed_payload(seed)


def _migrate_v5_to_v6(payload: dict[str, Any]) -> dict[str, Any]:
    """v6 makes the biological-memory-consolidation model (design
    docs/design/biological-memory-consolidation.md) the durable checkpoint
    shape. This is a privacy-reducing projection, not a lossless migration
    (§14): exact acclimation/rhythm/drift aggregates become consolidated
    classes, and self_model's exact last_observed_tick becomes a
    RecencyClass computed from this checkpoint's own saved_at_tick -- the
    one migration step in this chain that legitimately derives from real
    per-organism history, since it is re-deriving the *same* organism's own
    already-recorded state at the moment it was actually saved, not
    fabricating a fresh restart's history.
    """
    migrated = dict(payload)
    migrated["schema_version"] = 6
    saved_at_tick = migrated.get("saved_at_tick") or 0

    raw_acclimation = migrated.get("acclimation")
    if isinstance(raw_acclimation, dict):
        migrated["acclimation"] = {
            capability_id: _migrate_acclimation_style_entry(entry)
            for capability_id, entry in raw_acclimation.items()
            if isinstance(entry, dict)
        }

    raw_rhythms = migrated.get("rhythms")
    if isinstance(raw_rhythms, list):
        migrated_rhythms = []
        for entry in raw_rhythms:
            if not isinstance(entry, dict):
                continue
            stats = {key: value for key, value in entry.items() if key not in ("percept_name", "time_bucket")}
            converted = _migrate_acclimation_style_entry(stats)
            migrated_rhythms.append({"percept_name": entry["percept_name"], "time_bucket": entry["time_bucket"], **converted})
        migrated["rhythms"] = migrated_rhythms

    raw_drift = migrated.get("drift")
    if isinstance(raw_drift, dict):
        migrated["drift"] = {
            name: _migrate_acclimation_style_entry(entry)
            for name, entry in raw_drift.items()
            if isinstance(entry, dict)
        }

    raw_self_model = migrated.get("self_model")
    if isinstance(raw_self_model, dict):
        migrated_self_model = {}
        for sense_id, entry in raw_self_model.items():
            if not isinstance(entry, dict):
                continue
            if "last_observed_tick" in entry and "recency_class" not in entry:
                idle_ticks = max(0, saved_at_tick - entry["last_observed_tick"])
                entry = {key: value for key, value in entry.items() if key != "last_observed_tick"}
                entry["recency_class"] = _idle_ticks_to_recency_class(idle_ticks).value
            migrated_self_model[sense_id] = entry
        migrated["self_model"] = migrated_self_model

    return migrated
```

Add the small local helper (used only if `core.selfmodel._recency_class` can't be imported without a cycle -- verify first per Step 3's own instruction above; if the import works cleanly, skip defining this and call the imported function directly instead):

```python
def _idle_ticks_to_recency_class(idle_ticks: int) -> "RecencyClass":
    from ..core.selfmodel import RecencyClass  # local import: avoids a host->core module-load cycle

    thresholds = (
        (10, RecencyClass.CURRENT),
        (40, RecencyClass.SHORT_IDLE),
        (120, RecencyClass.IDLE),
        (400, RecencyClass.LONG_IDLE),
    )
    for threshold, recency in thresholds:
        if idle_ticks < threshold:
            return recency
    return RecencyClass.DORMANT
```

Register it:

```python
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
    4: _migrate_v4_to_v5,
    5: _migrate_v5_to_v6,
}
```

Simplify `_baseline_from_stats_entry` back to single-path (the dual-read was a temporary PR3 shim; migration now guarantees the new shape by the time this runs):

```python
def _baseline_from_stats_entry(entry: dict[str, Any]) -> CapabilityBaseline:
    return seed_capability_baseline(_seed_from_payload(entry))
```

- [ ] **Step 4: Fix the hardcoded literal schema-version assertions**

In `tests/unit/host/test_checkpoint.py`: change `assert CHECKPOINT_SCHEMA_VERSION == 5` to `assert CHECKPOINT_SCHEMA_VERSION == 6`, and `assert migrated["schema_version"] == 5` (the one in the v4-migration test, which asserts the *intermediate* v5 result of a single migration step -- check its context: if that test still calls only `_migrate_v4_to_v5` directly rather than the full `normalize_checkpoint` chain, `5` is still correct there and must NOT be changed; only change it if the test's own comment/intent was "the final current version").

In `tests/unit/core/test_resident_continuity.py`: change `assert normalized["schema_version"] == 5` to `assert normalized["schema_version"] == 6`.

In `tests/smoke/test_cli.py`: change both `assert checkpoint["schema_version"] == 5` and `assert payload["checkpoint"]["schema_version"] == 5` to `== 6`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/host/test_checkpoint.py tests/unit/core/test_resident_continuity.py tests/smoke/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/host/checkpoint.py tests/unit/host/test_checkpoint.py tests/unit/core/test_resident_continuity.py tests/smoke/test_cli.py
git commit -m "$(cat <<'COMMIT'
feat(host): add checkpoint schema v6 and the v5->v6 consolidation migration

CHECKPOINT_SCHEMA_VERSION becomes 6. _migrate_v5_to_v6 converts a real
historical v5 checkpoint's exact acclimation/rhythm/drift stats into
consolidated classes, and self_model's exact last_observed_tick into a
RecencyClass derived from that checkpoint's own saved_at_tick -- the
one migration step in this chain that legitimately derives from real
per-organism history, since it re-derives the same organism's own
already-recorded state, not a fresh restart's fabricated one.

Fixes a real regression found while planning this task: PR3 changed
SelfModel.restore() to require recency_class with no migration path,
so any genuine historical v5 checkpoint crashed on restore with a raw
KeyError. host/checkpoint.py's temporary PR3 dual-read fallback for
acclimation/rhythm/drift is retired now that migration handles the
boundary properly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
COMMIT
)"
```

---

### Task 2: Lock P4 (shutdown cannot force consolidation) and checkpoint byte bound end to end

**Files:**
- Test: `tests/unit/core/test_organism_runtime.py` (check the exact filename with `ls tests/unit/core/ | grep -i runtime` first)

**Interfaces:**
- Consumes: `OrganismRuntime` (existing).
- Produces: no new production code -- this task only adds end-to-end regression tests locking two properties the design's PR4 bullet list calls for explicitly, both of which should already hold given PR1-3's implementation, but were never verified end to end through the real `OrganismRuntime.checkpoint()`/`.save()` path.

- [ ] **Step 1: Write the tests**

```python
def test_p4_repeated_checkpoint_calls_never_force_consolidation():
    """P4/design §12.2: OrganismRuntime.checkpoint() is a pure export --
    calling it many times in a row must never itself advance any
    consolidation state."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    for tick in range(1, 6):
        runtime.tick()
    first = runtime.checkpoint()
    for _ in range(20):
        assert runtime.checkpoint() == first


def test_checkpoint_byte_bound_is_retained_with_real_cognition():
    """Design PR4 bullet: checkpoint byte bound retained."""
    import json

    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind

    limits = KernelLimits()
    genome = GenomeCodec().load(_GENOME_PAYLOAD)  # use this file's existing genome fixture if one exists; else build a minimal valid payload matching other tests in this file
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="s", kind=NodeKind.SENSE), PlasticNode(node_id="c", kind=NodeKind.CONCEPT)),
        edges=(PlasticEdge(source_id="s", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),),
        kernel_limits=limits,
    )
    runtime = OrganismRuntime(
        discover_senses=False, bootstrap_semantic_senses=True, min_samples=1,
        genome=genome, kernel_limits=limits, cognitive_graph=graph,
    )
    for tick in range(1, 50):
        runtime.tick()
    encoded = json.dumps(runtime.checkpoint(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= limits.max_plastic_checkpoint_bytes
```

Use whichever genome-fixture constant or helper this test file already defines (check with `grep -n "_GENOME_PAYLOAD\|def _genome" tests/unit/core/test_organism_runtime.py` first) rather than inventing a second one if one already exists in the file.

- [ ] **Step 2: Run test to verify it fails or passes for the right reason**

Run: `pytest tests/unit/core/test_organism_runtime.py -v -k "p4_repeated_checkpoint or checkpoint_byte_bound"`
Expected: both tests should already PASS given PR1-3's implementation (`checkpoint()` has never called `tick()` or any consolidation step, and every quantized field this session's work introduced is bounded by construction) -- if either fails, that is a real bug to fix in production code, not a plan error, since both properties are load-bearing exit conditions of the whole design (design §25 items 8-9).

- [ ] **Step 3: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/unit/core/test_organism_runtime.py
git commit -m "test(core): lock P4 (checkpoint never forces consolidation) and the checkpoint byte bound end to end"
```

---

## Self-Review Notes

**Spec coverage:** §14 v5->v6 migration -> Task 1. §12.2/§25 item 8 (shutdown/checkpoint never forces consolidation) and §19/§25 item 9 (bounded checkpoint) -> Task 2.

**Real regression fixed, not a design gap:** the self_model migration in Task 1 closes a genuine crash on any historical v5 checkpoint, discovered by direct testing before this plan was written (`SelfModel.restore()` raising a raw `KeyError: 'recency_class'` on an ordinary pre-PR3 checkpoint).

**Type consistency check:** `_migrate_v5_to_v6`'s self_model branch computes `recency_class` with the exact same threshold table `SelfModel._recency_class`/`export()` uses (`10/40/120/400`) -- if PR3's constants in `core/selfmodel.py` are ever tuned later, this migration's local copy (or its import, if the cycle-free path is used) must be updated in lockstep, which is why Step 3 above prefers importing the real function over duplicating the table when the import is possible without a cycle.
