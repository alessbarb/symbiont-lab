# Cross-Domain Revision Coherence v1

Status: **proposed** — owner approval required per wave before implementation.
Baseline: `main @ c1a43963`. Origin: owner audit of `org-5c3fb582fb17`
(2026-09-27), code claims re-verified against `main` (§1.2).

## 1. Problem

### 1.1 Diagnosis

Symbiont's subsystems are individually sound, but a revision learned by one
authority does not reach the others. Competence knowledge, execution
bindings, executive outcomes, generative cognition and embodiment adaptation
each hold a legitimate part of the truth about a competence, and each
decides "executable" or "still worth considering" by its own rule. The result
is an organism that has much knowledge but converts little of it into
stable, revisable, reusable agency: many primitives stuck at two or three
occurrences, one usable competence, hundreds of generative activations of a
target the executive already rejects, a private-model loop that retrains
from scratch, and an effect memory that silently forgets what is new.

The fix is **not** to merge these authorities. It is to add derived
projections and explicit revision semantics that connect them, and to make
bounded forgetting observable.

### 1.2 Verified findings (code at `c1a43963`)

| Id | Sev | Finding | Evidence |
|---|---|---|---|
| F1 | P0 | A suppressed competence keeps a valid binding; the registry cannot invalidate | `actuation/binding.py`: `bind_from_evidence/get/is_executable/invalid_for_surface/checkpoint/restore` only |
| F2 | P0 | Three definitions of "executable" | `ActionDomain.competence_is_executable` (binding+maturity+controller), `physics3d/runtime.py:938,1733,1818,1920` and `individual.py:199` (binding only), executive suppression (admission only) |
| F3 | P1 | Predictions served for competences the executive suppressed | `ActionDomain.predict_competence_effect` falls back to the binding without executability or suppression (`action.py:333-347`); registered as the generative `competence-effect` model (`runtime.py:820-829`) |
| F4 | P0 | `reacclimation_completed` means "window elapsed", not "adapted" | `physics3d/runtime.py:1838-1843` |
| F5 | P0 | Exported directories can pair stale `metadata.json` with a newer bundle | bundle atomic (`persistence.py` `os.replace`), metadata a separate file refreshed only in `Physics3DRunStore.finalize()` |
| F6 | P1 | Primitive→competence needs independent natural recurrence; no endogenous retest | `sensorimotor.py:368` ("no scheduled replay forces this"), `_record_primitive_episode` `stat.count < 2` |
| F7 | P1 | `EffectSpace` evicts at 512 by support: incumbency lock-in, unobservable | `effects.py:215-224` |
| F8 | P1 | Two passive-evidence mechanisms can diverge (motor baseline vs causal ledger) | `sensorimotor.py` passive stats; `evidence.py` `observe_passive_window`; `action.py` passive transition |
| F9 | P1 | Generative use tracker rewards recurrence without new evidence | `cognition/generative/consolidation.py` (`recurrent_activation`, `cross_episode_reuse`, `hypothesis_persistence`) |
| F10 | P2 | No ACTIVE private model ⇒ every training is a root; shadows never inform the next | `modeling/runtime.py:926` (`bootstrap-experience`), adaptation requires an ACTIVE parent |
| F11 | P2 | `established_competence_count` counts *executable* competences | `action.py:2077` |
| F12 | P1 | Hard bounds truncate without recording pressure or evictions | EffectSpace, primitive stats, bindings, executive keys (256), generative reps |

Additional findings from this session, relevant to the waves:

- **F13** (E8 v3 pilot, not evidence): footprint membership admits atoms on
  drifting receptors (13/22 members at 600 ticks, seed 101). Anything built
  on footprints (Wave 2 retest) inherits that noise. The preregistered E8 v3
  safety criterion measures its consequence on satisfaction.
- **F14** (Physics3D acceptance): a copy of `org-ea3e7bbbc628` starves at
  2 650 ticks with zero absorbed material, the audit's homeostasis→contact
  gap observed directly. The flag-off control decides whether this is
  independent of factorized effects.

Confirmed as correct and **kept**: competence knowledge ≠ binding;
generative hypothesis ≠ factual evidence; body time ≠ Symbiont time;
physical energy ≠ metabolic accounting (negative accounting balances are
debt, physical energy stays ≥ 0); rest never mints energy; energy comes only
from physical contact with a world resource; prediction ≠ action authority;
the SLM promotion gate.

## 2. Principles

