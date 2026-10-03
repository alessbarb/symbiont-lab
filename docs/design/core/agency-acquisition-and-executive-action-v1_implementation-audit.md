# Agency Acquisition & Executive Action v1 — Implementation Audit

**Spec:** `docs/design/core/agency-acquisition-and-executive-action-v1.md`
**Design baseline:** `main@ba84be7f`
**Implementation branch:** `agency-acquisition-v1`
**Audit date:** 2026-09-27

This audit maps every section of the specification to the implementation, the
tests that protect it and the scientific evidence produced. Mechanical test
evidence and scientific evidence are reported separately.

## 0. Status (owner review, 2026-09-27)

```text
Agency Acquisition & Executive Action v1
ARCHITECTURE: CLOSED (frozen; merged into main at 748bb292)

E6 acquisition -> reuse closure:        PASS
E1 causal acquisition necessity:        PASS
E3 persistent intention advantage:      PASS

E4 causal revision, permuted outputs:   PASS (condition-specific)
E4 causal revision, broken actuator:    OPEN - protocol/horizon confound
E2 executive bridge:                    PARTIAL - higher yield / lower cost, no hit-rate advantage
E5 reconciliation advantage (§116):     NOT ESTABLISHED
```

The entities of this spec (`ActionAttempt`, `InterventionSignature`,
`ActionDimension`, `ActionAffordance`, `ActionIntent`) are not reopened. The
open items continue as two separate investigations, each with its own
preregistered protocol:

1. **Causal belief revision after perturbation (E4-v4).** Change the protocol,
   not the organism's epistemology: perturb only once a relation is causally
   consolidated (support, controllability and agency above preregistered
   thresholds and stable over a fixed window) while still experimentally
   observable, and report preregistered post-perturbation horizons
   (+128, +256, +512, +1024, +2048). Only if revision is still too slow under
   a genuinely stable relation is recency considered, and then as recent
   contradiction evidence kept distinct from historical support, not as
   global forgetting.

   *First run* (`20260927T081259Z-learning-agency-consolidated-causal-intervention-2f2ce6a-c3c9`,
   preregistered at `2f2ce6a5`, 10 seeds): **primary endpoint not supported,
   and the protocol is underpowered.** The consolidation gate opened in 1/10
   seeds for broken_effector (163) and 2/10 for permuted (163, 211); in the
   others no invalidatable relation held support >= 16, controllability >= 0.10
   and agency >= 0.10 for 128 consecutive ticks within 4096 ticks. Where it
   opened, the normal-minus-perturbed residual controllability gap was 0.0 at
   +128..+1024 (neither twin changed the gated estimate) and 0.036 / 0.042 /
   0.0 at +2048. A single testable seed is not evidence either way; a gate the
   organism can actually reach is a new protocol version, not a re-read of
   this run.

   *Protocol v2* (`20260927T105518Z-learning-agency-consolidated-causal-intervention-95f4628-8dc6`;
   preregistered at `67224c95`, run on `95f4628`, which also carries Executive
   Outcome Learning v1.1; 20 seeds; gate controllability/agency >= 0.05,
   minimum age 1024 ticks): **primary endpoint not supported, and the reason
   is now identified.** Testable seeds rose to 7 (broken_effector) and 10
   (permuted). The +1024 normal-minus-perturbed gap is positive in 2/7 and
   3/10 seeds (means 0.007 / 0.008) and exactly 0 in most others: once past
   early development the organism does not re-test many consolidated
   relations (re-tested fraction of invalidated relations <= 0.5 in most
   seeds, 0.0-0.14 in some), so neither twin revises them and the gap is 0 by
   construction. Where they are re-tested (seeds 149, 163, 389) differences
   appear but are noisy. The open question is no longer revision but
   re-exploration of consolidated relations (whether causal information gain,
   §24-§25, should rise for relations that have gone unverified for long) — a
   modelling decision for its own specification, not a protocol change.
