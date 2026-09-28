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
| F13 | — | Footprints admit atoms on drifting receptors: pilot 13/22 members (seed 101, 600 ticks); **E8 v3 (preregistered): 8/8 satisfactions under current reconciliation and 106/127 under chance-corrected reconciliation are spurious** | Factorized Effects §16.4. Status (owner, 2026-09-28, after FP-0…FP-3): **OPEN — mechanism characterized, solution not established** (Footprint Precision v1 §14) |
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

### 2.1.1 Wave 0 baseline (2026-09-28, commit `50aeab50`)

Gate W0 passed: behaviour and provenance fingerprints identical to the
pre-Wave-0 commit (E6 both modes with checkpoint→restore→continue; E8 600
and 3 000 ticks). Baseline runs on `50aeab50`:

| Run | Result | Wave 0 measurements |
|---|---|---|
| E6 whole-state (`...-27d0`) | gate passed | known 1-2, executable 0-1; passive: ledger 0-1 windows, motor baseline 0 frames |
| E6 factorized (`...-84c4`) | gate passed | known 2-8, executable 2-7, suppressed 0-1; passive: ledger 36-175, motor 15-52 |
| E8 arm R, 10 seeds (`...-b0c8`) | 8 satisfied, 8 spurious | known 383, predictable 383, executable 328, suppressed 48; effect space **16 994 evictions, 1 375 relearned**; passive: ledger 6 268, motor 2 265 |
| Physics3D copy of `org-ea3e7bbbc628` | starved at tick 11 897 (reproduced) | known 27, predictable 22, executable 20, suppressed 1; `reacclimation_completed = true` with `adaptation_state = unstable` (F4 observed); private models 64, **all roots, generation 0**, 61 retired, 3 shadow (F10 observed); passive: ledger 754, motor 286 |

Readings: F4, F7 and F10 are now measured, not inferred; F8 shows as two
different counts everywhere and as near-zero passive evidence in whole-state
E6. Every suppressed competence is also non-executable in these runs.
**Limit:** `sterile_reactivation_count` is 0 in every run, including
Physics3D with 56 generative representations. Either no sterile reuse
occurred or the operational definition (same episode, no new source) never
matches because episode ids differ per activation; this must be resolved
before Wave 4 relies on it.

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

### 3.9 Wave 1 implementation decisions (2026-09-28)

Found while mapping the code: **no causal evidence invalidates a binding
today.** Bindings are only refreshed when an execution's observed effect
matches the competence's effect (`action.py` `bind_from_evidence`); the
only use of `required_causal_binding_invalidated` is a post-restore
consistency check (`action.py:2651`), not causal evidence.

Implemented in Wave 1 (no new modelling):

- binding lifecycle fields, invariants, schema bump and migration (§3.2);
- `STALE / SURFACE_NOT_CURRENT` when the current surface differs, reverting
  to `VALID` when it returns (replaces the implicit `invalid_for_surface`);
- `STALE / CONTROLLER_UNAVAILABLE` when a controller leaf cannot activate,
  reverting when it can — today's `competence_is_executable` controller
  condition, now recorded as a traced status instead of recomputed silently;
- the projection, read-only suppression query, consumers, annotations,
  metrics, structural test and export manifest (§3.1, §3.3-§3.7);
- the post-restore check keeps its reason but is traced as an intent
  consistency event, not as a binding invalidation.

**Owner decisions required before they are triggered** (schema admits them;
nothing produces them yet):

1. `INVALIDATED / CAUSAL_RELATION_REVISED` needs a producing rule. Proposal:
   since the binding's last confirmation, at least 4 executions of the
   competence and the Wilson upper bound (95%) of their match rate against
   the binding's effect below the length-matched quiet rate of that effect —
   symmetric with footprint membership (§13.7), so a binding is invalidated
   by the same kind of evidence that would have refused it.
2. `STALE / EMBODIMENT_NOT_CURRENT` on re-embodiment into a body with the
   **same** contract would mark every binding stale at each rebirth and
   remove all executable competences until re-confirmed. Proposal: do not
   trigger it in Wave 1 (surface change already covers different bodies);
   revisit with Physics3D rebirth data.
