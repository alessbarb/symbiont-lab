# Agency Acquisition & Executive Action v1 — Implementation Audit

**Spec:** `docs/design/core/agency-acquisition-and-executive-action-v1.md`
**Design baseline:** `main@ba84be7f`
**Implementation branch:** `agency-acquisition-v1`
**Audit date:** 2026-09-27

This audit maps every section of the specification to the implementation, the
tests that protect it and the scientific evidence produced. Mechanical test
evidence and scientific evidence are reported separately.

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
`tests/experiments/protocols/test_agency_acquisition_protocols.py` enforces the
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

### 1.5 Scientific evidence (registered runs, seeds 101/127/149, final code)

| Study | Run | Result |
| --- | --- | --- |
| E6 release gate | `20260927T052139Z-learning-agency-acquisition-reuse-closure-90e86c5-92f2` | **Passed on all seeds.** Satisfied self-acquired intent at ticks 236 / 402 / 612 (competence first acquired at 230 / 88 / 607); milestones in developmental order; reused competence grounded in the organism's own exploration evidence. |
| E1 acquisition ablation | `20260927T052144Z-learning-agency-acquisition-ablation-90e86c5-9a70` | Full: 28.7 dimensions (3.0 false positives on inert outputs), 6.3 agentic, 7.0 competences (2.0 executable). No counterfactual evidence: 0 dimensions, 0 competences. No AgencyModel: 27.7 dimensions (2.7 false positives), 0 agentic, 0 competences. |
| E3 intent persistence | `20260927T053734Z-learning-agency-intent-persistence-6258b8a-8d71` | Persistent vs re-decide: realized/competence commitments per seed 2/8, 0/0, 6/6 vs 0/5, 0/0, 2/6; realization 0.63 vs 0.17; satisfaction of activated intents 0.54 vs 0.17; mean activated-intent duration 2.7 vs 1.0 ticks; energy per realized effect 356 vs 569. |
| E2 executive bridge | `20260927T053658Z-learning-agency-executive-bridge-ablation-6258b8a-9cc9` | Intent vs direct: realized/competence commitments per seed 2/8, 0/0, 6/6 vs 5/9, 0/0, 2/3; realization 0.63 vs 0.61; energy per realized effect 356 vs 391; 17.7 intents per seed rejected before authority (§41). Small differences on few events. |
| E5 intentional causal advantage | `20260927T053811Z-learning-agency-intentional-causal-advantage-6258b8a-5be2` | A / B / C realized/competence commitments per seed: A 5/9, 0/0, 2/3; B 2/6, 0/0, 2/3; C 2/8, 0/0, 6/6. Realization 0.61 / 0.50 / 0.63; energy per realized effect 391 / 547 / 356. B's satisfaction (0.75) is completion without verification by construction and not comparable to C's verified 0.54. C beats B; C vs A is not yet distinguishable. |
| E4 embodied intervention | `20260927T052522Z-learning-agency-embodied-causal-intervention-b25409e-708a` | On ground-truth perturbed relations, perturbed twin vs matched normal twin: permuted agency drop 0.074 vs 0.051, controllability 0.040 vs 0.039; broken effector agency 0.075 vs 0.067, controllability 0.048 vs 0.043. Revision is condition-specific but small within 1024 ticks. |

Interpretation limits: three seeds, one synthetic body family, fixed budgets, and very few cognitive commitments per 1024-tick horizon (seed 127 has none in E2/E3/E5, so it is not testable there). Rates rest on single-digit event counts.

---

## 2. Section-by-section map

| § | Requirement | Implementation | Protection |
| --- | --- | --- | --- |
| 1–6 | Three loops: acquisition, executive, intentional feedback | `actuation/acquisition.py`, `core/domains/action.py` (`observe_consequences` / `act`), `core/domains/intention.py` | integration closure tests |
| 7.1 | Cognition never emits MotorCommand | unchanged single authority | `test_cognition_cannot_issue_motor_command`, `test_single_motor_authority` |
| 7.2 | Intent = WHAT, controller = HOW | `agency/intention.py` (no actuator/controller fields or refs) | `test_action_intent_contains_no_actuator_ids`, `test_action_intent_cannot_call_controller_directly` |
| 7.3 | Exploration without competence | ActionDomain + reduced Symbiont exploration name no competence; `ActionProposal` rejects intents on exploration | `test_exploration_creates_attempt_without_competence`, `test_exploration_does_not_require_action_intent` |
| 7.4 | Causal evidence without competence | `CausalEvidence` subject = attempt/signature/commitment/competence | `tests/unit/actuation/test_causal_evidence.py` |
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
| 85–91 | Observatory, Atlas, metrics (panels verified in a browser with a real organism snapshot; the Atlas canvas rendering of `action_intent` / `affords` is verified only at payload and syntax level) | snapshot §90 metrics; rich state → projection → Atlas (`action_intent` node, `affords` temporal overlay, agency metrics); Mind panels | atlas/projection tests |
| 104–111 | Integration | `tests/integration/test_agency_acquisition_closure.py` | 7 tests |
| 112–118 | E1–E6, release gate | `symbiont_lab/studies/learning/agency_acquisition.py`, `experiments/learning/agency-*` | `tests/experiments/protocols/test_agency_acquisition_protocols.py`; registered runs above |

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

## 5. Open scientific questions

- **E4:** revision of perturbed relations exceeds the matched normal twin, but
  only slightly within 1024 ticks, mostly in agency. The ledger weighs all
  retained evidence equally; whether recency weighting or change detection is
  needed is a new modelling decision beyond this spec and has not been tested.
- **E2/E5:** reconciled intents beat unreconciled ones and edge out direct
  proposals on efficiency, but the direct-proposal comparison is small at
  n = 3. More seeds, longer horizons and richer bodies are needed before
  claiming §116's causal advantage.
