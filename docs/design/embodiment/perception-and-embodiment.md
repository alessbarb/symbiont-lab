---
id: design.embodiment.percepcion-y-embodiment
title: "Technical design: emergent meaning of signals in Symbiont"
document_type: design
domain: embodiment
status: active
canonical: true
implementation_status: implemented
supersedes: []
extends: []
implements: []
depends_on: []
related_adrs: []
migrated_on: 2026-09-25
last_reviewed: null
review_required: false
language: en
---
# Technical design: emergent meaning of signals in Symbiont

<!-- markdownlint-disable MD025 -->

> Consolidated from: diseno-descubrimiento-senales-symbiont.md, digital-body-schema-and-emergent-morphology.md, recurrent-restoration-contract.md
>
> Note: the first absorbed document ("Diseño técnico:
> significado emergente de señales en Symbiont") uses `## 1.` … `## 12.`
> plus an unnumbered "Fuentes del repositorio" section. The second absorbed
> document (further down, "Digital Body Schema & Emergent Morphology")
> independently numbers `# 1. Motivation` … `# 36. Recommended
> implementation sequence` at heading level `#`, not `##`. These are NOT a
> single continuous sequence with the first document's numbering. The third
> absorbed document ("Contrato de restauración recurrente de Symbiont",
> further below still) does not use numbered headings and is unaffected.

**Status:** closed design; implementation of kernel, runtime, persistence, study and Observatory contract completed; verified by the full suite, SSE/replay contracts and smoke visual desktop/mobile in browser, September 15, 2026. **Initial reference:** `770f683ab273468b3290a0e988b3d69ce3d2314a`. **Inventory reconciliation:** local checkout `main` of `alessbarb/symbiont-lab`, commit `a7712550724e3d22571730297af1f72eecd32acb`. This document specifies changes and its status is verified by executed tests; the initial reconciliation was a code inspection, not a functional validation.

## 1. Objective and epistemological boundary

Symbiont must be able to formulate and revise verifiable claims about an opaque signal: behavior, regime shifts, predictive relationships with other signals, and utility to anticipate observable self-states. The result will be structured knowledge of its own, presented by Observatory with precise language. The stable identity remains opaque. The concrete decisions of §12 resolve the exploratory alternatives of previous sections and are normative. "Temperature", "CPU", "disk" and other platform meanings are not inferred from the shape of a series without discriminating evidence. The provider code, manifests, semantic aliases, operator names and evaluator truth are not inputs of the discovery engine.

The naming or definition by the operator is **outside the contract, interface, persistence and tests of this version**. In the future it could be studied independently; no reserved field for taught labels is necessary today. Synthetic or ordinal interface identifiers are visual references, never organism knowledge.

The basic unit is a **claim with falsifiable prediction**. Three distinct states must be preserved: `insufficient` (comparable observations missing), `hypothesis` (initial evidence), `supported` (repeated favorable out-of-sample contrast; incremental advantage for predictive claims, fulfillment of falsifiable criteria for descriptive ones). `contested` describes recent contradiction and `stale` describes expired evidence; neither equates to absolute certainty. An observational relationship does not authorize the verb "cause". On the real local host, readings are read-only, so the first design does not attribute causal effects to organism actions.

## 2. Inventory of current system

| Path | Verified fact | Proposed modification |
| --- | --- | --- |
| `src/symbiont/core/foundation/narrative.py` | `NarrativeEntry` expresses baseline, uncertainty, attention, evidence and dissent; the `summary` reproduces the ID. | Add claim projection with closed templates; maintain existing narrative for compatibility. |
| `src/symbiont/core/orchestration/runtime.py` | `tick()` observes readings in `AdaptiveSenseModel`, synthesizes percepts, updates acclimation, drift, bridge and memory; narration is formed at the end. | Inject an independent engine after acquiring tick readings and before building the result; include its view and events in `RuntimeTickResult`. |
| `src/symbiont/host/adaptive.py` | `PairAccumulator` computes synchronous correlation and one-tick lag in both directions; `SensoryRelation` is not causal. Selection uses a relation window and selective sampling. | Reuse as candidate source; do not turn correlation into validated knowledge. Add explicit access to counts per direction if used as filter. |
| `src/symbiont/host/drift.py` | Classifies observations into `none`, `isolated`, `gradual`, `creep`, `regime_shift`. | Use classes as contextual evidence, without attributing retrospective stability to a newly readjusted baseline. |
| `src/symbiont/core/cognition/consolidation.py` | There is statistical memory and bounded categorical traces, without durable raw telemetry. | Integrate claim maturity, without saving sequences of samples in checkpoint or confusing a highlighted trace with a predictive relationship. |
| `observatory/adapter.py` | Joins summaries into `organism.narrative` limited to 600 characters and memory to 32 strings. | Publish bounded structured cards and revision events; general narrations will be summaries, not the sole channel. |
| `observatory/snapshot.schema.json`, `projection/snapshot.js` | There are v1, v2 and v3, with cognition and body schema per version; `beliefs` only contains 120-character labels. | Additive validated extension of v3 or explicit v4 if the field is required. Maintain old consumers. |
| `observatory/render/senses.js`, `render/inspector.js` | The click searches for belief with `includes` and, if it fails, selects by index; the inspector has a fixed explanation that assumes consistency. | Exact selection by sense ID and own card; render structured facts without false fixed claims. |

The semantic sense bootstrap (`bootstrap_semantic_senses`) adds predefined names in the runtime. Moreover, `SensorReading.capability_id` **does not guarantee opacity**: stdlib providers use, for example, `compute.logical_cpu`; LinuxSurfaceProvider uses hashes. An identity boundary before the engine will convert all IDs into organism-local tokens, without passing `source`, `unit`, timestamps, `DEFAULT_PERCEPT_NAMES`, `percept_names`, `cognitive_aliases`, provider names or semantic `manifest`. Core tests will disable that bootstrap. If representation in the CognitiveGraph requires aliases, a private reference mapping can link signal identity and node; the mapping does not provide the meaning of the alias nor is it exported as inference.

The boundary will use HMAC-SHA256 with a durable random 32-byte key and domain `signal-knowledge-v1`, producing `signal.<64 hex>` from the exact capability ID. The key belongs to the private runtime checkpoint, never to the public view or the statistical engine. Provider IDs are only used to detect shared acquisition groups in that boundary, not to build knowledge. Reversible correspondence for clicks lives in the Phenotype projection; Self exclusively receives tokens. A change of capability ID opens a new identity, even if their values match; continuity is not inferred by statistical similarity. Claims use full SHA256 over the canonical JSON tuple `[subject_id, kind, object_id, horizon]`, with uniqueness validation and collision rejection, never silent reassignment.

### 2.1 Changes incorporated to inventory after initial reference

- [`cognitive_self.py`](../../src/symbiont/core/cognition/self_model.py) projects internal activations into opaque channels and bounded activity classes, excluding known sensory IDs before producing tokens. [`body_schema.py`](../../src/symbiont/core/embodiment/body_schema.py) learns and exports cognitive regions and dependencies; Self must no longer be described as lacking any cognitive organization of its own. These channels do not constitute in themselves host signal prediction claims, nor do they prove independent relevance: any `self_relevance` target still requires the circularity audit of §5.4.
- [`predictive_utility.py`](../../src/symbiont_lab/studies/learning/predictive_utility.py) contains a trial of a series with negative autocorrelation, one-tick horizon, zero/historical mean/persistence references and plasticity and edge ablations. Its [tests](../../tests/unit/lab/test_predictive_utility.py) include seeds 101, 127 and 149. It is infrastructure and potential evidence for the design, **not** the discovery study demanded by §10: it does not implement claim profiling or review, selection among multiple signals, diverse negative environments or integration of `SignalKnowledgeEngine` in runtime. Nor is the proposed recent mean replaced without evaluation by the full history mean used in that trial.
- The [recurrent restoration contract](percepcion-y-embodiment.md) distinguishes durable state, dynamic restart and discrete parameter reconstruction. The [continuity study](../../src/symbiont_lab/studies/continuity/recurrent_restoration.py) is an integration point for §7 and §11, not a proof of continuity of yet non-existent claims. Preserving a mature claim does not guarantee that the restarted predictor maintains its advantage; post-cut opportunities and validation must be measured again without scoring trials whose transient state was lost.

The implementation already adds the `signal_knowledge` contract to the runtime, the `selectedSignalId` selection to Observatory state, a bounded out-of-sample ridge predictor and durable host v6→v7 migration with empty knowledge for old checkpoints. Full acceptance and coverage of the environments defined in §10 are implemented in the deterministic study and covered by unit and integrated tests; the suite keeps truth exclusively in `symbiont_lab`. The inventory reconciliation did not fix thresholds; subsequent decisions and the pilot that grounds them are noted in §12.

## 3. Internal data contract

Create `src/symbiont/core/signal_knowledge.py` with `SignalKnowledgeEngine`, `SignalProfile`, `Claim`, `EvidenceWindow`, `PredictionTrial` and `KnowledgeEvent`. Every model is bounded by kernel limits and JSON-safe. Type and field names are indicative, but the meaning and invariants are normative.

```text
SignalProfile {
  signal_id: organism-local opaque signal token,
  observed_opportunities: int, valid_observations: int,
  last_observed_tick: int | null,
  claims: bounded list[Claim]
}
Claim {
  claim_id: stable opaque ID,
  subject_id: signal ID,
  kind: stability | change | synchronous_association |
        lead_prediction | self_relevance,
  object_id: signal ID | bounded organism-owned outcome | null,
  horizon: positive tick count | null,
  direction: same | opposite | unspecified,
  status: insufficient | hypothesis | supported | contested | stale,
  strength_class: discrete class | null,
  validation: trials, comparable_trials, baseline_loss_class,
              candidate_loss_class, improvement_class,
              successful_epochs, failed_epochs,
  context: regime_class, reliability_class, last_tested_tick,
  revision: monotonic integer, reason_class
}
KnowledgeEvent {claim_id, tick, from_status, to_status, reason_class}
```

`valid_observations` and `observed_opportunities` count different things. An opportunity to compare two signals requires **both available, valid and observed with known synchrony**; an absence of sampling is not a zero or a proof of absence of relationship. Raw supports of profiles with different ages and sampling rates will not be compared. Claim IDs are persistent, derived from a canonical key of subject, object, type and horizon with collision control; when recovering or removing nodes, an old claim is never silently linked to another signal.

Claims have exclusively endogenous provenance: valid observations, predictive error, drift, attention and self-state already observable by the organism. They do not accept arbitrary text strings, platform quotes or semantic labels. The exported view retains `evidence_count` and discrete classes, not exact reading values, means based on few samples, real timestamps or raw windows.

## 4. Acquisition, synchrony and transient state

In `OrganismRuntime.tick()`, build a `SignalObservationBatch` upon completing `snapshot.readings`: `tick`, ID, finite numeric value when existing, quality, availability and aggregate self-reliability. Deliver it to the engine only once per tick. The signal remains identifiable even if there is no value this tick. Clearly separate `manifest available`, `selected for sampling`, `reading obtained` and `value valid`. The engine does not interpret available capability as a measured signal. `observed_opportunities` counts explicit sampling attempts of that signal; `valid_observations` counts its finite nominal readings. Availability without selection increments neither. Claim coverage is computed by epoch in real ticks, not by dividing historical profile supports.

The engine retains only in RAM the minimum transient required for predictions of defined horizons, such as the last value or normalized class per signal and pending predictions. An absent or invalid target leaves the trial **unresolved**; it does not count as success or failure. Opportunity counters record that censoring. Delays are expressed in real ticks and evaluated only if observation continuity satisfies the contract; if selective sampling left gaps, values are not imputed. Limit horizons initially to 1 tick; larger horizon requires bounded buffers and its own tests.

Resolve the pending trial before updating the predictor with the target reading of the current tick. Preserve the order: `predict(t)` with state up to `t`, `observe(t+1)` to score, and then `learn(t+1)`. Prevents target leakage to training or to out-of-sample report. The `AdaptiveSenseModel` may select pairs to explore, but the engine will not consider that selection a proof of relationship; selection biases must be recorded by coverage.

## 5. Hypothesis generation and contrast

### 5.1 Univariate claims

After a minimum of comparable observations in non-overlapping blocks, estimate classes of stability, variability and regime shifts from robust statistics and `DriftObservation`. The "stable" claim is evaluated over a bounded recent window or comparable epochs, not over the entire accumulated history. A sequence with regime shift invalidates or contextualizes the old claim, increments its revision and opens a new hypothesis; it is not declared stable by the mere readjustment of the baseline. Constant data, ramps, missing values, monotonic counters and non-finite inputs have specific cases.

### 5.2 Associations between signals

`AdaptiveSenseModel.strongest_relations()` proposes pairs; it is an economic filter, not a verdict. The engine records simultaneity, direction, comparable counts, effective variability and coverage. A strong correlation only authorizes "they move together in observed opportunities". Require several non-overlapping epochs, recent support and minimum coverage. Discount trivial association due to common trend, autocorrelation or shared regime shifts via differences/normalized classes and appropriate temporal controls. Do not select only the highest coefficient among numerous pairs without correction or independent evaluation.

### 5.3 Out-of-sample predictive utility

For `A(t) → B(t+1)` use progressive temporal comparison: train with past, emit prediction before the target, score the pre-emitted prediction at the next tick and only then update. Compare with references per target (`persistence`, `recent mean` and `zero` when scale allows). Choose or predefine reference according to the series, without retrospectively choosing the worst one. The loss and the minimum improvement are set before the experiment; report discretized aggregated losses and comparable opportunity. The claim goes to `supported` only after material advantage in several separate epochs and with a minimum number of valid trials; a single favorable result remains `hypothesis`.

If `A` predicts `B` as much as `B(t)` already does, signal A provides no incremental predictive discovery. Always include the conditional reference with the available history of B defined in §12; without sufficient history there is no comparable trial. In the presence of high autocorrelation or negative coupling, test both regimes; "persistence" is not a universally good reference. A predictor converging to zero is not credited for lowering its initial loss: it must beat the relevant references on new ticks.

### 5.4 Relevance for the organism itself

Relate the signal with outcomes that Symbiont already perceives as its own and that are recorded in its contract (`SelfModel`/`BodySchema` or sampling quality), regardless of external labels. Distinguish predicting own outcomes from change caused by actions. If the own outcome depends mathematically on the signal, declare that dependency as circular and exclude it from the independent relevance test. Do not use the same predictor's loss or attention as a target if that creates a tautological advantage.

## 6. Revision, expiration and budget

Continuously re-evaluate `supported` claims against new trials. If advantage is lost in enough epochs, move to `contested` with reason and contradictory evidence; if there are no recent opportunities, move to `stale`. A new sustained advantage can return it to `supported` preserving history and incrementing `revision`. Do not reuse baseline `DissentRecord` as proof of falsehood of a different relationship.

Apply kernel limits set in §12: `max_signal_profiles=64`, `max_claims_total=192`, `max_claims_per_signal=4`, `max_pair_candidates=64`, `max_pending_trials=128`, `max_horizon=1`, `min_validation_trials=144` and `max_knowledge_checkpoint_bytes` within existing global budget. The values are fixed in §12 and will be verified against the integrated engine; they are not introduced as learnable genetics. Eviction: first `insufficient` or `stale` claims, then inactive profiles; protect validated claims and ensure young profiles do not lose memory just for having lower accumulated support. Eviction decisions are observable and deterministic.

## 7. Persistence and restoration

Include `signal_knowledge` in `OrganismRuntime.checkpoint()` and restore it with explicit migration of current host checkpoint schema (v6). Previous checkpoints migrate to empty knowledge; advanced knowledge is not reconstructed from narrative strings or incomplete correlations. Validate types, bounds, IDs, indices, counts, classes, revisions and size before committing restoration. Restart all pending trials and mark the restoration interval as non-comparable, preserving mature claims and discrete statistics. Measure how much validation changes due to that decision.

The new `signal_knowledge` block in the checkpoint saves only sufficient counters, quantized classes and support by epochs; this statement does not describe the aggregates inherited from the full host checkpoint. Prohibit individual samples, exact delay buffers, last value, sums allowing reconstruction of a sample with low count, provider labels and short reversible series. Quantization must be specific to losses, strength and reliability: do not reuse weight bins for convenience. Review `AdaptiveSenseModel.export()` because its relationship accumulators and gating by `min_samples` must remain coherent with the privacy of this new persistence. The decision to publish knowledge classes and the durable checkpoint decision are audited separately.

## 8. Observation contract

Publish `organism.signal_knowledge` as a bounded full collection of profiles with ID and structured claims, once per tick. Deltas are not implemented in this version: full collection simplifies SSE/replay and reconstruction after reconnection. The maximum is 256 KiB including events, to be verified with the real producer. View fields: `signal_id`, `observed_opportunities`, `last_seen_age_class`, `claims[]` with `claim_id`, `kind`, `related_signal_id`, `status`, `strength_class`, `evidence_count`, `validation_opportunities`, `improvement_class`, `revision`, `reason_class`. Do not include free text. `KnowledgeEvent` is published bounded in tick events with stable IDs; a delayed consumer can reconstruct the situation from full state.

Versioning decided: keep v1 and v2 exactly as they are and add `signal_knowledge` **optional only in v3**, without creating v4. The new producer emits `[]` when it has the new interface but not yet knowledge; an old producer can omit the field. The normalizer distinguishes absence of interface from empty collection, without inventing claims. v1/v2 snapshots do not carry the field, even if the adapter receives knowledge; the new integrated export preserves BodySchema and produces v3. Tests must reject v1/v2 with the new field and accept old v3 without it. Update `snapshot.schema.json`, `adapter.py`, `schema_validate.py`, `projection/snapshot.js`, selectors, demo fixtures, replay and resident/transport where applicable. Do not expose the private checkpoint to Observatory.

Narration is generated with deterministic templates from structured claims: "insufficient observations", "move together in X opportunities", "A has anticipated B with class M improvement in several epochs" and "the hypothesis stopped holding". Language of hypothesis and support reflects the state. Never convert `strength_class` into "I know what this is". Avoid joining hundreds of summaries until truncating to 600 characters; general narrative selects few novelties and the inspector shows the full card. Current `beliefs` can remain for compatibility, but do not introduce claims into them without an exact link of ID and certainty semantics.

## 9. Observatory interface and Phenotype/Self boundary

Create card component `render/signal-knowledge.js` and persistent `selectedSignalId` selection. The click in `render/senses.js` selects the sense by exact equality `sense.id` and resolves its profile by exact equality `sense.knowledge_signal_id === profile.signal_id`, without `includes` or index-based fallback. If there is no profile: "Symbiont has not yet gathered sufficient evidence"; if absent this tick, indicate observation age without claiming it is forgotten. Show claims, comparable evidence, state, contradictions and revision, with full ID in details. Use DOM `textContent` for external fields; templates do not interpolate IDs into `innerHTML`. Current inspector static statements about "repeated platform-neutral percepts", "consistent with recent context" and "why it matters" are replaced by real projection.

In Phenotype, Observatory can show own instrumentation labeled as such and the organism's knowledge card as a differentiated layer. In Self, show only claims recorded in the organism's knowledge and its BodySchema; no manifest, no external topology, no semantic provider names, no derived state heading from the observer. The new panel must not turn a UI alias into `Self` data. If existing Self does not yet have signal knowledge, indicate that state without inventing introspective capability. Exact visual placement is adjusted with the current Self revision, without leaking privileged information to the central area.

## 10. Evaluation and acceptance tests

A deterministic lab study will feed the engine with **only opaque observations** and keep truth in the evaluator. Minimal environments: constant/noise; positive autocorrelated series; negative autocorrelation; A anticipates B with known lag; A and B correlated by common cause without incremental advantage; regime shift; noise with multiple pairs; selective observations, gaps and invalid qualities; signals with scale, shift and trend; ID change. At least three seeds per environment, with observed support, false positives and comparison with references. Do not mix seeds with different problems. Advantage is measured in subsequent horizon, without future training.

| Case | Closure condition |
| --- | --- |
| Signal without comparable observations | `insufficient`, no persistent raw mean or inference. |
| Synchronous correlation without future improvement | Descriptive association possible; no predictive claim `supported`. |
| Relationship with out-of-sample advantage | Claim `supported` only after defined trials and epochs; losses and reference recorded. |
| Spurious relationship by trend or common cause | Do not promise causality or non-existent incremental advantage. |
| Regime changes or prediction fails | Claim revision, `contested` or `stale` status and observable reason. |
| Absent or invalid sampling | Censored trial and updated coverage, never treated as zero. |
| Multiple signals and full budget | Strict limits, deterministic eviction and stable memory. |
| Save/restore | Claims and revisions continue; pending trials restarted or restored per contract; old schema migrates. |
| Semantic bootstrap disabled | Identical discoveries for any provider renaming leaving values and opaque IDs equivalent. |
| Observatory Self | No name, manifest or privileged state enters the own knowledge panel. |
| Sense click, SSE and replay | Exact ID, correct card after tick change/reconnection; v1/v2/v3 continue loading. |

The report will publish emitted hypothesis rate, precision of `supported` claims, observation cost, coverage, time to discovery, predictive advantage against each reference, revision frequency and checkpoint size. Do not declare that it "discovers CPU" for guessing a human label it never received. The evaluator can verify if a functional relationship corresponds to the generating signal without sharing that truth with the organism.

## 11. Implementation order and dependencies

The baseline plan contains the requirements and tasks matrix. It is not currently executing: the requested active scope is to review and close this design.

1. **Contract and study:** set claim classes, limits, loss, references, promotion conditions and opaque trials. A null or trivial baseline must be hard to beat in negatives.
2. **Univariate engine:** profiles, opportunities, stability/change classes and revision; own `RuntimeTickResult`. No platform narrative. Validate limits and privacy.
3. **Relationships:** use `AdaptiveSenseModel` candidates, pre-emitted trials, progressive evaluation, autocorrelation/common cause control, costs and coverage. A synchronous relationship does not enter as anticipation.
4. **Durability:** checkpoint, migrations, invariants and transient discontinuity, with restoration tests during a prediction horizon and near a regime shift.
5. **Observatory:** schema, adapter, normalizer/store, card view, exact selection, replays/SSE and Self/Phenotype boundary. Publish the result of the claim review, not just an internal counter.
6. **Integrated study:** same flow in isolated engine and runtime with controlled providers; review regressions of perception, attention, consolidation, structural plasticity and checkpoint size.

Knowledge integration can advance while checkpoint continuity and graph recycling are investigated. **Meaning is not deduced from cognitive topology alone**: a recurrent concept needs traceability of inputs, predictions and validation before becoming a readable claim. If the graph remains degenerate or without readouts, the knowledge engine can still describe basic statistics, but it must not ascribe structural discovery to the graph.

## 12. Decision log and closure gates

### Decisions resolved by inspection

1. **Identity:** the token boundary of §2 is mandatory also with semantic providers. The click exact equality resolves with a `knowledge_signal_id` reference from Phenotype, not comparing tokens with names or passing names to Self. A provider rename preserving capability ID preserves the token; an ID change creates another identity.
2. **Public compatibility:** optional v3 extension per §8. BodySchema format is unaltered for storing claims; separation between both knowledge views is preserved.
3. **Durable privacy:** `AdaptiveSenseModel.export()` saves exact means and moments after independent support gates; there is **no** relationship quantization that can be reused. Those inherited fields do not enter the `signal_knowledge` block, nor its views or restore. The new block retains only counters, discrete classes and closed epochs; predictors, means, covariances, continuous losses and pending trials are restarted. Host migration will be v6 → v7, empty knowledge for prior versions and rejection of malformed new content. This decision does not claim the full host checkpoint lacks exact statistics: the new privacy contract and the audit of inherited aggregates are separate.
4. **Initial own targets:** only success of acquisition of another capability at the next tick is allowed, observable via `CapabilitySamplingOutcome`. The binary target is 1 for `SUCCEEDED` with `NOMINAL` quality and 0 for failure/absence or non-nominal quality after an explicit attempt; without attempt it is censored. The boundary discards source equal to target and acquisition groups with the same provider; it delivers tokens and eligibility to the engine, not provider names. Exact cost, attention, predictor loss or activations derived from the same input are not used. BodySchema regions are not targets of this version as long as traceability ruling out circular mathematical dependency does not exist. The relation with another sampling outcome remains predictive, not causal. If there are no eligible pairs, own relevance is not fabricated.

### Predictive protocol set by pilot

The [reproducible pilot](../../experiments/learning/signal-knowledge-pilot/README.md) rehearsed 126 runs with seeds 17, 29 and 43. Its results justify adopting the following initial protocol, without converting the pilot into production acceptance. Acceptance seeds will be 101, 127 and 149; thresholds will not be adjusted to their results. An acceptance failure requires explicitly revising the protocol version and separating calibration and evaluation again.

- Predictor: linear ridge with intercept, `1e-6` regularization, last 64 resolved transitions in RAM. Predicts `ΔB(t+1)` using `ΔB(t)`, `ΔB(t-1)` and `ΔA(t)`; adds `B(t)` to produce the target. Conditional reference omits `ΔA(t)`. Other references are zero, mean of last 64 B readings and persistence. The first 32 valid transitions only train. Does not learn with invented targets, nor normalize a prediction with future target.
- Loss scale: standard deviation of the last 64 B readings available upon emission, floored at `1e-12`; loss `min(4, abs(error / scale))²`, range `[0,16]`. The five losses are compared on exactly the same trials; material advantage requires reducing loss against **each** reference by at least 15% and 0.01 units per trial. If all are zero, there is no incremental improvement.
- Epochs: non-overlapping blocks of 64 real ticks, at least 48 comparable trials per epoch (75% coverage). Three consecutive favorable epochs allow `supported` (minimum 144 comparable trials); two unfavorable comparable epochs drop to `contested`. An epoch without enough coverage breaks the promotion streak but doesn't count as failure. Without comparable test during 192 ticks after gathering evidence, `stale`; a claim that never had enough opportunities retains `insufficient`. A new streak of three epochs can restore support. Each state change increments revision and emits typed reason.
- A candidate proposed by AdaptiveSenseModel begins contrast in the next epoch: observations that selected it don't count as confirmation. Max 64 candidate pairs per epoch, not replaced within it by the winning coefficient. Negatives with multiple pairs and prospective confirmation are empirical controls; formal false discovery rate guarantee is not announced.
- Only `NOMINAL`, finite readings with known tick continuity train or score. `DEGRADED`, `STALE`, `UNAVAILABLE`, boolean/non-finite values and absences are invalid for the engine. Expired trials without target are counted as censored and retired without loss; they do not wait for a late sample as if it was the due tick. Differences require three consecutive own observations and two of the source; a gap restarts that continuity. The pilot confirms reduced sensitivity with gaps: only 1/3 of its sparse runs reached support. Coverage is not lowered to hide this.
- For the binary own target of §12.4, probabilistic references zero, recent frequency, persistence and conditional predictor are used; regression outputs are clipped to `[0,1]`, fixed scale 1 and quadratic loss (Brier). Only explicit attempts have a target. Same thresholds and epochs are kept; this case requires own validation in the acceptance study and is not attributed to the continuous pilot.

### Descriptive contrast, memory and bounds

- Univariate: RAM of 64 consecutive observations; robust median and MAD stats, not exported. `stability` predicts next absolute change does not exceed `max(1e-12, 0.1 * MAD)` of the past window. A favorable epoch requires at least 90% hits among 48 comparables; three epochs support, two contradict. A constant series can support stability, not association or predictive advantage. A ramp is not stable for having predictable increments.
- `change`: compare medians of two consecutive blocks of 32 valid readings; separation greater than `max(1e-12, 3 * MAD_previous)` opens change hypothesis and contradicts previous stability. Its prediction is permanence of the shift outside that band in the subsequent epoch; shares support/revision requirements. Baseline readjustment does not automatically support stability again.
- Synchronous association: correlation of consecutive differences, not levels with trend. Favorable epoch with 48 comparables, non-zero variability on both sides, `abs(r) >= 0.75` and magnitude advantage ≥0.15 over the 8-tick lagged control of the same epoch. Three epochs of prospective confirmation; without continuity for the control there is no favorable epoch. Direction comes from the sign and must hold during the streak. These controls are descriptive, not causal.
- Final limits: 64 profiles, 192 global claims, 4 per signal, 64 candidate pairs, 128 pending trials, horizon 1, 64 events per tick, four epoch summaries per claim, 64 training transitions per predictor and 64 observations per signal. Own outcomes: max 64 additional outcome channels, no artificial host profiles. Exact transient values remain only in RAM. Limits are from the kernel, not the genome.
- Public and durable counters saturate at `2**31-1`; saturated revision does not cycle: new claim revisions are rejected with `revision_limit` event. Internal tick does not saturate; validated as non-negative integer and strict continuity. Byte limit is still checked for large ticks. Public age: `current` (0), `recent` (1–63), `aging` (64–191), `long_absent` (≥192), `never` (no observation).
- Deterministic eviction: `insufficient` claims, then `stale`, then `hypothesis`, ordered by age of last test and finally ID; then inactive profiles without protected claims. `supported`/`contested` are not evicted to admit new candidates. If only protected memory remains, admission is rejected and `budget_rejected` emitted. An aggregated overflow event is reserved when decisions exceed 64 events; the queue never grows unboundedly.
- Loss classes: 16 uniform intervals of width 1 in `[0,16]`, last inclusive of 16; improvement classes `none` (<15%), `material` (15–<30%), `substantial` (≥30%), always conditioned on absolute margin. Descriptive strength `weak` (<0.5), `moderate` (0.5–<0.75), `strong` (≥0.75). Reliability `insufficient` or `nominal` based on coverage. Only closed epochs with 48 comparables export loss classes; do not export moments, coefficients or reversible partial losses.
- Sub-budgets of 256 KiB for durable knowledge block and 256 KiB for projection with events, compact JSON UTF-8 `allow_nan=False`. The [budget fixture](../../experiments/learning/signal-knowledge-pilot/budget.py) takes 215577 bytes with 64 profiles, 192 claims and 64 events; does not measure RSS nor the rest of the host. The existing host ceiling remains 2 MiB. A save exceeding the combined limit is rejected before overwriting the previous file; memory from other subsystems is not discarded to make it fit. The integrated study will measure real block, RAM, full host and journal with its existing retention.

### Closed semantics of states and errors

A profile is born without observations and can contain `insufficient` claims. An admitted claim transitions to `hypothesis` upon closing its first comparable epoch, without this affirming advantage; only a favorable streak allows support. The render explicitly distinguishes "hypothesis without proven advantage" from "supported". A contradiction of a previously supported claim preserves identity; a new evaluation does not erase its historical revision. Upon restore, identity, revision and closed epochs are preserved, but scoring waits until regaining continuity and training. A change hypothesis whose transient anchor was lost is marked `stale` with reason `restored_discontinuity` and opens new revision upon establishing a future anchor; exact continuity of that contrast is not faked.

Allowed reasons: `insufficient_observations`, `insufficient_coverage`, `initial_evidence`, `prospective_advantage`, `no_incremental_advantage`, `recent_contradiction`, `regime_changed`, `no_recent_trials`, `restored_discontinuity`, `invalid_observation`, `censored_target`, `evicted`, `budget_rejected`, `revision_limit`, `event_overflow`. Arbitrary reasons/texts are not accepted. Global budget/overflow events carry `claim_id=null`; others reference an exact claim. Full state allows reconnecting even if an event was omitted by limit.

Signal and claim IDs: fixed length per §2; capability input to private limit, non-empty token up to 512 characters without spaces. Private key: 32 bytes, represented in checkpoint by 64 hex digits. Reject duplicates, booleans used as integers, unknown classes and non-existent references before applying a batch or restore. An invalid read value is censored; a malformed structure rejects the whole operation. If a numeric operation produces overflow/non-finite, that trial is censored and the predictor is not updated with the corrupted result. Restoration rejects unexpected fields and contradictory states; it does not attempt to repair them silently.

### Delivery condition

These decisions fix the behavior to implement, they do not certify it works. Implementation closure requires all cases from §10, coverage matrix from plan, adversarial migration and privacy tests, engine/runtime comparison, visual desktop/mobile QA and SSE/replay. The pilot, its five tests and the bytes fixture do not substitute those acceptance gates. Scope will not be reduced to accommodate what is easy to demonstrate.

## Repository Sources

[`AGENTS.md`](https://github.com/alessbarb/symbiont-lab/blob/main/AGENTS.md) · [`runtime.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/orchestration/runtime.py) · [`narrative.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/foundation/narrative.py) · [`adaptive.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/host/adaptive.py) · [`drift.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/host/drift.py) · [`consolidation.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/cognition/consolidation.py) · [`adapter.py`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/adapter.py) · [`snapshot.schema.json`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/snapshot.schema.json) · [`senses.js`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/render/senses.js) · [`inspector.js`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/render/inspector.js).

---
# Digital Body Schema & Emergent Morphology

## Status

Proposed design.

This document defines the architecture for giving Symbiont a substrate-native form of self-perception and replacing Observatory's fixed cell metaphor with an emergent digital morphology.

The design deliberately separates three different things:

1. **the organism as it actually exists**;
2. **the organism's learned representation of itself**;
3. **the human-facing visualization produced by Observatory**.

These must never be silently collapsed into the same representation.

---

# 1. Motivation

Observatory currently represents an individual Symbiont using a fixed SVG cell-like outline.

That shape is a visualization metaphor chosen by the interface. It is not produced by the organism and does not represent anything Symbiont knows about itself.

The current organism already maintains a limited `SelfModel`, but that model describes only properties of its sensory apparatus such as:

- health,
- confidence,
- cost,
- maturity,
- recency.

It does not yet contain an explicit concept of:

- organism identity,
- body boundary,
- internal parts,
- functional dependencies,
- cognitive regions,
- global viability,
- organism continuity.

The next step is therefore not to decide whether Symbiont is a cell, sphere, graph or blob.

The next step is to introduce a **Digital Body Schema**.

The central idea is:

> A Symbiont has no intrinsic Euclidean shape. It has an organization.

Observatory may translate that organization into geometry, but the geometry is a projection.

---

# 2. Core distinction

The architecture defines three epistemic layers.

```text
ACTUAL ORGANISM
    │
    │ observable state
    ▼
PHENOTYPE PROJECTION
    │
    │ human visualization
    ▼
OBSERVATORY
```

and independently:

```text
ACTUAL ORGANISM
    │
    │ internal evidence
    ▼
BODY SCHEMA LEARNING
    │
    ▼
SELF MODEL
    │
    │ exported representation
    ▼
OBSERVATORY SELF VIEW
```

The Observatory therefore exposes two distinct views:

```text
[ Phenotype ] [ Self ]
```

## Phenotype View

Represents what the scientific apparatus can legitimately observe about the organism.

It may use:

- genome identity,
- current cognitive topology,
- sensory development,
- memory state,
- safety state,
- runtime state,
- health summaries,
- topology revision.

It is the external scientific view.

## Self View

Represents only what the organism currently knows or believes about itself.

It must use only the organism's exported self-representation.

Observatory must not fill missing knowledge using privileged runtime information.

This creates a meaningful distinction between:

```text
what I am
```

and:

```text
what I think I am
```

---

# 3. Design principle: no perfect introspection

The Body Schema must not simply expose the runtime's internal structures to cognition.

This would be invalid:

```python
body_schema.parts = cognitive_graph.nodes
body_schema.dependencies = cognitive_graph.edges
```

because it gives the organism perfect administrative introspection.

Instead, self-perception must be evidence-based.

```text
experience
   │
   ▼
evidence about own functioning
   │
   ▼
self hypotheses
   │
   ▼
consolidation
   │
   ▼
BodySchema
```

The organism should be able to be:

- incomplete about itself,
- uncertain about itself,
- temporarily wrong about itself,
- more knowledgeable about some regions than others.

That is not a defect.

It is part of the research model.

---

# 4. Digital body

A digital body is defined as the bounded organization whose continued operation constitutes the individual Symbiont.

It is not identical to the host computer.

It is not identical to the operating-system process.

It is not identical to the checkpoint.

Conceptually:

```text
HOST
  │
  ▼
computational substrate

RUNTIME
  │
  ▼
execution of organism

ORGANISM
  │
  ▼
persistent developmental individual

BODY SCHEMA
  │
  ▼
organism's representation of itself
```

The body boundary is therefore functional rather than geometric.

---

# 5. Initial body domains

The Body Schema is divided into five domains.

## 5.1 Identity

Represents continuity of the individual.

```text
identity
├── organism_id
├── genome_id
├── lineage_id
├── developmental_age_class
└── continuity_state
```

The organism does not need access to implementation-specific identifiers unless they form part of its explicit identity model.

---

## 5.2 Boundary

Represents the organism's current distinction between self and environment.

```text
boundary
├── known_self
├── known_environment
├── uncertain
└── future: other_organism
```

Membership should be learned or derived from bounded evidence.

Possible states:

```text
SELF
NON_SELF
UNCERTAIN
```

Future ecology adds:

```text
OTHER_SELF
```

---

## 5.3 Parts

A body part is a stable functional component represented by the organism.

Initial kinds:

```text
SENSE
COGNITIVE_REGION
MEMORY_REGION
READOUT_REGION
```

Future physiology may add:

```text
METABOLIC_REGION
MAINTENANCE_REGION
REPRODUCTIVE_REGION
```

Suggested internal model:

```python
@dataclass(slots=True)
class BodyPartState:
    part_id: str
    kind: BodyPartKind
    existence_confidence: float
    health: float
    functional_importance: float
    activity_class: ActivityClass
    recency_class: RecencyClass
    uncertainty: float
```

No geometry is stored.

Geometry belongs to Observatory.

---

# 6. Functional dependencies

A list of parts is not enough to form a body schema.

The organism must gradually learn relationships such as:

```text
part A contributes to part B
part C degrades when part D fails
part E is usually active before part F
part G supports organism viability
```

The self-model therefore includes bounded dependencies.

```python
@dataclass(slots=True)
class BodyDependency:
    source_id: str
    target_id: str
    relation: DependencyKind
    confidence_class: int
    support_class: int
```

Initial relation kinds should remain intentionally weak:

```text
SUPPORTS
CO_ACTS_WITH
PRECEDES
DEGRADES_WITH
UNKNOWN_DEPENDENCE
```

Avoid prematurely encoding causal semantics.

---

# 7. Global organism state

The schema also represents organism-level internal state.

Initial fields:

```text
global_state
├── self_model_confidence
├── integrity
├── stress
├── maintenance_load
├── dormancy_pressure
└── viability
```

Future physiology can add:

```text
metabolic_balance
resource_deficit
waste_pressure
repair_pressure
reproductive_readiness
```

These values should be:

- bounded,
- coarse,
- learned or computed from permitted internal evidence,
- checkpoint-safe,
- non-identifying.

---

# 8. Relationship with current SelfModel

The existing `SelfModel` should not be deleted.

It becomes one evidence source feeding the broader Body Schema.

```text
SelfModel
   │
   │ sensory health / cost / confidence
   ▼
BodySchemaEngine
```

The responsibilities remain distinct:

```text
SelfModel
→ how individual senses are doing

BodySchema
→ what parts of myself I believe exist and how they relate
```

This prevents a large, monolithic self-model.

---

# 9. BodySchemaEngine

Introduce:

```text
src/symbiont/core/embodiment/body_schema.py
```

Suggested architecture:

```text
AdaptiveSenseModel ───────┐
SelfModel ────────────────┤
CognitiveBridge ──────────┤
MemoryConsolidator ───────┤
Runtime outcomes ─────────┤
SafetyState ──────────────┤
                           ▼
                    BodySchemaEngine
                           │
                           ▼
                       BodySchema
```

The engine receives bounded observations about the organism.

It must not receive arbitrary references to runtime internals.

---

# 10. First learning scope

The first implementation should be intentionally narrow.

## Phase A — Sensory body

The organism may learn:

```text
these senses belong to me
this sense is reliable
this sense is unhealthy
this sense is costly
this sense appears persistent
```

This can be built almost entirely from the existing `SelfModel`.

## Phase B — Cognitive regions

The organism begins learning coarse internal regions.

It should not be told:

```text
concept_0000000000000003
```

Instead, stable topology may be grouped into opaque regions:

```text
region.01
region.02
region.03
```

Region identity must remain persistent enough for longitudinal learning.

## Phase C — Dependencies

The organism learns that internal regions appear functionally related.

## Phase D — Global integrity

The organism forms a coarse model of:

```text
healthy
strained
unstable
recovering
dormant
```

---

# 11. Checkpoint representation

The Body Schema is persistent learned state.

Suggested checkpoint namespace:

```json
{
  "body_schema": {
    "schema_version": 1,
    "identity": {},
    "parts": [],
    "dependencies": [],
    "global_state": {}
  }
}
```

Requirements:

- bounded number of parts,
- bounded number of dependencies,
- quantized values,
- no raw activation history,
- no exact host readings,
- no runtime object names unless intentionally exposed,
- no implementation paths,
- no arbitrary strings originating from host resources.

---

# 12. Observatory projection architecture

Observatory must never directly convert `BodySchema` into internal cognition.

Its role remains passive.

The new individual visualization becomes:

```text
                 Observable organism state
                          │
                          ▼
                 MorphologyProjection
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
          Phenotype View         Self View
```

The projection is visual only.

It is not persisted back into Symbiont.

---

# 13. Emergent morphology

The current fixed cell boundary is replaced by a deterministic morphology generator.

No `cellPath` constant should remain.

Suggested input:

```typescript
interface PhenotypeMorphologyInput {
  identitySeed: string
  senseCount: number
  conceptCount: number
  readoutCount: number
  edgeCount: number
  topologyRevision: number
  health: number | null
  confidence: number | null
  frozen: boolean
}
```

The output remains geometry:

```typescript
interface MorphologyGeometry {
  boundaryPath: string
  senseAnchors: Point[]
  internalAnchors: Point[]
  coreAnchor: Point
}
```

---

# 14. Stable morphology identity

The organism should not change visual identity on every frame.

The basal contour must derive from a stable seed.

Preferred order:

```text
genome hash
+
organism identity
```

The genome defines inherited morphology characteristics.

The organism identity prevents genetically identical siblings from becoming visually indistinguishable.

Conceptually:

```text
genome
  │
  ├── inherited base morphology
  │
organism identity
  │
  └── individual variation
            │
            ▼
     stable basal shape
```

Developmental state produces small changes around that baseline.

---

# 15. Morphology semantics

Possible projection mapping:

| Organism property    | Visual representation         |
| -------------------- | ----------------------------- |
| Genome / identity    | stable base contour           |
| Sense                | peripheral receptor           |
| Active sense         | open / luminous receptor      |
| Probing sense        | intermittent receptor         |
| Dormant sense        | contracted receptor           |
| Concept              | internal region               |
| Readout              | integrative core              |
| Cognitive edge       | internal fibre                |
| Edge weight          | fibre intensity               |
| Health               | boundary integrity            |
| Confidence           | visual clarity                |
| Stress               | contour tension / contraction |
| Frozen state         | reduced motion / desaturation |
| Topology change      | slow structural rearrangement |
| Memory consolidation | persistent internal texture   |
| Pruning              | gradual disappearance         |
| New structure        | controlled growth             |

No biological organ names should be used in the data model.

---

# 16. Phenotype View

This view is allowed to display the actual observable phenotype.

Example for the historical worker-3 checkpoint:

```text
Phenotype

58 SENSE
5 CONCEPT
1 READOUT
0 EDGES
topology revision 29
```

The resulting morphology should visibly show:

- many peripheral receptors,
- five disconnected internal regions,
- a central readout region,
- no fabricated connectivity.

A graph with zero edges must look disconnected.

The visualization must never invent structure for aesthetics.

---

# 17. Self View

The Self View must be driven exclusively by:

```text
body_schema
```

During the transition period, before `BodySchema` exists, it may use only the current exported `SelfModel`.

It should explicitly indicate:

```text
BODY SCHEMA
not yet developed
```

rather than reconstructing the missing schema from topology.

This is especially important for organisms such as worker-3, where actual graph structure and self-modelled sensory state diverge.

---

# 18. Self/Phenotype divergence

Observatory should eventually distinguish four cases:

```text
REAL + KNOWN
REAL + UNKNOWN
BELIEVED + UNCONFIRMED
BELIEVED + CONTRADICTED
```

Suggested visual language:

```text
solid          = known
faint          = real but not self-modelled
dashed         = uncertain
fragmented     = contradicted
```

This is one of the scientifically valuable outputs of the design.

---

# 19. Refactoring Observatory

The current `observatory/app.js` has accumulated too many responsibilities.

Before implementing the complete Body Schema visualization, it should be decomposed.

Current responsibilities include:

- demo state,
- application state,
- SVG helpers,
- senses rendering,
- organism rendering,
- population rendering,
- inspector,
- timeline,
- replay,
- snapshot normalization,
- snapshot bounds checking,
- cognition rendering,
- SSE fleet connection,
- event history,
- UI actions.

This makes morphological evolution risky.

The refactor should happen as part of this work, not afterwards.

---

# 20. Proposed Observatory structure

```text
observatory/
│
├── app.js
│
├── state/
│   ├── store.js
│   ├── demo-state.js
│   └── selectors.js
│
├── transport/
│   ├── fleet-stream.js
│   ├── instance-stream.js
│   └── replay.js
│
├── projection/
│   ├── snapshot.js
│   ├── cognition.js
│   ├── morphology.js
│   └── self-schema.js
│
├── render/
│   ├── svg.js
│   ├── organism.js
│   ├── phenotype.js
│   ├── self.js
│   ├── senses.js
│   ├── population.js
│   ├── inspector.js
│   ├── timeline.js
│   └── cognition.js
│
├── ui/
│   ├── controls.js
│   ├── profiles.js
│   ├── drawers.js
│   └── dialogs.js
│
└── ...
```

`app.js` becomes composition only.

---

# 21. Target app.js

After refactor, `app.js` should be approximately orchestration code:

```javascript
import { createStore } from "./state/store.js";
import { createDemoState } from "./state/demo-state.js";
import { connectFleet } from "./transport/fleet-stream.js";
import { bindControls } from "./ui/controls.js";
import { renderApp } from "./render/app.js";

const store = createStore(createDemoState());

store.subscribe(state => {
  renderApp(state);
});

bindControls(store);
connectFleet(store);
```

The goal is not a specific line count.

The goal is that `app.js` no longer contains domain logic.

---

# 22. Pure morphology module

Create:

```text
observatory/projection/morphology.js
```

It must be deterministic and side-effect free.

Example API:

```javascript
export function projectPhenotypeMorphology(input) {
  return {
    boundary,
    receptors,
    regions,
    core,
  };
}
```

Tests must verify:

```text
same input → same morphology
same identity → stable base morphology
topology revision change → bounded shape evolution
frozen state → no structural invention
0 edges → no rendered fibres
```

---

# 23. Separate rendering from projection

Do not calculate organism structure inside SVG rendering code.

Bad:

```javascript
function renderOrganism() {
  // infer biology
  // create geometry
  // inspect cognition
  // manipulate DOM
}
```

Preferred:

```text
raw state
   │
   ▼
projection
   │
   ▼
geometry model
   │
   ▼
renderer
```

Example:

```javascript
const model = projectPhenotype(state);
renderPhenotype(canvas, model);
```

The renderer receives already-resolved semantics.

---

# 24. New morphology mode state

Add:

```javascript
state.organismView = "phenotype";
```

Allowed values:

```text
phenotype
self
```

UI:

```html
<div class="organism-view-toggle">
  <button data-organism-view="phenotype">Phenotype</button>
  <button data-organism-view="self">Self</button>
</div>
```

This toggle belongs inside the individual view, not in the global `Individual / Population` selector.

Hierarchy:

```text
Individual
    ├── Phenotype
    └── Self

Population
```

---

# 25. Observatory self projection

Create:

```text
observatory/projection/self-schema.js
```

It receives only exported self-model data.

No topology fallback.

Example:

```javascript
export function projectSelfMorphology(bodySchema) {
  if (!bodySchema) {
    return {
      state: "undeveloped",
      parts: [],
      dependencies: [],
    };
  }
}
```

The renderer must explicitly support:

```text
undeveloped
partial
developed
```

---

# 26. Topology source

The Phenotype view may use Observatory topology data.

The Self view must not.

This distinction must be tested.

Example invariant:

```text
topology.nodes = 64
body_schema.parts = 12

Phenotype view → may show 64 structural elements
Self view      → may show only 12 represented parts
```

No implicit merge.

---

# 27. SVG vocabulary cleanup

Rename existing cell-specific concepts.

```text
cellPath
→ phenotypeBoundary

cell-fill
→ organism-fill

membrane
→ phenotype-boundary

membrane-inner
→ phenotype-boundary-inner
```

The word `membrane` should only remain if used explicitly as a visual metaphor, not as a domain concept.

---

# 28. Accessibility

The visual distinction must have a textual equivalent.

Accessible table should eventually include:

```text
Perspective
Part
Type
Known to organism?
Confidence
Health
Relation
```

Example:

```text
Phenotype | sense_123 | sense | no | — | healthy
Self      | part.07   | sense | yes | high | healthy
```

Color must not be the only carrier of meaning.

---

# 29. Observatory schema evolution

The snapshot contract should eventually add an optional self-model section.

Possible v3:

```json
{
  "schema_version": 3,
  "organism": {
    "cognition": {},
    "self": {
      "body_schema": {}
    }
  }
}
```

Do not force this into v2 if doing so weakens version semantics.

Preferred rule:

```text
v1 → no cognition
v2 → cognition
v3 → cognition + optional/required body schema according to contract
```

The exact compatibility rule should be made explicit in JSON Schema.

---

# 30. Research invariants

The implementation must preserve the following invariants.

## I1 — No false self-knowledge

Observatory must never synthesize body-schema knowledge from privileged topology.

## I2 — Visualization is one-way

Morphology never feeds back into cognition.

## I3 — Stable identity

The same organism should not appear as a completely different morphology between adjacent ticks without a corresponding developmental event.

## I4 — Developmental change is bounded

Morphological change must reflect real state changes and remain temporally smooth.

## I5 — No fabricated connectivity

If the graph has zero edges, no apparent cognitive connections are drawn.

## I6 — Self can be incomplete

Missing BodySchema data is valid.

## I7 — Self can disagree with phenotype

Divergence is preserved rather than corrected by the Observatory.

## I8 — Human geometry is not organism knowledge

SVG coordinates are never exposed back to Symbiont.

---

# 31. Development phases

## Phase 1 — Observatory refactor

No behavioral change.

Tasks:

- split `app.js`,
- isolate store,
- isolate snapshot projection,
- isolate SVG helpers,
- isolate render modules,
- maintain existing UI behavior,
- preserve replay/SSE semantics.

Exit condition:

> Observatory behaves identically to the current version with the old visual model, but rendering and projection are modular.

---

## Phase 2 — Phenotype morphology

Replace fixed cell.

Tasks:

- deterministic morphology seed,
- generated phenotype boundary,
- peripheral sensory layout,
- internal concept/readout layout,
- topology-derived fibres,
- health/safety visual modulation.

Exit condition:

> Two organisms with different phenotype/identity can visibly differ without invented structure.

---

## Phase 3 — Individual perspective toggle

Introduce:

```text
Phenotype | Self
```

Self initially displays:

```text
Body schema not yet developed
```

where no body schema is exported.

Exit condition:

> Observatory explicitly distinguishes scientific view from organism self-view.

---

## Phase 4 — Sensory BodySchema

Implement in organism:

```text
src/symbiont/core/embodiment/body_schema.py
```

Initial scope:

- sensory parts only,
- membership,
- health,
- confidence,
- recency,
- global schema confidence.

Exit condition:

> The organism can represent a subset of its own sensory apparatus without being handed the complete runtime topology.

---

## Phase 5 — Cognitive regions

Introduce coarse learned internal regions.

Exit condition:

> Symbiont can represent internal cognitive organization using opaque region identities.

---

## Phase 6 — Functional dependencies

Add learned relationships between body parts.

Exit condition:

> Self View can show organism-inferred internal structure rather than only parts.

---

## Phase 7 — Physiology integration

Connect BodySchema to Milestone F.

Add:

- stress,
- maintenance,
- dormancy,
- viability,
- metabolic state.

At this point the Body Schema becomes the organism's functional digital body model.

---

# 32. Testing strategy

## Unit tests

### Morphology

```text
same seed = same boundary
different identity = distinguishable boundary
health does not change identity
edge count controls fibres
no edge means no fibre
```

### BodySchema

```text
bounded parts
bounded dependencies
unknown part remains unknown
self membership does not come from evaluator
confidence evolves with evidence
checkpoint round-trip preserves consolidated schema
```

## Contract tests

Validate:

```text
v1
v2
v3
```

and reject illegal cross-version combinations.

## Integration tests

Example protocol:

```text
organism develops senses
→ SelfModel stabilizes
→ BodySchema discovers sensory parts
→ Observatory receives body_schema
→ Self View renders only known parts
```

## Adversarial tests

Ensure Observatory cannot:

```text
read phenotype topology
and silently insert it into Self View
```

---

# 33. Worker-3 validation protocol

Use the existing worker-3 checkpoint as the first reference case.

Expected phenotype:

```text
58 senses
5 concepts
1 readout
0 edges
```

Expected initial self view:

```text
partial sensory self-model
no complete cognitive body schema
```

The visualization should therefore show a visible mismatch.

This becomes a regression fixture for the core principle:

> Phenotype truth and self-perception are not the same data source.

---

# 34. Future extensions

The design intentionally supports later milestones.

## Digital physiology

Body Schema can represent:

```text
metabolism
maintenance
stress
waste pressure
viability
```

## Reproduction

Body Schema can later represent:

```text
lineage
reproductive maturity
offspring relation
continuity before/after fission
```

## Ecology

The boundary model gains:

```text
SELF
ENVIRONMENT
OTHER_SELF
```

This enables studying whether Symbiont distinguishes:

```text
me
world
other organism
```

without hand-coding social identity directly into cognition.

---

# 35. Long-term research question

The final objective is not to create a prettier visualization.

The objective is to make this measurable:

```text
actual organism
       │
       ├───────────────┐
       ▼               ▼
what it is       what it believes it is
       │               │
       └───────┬───────┘
               ▼
          divergence
```

That divergence may itself become a scientific observable.

A mature Symbiont should not necessarily have perfect self-knowledge.

It should have a developed, revisable and bounded model of itself.

---

# 36. Recommended implementation sequence

The recommended PR sequence is:

```text
PR 1
refactor(observatory): split state, projection and render layers

PR 2
feat(observatory): replace fixed cell with deterministic phenotype morphology

PR 3
feat(observatory): add phenotype/self perspective

PR 4
feat(self): introduce sensory digital body schema

PR 5
feat(observatory): render organism-owned body schema

PR 6
feat(self): learn coarse cognitive regions and dependencies
```

Do not combine all six into one PR.

The main architectural rule is:

> **The Observatory may know more about a Symbiont than the Symbiont knows about itself, but it must never pretend that privileged knowledge belongs to the organism.**

And the corresponding visual rule is:

> **Morphology represents organization. Geometry is a projection, not the organism's ontology.**

---
# Recurrent restoration contract in Symbiont

## Contract decision

## Two usage modes

## Temporal boundary

## Preserved state and reinitialized state

| Buffer / Variable | In inspected checkpoints | Dynamic restart criteria (`resume=True`) |
| --- | --- | --- |
| Learned graph (`CognitiveGraph` nodes and weights) | Always present and matched by topology verifier | Maintained exactly; structure continues unchanged |
| Accumulators of `ExperienceLedger` and `SensoryRelation` | Not present in block | Restarted; correlations will take N ticks to be reliably evaluated |
| Delay buffers | Not in inspected checkpoints | Initialized according to kernel; previous temporal content is lost |
| Current eligibility trace values | Not in inspected checkpoints | Initialized to zero (`eligibility=0.0`) according to kernel, changing future updates if there were non-zero traces |
| Eligibility decay coefficient | Part of the genome (`plasticity.eligibility_decay`) | Keeps its configured value; **must not be described as `λ=0`** |
| Random state, accumulators and additional runtime data | Require inventory in active code | Exact parity not promised until every state affecting subsequent ticks is verified |

The precise statement for eligibility is: "**the value of non-persisted traces is initialized upon restoration (`eligibility=0.0`)**". The initial value comes from the verified implementation and must not be confused with the genome's `eligibility_decay` coefficient. Loss of traces or variables from other subsystems should not be declared without inspecting their schemas.

## Available experimental evidence

The `continuity.recurrent-restoration` laboratory study compares A (continuous), B (full memory copy), C (real checkpoint) and D (experimental restoration with exact weights and restarted dynamics). The B/A comparison shows parity at the three evaluated levels. D preserves exact weights to isolate the effect of restarting dynamics; C adds the discrete checkpoint effect **if C and D identically reconstruct all other fields**.

| Measured level, three seeds | B vs A | D vs A | C vs A |
| --- | --- | --- | --- |
| Fixed dynamics, frozen learning | Reported divergence 0 | Maximum initial difference ~0.23; threshold <10⁻⁴ reached on average in 8.67 ticks; final error ~10⁻¹⁵ | Reported residual error ~0.0627; does not reach 10⁻⁴ threshold in the evaluated horizon |
| Active plasticity, fixed topology | `Δw=0`, `Δq=0` reported | Residual weight drift ~0.00104 attributed to the differing activations period | Reported weight drift ~0.06255 and eligibility drift ~0.1634 |
| Active structural development | Same trajectory and revisions reported | Matches in first consolidations of the experiment; late drift reported in long horizons | First post-cut consolidation, tick 48, divergent in all three evaluated seeds |

The loss of `previous_frame` produces, in D and in the three tested graphs/stimuli, a transient that diminishes. From this **it is not inferred that every `CognitiveGraph` is contractive**. In C, the observed residual and bifurcation are compatible with parametric changes due to quantization; the "100% weights" causality requires proving identity of C and D in all the rest of the restored state or performing additional ablations.

"Three out of three seeds differ in the first consolidation" is the formulation supported by those data. "Bifurcation is inevitable for any checkpoint" is not. With fixed topology and active plasticity, drift can persist even if output error decreases again: readout convergence and learning parity are separate properties.

## Limits of any numerical guarantee

A general guarantee of "transient dissipated in ≤12 ticks" is not declared. The observed average of 8.67 ticks for a 10⁻⁴ threshold across three seeds **is not an upper bound**, nor does it include all admissible recurrent graphs. A valid bound must declare norm, horizon, initial states, stimuli, topologies and permitted parameters, and sufficiently demonstrate or verify its stability condition.

If, for a bounded domain, the transition with fixed weights satisfies

$$
\|F_W(x,u)-F_W(y,u)\|\le L\|x-y\|,\quad 0\le L<1,
$$

then two trajectories with **the same weights and stimuli** fulfill

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|.
$$

This reasoning only applies as long as topology and relevant parameters remain fixed and the comparable state includes buffers, activations, and any other recurrent variable. The appearance of delayed cycles does not by itself prove or refute the condition ($L<1$). An empirical test reaching a threshold does not prove the inequality for all states.

With approximated weights $\widehat W$, if there is also a uniformly bounded perturbation per step $\delta$ such that

$$
\|F_W(x,u)-F_{\widehat W}(x,u)\|\le\delta,
$$

the comparison can be conditionally bounded by

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|+\delta\frac{1-L^t}{1-L}.
$$

The state residual is then limited by $\delta/(1-L)$; the readout error needs **another** output sensitivity bound.

In the current implementation (`symbiont.cognition.checkpoint`), the quantizer uses `WEIGHT_CLASSES = 16` over `WEIGHT_RANGE = (-2.0, 2.0)`. The discretization assigns:

$$
\text{class\_id} = \text{round}\left(\frac{\text{clipped} - \text{low}}{\text{high} - \text{low}} \cdot (N - 1)\right) = \text{round}\left(\frac{w - (-2.0)}{4.0} \cdot 15\right)
$$

The uniform step between levels is $\Delta w = 4.0 / 15 \approx 0.266667$. Exact zero is not a grid point (classes 7 and 8 correspond respectively to $-0.133333$ and $+0.133333$). Therefore, any weight close to 0 shifts at least $0.133333$ in magnitude when quantized.

## Compatibility, failure and observability

A checkpoint must validate schema version, kernel/genome compatibility, numerical integrity, node/edge identity and persisted temporal states before resuming. If validation or application fails, it must keep the original checkpoint intact and emit an observable failure.

Consumers —including Observatory— must be able to distinguish: continuous execution, resumed execution from checkpoint, and laboratory experiment. A first zero output when starting a new run must not be automatically attributed to a cognitive lesion: in topologies with delays $\ge 1$ between senses and readouts, the first output after a dynamic cold start is structurally 0 while the signal transits through latent layers. The Self view can only show what has been incorporated into the organism's own knowledge; the restoration warning and the technical origin of the checkpoint belong to external instrumentation.

The minimum telemetry required for Priority 4 is: `organism_id`, `run_id`, `sequence`, tick and cut-point revision, checkpoint hash/version, effective `kernel_version`/build, restoration mode, restarted fields and first confirmed event after resuming. A coherent capture must link registry, journal, topology and checkpoint without treating them as a global transaction if there was no export barrier.

## Criterion to close Priority 3

1. Incorporate into the repository documentation the approximate continuation / dynamic cold start contract, expressly noting that exact replay of output, weight or topology is not guaranteed.
2. Verify in the code that C and D only differ in weight precision if exclusive causality is claimed, and review the communicated numbers, norms, thresholds and horizons against the reproducible artifact of the study.
3. Inventory the non-persisted state that determines the next ticks and specify its initial values upon restoration (`previous_frame={}`, `eligibility=0.0`).
4. Validate save/restore at cuts with occupied buffers, non-zero eligibility and before/after consolidation. Declare trajectory divergence where appropriate, even if the readout becomes active again.
5. Reserve the observed empirical bound and the assumed global contractive character for a mathematical proof with explicit domain or a limited empirical promise validated separately; do not include them as a general guarantee in this contract.

