# Cross-Domain Revision Coherence v1

Status: **revision 3 — approved for Wave 0 implementation** (owner, 2026-09-28).
Wave 1 conceptually approved, pending owner start. Waves 2-5 remain gated by
their preregistered decisions. Baseline: `main @ c1a43963`. Origin: owner audit of
`org-5c3fb582fb17` (2026-09-27), code claims re-verified against `main`
(§1.2).

Revision 2 incorporates the owner review: the executive never invalidates
bindings (§3.3); predictions depend on predictability, not admissibility
(§3.1, §3.5); four orthogonal competence questions and two hypothesis axes
(§3.1, §7.1); closed staleness/invalidation reasons (§3.2); evidence-based
retest independence and an explicit relevance formula (§4); Wave 3 split
into 3A/3B with non-circular pool scores and lifecycle-aware pins (§5, §6);
common passive event with two derived views (§6); ancestry eligibility and
lineage stagnation (§8); and a behaviour-neutral Wave 0 (§2.1).

Revision 3 (second owner review): `actionable_test_now` and
`prediction_scope` (§3.1); binding status/reason invariants (§3.2); Wave 0
observes capacity decisions only after they resolve (§2.1); the retest
formula corrected to the stored effect semantics and its support cap scoped
to the option (§4.2); hard-pin saturation (§5); passive event fields (§6);
generative activation state as its own axis (§7.1); `validation_gain`
reference (§8); a common `revision_id` (§2.2); and extended gates.

## 1. Problem

### 1.1 Diagnosis

Symbiont's subsystems are individually sound, but a revision learned by one
authority does not reach the others. Competence knowledge, execution
bindings, executive outcomes, generative cognition and embodiment adaptation
each hold a legitimate part of the truth about a competence, and each decides
"executable" or "still worth considering" by its own rule. The result is an
organism with much knowledge but little stable, revisable, reusable agency:
primitives stuck at two or three occurrences, one usable competence,
hundreds of generative activations of a target the executive rejects, a
private-model loop retraining from scratch, and an effect memory that
silently forgets what is new.

The fix is **not** to merge these authorities. It is to preserve distinct
forms of truth and make their relations and revisions explicit, and to make
bounded forgetting observable.

### 1.2 Verified findings (code at `c1a43963`)

| Id | Sev | Finding | Evidence |
|---|---|---|---|
| F1 | P0 | Bindings have no lifecycle; a binding whose causal basis was revised stays valid | `actuation/binding.py`: `bind_from_evidence/get/is_executable/invalid_for_surface/checkpoint/restore` only |
| F2 | P0 | Three definitions of "executable" | `ActionDomain.competence_is_executable` (binding+maturity+controller); `physics3d/runtime.py:938,1733,1818,1920` and `individual.py:199` (binding only); executive suppression (admission only) |
| F3 | P1 | Prediction and action policy are entangled in one fallback | `ActionDomain.predict_competence_effect` (`action.py:333-347`) serves predictions from the binding with no notion of predictability vs. executability |
| F4 | P0 | `reacclimation_completed` means "window elapsed", not "adapted" | `physics3d/runtime.py:1838-1843` |
| F5 | P0 | Exported directories can pair stale `metadata.json` with a newer bundle | bundle atomic (`os.replace`); metadata separate, refreshed only in `Physics3DRunStore.finalize()` |
| F6 | P1 | Primitive→competence needs independent natural recurrence; no endogenous retest | `sensorimotor.py:368`; `_record_primitive_episode` `stat.count < 2` |
| F7 | P1 | `EffectSpace` evicts at 512 by support: incumbency lock-in, unobservable | `effects.py:215-224` |
| F8 | P1 | Two passive-evidence mechanisms can diverge | `sensorimotor.py` passive stats; `evidence.py` `observe_passive_window`; `action.py` passive transition |
| F9 | P1 | Generative use tracker rewards recurrence without new evidence | `cognition/generative/consolidation.py` |
| F10 | P2 | No ACTIVE private model ⇒ every training is a root | `modeling/runtime.py:926` |
| F11 | P2 | `established_competence_count` counts *executable* competences | `action.py:2077` |
| F12 | P1 | Hard bounds truncate without recording pressure or evictions | EffectSpace, primitive stats, bindings, executive keys, generative reps |
| F13 | — | Footprints admit atoms on drifting receptors: pilot 13/22 members (seed 101, 600 ticks); **E8 v3 (preregistered): 8/8 satisfactions under current reconciliation and 106/127 under chance-corrected reconciliation are spurious** | Factorized Effects §16.4 |
| F14 | — | Physics3D copies of `org-ea3e7bbbc628` starve with zero absorbed material (factorized 2 650 ticks, flag-off control 2 604) | Factorized Effects §15 |