3. `STALE / EVIDENCE_AGED` needs an age scale; proposal: not triggered in
   Wave 1.

Telemetry: `executable_competence_count` and the new counts are added and
`established_competence_count` kept as a deprecated alias (the live
telemetry contract is changed only through its own design, per the project
rule on live protocol changes); likewise `reacclimation_completed` stays
beside `reacclimation_window_completed`.

### 3.10 Wave 1 result (2026-09-28, commits `6dbfc0d6`, `57f6ec8a`, `c3ece2d4`)

**Gate W1 passed.**

- Property: across 900 ticks of E6 in both effect modes, no competence is
  suppressed and admissible, and nothing is executable without a
  live-usable binding; projections are identical after restore (tests in
  `tests/integration/test_competence_availability_runtime.py`).
- Structural: no `is_executable` call outside the projection; only the
  action domain revises binding status; the executive never imports
  bindings.
- E6 passes in both effect modes on `c3ece2d4`.
- Trajectory against the Wave 0 baseline (`50aeab50`): **behaviour
  identical** — actuations, causal evidence and body state match for E6
  (both modes, with checkpoint→restore→continue) and E8; E6/E8/Physics3D
  Wave 0 measurements match exactly. Provenance differs only by the new
  traced binding transitions (+1 to +2 events per run). The intended
  change (affordances require an available controller) did not alter any
  decision in these runs because admission already rejected those
  candidates later.
- Observed: in E6 (seed 127, tick 600) a binding was already STALE /
  CONTROLLER_UNAVAILABLE — the audit's "competence outlives its
  controller", now a traced status.

**§3.9 decisions (owner, 2026-09-28): all three proposals accepted.**
Decision 1 is implemented with one refinement found while testing: the
rest rate it compares against is its Wilson upper bound (95%), not its
point estimate. Every bound effect in the E6 fixture had never been seen in
135 passive windows (point estimate 0), and no match rate can be shown to
be below 0, so the literal rule could never invalidate anything. With the
upper bound (~0.027 per window at 135 windows) roughly 30 or more
consecutive unconfirmed executions of a few windows are needed —
testable, still conservative. Decisions 2 and 3 are not triggered.

### 3.11 Decision 1 failed the E6 gate — now off by default (2026-09-28)

Comparison runs of `f2538744` (rule on) against Wave 1 (`c3ece2d4`):

| Run | Wave 1 | Rule on |
|---|---|---|
| E6 whole-state | gate passed | gate passed |
| E6 factorized | gate passed | **gate FAILED**: seed 149 never closes (Wave 1: first satisfied intent at 1 832); 6 bindings invalidated, 24 competences known (8 before) |
| E8 arm R | 8 satisfied, 8 spurious; 328 executable | 15 satisfied, 5 spurious; 226 executable; 140 bindings invalidated |

Cause: the refinement (upper bound of the rest rate) makes the rule most
aggressive when the organism knows least. With few passive windows the
upper bound is large (~0.16 per window at 20 windows, ~0.65 over a
6-window commitment), so 4 failures (Wilson upper bound 0.49) already
invalidate a binding that would later have closed. The literal rule (point
estimate) never fires for effects never seen at rest. Both show that
"no better than rest" is the wrong comparison when rest is unobserved.

**Owner decision (2026-09-28):** the rest-based rule is a recorded
negative result, kept only as an experimental control arm and never
promoted. Invalidation against the binding's own history is studied as an
independent preregistered experiment (Binding Degradation v1), not as a
Wave 1 default.

Because E6 is a release gate, the rule is **off by default**
(`ActionDomain.causal_binding_invalidation = False`); with it off,
behaviour and provenance are identical to Wave 1. Proposal for an owner
decision: compare the competence with **its own history** instead of rest —
invalidate when the Wilson upper bound of the match rate since the last
confirmation falls below the Wilson lower bound of its match rate while
the binding was being confirmed — preregistered with the E6 gate and the
E8 spurious-satisfaction metric (which the rule did improve: 5/15 vs 8/8).

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

### 8.1 Wave 5 implementation plan (2026-09-28)