2. **Executive Outcome Learning v1 (E2/E5).** Real intent outcomes become
   local, context-specific, failure-reason-aware executive evidence for
   (competence, anticipated effect, context) that modulates future
   *admission confidence*, never a scalar reward or a `ProspectivePolicy`
   penalty; `ActionIntent` remains lifecycle only. Terminal/binding failures
   suppress equivalent re-admission, mismatch/stagnation failures reduce it
   gradually, satisfactions raise it, INTERRUPTED/REJECTED are neutral,
   INVALIDATED suppresses until causal or binding evidence changes. E2 and E5
   are then rerun with unchanged criteria; E5 must remain able to fail.

### 0.1 Physics3D organism (read-only inspection, 2026-09-27)

The owner's Physics3D organism (`org-ea3e7bbbc628`, anthropomorphic-v6, 62
effectors, 107 receptors, checkpoint tick 5120) has formed **no intent at
all**: 5 competences, 0 execution bindings, so no affordance, no intent and no
Executive Outcome Learning lookup. Cause: every competence has
`effect_id = None` because whole-state effects do not recur in this body —
the EffectSpace is saturated at its 512-signature cap with 84% of signatures
seen once, and 1309 effectful attempts produced 832 distinct effects (most
frequent: 43). The synthetic 4-actuator body used by E1-E6 does not show this.
This is the v1 limitation of whole-state effect identity with identity
matching (§33 already names `EffectMatcher.similarity` as the extension point).
Making the executive loop engage in high-dimensional bodies needs a new
effect-representation specification (factorized per-feature effects and/or a
similarity matcher, and the EffectSpace bound), not a configuration change.

---

## 1. Evidence summary

### 1.1 Test evidence

| Check | Result |
| --- | --- |
| Full suite incl. slow (`-m "not slow or slow"`, excluding `tests/integration/studies` and the two 90 s W03 world tests) | 2672 passed, 69 failed, 4 collection errors |
| Baseline on `main@ba84be7f`, same selection | 2562 passed, 69 failed, 4 collection errors |
| New failures introduced | **0** (every failing node id is in the baseline list) |
| Spec-named tests (§92–§103) present | 70 / 70 |
| Fresh-organism integration closure (§104–§111) | 7 passed |
| `tests/integration/studies` + W03 world experiments (previously excluded) | 133 passed, 12 failed on both baseline and branch; identical failure sets |

The 69 failures and 4 collection errors pre-exist on `main` (docs links,
salient-trace/checkpoint-size runtime tests, cartography smoke tests, world
drift imports, etc.) and are unrelated to this spec.

### 1.2 Pure refactor verification

`refactor(action): split ActionDomain step into observe and act phases` was
verified byte-identical against `main` with a deterministic-clock trajectory
fingerprint (600 ticks, 4 actuators) before any semantic change.

### 1.3 Reproducibility

Study subjects run on apparatus time (`ApparatusClock`, body timestamps), and
every sampling path of a tick now shares the host time base. A fresh run gives
identical trajectories across processes, twins restored from one checkpoint
continue identically, and restore reproduces the causal estimate tables exactly.
`lab/tests/experiments/protocols/test_agency_acquisition_protocols.py` enforces the
first two (E6 through a closed loop, run twice; matched twins).

### 1.4 Overhead

| Setting | main | branch |
| --- | --- | --- |
| 4-actuator synthetic body, ms/tick at 1k / 5k ticks | 3.66 / 12.13 | 3.84 / 12.34 |
| Physics3D canonical body (62 effectors), ms/tick at 250 / 500 ticks | 112 / 343 | 114 / 352 |

The growth over lifetime is pre-existing on `main` (competence development and
cognition scans). All new tables are bounded: estimates (8192 each, pruned by
recency), signatures and dimensions (512), ledger (4096 interventions and 1024
passive windows), controller-signature memo (1024), intent outcome history (32).

### 1.5 Scientific evidence (registered runs, final code)