Kept as correct: competence knowledge ≠ binding; generative hypothesis ≠
factual evidence; body time ≠ Symbiont time; physical energy ≠ metabolic
accounting (negative balances are debt; physical energy ≥ 0); rest never
mints energy; energy only from physical contact with a world resource;
prediction ≠ action authority; the SLM promotion gate; body, torques,
gravity, competence thresholds and store sizes.

## 2. Principles

1. **Projections, not new authorities.** Derived every tick from existing
   authorities, never an independent source of fact, not persisted.
2. **Each authority revises only what it owns.** Causal/binding evidence
   revises bindings; the executive records outcomes and suppresses
   admission; neither mutates the other. Revisions flow as traced events.
3. **Orthogonal questions.** For competences: *known → predictable →
   executable → admissible*. For hypotheses: *believed (epistemic status)*
   and *testable (opportunity)* are separate axes.
4. **Forgetting is a phenomenon.** Every bounded store reports pressure and
   evictions.
5. **No hidden policy.** No scheduled replay, no "go to resource", no
   semantic goals.
6. **Fact ≠ imagination.** Generative activity never counts as evidence; it
   may be cooled by lack of evidence.
7. **Preregistration.** Behaviour-changing waves ship behind options off by
   default (except Wave 1, §3.8), with preregistered studies and gates.
8. **Checkpoint → restore → continue** yields the same causal history in
   every touched domain.

### 2.1 Wave 0 — Measurement coherence (behaviour-neutral)

Observability only; no decision of the organism changes (trajectory hashes
identical, asserted by test). Establishes the last clean baseline before
Wave 1.

- Telemetry of the four competence questions computed *as if* the
  projection existed (counts: known, predictable, executable, admissible,
  suppressed) plus today's `established_competence_count` for continuity.
- `CapacityPressure` record (`capacity`, `occupancy`, `evictions`,
  `promotions`, `demotions`, `relearned_after_eviction`) for EffectSpace,
  primitive stats, bindings, executive keys, generative representations;
  evictions emitted as provenance events.
- Generative `sterile_reactivation_count` (activation with no new evidence,
  branch, uncertainty reduction or context change) — counted, not acted on.
- Private-model lineage metrics (roots, generations, retirements by reason).
- Passive-evidence counters for both mechanisms (motor baseline frames,
  ledger passive windows).
- `reacclimation_window_completed` and `adaptation_state` (§3.6) added
  alongside the old field.
- Baseline run: E6, E8 (arm R) and a Physics3D copy recorded with Wave 0
  metrics before Wave 1 changes behaviour.

**Instrumentation rule.** Wave 0 may observe an existing capacity or
lifecycle decision only after that decision is fully resolved: the
existing policy selects and applies its victims, and only then are they
noted. Instrumentation must not change sort order, eviction timing, dict
iteration, hash material, or any checkpoint content that behaviour reads;
new metrics live in separate checkpoint sections that no decision reads.

**Implementation decisions (Wave 0).**

- Evictions are recorded in `CapacityPressure` only (with a short one-way
  fingerprint per evicted item for `relearned_after_eviction`). Emitting
  them as provenance events would change the provenance history the W0 gate
  requires to be identical, so eviction events arrive with Wave 3A.
- `sterile_reactivation_count` is defined operationally as a reactivation of
  an already tracked representation in an already seen episode (context)
  that adds no new source ref (evidence or branch). Uncertainty reduction is
  not observable at the tracker; Wave 4 refines the definition.
- Found while instrumenting (not changed, behaviour): `GenerativeUseTracker`
  evicts the oldest representation by insertion order, but
  `from_checkpoint` rebuilds in sorted order, so after a restore the victim
  can differ from a continuous run — a replay-determinism defect to repair
  with a strict regression test outside Wave 0.

