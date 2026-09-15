# Signal Knowledge Implementation Plan

> **For agentic workers:** use superpowers:executing-plans task-by-task, with red/green tests and review checkpoints. No commits, service installation or host writes are authorized by this plan.

**Status:** implementation in progress on `feat/signal-knowledge`; identity, observation types, bounded engine, runtime wiring, predictive scoring, durable host migration v6→v7, study fixture, Observatory projection, and evaluator-only aggregate acceptance metrics are landed locally. Full acceptance and remaining descriptive protocol coverage remain pending.

**Goal:** Implement the complete closed signal-discovery design, including empirical acceptance and Observatory, not merely a correlation report.

**Architecture:** A private identity boundary produces opaque observation batches for a bounded independent engine. Runtime feeds it once per tick; only discrete claim projections enter Observatory. Laboratory truth stays in `symbiont_lab`.

**Tech Stack:** Python 3.11+, standard library, pytest; existing Observatory vanilla JavaScript and schema tooling. No new runtime dependency.

**Spec:** `docs/design/diseno-descubrimiento-senales-symbiont.md`, especially normative decisions in §12.

## Global constraints

- Read-only aggregate host observation; no expanded discovery or permission seeking.
- `symbiont` never imports `symbiont_lab`.
- No source/unit/provider names, timestamps, labels or manifest in the engine or Self.
- 64 profiles, 192 claims, 4 per signal, 64 candidate pairs, 128 pending trials, horizon 1; 64 events/tick; 256 KiB knowledge checkpoint and 256 KiB public projection; existing 2 MiB host ceiling.
- Snapshot v1/v2 unchanged; v3 optional knowledge. Host checkpoint v7 migrates v6 and earlier to empty knowledge.
- Production acceptance uses seeds 101, 127, 149, not pilot seeds 17, 29, 43. No calibration on acceptance outcomes.
- The pilot and byte fixture are design evidence, not proof of runtime correctness or total memory consumption.

## 1. Identity and observation contract — pending

**Files:** create `src/symbiont/core/signal_identity.py`, `src/symbiont/core/signal_knowledge_types.py`; test `tests/unit/core/test_signal_identity.py`, `tests/unit/core/test_signal_knowledge_types.py`.

**Interfaces:** `SignalIdentity(key: bytes)`, `signal_id(capability_id: str) -> str`; immutable `SignalObservation(signal_id, available, selected, value, quality)` and `SignalObservationBatch(tick, observations)`. Identity holds the private key; engine types have no capability/provider metadata. Claim IDs hash the canonical tuple specified by the design.

- [ ] Write tests for stable tokens, independent namespaces, invalid keys/IDs, absence of semantic strings, duplicate batch IDs, invalid tick/bools/nonfinite values and field bounds.
- [ ] Run `.venv/bin/python -m pytest tests/unit/core/test_signal_identity.py tests/unit/core/test_signal_knowledge_types.py -q` and record intended failure before implementation.
- [ ] Implement token boundary with HMAC domain separation and frozen data types with explicit validators. A returned reading may be invalid; represent it as noncomparable rather than a numeric zero. Malformed structural input is rejected atomically.
- [ ] Re-run the command and inspect serialized public types for exact-value/privacy leakage.

Minimal identity regression:

```python
identity = SignalIdentity(bytes(range(32)))
token = identity.signal_id("compute.logical_cpu")
assert token == identity.signal_id("compute.logical_cpu")
assert token != SignalIdentity(bytes(reversed(range(32)))).signal_id("compute.logical_cpu")
assert token.startswith("signal.") and len(token) == 71
assert "compute" not in token
```

## 2. Engine and predictive validation — pending

**Files:** create `src/symbiont/core/signal_knowledge.py`, `src/symbiont/core/signal_prediction.py`; tests `tests/unit/core/test_signal_knowledge.py`, `tests/unit/core/test_signal_prediction.py`.