Code facts: every training result carries `candidate_loss` (held-out
validation), `best_baseline` / `best_baseline_loss` (the canonical
non-neural baseline) and `gain_over_trivial` (`physics3d/slm.py` `poll`),
but `ModelRecord` keeps neither loss; `request_private_model_training`
accepts a parent only if it is ACTIVE (`modeling/runtime.py`), which is why
all 64 models of the Wave 0 Physics3D baseline are generation-0 roots.

1. `ModelRecord` gains `validation_loss` and `baseline_loss` (adopted from
   the training result; schema bump, older records migrate with `None`,
   which makes them ineligible as ancestors).
2. **Ancestry eligibility** (pure function): `validation_loss <
   baseline_loss`, `validation_loss < parent.validation_loss` (roots: no
   parent condition), state SHADOW or ACTIVE, and not contradicted
   (`prediction-revision` has not fired against it).
3. A training request may name an **ancestry parent** (eligible SHADOW or
   ACTIVE), distinct from the existing adaptation parent (ACTIVE only).
   The child records `parent_model_id` and `generation + 1`. Activation is
   untouched: the promotion gate still decides authority alone
   (structural test: no code path from ancestry to activation).
4. **Parent choice:** the eligible model with the lowest validation loss
   of the same architecture. **Root reasons** (traced in the request):
   `no-eligible-ancestor`, `ancestor-contradicted`, `architecture-change`,
   `lineage-stagnation` — the last after **N = 3** consecutive generations
   without improving the lineage's best validation loss.
5. Option `ancestry_training=False` by default; Wave 0 lineage metrics
   report roots, generations and root reasons.

### 8.2 Preregistered study P5 (before any run)

Physics3D copy of `org-ea3e7bbbc628` (tick 9 246), private SLM enabled,
factorized effects as in the Wave 0 baseline, run until body death or
6 000 ticks; arms **root-only** (current) and **ancestry**, same copy, same
seeds. Reported: models trained, generation distribution, root reasons,
fraction of candidates beating the baseline, best and median validation
loss of the last 10 candidates, promotions to ACTIVE, training compute.

Criteria, fixed now:

1. **Mechanics:** in the ancestry arm, every training after the first
   eligible model has `generation > 0` or a traced root reason.
2. **Improvement:** median validation loss of the last 10 candidates lower
   in the ancestry arm than in the root-only arm, and at least as many
   candidates beating the baseline.
3. **Safety:** no ACTIVE model without the unchanged promotion gate; no
   lineage longer than N non-improving generations.

Decision rule: 1 and 3 pass and 2 passes → propose `ancestry_training`
on by default (owner decision); 1 or 3 fails → fix before any adoption;
2 fails → report, not adopted. Limit: one organism, one run per arm
(Physics3D is deterministic apart from training nondeterminism, which is
recorded).

### 8.3 Wave 5 amendment — implementation stopped at the spec boundary (2026-09-28)

Mapping the code before implementing §8.1 found facts that invalidate
part of the plan; nothing of Wave 5 is implemented and P5 is not run until
the owner decides the items below.

1. **F10 has two causes, not one.** `physics3d/slm.py` `_train_job` always
   calls `PrivateModelFactory.build` (training from scratch) and never
   `adapt`; and `request_private_model_adaptation` has no caller in `src`.
   Even with an ACTIVE model the autonomous plan trains a new root. P5's
   "root-only" arm is therefore "never adapt"; wiring adaptation of an
   ACTIVE model is a separate behaviour decision.
   *Recommendation:* keep ACTIVE adaptation out of P5's scope; treat it as
   its own decision after P5.
2. **Tokenizer inheritance.** Adaptation requires the parent's tokenizer,
   but each plan rebuilds the vocabulary from the current corpus. Data (a
   copy of `org-ea3e7bbbc628/models`, 186 historical models): only **4 of
   185** consecutive vocabularies are subsets of their predecessor;
   vocabulary grows from 769 to 4 814 tokens, median 54 new tokens per
   training (max 431). Options:
   (a) the child reuses the parent vocabulary, new tokens become `<UNK>`
   (lossy, ~54 tokens per generation, confounds the arms);
   (b) a new root whenever the corpus has tokens outside the parent
   vocabulary (no parameter, but by the data it would almost never allow
   ancestry);
   (c) **append-only vocabulary extension**: the child's vocabulary is the
   parent's followed by the new tokens, and the parent's embedding/output
   rows are copied with new rows initialised as for a root (a lab-side
   trainer change; no free parameter).
   *Recommendation:* (c).