**Gate W0:** trajectory hashes byte-identical and provenance histories
identical (by `revision_id`/event id) with Wave 0 on vs. the pre-Wave-0
commit; every metric above present, checkpoint-stable and documented.

### 2.2 Revision identity

Every revision (binding status change, causal revision, suppression,
suppression lift, embodiment change, eviction) carries a content-addressed
`revision_id`, emitted as a Causal Provenance v1 event with `caused_by`
evidence refs. It is an identity, not an authority: consumers (executive,
availability, generative testability, embodiment adaptation) record which
`revision_id` they observed. "Same causal history after restore" is checked
by comparing revision ids, not only final states.

## 3. Wave 1 — Cross-domain competence revision (P0)

### 3.1 `CompetenceAvailability` projection

Owned by `ActionDomain`, memoized per tick, never checkpointed. Per
competence, grouped by authority:

| Group | Fields |
|---|---|
| knowledge | `known`, `maturity`, `support`, `reproducibility` |
| causal | `predictable_now`, `controllability`, `agency`, `last_evidence_tick` |
| physical | `binding_status`, `surface_match`, `controller_available`, `executable_now` |
| executive | `suppressed`, `suppression_reason`, `admissible_now` |
| epistemic | `testable_now`, `actionable_test_now`, `prediction_scope` |
| verdict | `reason` (first failing condition, closed set) |

- `predictable_now = known ∧ effect representation available ∧
  binding_status ∈ {VALID, STALE}` — the causal relation is still believed,
  whether or not it can be acted on now.
- `executable_now = binding_status == VALID ∧ surface_match ∧ maturity ∈
  {ESTABLISHED, ROBUST} ∧ controller_available` (today's
  `competence_is_executable`, now the single definition).
- `admissible_now = executable_now ∧ ¬suppressed`.
- `testable_now = predictable_now ∧ executable_now` — a prediction about it
  could physically be checked by acting now (independent of suppression).
- `actionable_test_now = testable_now ∧ admissible_now` — the organism may
  legitimately attempt that check now. Budget aimed at real execution
  (Wave 4) uses this, not `testable_now`.
- `prediction_scope ∈ {CURRENT, HISTORICAL, UNCERTAIN_CURRENT}`: VALID →
  CURRENT; STALE by `SURFACE_NOT_CURRENT`/`EMBODIMENT_NOT_CURRENT` →
  HISTORICAL ("this happened on that body"); STALE by `EVIDENCE_AGED` or
  `CONTROLLER_UNAVAILABLE` → UNCERTAIN_CURRENT. Consumers must not treat a
  HISTORICAL prediction as a claim about the current body.

Legitimate combination example: predictable ∧ executable ∧ ¬admissible
("I believe C produces E, C can run, but C is suppressed now").

### 3.2 Binding lifecycle

`CompetenceExecutionBinding` gains `status ∈ {VALID, STALE, INVALIDATED}`,
`status_reason`, `valid_from_tick`, `last_confirmed_tick`,
`status_changed_tick`, `revision`. `reliability` is explicitly historical.

Closed, extensible reason sets (schema admits all; each wave implements the
subset it needs):

- `StalenessReason`: `SURFACE_NOT_CURRENT`, `EMBODIMENT_NOT_CURRENT`,
  `CONTROLLER_UNAVAILABLE`, `EVIDENCE_AGED`. Stale is reversible when the
  cause clears.
- `InvalidationReason`: `CAUSAL_RELATION_REVISED`, `EFFECT_SUPERSEDED`,
  `EVIDENCE_CONTRADICTED`. Only causal/binding evidence produces these.

Invariants: `VALID ⇒ status_reason is None`; `STALE ⇒ status_reason ∈
StalenessReason`; `INVALIDATED ⇒ status_reason ∈ InvalidationReason`.
`last_confirmed_tick` and `status_changed_tick` are independent (an
invalidation may follow the last confirmation). `previous_status` and
`previous_revision` live only in the provenance event of the change, not in
the persisted binding.

Wave 1 implements `SURFACE_NOT_CURRENT`, `EMBODIMENT_NOT_CURRENT`,
`CONTROLLER_UNAVAILABLE` and `CAUSAL_RELATION_REVISED`. Rebinding from new
evidence ⇒ `VALID`, `revision + 1`. Nothing is deleted. Checkpoint schema
bump; migration: existing bindings `VALID`, `revision 0`
(tests/compatibility).