**Interfaces:** `SignalKnowledgeEngine.observe(batch, *, candidate_pairs=(), outcomes=()) -> None`, `view() -> tuple[dict, ...]`, `drain_events() -> tuple[dict, ...]`; prediction module owns bounded training rows and pending `PredictionTrial`. Inputs contain tokens and endogenous data only. Calls enforce strictly increasing ticks and gap censoring.

- [ ] Test an unobserved profile remains insufficient and availability does not increment sampling opportunities; selected invalid reading increments opportunities but not valid observations.
- [ ] Test order using a prefix followed by two different futures: all prefix epochs/events must match. First scored trial occurs only after 32 resolved training rows. Missing objective never creates a loss or a training target.
- [ ] Implement §12 ridge/past-scale/persistence/mean/zero/conditional comparison; keep resolved rows and buffers in RAM only. Exercise constant, independent, positive/negative AR, true lag, common source, trend, scale, regime and gaps as separate tests.
- [ ] Implement robust univariate/change and differenced synchronous claims with the eight-tick temporal control. Do not use adaptive correlation magnitude as evidence of validation.
- [ ] Test three prospective favorable epochs, two failures, 192-tick staleness, recovery/revision, coverage reset, independent per-direction trial counts, bin boundaries and invalid/nonfinite arithmetic. Numerical overflow censors the affected trial without partial update.
- [ ] Exercise all admission/eviction limits, protected memory rejection, revision saturation and bounded event overflow with deterministic ordering.
- [ ] Run `.venv/bin/python -m pytest tests/unit/core/test_signal_knowledge.py tests/unit/core/test_signal_prediction.py -q` red then green for each behavior.

## 3. Runtime, endogenous outcomes and narration — pending

**Files:** modify `src/symbiont/core/runtime.py`, `src/symbiont/core/narrative.py`, `src/symbiont/cognition/limits.py`; test `tests/unit/core/test_signal_knowledge_runtime.py`.

**Interfaces:** append defaulted `signal_knowledge` and `knowledge_events` fields to `RuntimeTickResult`. Runtime owns identity and engine. Candidate pair IDs from AdaptiveSenseModel are mapped at the boundary. Result carries a Phenotype-only token reference per sense; Self never receives the reverse mapping.

- [ ] Use controlled reading providers, semantic bootstrap disabled, to assert one engine observation per runtime tick and separated manifest/selected/obtained/valid flags.
- [ ] Implement pure batch projection after readings acquired, use actual runtime tick continuity, and publish engine result before final narrative/result construction.
- [ ] Project attempted acquisition outcomes into binary endogenous targets. Exclude same capability and same-provider group before entering the engine. No attempt censors; do not derive a target from predictor loss/attention.
- [ ] Test provider renames retaining capability IDs leave discovery unchanged; replacing capability IDs creates new profiles and never reconnects retired claims.
- [ ] Add deterministic closed templates for all kinds/statuses, selecting bounded recent changes rather than concatenating every claim. Keep existing narrative compatibility.
- [ ] Run `.venv/bin/python -m pytest tests/unit/core/test_signal_knowledge_runtime.py tests/unit/core -q`; review package imports for laboratory leakage.

## 4. Checkpoint and restore — pending

**Files:** modify `src/symbiont/host/checkpoint.py`, runtime; create `src/symbiont/core/signal_knowledge_checkpoint.py`; test `tests/unit/core/test_signal_knowledge_checkpoint.py`.

**Interfaces:** `engine.checkpoint() -> dict`, `SignalKnowledgeEngine.from_checkpoint(payload, *, limits)`. Restore validates into a new engine before committing. Identity key is a separate private runtime field. Engine buffers, numerical models and pending trials are empty after restoration.

- [ ] Test v6→v7 migration empty, valid roundtrip preserves IDs/classes/epochs/revisions, malformed payload rejected with original runtime/checkpoint intact.
- [ ] Reject bool-as-int, negative/oversized counters, duplicate or mismatched claim IDs, unknown enums/fields, inconsistent counts, foreign references and byte-budget overflow.
- [ ] Scan checkpoint for raw samples, last values, model coefficients, means/covariances, partial loss and semantic metadata. Inspect inherited adaptive export separately, without claiming its exact moments are quantized.
- [ ] Restore with a pending target and around a regime boundary; ensure no crossing trial gets scored and new validation warms up independently while mature claims remain traceable.
- [ ] Measure actual full host checkpoint at 64 profiles/192 claims and save rejection above 2 MiB without replacing the prior file.
- [ ] Run `.venv/bin/python -m pytest tests/unit/core/test_signal_knowledge_checkpoint.py tests/unit/host -q`.