1. **Projections, not new authorities.** New structures derive from existing
   authorities every tick, are never an independent source of fact, and are
   not persisted (recomputed after restore).
2. **Revision is explicit and traced.** Every lifecycle change (invalidate,
   stale, lift, promote, evict) is a Causal Provenance v1 event with its
   causes.
3. **Forgetting is a phenomenon.** Every bounded store reports pressure and
   evictions; nothing truncates silently.
4. **No hidden policy.** No scheduled replay, no "go to resource", no
   semantic goals. New behaviour must arise from the organism's own
   epistemic or homeostatic state.
5. **Separation of fact and imagination is preserved.** Generative activity
   never counts as evidence; it may be *cooled* by lack of evidence.
6. **Preregistration.** Behaviour-changing waves ship behind options off by
   default, with preregistered studies and gates; defaults change only by
   owner decision after results.
7. **Checkpoint → restore → continue** yields the same causal history in
   every touched domain.

## 3. Wave 1 — Competence availability and revision consistency (P0)

### 3.1 `CompetenceAvailability` projection

Owned by `ActionDomain`, recomputed on demand per tick (memoized per tick),
never checkpointed. Per competence:

| Group | Fields |
|---|---|
| knowledge | `maturity`, `support`, `reproducibility` |
| binding | `binding_status` (§3.2), `surface_match`, `historical_reliability`, `binding_revision` |
| causal | `controllability`, `agency`, `last_evidence_tick` |
| controller | `controller_available` (every leaf `can_activate`) |
| executive | `suppressed`, `suppression_reason`, `suppression_key` |
| verdict | `executable_now`, `admissible_now`, `reason` |

- `executable_now = binding_status == VALID ∧ surface_match ∧ maturity ∈
  {ESTABLISHED, ROBUST} ∧ controller_available` (today's
  `competence_is_executable`, now the single definition).
- `admissible_now = executable_now ∧ ¬suppressed`.
- `reason` is the first failing condition, from a closed set
  (`not_mature`, `unbound`, `surface_mismatch`, `binding_stale`,
  `binding_invalidated`, `controller_unavailable`, `executively_suppressed`,
  `ok`).

### 3.2 Binding lifecycle

`CompetenceExecutionBinding` gains `status ∈ {VALID, STALE, INVALIDATED}`,
`valid_from_tick`, `last_confirmed_tick`, `invalidated_tick`,
`invalidation_reason`, `revision`. `reliability` becomes explicitly
*historical* and is never read as current executability.

- **STALE**: surface fingerprint no longer current (replaces the implicit
  `invalid_for_surface` check); reversible when the surface returns.
- **INVALIDATED**: the executive records `required_causal_binding_invalidated`
  or `surface_incompatible` for this competence's key.
- **VALID again**: `bind_from_evidence` with new evidence ⇒ `revision + 1`.
- Nothing is deleted. Checkpoint schema bump; migration: existing bindings
  become `VALID` with `revision = 0` (tests/compatibility).

### 3.3 Read-only executive suppression

`ExecutiveOutcomeLedger.suppression(key, revision) -> SuppressionEvidence |
None` answers without side effects (today only `modulation()` exists, which
lifts suppression and counts lookups). Lifting stays where it is (admission).

### 3.4 Consumers switched to the projection

| Consumer | Today | Wave 1 |
|---|---|---|
| `predict_competence_effect` fallback (generative `competence-effect` model) | binding exists | `admissible_now`; otherwise no prediction |
| `AffordanceResolver` | `bindings.is_executable` | `executable_now` |
| Physics3D adaptation `revalidated_count` (`runtime.py:938`) | binding | `executable_now` |
| Physics3D unbound/telemetry (`1733`, `1818`, `1920`), `individual.py:199` | binding | projection |
| intent reconciliation `competence_executable` | `competence_is_executable` | `executable_now` (unchanged meaning) |

A structural test forbids direct `is_executable` calls outside the
projection.

### 3.5 Metrics renamed

`established_competence_count` → `executable_competence_count`; add
`candidate/emerging/established/robust` knowledge counts and
`bound/executable/admissible/suppressed` availability counts.
Old telemetry is read through a named migrator; writers emit the new names.

### 3.6 Reacclimation semantics