### 3.3 Revision flow between authorities

```
causal/binding evidence --(traced: binding_invalidated / binding_stale)--> binding status
binding status --(observed by)--> executive: suppress admission for the key
                                             (event: executive_suppressed_due_to_binding_*)
```

The executive **never** mutates a binding. `required_causal_binding_invalidated`
becomes an executive *observation* of a prior factual `binding_invalidated`
event (its cause in provenance). A surface change marks bindings STALE
directly (the surface is binding evidence).

`ExecutiveOutcomeLedger.suppression(key, revision)` answers without side
effects; lifting stays in admission (`modulation()`).

### 3.4 Consumers switched to the projection

| Consumer | Wave 1 reads |
|---|---|
| `predict_competence_effect` (generative `competence-effect` model) | `predictable_now`; the prediction carries `prediction_scope`, `executable_now`, `admissible_now`, `testable_now`, `actionable_test_now` as annotations |
| `AffordanceResolver` | `executable_now` (admission applies suppression) |
| executive admission | `admissible_now` |
| Physics3D adaptation `revalidated_count`, unbound/telemetry (`runtime.py:938,1733,1818,1920`), `individual.py:199` | `executable_now` |
| intent reconciliation `competence_executable` | `executable_now` |

A structural test forbids direct `bindings.is_executable` outside the
projection.

### 3.5 Generative use in Wave 1

Generative cognition keeps receiving predictions for predictable
competences; it learns *why* it cannot act on them through the annotations.
Budget policy on untestable targets is Wave 4; Wave 1 only guarantees the
information is available and consistent.

### 3.6 Reacclimation semantics

`reacclimation_window_completed` (timer) plus `adaptation_state ∈
{reacquiring, unstable, stabilizing, adapted}` and
`adaptation_recovered_at_tick` from `EmbodimentAdaptation` (`reacquiring`
while the window runs; `unstable` when it ended with `stable_ticks == 0`;
`stabilizing` with `stable_ticks > 0` and no recovery; `adapted` once
`recovery_tick` is set). Added in Wave 0; Wave 1 retires the old name via a
named telemetry migrator. Observatory display: separate contract.

### 3.7 Export manifest

Exports derive a manifest from the runtime payload inside the bundle
(`checkpoint_id`, `saved_at_tick`, `runtime_sha256`, `embodiment_id`,
`body_id`, `embodiment_epoch`, `generated_from_runtime: true`) and verify it.
`metadata.json` is never exported as scientific authority.

### 3.8 Tests and gate

Tests: a factual binding invalidation propagates to executive suppression
with a provenance cause; the executive cannot change binding status; a
causal revision lifts suppression; suppressed competences stay predictable
with correct annotations; adaptation uses canonical executability;
reacclimation window never claims adaptation; export manifest matches the
runtime; lifecycle survives checkpoint→restore; bindings migrate.

**Gate W1:** property over E6/E8 runs — never `suppressed ∧ admissible_now`
absent a later traced revision, and never `executable_now` with a
non-VALID binding; predictable historical knowledge survives a
non-current embodiment (no fix by forgetting); the same factual revision
yields the same projection after restore; E6 passes in both effect modes; trajectory changes are
documented against the Wave 0 baseline. Wave 1 changes defaults without an
option because it removes contradictions rather than adding capability.

## 4. Wave 2 — Endogenous epistemic retest (P1)

### 4.1 Mechanism

Primitive uncertainty becomes the `epistemic_relevance` of an ordinary
affordance, competing in existing executive admission. Nothing is
scheduled. Option `CompetenceDevelopmentEngine(epistemic_retest=False)` by
default.

### 4.2 Relevance formula (fixed before E9)

From the primitive's own statistics — occurrences `n`, effect mean `m` and
variance `v`, directional consistency `d` — and the passive effect variance
`v0`. `m` is the stored `stat.mean`: **non-negative effect strength after
passive subtraction** (`max(0, raw_effect − passive_mean)`,
`sensorimotor.py` `_record_primitive_episode`); direction is carried by `d`,
so the baseline is not subtracted again:

- relative uncertainty reduction of one more independent occurrence:
  `g(n) = 1 − sqrt(n / (n + 1))` (0.184 at n=2, 0.106 at n=4);
- standard error with a floor from the organism's own passive noise:
  `se = sqrt(max(v, v0, 1e-3) / n)`;