3. **Vocabulary storage.** `symbiont` cannot read lab files, so the
   organism must keep ancestor vocabularies itself. *Recommendation:* keep
   them only for SHADOW and ACTIVE records (bounded by the registry's
   non-retired models), dropped on retirement.
4. **Ancestor pool.** `_retire_stale_candidates(keep=3)` retires shadows by
   recency, so the best-validation ancestor can be retired before it is
   chosen. *Recommendation:* the current best eligible ancestor is exempt
   from recency retirement (still retired when superseded or contradicted).
5. **P5 validity.** Training runs in a `ProcessPoolExecutor` polled per
   tick; the tick at which a model is adopted depends on wall-clock time and
   CPU load, not only on seeds. *Recommendation:* amend P5 so the study
   waits for each training synchronously at the tick it was requested (a
   study-only switch; the resident behaviour is unchanged), and run the
   arms on an otherwise idle machine; record wall-clock and training
   nondeterminism.

P5's criteria are unchanged; this amendment is recorded before any Wave 5
code or run.

### 8.4 Wave 5 amended design and P5 preregistration (owner, 2026-09-28)

Supersedes §8.1 and §8.2 where they differ. Scope: **training ancestry of
non-authoritative models only**; only ACTIVE controls; P5 never adapts the
ACTIVE model; the promotion gate is unchanged.

**Design.**

1. `ModelRecord` records `validation_loss` and `baseline_loss` from the
   training result (older records: `None`, never ancestry-eligible).
2. **Ancestry eligibility** (unchanged from §8.1 item 2) plus the
   invariant *ancestry-eligible ⇒ tokenizer available*. The organism keeps
   the vocabulary of SHADOW and ACTIVE models only; retirement removes,
   together, eligibility, tokenizer and training-parent capability. No
   usable genealogical reference points at an artifact that can no longer
   be reproduced.
3. **Inherited, append-only vocabulary.** A child starts from the parent's
   tokenizer exactly; tokens of the current corpus absent from it are
   appended (deterministic order: descending corpus frequency, then
   lexical). Existing ids never change, nothing is reordered or removed.
   Embeddings of inherited tokens are copied; new rows are initialised
   deterministically from the training seed. Every vocabulary-shaped
   matrix (input embedding, output projection) is expanded coherently;
   tied weights stay tied. Vocabulary growth is a mechanical consequence,
   not a tunable P5 parameter.
4. **Retirement protection.** The best ancestry-eligible SHADOW is exempt
   from recency retirement while it remains the best under the
   eligibility criterion; it loses protection when contradicted, when a
   better eligible descendant appears, or when it stops being eligible.
   Each deferral is recorded (`retirement_deferred`, reason
   `protected_training_ancestor`).
5. **Root reasons** as §8.1 item 4 (`no-eligible-ancestor`,
   `ancestor-contradicted`, `architecture-change`, `lineage-stagnation`
   after N = 3 non-improving generations).
6. **Synchronous training for P5.** At a training boundary the corpus is
   frozen, the request issued, the simulation paused until training,
   validation and the registry transition complete, then resumed; the
   resident's asynchronous behaviour is unchanged outside the study
   switch. Each request is a provenance event carrying corpus hash,
   `parent_model_id`, parent tokenizer hash, training seed, architecture,
   training configuration and requested tick.

**P5 (preregistered).** Physics3D copy of `org-ea3e7bbbc628` (tick 9 246),
private SLM on, synchronous training, factorized effects as in the Wave 0
baseline, until body death or 6 000 ticks, arms:

- **P5-A — Independent Roots:** every training starts from fresh weights
  and a fresh tokenizer;
- **P5-B — Shadow Lineage:** eligible SHADOW ancestor, append-only
  inherited tokenizer, inherited compatible parameters and embeddings,
  new-token expansion.

The only causal difference is inherited training ancestry. Reported: models
trained, generations, root reasons, retirement deferrals, candidates
beating the baseline, best and median validation loss of the last 10
candidates, promotions, compute and wall-clock.

