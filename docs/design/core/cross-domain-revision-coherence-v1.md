# Cross-Domain Revision Coherence v1

Status: **proposed, revision 2** — conceptually approved by the owner
(review 2026-09-28); implementation of each wave still needs its own
approval. Baseline: `main @ c1a43963`. Origin: owner audit of
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
| F13 | — | (E8 v3 pilot, not evidence) footprints admit atoms on drifting receptors (13/22 members, seed 101, 600 ticks) | measured against the E8 body's ground truth |
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

**Gate W0:** trajectory hashes unchanged; every metric above present,
checkpoint-stable and documented.

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
| epistemic | `testable_now` |
| verdict | `reason` (first failing condition, closed set) |

- `predictable_now = known ∧ effect representation available ∧
  binding_status ∈ {VALID, STALE}` — the causal relation is still believed,
  whether or not it can be acted on now.
- `executable_now = binding_status == VALID ∧ surface_match ∧ maturity ∈
  {ESTABLISHED, ROBUST} ∧ controller_available` (today's
  `competence_is_executable`, now the single definition).
- `admissible_now = executable_now ∧ ¬suppressed`.
- `testable_now = predictable_now ∧ executable_now` — a prediction about it
  could be checked by acting now (independent of executive suppression,
  which is policy, not opportunity).

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
| `predict_competence_effect` (generative `competence-effect` model) | `predictable_now`; the prediction carries `executable_now`/`admissible_now`/`testable_now` as annotations |
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
non-VALID binding; E6 passes in both effect modes; trajectory changes are
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
variance `v`, directional consistency `d`, and the passive baseline mean
`m0` and variance `v0` of the same effect channel:

- relative uncertainty reduction of one more independent occurrence:
  `g(n) = 1 − sqrt(n / (n + 1))` (0.184 at n=2, 0.106 at n=4);
- standard error with a floor from the organism's own passive noise:
  `se = sqrt(max(v, v0, 1e-3) / n)`;
- causal plausibility: `p = Φ((m − m0) / se) × d`;
- `epistemic_relevance = (g(n) / g(1)) × p`, zero when `n > 8` or
  `epistemic_relevance < 0.05`.

`g(1) = 1 − sqrt(1/2)` normalizes to [0, 1]. The constants (1e-3, 8, 0.05)
are preregistered parameters of E9, not tuned after results.

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
- Provenance events: `effect_created`, `effect_promoted`, `effect_evicted`,
  `effect_reobserved`.
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
  `BLOCKED_BY_BINDING`, `AWAITING_NEW_EVIDENCE` (whether it can be checked),
  derived from the Wave 1 projection (`testable_now` and its reason).

Untestable hypotheses keep their epistemic status and receive no activation
budget; supersession comes only from causal revision events.

### 7.2 Sterile reactivation

Wave 0's `sterile_reactivation_count` now acts: consolidation signal and
priority decay with sterile reactivations (cooling, never deletion);
recurrence alone no longer raises consolidation. Tracker adds
`new_evidence_since_last_use`, `new_branch_since_last_use`,
`uncertainty_reduction`.

**Gate W4:** budget stops flowing to untestable targets; sterile activations
bounded; generative→factual reconciliation rate rises; generative output
never enters factual evidence (existing boundary tests).

## 8. Wave 5 — Private-model genealogy (P2, parallel after Wave 0)

- **Training ancestry ≠ control authority.** Only ACTIVE models control; a
  SHADOW model may be a training parent only if **ancestry-eligible**:
  `validation_gain > 0`, no catastrophic regression on the held-out
  validation, and not contradicted by later evidence.
- Children record `parent_model_id`, `generation + 1`.
- A new root requires a traced reason: `no-eligible-ancestor`,
  `ancestor-contradicted`, `architecture-change`, or `lineage-stagnation`
  (N generations without validation gain; N preregistered).
- Promotion gate to ACTIVE unchanged.

**Gate W5:** after repeated failed promotions the next training has
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