- causal plausibility: `p = Φ(m / se) × d`;
- `epistemic_relevance = (g(n) / g(1)) × p`, zero when
  `n > epistemic_retest_max_support` (8) or below 0.05.

`g(1) = 1 − sqrt(1/2)` normalizes to [0, 1]. The constants (1e-3, 8, 0.05)
are preregistered E9 parameters of the `epistemic_retest` option, not
properties of motor primitives: after drift, injury, embodiment change or a
causal revision a well-supported primitive may become uncertain again, and a
later version should let evidence age, revision and prediction mismatch
restore relevance.

### 4.3 Independence

A retest counts as an independent occurrence only if it has a **new
commitment id**, **disjoint evidence blocks** from every previous occurrence
(`_primitive_last_evidence_blocks`), and **no overlap of causal windows**
with them; context-state distance is added when available. A passive window
between them is recorded as a supporting signal, not the definition.

A failed retest weakens (mean/consistency update); spent demand without
support cools the primitive (relevance → 0), never deletes it.

### 4.4 Dependency, study, gate

Starts after E8 v3 reports spurious rates (F13); if high, a
footprint-precision spec comes first. Preregistered **E9** (synthetic body,
ground truth): retest off/on; fraction of primitives leaving n ≤ 3, retests
per primitive, promotions matching ground truth vs. spurious, competences per
1 000 attempts. **Gate W2:** promising primitives are independently retested
and either gain support or weaken; spurious promotions within a
preregistered bound; E6 passes.

## 5. Wave 3A — Open-world effect memory (P1)

- **Candidate pool** (default 128): new effects enter here; score from
  **recurrence, recency, novelty** only (a candidate cannot yet have causal
  use, so it is never penalized for lacking it).
- **Consolidated pool** (default 512): promotion at `support ≥ 2`; score from
  support, causal reuse, binding references, intent references, recency.
- Retention by lifecycle: VALID binding → hard pin; STALE binding → soft
  retention bonus; INVALIDATED binding → no pin; live intent → hard pin;
  explicit experimental pin → hard pin. Hard pins count against capacity and
  are reported in `CapacityPressure`.
- **Hard-pin saturation:** if every consolidated slot is hard-pinned, no pin
  is evicted; a promotable candidate stays a candidate and the store records
  `promotion_blocked_by_pinned_capacity` (in `CapacityPressure` and
  provenance). A bounded store defines what happens when its invariants make
  admission impossible.
- Provenance events: `effect_created`, `effect_promoted`, `effect_evicted`,
  `effect_reobserved`, `promotion_blocked_by_pinned_capacity`.
- Checkpoint schema bump; migration: all existing effects consolidated.

**Gate W3A:** with the consolidated pool full, a novel reproducible effect is
promoted; every eviction is auditable; E8 (arm R) rerun shows no loss of
effects bound by VALID bindings and a non-zero promotion rate at saturation.

## 6. Wave 3B — Passive counterfactual canonicalization (P1)

One common factual event, two derived views:

```
PassiveObservation (one event per passive window, traced)
   ├──> CausalEvidenceLedger        (counterfactual windows)
   └──> PassiveBaselineAccumulator  (incremental motor baseline)
```

The event carries `observation_id`, `tick_start`, `tick_end`, `context_ref`,
`state_before_ref`, `state_after_ref` and its effect atoms / opaque deltas;
each view persists only its own aggregates, and the event (provenance) is
the common causal reference.

The motor learner stops detecting passivity on its own; both views consume
the same events, so they cannot diverge, and the motor accumulator stays
incremental and bounded. Run separately from 3A so trajectory changes can be
attributed.

**Gate W3B:** every passive event reaches both views; counts consistent
across checkpoint→restore; E6/E8 reruns documented against 3A.

## 7. Wave 4 — Generative epistemic hygiene (P1)

### 7.1 Two axes

- `HypothesisEpistemicStatus`: `HYPOTHESIZED`, `PREDICTED`, `SUPPORTED`,
  `CONTRADICTED`, `SUPERSEDED` (what is believed).
- `HypothesisTestability`: `TESTABLE_NOW`, `BLOCKED_BY_EMBODIMENT`,
  `BLOCKED_BY_BINDING` (whether it can be checked), derived from the Wave 1
  projection (`testable_now` and its reason).