| Study | Run | Result |
| --- | --- | --- |
| E6 release gate | `20260927T052139Z-learning-agency-acquisition-reuse-closure-90e86c5-92f2` | **Passed on all seeds.** Satisfied self-acquired intent at ticks 236 / 402 / 612 (competence first acquired at 230 / 88 / 607); milestones in developmental order; reused competence grounded in the organism's own exploration evidence. |
| E1 acquisition ablation | `20260927T052144Z-learning-agency-acquisition-ablation-90e86c5-9a70` | Full: 28.7 dimensions (3.0 false positives on inert outputs), 6.3 agentic, 7.0 competences (2.0 executable). No counterfactual evidence: 0 dimensions, 0 competences. No AgencyModel: 27.7 dimensions (2.7 false positives), 0 agentic, 0 competences. |
| E3 intent persistence (protocol v2, 4096 ticks, 10 seeds) | `20260927T064314Z-learning-agency-intent-persistence-65fbbd9-dc83` | Testable seeds 101/149/163/179/193/227/241/257 (127 and 211 form no intent in either arm). Persistent vs re-decide realized commitments per seed: 23/5, 24/4, 10/4, 15/3, 9/6, 30/6, 13/7, 19/6 — persistent higher on **8/8** seeds. Realization 0.47 vs 0.15; satisfaction 0.39 vs 0.15; mean activated-intent duration 2.7 vs 1.0 ticks; energy per realized effect 277 vs 872; switches per realized effect 35 vs 114. **Clear.** (3-seed run `...062451Z-...758d323-5c95`: 0.60 vs 0.17.) |
| E2 executive bridge (protocol v2, 4096 ticks, 10 seeds) | `20260927T064314Z-learning-agency-executive-bridge-ablation-65fbbd9-ff56` | Same 8 testable seeds. Intent vs direct proposal realized per seed: 23/21, 24/14, 10/7, 15/6, 9/15, 30/30, 13/13, 19/11 — intent higher on 5, equal on 2, lower on 1. Mean realized 17.9 vs 14.6; energy per realized effect 277 vs 366; switches per realized effect 35 vs 46; prediction error 0.878 vs 0.864. The per-commitment realization *rate* does not favour intents (0.47 vs 0.49): intents commit more often and realize more effects at lower cost, not at a higher hit rate. 8.0 failed commitments per seed occur only in the intent arm (reconciliation declares failures; direct proposals never do). (3-seed run `...061929Z-...758d323-c220`.) |
| E5 intentional causal advantage (protocol v2, 4096 ticks, 10 seeds) | `20260927T073213Z-learning-agency-intentional-causal-advantage-ec947b6-4547` | Same 8 testable seeds. A direct / B unreconciled / C reconciled realized per seed: 21/13/23, 14/10/24, 7/12/10, 6/7/15, 15/12/9, 30/14/30, 13/25/13, 11/19/19. C > A on 5, = on 2, < on 1; **C > B on only 4, = on 1, < on 3.** Means: realized 14.6 / 14.0 / 17.9; realization rate 0.49 / 0.52 / 0.47; energy per realized effect 366 / 338 / 277; switches per realized effect 46 / 43 / 35; prediction error 0.864 / 0.861 / 0.878. B's satisfaction (0.83) is completion without verification by construction. The 3-seed result "C > B clear" (`...063025Z-...758d323-5043`) does **not** hold at ten seeds: C's mean advantage is yield and cost, not a per-seed or per-commitment one. |
| E4 embodied intervention (protocol v3, 4096 ticks) | `20260927T072146Z-learning-agency-embodied-causal-intervention-83d21bf-aa75` | Relations classified by apparatus ground truth; every invalidated relation was re-tested (retested fraction 1.0). **Permuted: condition-specific.** Invalidated controllability drop 0.221 vs 0.168 in the normal twin (per seed 0.225/0.176, 0.312/0.194, 0.127/0.134), residual controllability 0.004 vs 0.058; intact relations 0.071 vs 0.066. **Broken effector: not distinguishable at this horizon.** Invalidated drop 0.106 vs 0.102 (residual 0.005 vs 0.008); intact relations drop more in the perturbed twin (0.217 vs 0.170). Over 4096 ticks the normal twin also revises its early relations almost to zero (developmental drift after onset at acquisition + 64 ticks), leaving no headroom. Lost agentic dimensions 1.0 / 0.67 vs 1.0; new dimensions 4.7 / 6.0 vs 6.0; body-schema revisions 45 / 52 vs 44; affordance turnover 1.0 vs 0.94. v2 run (`...060626Z-...44061ac-12d4`) used a diluted relation set; see §4. |