## 5. Observatory full contract and UI — pending

**Files:** modify `observatory/adapter.py`, `snapshot.schema.json`, `schema_validate.py`, `projection/snapshot.js`, `state/store.js`, `state/selectors.js`, `render/senses.js`, `render/inspector.js`, `render/self.js`; create `render/signal-knowledge.js`, `signal_knowledge.schema.json`, `test_signal_knowledge.py`; extend resident, replay, snapshot and state-flow tests as necessary.

**Interfaces:** `organism.signal_knowledge` optional only in v3, bounded complete collection; `state.selectedSignalId` independent of selected belief; sense `knowledge_signal_id` is an exact reference. Renderer takes structured projection only and uses `textContent` for external strings.

- [ ] Add schemas and adapter tests rejecting new fields on v1/v2, accepting old v3 absence and new v3 empty/populated profiles; distinguish unavailable interface from insufficient knowledge.
- [ ] Preserve selected token across tick changes, reconnect and replay. Removed profile renders absence, never unrelated fallback belief. No `includes` or index-based association.
- [ ] Render statuses, comparable support, loss/improvement classes, revision/reason and full IDs in details; replace unsupported fixed inspector assertions.
- [ ] Keep instrumentation in Phenotype and only endogenous claims/BodySchema in Self. Test forbidden names with deliberately semantic provider fixtures.
- [ ] Run `.venv/bin/python -m pytest observatory -q`; run real-browser desktop/mobile click, keyboard, resize, SSE/reconnect and replay scenarios. Add an automated click-regression test, not just source-string assertions.

## 6. Integrated study and closure audit — pending

**Files:** create `src/symbiont_lab/studies/learning/signal_knowledge.py`, `tests/unit/lab/test_signal_knowledge.py`, `experiments/learning/signal-knowledge/experiment.toml`; modify study exports/registry following existing predictive utility integration. Publish a reproducible report under `research/` with actual invocation and measured results.

- [ ] Run all §10 environments with seeds 101/127/149, including quality faults, ID replacement, sparse sampling and 64-signal pressure. Labels/truth exist only in the evaluator.
- [ ] Compare isolated engine versus controlled runtime with identical opaque inputs, and continuously running versus restored with declared censoring/warm-up.
- [ ] Report hypotheses, each baseline loss, revisions, actual RSS/tracemalloc methodology, serialized block/full checkpoint and journal growth/retention. The current suite reports supported precision/false positives, coverage, first-support latency and selected-observation cost; it does not yet claim the remaining operational metrics.
- [ ] Require negative environments to produce no supported incremental claim and true-lag full-coverage runs to support on all three seeds; disappearing lag must become contested or stale. Low-coverage runs must explain abstention, not fabricate negatives or support.
- [ ] Run `.venv/bin/python -m pytest -q`, all Observatory tests and rendered QA; inspect actual coverage against every design section before declaring complete.

## Requirement map

| Design | Tasks proving it |
| --- | --- |
| §1–4 identity, epistemic boundary, contract, synchronization | 1, 2, 3 |
| §5 all five claim kinds and noncircular self relevance | 2, 3, 6 |
| §6 revision, staleness, eviction and budgets | 2, 4, 6 |
| §7 privacy, atomic restore and migrations | 4, 6 |
| §8–9 schema, projection, exact selection, Self/Phenotype | 5 |
| §10 every acceptance environment and metric | 6 plus specific regressions in 1–5 |
| §11 integration order, laboratory isolation | 1 through 6 |
| §12 frozen algorithms, calibration split, limits | 2, 4, 6 |

The implementation is not complete while any task above remains pending. No pilot result or green narrow test replaces this map.