- `GenerativeActivationState`: `ACTIVE`, `COOLED_PENDING_EVIDENCE` (whether
  it deserves activation until something changes).

Execution-directed budget requires `actionable_test_now`; untestable or
cooled hypotheses keep their epistemic status; supersession comes only from
causal revision events.

### 7.2 Sterile reactivation

Wave 0's `sterile_reactivation_count` now acts: consolidation signal and
priority decay with sterile reactivations (cooling, never deletion);
recurrence alone no longer raises consolidation. Tracker adds
`new_evidence_since_last_use`, `new_branch_since_last_use`,
`uncertainty_reduction`.

**Gate W4:** cooling never changes factual hypothesis status; budget stops
flowing to non-actionable targets; sterile activations
bounded; generative→factual reconciliation rate rises; generative output
never enters factual evidence (existing boundary tests).

## 8. Wave 5 — Private-model genealogy (P2, parallel after Wave 0)

- **Training ancestry ≠ control authority.** Only ACTIVE models control; a
  SHADOW model may be a training parent only if **ancestry-eligible**: its
  validation exceeds both its parent's validation (roots: none) **and** the
  canonical non-neural baseline of the predictive study; no catastrophic
  regression on the held-out validation; not contradicted by later evidence.
- Children record `parent_model_id`, `generation + 1`.
- A new root requires a traced reason: `no-eligible-ancestor`,
  `ancestor-contradicted`, `architecture-change`, or `lineage-stagnation`
  (N generations without validation gain; N preregistered).
- Promotion gate to ACTIVE unchanged.

**Gate W5:** training ancestry never grants action authority (structural
invariant); after repeated failed promotions the next training has
`generation > 0` or a traced root reason; no indistinguishable root chains;
no lineage of more than N non-improving generations.

## 9. Out of scope

- Homeostasis → foraging learning (F14): open scientific question; no
  semantic goals. A separate study proposal after Wave 1 (affordance credit
  from homeostatic relief after real contact).
- Observatory displays (metabolic debt vs. physical energy; body-schema
  maturity vs. boundary confidence; adaptation state): passive views,
  separate live-protocol contract.

## 10. Order and decisions

```
Wave 0 (measurement) ──> Wave 1 (competence revision) ──┬──> Wave 2 (retest) ──┐
          │                                             └──> Wave 3A ──> 3B ────┴──> Wave 4
          └──> Wave 5 (private-model genealogy, parallel)
```

| Wave | Behaviour change | Owner decision |
|---|---|---|
| 0 | none (asserted) | approve |
| 1 | yes, by design | approve; accept documented trajectory change |
| 2 | behind option | approve; E9 preregistration (incl. §4.2 constants) |
| 3A | behind option | pool sizes; E8 rerun preregistration |
| 3B | yes (single passive source) | approve |
| 4 | behind option | approve cooling rule |
| 5 | behind option | approve ancestry rule and N |

## 11. Test inventory

| # | Test | Wave |
|---|---|---|
| 0 | Wave 0 metrics leave trajectory hashes unchanged | 0 |
| 1 | factual binding invalidation propagates to executive suppression (traced cause) | 1 |
| 2 | executive cannot mutate binding status | 1 |
| 3 | causal revision legitimately lifts suppression | 1 |
| 4 | suppressed competence stays predictable with correct annotations | 1 |
| 5 | embodiment adaptation uses canonical executability | 1 |
| 6 | reacclimation window does not claim adaptation | 0/1 |
| 7 | export manifest and runtime are the same checkpoint | 1 |
| 8 | promising primitive receives endogenous, independent retest | 2 |
| 9 | unsuccessful retest weakens the primitive | 2 |
| 10 | successful retest promotes evidence | 2 |
| 11 | full effect space still admits a novel recurrent effect | 3A |
| 12 | effect eviction is causally auditable | 3A |
| 13 | invalidated bindings do not pin effects | 3A |
| 14 | passive event reaches both views | 3B |
| 15 | generative budget stops on untestable targets | 4 |
| 16 | failed shadow training informs next generation; stagnation allows traced root | 5 |
| 17 | resource contact changes physical energy exactly once | kept |
| 18 | rest never mints physical energy | kept |
| 19 | checkpoint → restore → continue gives the same causal history in every touched domain | all |