Interpretation limits: one synthetic body family, fixed budgets; E1/E4/E6 on three seeds, E2/E3/E5 on ten (eight testable). Seed 127's original organism acquires one competence that falls back to "emerging" and never forms an intent; this is organism behaviour, not a restore defect (checked against the uninterrupted run).

---

## 2. Section-by-section map

| § | Requirement | Implementation | Protection |
| --- | --- | --- | --- |
| 1–6 | Three loops: acquisition, executive, intentional feedback | `actuation/acquisition.py`, `core/domains/action.py` (`observe_consequences` / `act`), `core/domains/intention.py` | integration closure tests |
| 7.1 | Cognition never emits MotorCommand | unchanged single authority | `test_cognition_cannot_issue_motor_command`, `test_single_motor_authority` |
| 7.2 | Intent = WHAT, controller = HOW | `agency/intention.py` (no actuator/controller fields or refs) | `test_action_intent_contains_no_actuator_ids`, `test_action_intent_cannot_call_controller_directly` |
| 7.3 | Exploration without competence | ActionDomain + reduced Symbiont exploration name no competence; `ActionProposal` rejects intents on exploration | `test_exploration_creates_attempt_without_competence`, `test_exploration_does_not_require_action_intent` |
| 7.4 | Causal evidence without competence | `CausalEvidence` subject = attempt/signature/commitment/competence | `symbiont/tests/unit/actuation/test_causal_evidence.py` |
| 7.5 | Dimension ≠ actuator | channel-set families, opaque ids | `test_dimension_identity_does_not_equal_actuator_identity`, `test_dimension_can_span_multiple_channels` |
| 7.6 | Intent does not govern all action | protection/exploration/regulation proposals need no intent | `test_protection_does_not_require_action_intent` |
| 7.7, 22–23 | Prediction match ≠ agency | `AgencyModel`: zero unless positive contingency and specificity; counterfactual support factor | `test_prediction_match_alone_does_not_create_agency` |
| 7.8 | No body semantics | none introduced | review + opaque-id tests |
| 7.9 | No global reward | vector evaluations and relevance only | review |
| 7.10, 72, 75 | Imagination never factual | GC exposes read-only `anticipated_effects()`; only Body transitions write ledger/EffectSpace | `test_imagination_never_reaches_factual_evidence` |
| 8 | New entities | `ActionAttempt`, `ActionIntent`, internal `InterventionSignature`, derived `ActionAffordance`; no ExecutiveChoice/ActionConsideration | review |
| 9–10 | ActionAttempt, 1 command → 1 attempt | `actuation/attempt.py`; opened at T11, closed at T1 | §92 tests |
| 11–12, 79 | InterventionSignature + registry, sequences | `actuation/intervention.py` (channel set + relative profile; intensity histogram; `signature_for_command/_sequence/_pattern_sequence`; temporal families of completed commitments) | §93 tests, `test_completed_commitment_becomes_a_temporal_intervention_family` |
| 13 | Transition attempt/signature ids | `SensorimotorTransition` requires both for motor-caused transitions | `test_motor_transition_requires_attempt_and_signature` |
| 14–16 | Generalized evidence, queries, passive windows | ledger schema 3: incremental counters; `signature_/signatures_/commitment_/attempt_effect_opportunities`; separately bounded passive windows | §95 tests |
| 17–20 | Learned dimensions, discovery policy | `actuation/dimension.py` (`ActionDimensionDiscoveryPolicy`, `assess_family`); no surface bootstrap | §94 tests |
| 21 | `CausalSourceKind`, generalized estimates | `actuation/model.py` | model tests |
| 24–25 | Causal information gain | `AgencyAcquisition.causal_information_gain` (untried, unresolved contrast, missing passive windows, missing intensity variants, untried nearby families); `ExplorationSignals.causal_information_gain` | `test_untried_neighbour_families_raise_causal_information_gain` |
| 26–27 | Body schema before competence | `BodySchemaEngine.observe_agentic_sensorimotor_evidence`; boundary inference from any causal source | §97 tests |
| 28–29, 122 | Competence convergence | `AgencyAcquisition.ground_competence`; ActionDomain and reduced Symbiont promote only through it; maturity re-derived each tick | §98 tests |
| 30–32 | EffectSpace hinge; derived reverse mapping | `AffordanceResolver.for_effect` over predictor/controllability/bindings | §99 tests |
| 33 | EffectMatcher | `actuation/effects.py`; all intent logic compares through it | review |
| 34–38 | Affordances (both directions, not persisted) | `agency/affordance.py`, `agency/affordances.py` | §99 tests |
| 39–46 | ActionIntent, IntentionDomain | `agency/intention.py`, `core/domains/intention.py` | §100 tests |
| 47–48 | Executive admission gate | `agency/prospective.py::admit_afforded_action` | §101 tests |
| 49–53 | ProspectiveDecision, `_choose_acquired_action` | `agency/prospective.py`; runtime and private runtime hooks (old deliberation result renamed `DeliberationOutcome`) | admission/intention tests |
| 54–61 | intent_id on proposal/commitment; activation/rejection | `actuation/action.py`, `actuation/commitment.py`, `ActionDomain._settle_intent_arbitration` | §100, §111 |
| 62–63, 86–87 | Traceability | `ActionDomain.action_trace()` / `observation_view()` | integration tests; Observatory panel |
| 64–71 | Reconciliation lifecycle | `IntentionDomain.observe_effect`, `ActionDomain._reconcile_intent` | §100, §110 |
| 76 | Tick ordering | runtime: perception → `observe_consequences` (T1–T3) → factual GC reconciliation → projection → cognition (T4) → `act` (T5–T11) | `test_runtime_reconciles_previous_action_before_new_cognition`, §103 |
| 77–78 | Multi-horizon evidence | commitment-level queries and evidence; temporal commitment families | evidence tests |
| 80–81 | Re-embodiment | pending attempt discarded, intent invalidated, affordances cleared; dimensions known but unbound (surface-fingerprint verification); Physics3D transplant carries them | `test_reembodiment_does_not_fake_current_binding`, `test_reembodiment_carries_learned_dimensions_as_unbound_knowledge` |
| 82–83 | Checkpoint v4, executive section, migration | sensorimotor schema 4 (`agency_acquisition`), top-level `executive_intention`; v3 and older restore with no dimensions | `test_dimension_survives_checkpoint`, `test_intention_checkpoint_keeps_only_live_intent`, legacy tests |
| 84 | Reduced Symbiont | shares `AgencyAcquisition` through its ActionDomain | experimental-integrity embodiment tests |
| 85–91 | Observatory, Atlas, metrics (verified in the real Observatory app with a live organism: the Mind agency panels populate through `applyMindSnapshot`, and the Atlas canvas draws the live `action_intent` node in the region of its competence and target effect) | snapshot §90 metrics; rich state → projection → Atlas (`action_intent` node, `affords` temporal overlay, agency metrics); Mind panels | atlas/projection tests |
| 104–111 | Integration | `lab/tests/integration/test_agency_acquisition_closure.py` | 7 tests |
| 112–118 | E1–E6, release gate | `symbiont_lab/studies/learning/agency_acquisition.py`, `experiments/learning/agency-*` | `lab/tests/experiments/protocols/test_agency_acquisition_protocols.py`; registered runs above |