`reacclimation_completed` → `reacclimation_window_completed` (pure timer),
plus `adaptation_state ∈ {reacquiring, unstable, stabilizing, adapted}` and
`adaptation_recovered_at_tick`, derived from `EmbodimentAdaptation`
(`reacquiring` while the window runs; `unstable` when the window ended with
`stable_ticks == 0`; `stabilizing` with `stable_ticks > 0` and no recovery;
`adapted` once `recovery_tick` is set). A timer never declares adaptation.
Epoch metrics and telemetry only; the Observatory display is a separate
contract.

### 3.7 Export manifest

Exports derive a manifest from the runtime payload inside the bundle
(`checkpoint_id`, `saved_at_tick`, `runtime_sha256`, `embodiment_id`,
`body_id`, `embodiment_epoch`, `generated_from_runtime: true`) and verify
`manifest == runtime`. `metadata.json` stays a Workbench convenience, never
exported as scientific authority.

### 3.8 Tests and gate

Tests: suppression propagates end to end (prediction, affordance,
adaptation all see it); a causal revision legitimately lifts it; generative
cognition stops receiving predictions for a non-admissible target; adaptation
uses canonical availability; reacclimation window never claims adaptation;
export manifest and runtime are the same checkpoint; binding lifecycle
survives checkpoint→restore; v-previous bindings migrate.

**Gate W1:** no competence is ever `suppressed ∧ admissible_now` absent a
later traced causal revision (property test over E6/E8 runs); E6 passes in
both effect modes; the trajectory change caused by F3 is documented (hash
changes are expected here and recorded, not hidden).

## 4. Wave 2 — Endogenous epistemic retest (P1)

### 4.1 Mechanism

A primitive with few occurrences carries posterior uncertainty about its
controllability. That uncertainty becomes an **epistemic demand** — the
expected information gain of re-executing it — exposed as the
`epistemic_relevance` of an ordinary affordance. It competes with
homeostatic and prospective relevance in the existing executive admission;
nothing schedules it.

```
primitive evidence -> posterior uncertainty -> epistemic demand
  -> affordance (epistemic_relevance) -> executive admission
  -> re-execution -> factual evidence (support or weakening)
```

- Gain uses the same statistics the primitive already has (count, variance,
  directional consistency); it decays as occurrences accumulate.
- A retest is an independent occurrence only if it is a new commitment
  separated from the previous one by at least one passive window (reuses the
  passive baseline machinery, §5.4), so self-chosen retests cannot fake
  recurrence by repetition inside one bout.
- A failed retest **weakens** (lower mean effect / consistency); a primitive
  whose demand is spent without support is cooled, not deleted.
- Option `CompetenceDevelopmentEngine(epistemic_retest=False)` by default.

### 4.2 Dependency

Wave 2 starts only after E8 v3 reports footprint-related spurious rates
(F13). If spurious satisfaction is high, a footprint-precision spec comes
first: retest built on drift-contaminated evidence would reinforce noise.

### 4.3 Study and gate

Preregistered **E9** (synthetic body with ground truth, longitudinal):
arms retest off/on. Metrics: fraction of primitives leaving N ≤ 3; retests
per primitive; promotions that match ground truth vs. spurious promotions;
competences per 1 000 attempts.
**Gate W2:** promising primitives get independently retested and either gain
support or weaken; spurious promotions do not increase beyond a threshold
fixed in the preregistration; E6 still passes.

## 5. Wave 3 — Bounded open-world memory (P1)

### 5.1 Two-stage `EffectSpace`

- **Candidate pool** (default 128): new effects enter here; eviction by a
  score of recurrence, recency and causal usefulness (never support alone).
- **Consolidated pool** (default 512): promotion at `support ≥ 2` recurrence;
  eviction by support, causal relevance (bound competences, live intents,
  footprints), reuse and recency. Effects referenced by a binding, a live
  intent or a pin are never evicted.
- A novel recurrent effect therefore always has a path: it competes only
  with other candidates until it recurs.
- Checkpoint schema bump; migration: every existing effect is consolidated.

### 5.2 Capacity pressure as a phenomenon (F12, cross-cutting)

A shared `CapacityPressure` record (`capacity`, `occupancy`, `evictions`,
`promotions`, `demotions`, `relearned_after_eviction`) for EffectSpace,
primitive stats, bindings, executive keys and generative representations;
evictions and promotions are provenance events (`effect_created`,
`effect_promoted`, `effect_evicted`, `effect_reobserved`), so every
forgotten item has a traced cause.

### 5.3 Gate

Tests: with the consolidated pool full, a novel reproducible effect is
promoted; every eviction is auditable through provenance.
**Gate W3:** E8 rerun shows no loss of consolidated effects bound to
competences and a non-zero promotion rate for novel effects at saturation.