**Gates (all fixed now).**

1. *Mechanics:* in P5-B every training after the first eligible model has
   `generation > 0` or a traced root reason.
2. *Vocabulary continuity:* every parent token has the same id and the
   inherited embedding in the child; no child loses a parent token.
3. *Restore:* checkpoint → restore preserves the exact ancestry-capable
   tokenizers.
4. *Safety:* no ACTIVE model without the unchanged promotion gate; no
   lineage longer than N non-improving generations; training ancestry never
   grants action authority (structural).
5. *Improvement:* median validation loss of the last 10 candidates lower in
   P5-B than P5-A, and at least as many candidates beating the baseline.

Decision: 1-4 pass and 5 passes → propose `ancestry_training` (owner
decision on the default); any of 1-4 fails → fix before any adoption; 5
fails → reported, not adopted. Limit: one organism, one run per arm.

**Descriptive observations (owner, 2026-09-28, added while P5 runs; not
gates, criteria above unchanged).** The P5 report compares A and B on:
(1) predictive validation; (2) training generations and genealogy;
(3) promotion and retirement outcomes; (4) representational continuity —
parent tokens and ids preserved, inherited embeddings preserved; and
(5) **vocabulary expansion cost per generation** (child vocabulary size
against its parent's, along each lineage), computed afterwards from model
manifests. Unbounded growth along a lineage would be reported as a new
growth limit to study, not as a P5 failure. P5 is judged by training
transitions and outcomes, not wall-clock duration.

### 8.5 P5 result (2026-09-28) — ancestry never engaged; inconclusive

Runs on `95267c78`, copies of `org-ea3e7bbbc628` at tick 9 246, synchronous
training, factorized effects, both arms to body death at tick 11 891
(2 645 ticks; wall-clock A 64 min, B 71 min). Artifacts:
`.symbiont/archive/p5/` (measurements, provenance, final runtime state).

| | P5-A | P5-B |
|---|---:|---:|
| trainings (provenance `train_request`) | 41 | 41 |
| generation > 0 | 0 | 0 |
| root reasons | (not recorded, ancestry off) | `no-eligible-ancestor` × 41 |
| eligible ancestors at any time | 0 | 0 |
| retirement deferrals | 0 | 0 |
| candidates beating the baseline | 0 / 41 | 0 / 41 |
| last 10 candidates: best / median validation loss | 6.197 / 6.362 | 6.197 / 6.362 |
| validation − baseline loss: min / median | +0.501 / +0.922 | +0.501 / +0.922 |
| promotions to ACTIVE | 0 | 0 |

The two arms are identical: same model artifacts (content-addressed file
names match), same final registry, byte-identical provenance journals.
**No trained model ever beat the non-neural baseline**, so no model was
ancestry-eligible (§8.4 item 2) and P5-B never had a parent to inherit
from. The only causal difference between the arms was never exercised.

Gates: 1 *mechanics* — holds vacuously (no eligible model; every training
carries a traced root reason); 2 *vocabulary continuity* and 3 *restore* —
not exercised (no child, no ancestry-capable tokenizer); 4 *safety* —
passes (no ACTIVE model, no lineage); 5 *improvement* — fails (equal, not
lower). By the decision rule `ancestry_training` is **not adopted**; the
result is **inconclusive about ancestry itself**, not evidence against it.

Descriptive observations (§8.4): (1) predictive validation 0.50-0.92 nats
worse than the baseline for every candidate; (2) 41 generation-0 roots;
(3) 38 retired by recency, 3 SHADOW at death, none promoted;
(4) continuity not exercised; (5) root vocabularies are rebuilt each time
and *shrink* slightly over the run (4 822 → 4 489 tokens) as the corpus
window moves, so the growth concern does not arise for roots.

The binding constraint P5 exposes is upstream of ancestry: from-scratch
training at the authorized budget (48 steps, 8 epochs, ≤ 1 M parameters)
never reaches the baseline on this organism. Any further ancestry study
first needs eligible models to exist; what to change (training budget,
eligibility criterion, or seeding P5-B from a baseline-beating model) is an
owner decision and needs its own preregistration.

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