---

## 3. Decisions recorded during implementation

1. **Signature identity** = opaque driven-channel set + two-bucket relative
   activation profile. A feasibility spike showed full quantization produced
   202 families in 1500 ticks (no accumulation) versus 15 recurring channel
   sets; absolute intensity is kept as a variant histogram (§25).
2. **Dimension discovery is context-free.** The spike saw 145 distinct
   context refs in 1500 ticks, too sparse to accumulate evidence; competence
   level estimates remain context-specific.
3. **Binding requires evidence on the current surface fingerprint.** Bodies
   with equal actuator counts share opaque channel ids; availability alone
   would have faked binding after re-embodiment.
4. **Passive windows** are ledger evidence without an action ref, bounded
   separately so idle ticks cannot evict intervention evidence.
5. **Model-free executive admission**: represented (readout or generative
   anticipation) + afforded + epistemic or homeostatic relevance ≥ threshold.
   Epistemic relevance is the stronger of generative expected uncertainty
   reduction and the competence's own predictive uncertainty.
6. **Open attempt is not checkpointed** (raw baselines are never persisted);
   a restored organism cold-starts its next attempt (§82.3).
7. **Control arms** (E2/E3/E5) are explicit `ExecutiveMode` /
   `IntentionPolicy` construction parameters; the organism default is FULL and
   rejects cognitive proposals without an intent.