### 5.4 Passive evidence reconciliation (F8)

The motor learner's passive baseline and the causal ledger's passive windows
become one source: the causal ledger's passive windows (canonical), with the
motor baseline derived from them. Test: a motor-detected passive opportunity
is always visible to the ledger (different window lengths allowed, zero vs.
many forbidden). Part of Wave 3 because both stores are bounded evidence.

## 6. Wave 4 — Generative epistemic hygiene (P1)

### 6.1 Viability

Hypotheses gain `viability ∈ {TESTABLE_NOW, BLOCKED_BY_EMBODIMENT,
BLOCKED_BY_BINDING, SUPERSEDED_CAUSALLY, AWAITING_NEW_EVIDENCE}`, derived from
the Wave 1 projection and causal revision events. Blocked hypotheses keep
their epistemic status (not falsified) but receive no activation budget.

### 6.2 Sterile reactivation

`GenerativeUseTracker` adds `new_evidence_since_last_use`,
`new_branch_since_last_use`, `uncertainty_reduction`,
`sterile_reactivation_count`. Consolidation signal and priority decay with
sterile reactivations (cooling, never deletion); recurrence alone no longer
raises consolidation.

### 6.3 Gate

Tests: generative cognition stops spending budget on a non-testable target;
a representation cannot accumulate unbounded identical activations without a
new branch, new evidence, uncertainty reduction or context change.
**Gate W4:** on a replay of the audited pattern, sterile activations are
bounded and generative→factual reconciliation rate rises; generative output
still never enters factual evidence (existing boundary tests).

## 7. Wave 5 — Private-model genealogy (P2)

- Separate **training ancestry** from **control authority**: a SHADOW model
  that passed internal validation may be the parent of the next training
  (`parent_model_id`, `generation + 1`); only ACTIVE models control.
- A new root is allowed only with a traced reason (`no-eligible-ancestor`,
  `ancestor-contradicted`, `architecture-change`).
- The promotion gate to ACTIVE is unchanged.
- **Gate W5:** after repeated failed promotions, the next training has
  `generation > 0` or a traced root reason; no indistinguishable root chains.

## 8. Out of scope

- Homeostasis → foraging learning (F14): kept as an open scientific question;
  no semantic goals are added. Its study is proposed separately once Wave 1
  lands (affordance credit from homeostatic relief after real contact).
- Observatory display of metabolic debt vs. physical energy and of body-schema
  maturity vs. boundary confidence: passive views, separate live-protocol
  contract.
- Body, torques, gravity, competence thresholds, SLM promotion threshold,
  bound sizes: unchanged.

## 9. Order, dependencies and decisions

| Wave | Depends on | Changes behaviour | Owner decision needed |
|---|---|---|---|
| 1 | — | yes (F3 predictions) | approve spec; accept documented trajectory change |
| 2 | 1, E8 v3 (F13) | behind option | approve + E9 preregistration |
| 3 | 1 | yes (eviction policy) behind option | pool sizes; E8 rerun preregistration |
| 4 | 1 | behind option | approve cooling rule |
| 5 | — | behind option | approve ancestry rule |

Wave 1 is the only one that changes default behaviour without an option,
because it removes a contradiction rather than adding a capability.

## 10. Test inventory

| # | Test | Wave |
|---|---|---|
| 1 | competence suppression propagates end to end | 1 |
| 2 | causal revision can legitimately lift suppression | 1 |
| 3 | generative cognition stops spending on unexecutable target | 1/4 |
| 4 | embodiment adaptation uses canonical availability | 1 |
| 5 | reacclimation window does not claim adaptation | 1 |
| 6 | full effect space still admits a novel recurrent effect | 3 |
| 7 | effect eviction is causally auditable | 3 |
| 8 | promising primitive receives endogenous retest | 2 |
| 9 | unsuccessful retest weakens the primitive | 2 |
| 10 | successful retest promotes evidence | 2 |
| 11 | passive motor baseline and causal counterfactual stay consistent | 3 |
| 12 | failed shadow training informs next training generation | 5 |
| 13 | export manifest and runtime are the same checkpoint | 1 |
| 14 | resource contact changes physical energy exactly once | kept (regression) |
| 15 | rest never mints physical energy | kept (regression) |
| 16 | checkpoint → restore → continue gives the same causal history in every touched domain | all |