8. `core/cognition/bridge.py` (listed in §129) needed no change: cognition
   receives the reconciled executive state through the action projection and
   Generative Cognition, and readouts no longer become proposals.

## 4. Defects found and fixed on the way

- `main` never made any competence executable in the base runtime (bindings
  were only created from competence-executed transitions) — the Gap A
  circularity, confirmed by the spike (15 competences, 0 executable).
- Competences kept stale maturity after their controller lost reproducibility,
  producing a controller-failure intent loop.
- Estimates for consequences that stopped occurring were never revised.
- The Physics3D transplant dropped learned dimensions (stamped schema 3).
- Restores rebuilt path-dependent estimates from final counts (213 vs 116
  estimates in one case); estimate tables and the body-schema sensorimotor view
  are now persisted (agency acquisition checkpoint schema 2).
- Wall-clock time leaked into perception and the self-model (proprioceptive
  and habitat reading timestamps, second-look sampling cost), so runs were
  not reproducible.
- Generative Cognition never retired prospective targets whose source had
  vanished (GC §38); after ~4.5k ticks the agenda filled and the organism
  crashed. Vanished sources are now retired and overflow is dropped/counted.
- The Observatory agency panels were hidden whenever no node was focused
  (found by rendering a real organism snapshot in a browser).
- The workbench Mind snapshot path (`applyMindSnapshot` / `state.js`) dropped
  `agencyAcquisition`, `affordances` and `executiveIntention`, so the panels
  stayed empty in the live app; panel rows overlapped on long ids.
- Study metrics measured intent duration/satisfaction over all intents instead
  of activated ones; E2–E5 now aggregate only seeds where the question is
  testable (both arms form cognitive events) and record the flag per seed.
- E4 v2 measured the dominant effect of every dimension touching a perturbed
  output, mixing relations the perturbation invalidates with ones it leaves
  intact, and read the pre-perturbation state from a freshly restored twin
  whose derived affordances are always empty (turnover 1.0 in every arm).
  Protocol v3 classifies relations by apparatus ground truth and reads the
  source organism. A diagnostic confirmed stored estimates equal estimates
  recomputed from the ledger (no refresh defect) and that perturbed families
  receive 197–999 of 1023 post-onset attempts, refuting the earlier claim that
  they were never re-tested.

## 5. Open scientific questions

- **E4 broken effector.** At the 1024-tick diagnostic horizon the broken twin
  drove invalidated relations to a zero post-onset hit rate and residual
  controllability ~0.02 while the normal twin kept 0.04–0.25; at the
  registered 4096-tick horizon the normal twin's developmental drift erases
  the contrast. The horizon was not changed after seeing results. Whether E4
  should perturb a consolidated organism (longer settle) or weight recent
  evidence is a protocol/modelling decision for the owner; note that with a
  long settle the exploration controller drives some outputs tonically, so a
  change-based effect space sees few consequences of them in either twin.
- **E2/E5 (§116 not established).** Across eight testable seeds reconciled
  intents realize more effects on average at lower energy and switching cost,
  but not at a higher per-commitment hit rate, and against unreconciled
  intents (B) the per-seed direction is mixed (4 better, 1 equal, 3 worse).
  Reconciliation currently declares failures (8 per seed) that make C commit
  more often rather than more accurately. Whether reconciliation should shape
  the next choice more strongly (e.g. how failed intents re-enter admission)
  is a design question beyond this implementation.
