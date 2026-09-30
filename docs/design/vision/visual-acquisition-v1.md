# Visual Acquisition v1 (EW-D): preregistration

Status: **D1-v1 `not_assessable` (§6.4–§6.5). D1-v2 closed `not_assessable` (§12): structural negative. Held-out seeds disabled and not authorized.**

D2–D4 are outlines only (§10) and are **not preregistered**.

Context: Experience & World Architecture v1, and the pending-implementation specification of 2026-09-28 (§4–§9, EW-D0 → EW-D4). Prerequisites met on `main`:

- **EW-C (ADR-0011):** causal visual apparatus.
- **EW-T (ADR-0042):** deterministic causal time and cost.
- **Gates H and I:** hold at engine level, also for the vision body in the moving-source nursery (`tests/integration/test_physics3d_reproduction_gates.py`).

Implementation: `src/symbiont_lab/studies/learning/visual_acquisition.py`, protocol `learning.visual-acquisition-v1`, experiments under `experiments/learning/visual-acquisition-v1/`.

## 1. Question (D1: temporal predictive structure)

> Can Symbiont learn visual regularities that improve prediction of future opaque visual signals?

It is not asked whether it sees objects. Producing more concepts, edges, predictors or sensors is not evidence; held-out predictive utility beyond the baselines is.

## 2. Hypotheses

- **H1 (utility).** After the experience, predictors of visual senses beat persistence, the causal running mean and zero on held-out late windows.
- **H2 (novelty).** Those predictors did not exist at State X.
- **H3 (acquisition).** The gain requires cognitive acquisition. Arm B has the same visual sensors, no plasticity and no predictor promotion, and does not reproduce it.

## 3. Apparatus and nursery

- **Apparatus.** `anthropomorphic-v6-vision`: a 12×12 luminance array on the head link, with opaque ids and a fixed versioned permutation. No depth, entity identity or colour names (ADR-0011).
- **Nursery.** `vision-nursery-d1-v1`:
  - a uniform background, luminance 0.45;
  - one coherent source, luminance 0.95, 0.35 m square, sweeping sinusoidally along the lateral axis (amplitude 0.8 m).
- **Seeded motion.** The phase fraction and the period (72–120 ticks) come from `derive_world_rng(seed, "vision.d1.source-motion.v1")`. That is a world-side RNG namespace, never the organism's. The position is then a pure function of `(causal tick, derived parameters)`, so it is exact on resume, with no runtime random state.
- **Source properties.** The source is kinematic, has no collision shape, and reaches the organism only through the apparatus.
- **What Symbiont receives.** Only `rec.N → luminance`. The ids `background` and `source`, their purpose and the motion parameters are observer-only.

## 4. State X

For each seed, a new Symbiont is born into the vision body in the D1 nursery and runs 4 ticks. The result, organism and body, is X. Every arm of that seed resumes from the same X. The number of predictors targeting visual senses at X is recorded.

## 5. Arms and measurement

**Arms.**
- **A — acquisition.** Default behaviour.
- **B — sensors without acquisition.** A Lab-owned `CognitiveAcquisitionAblation` (`symbiont_lab/studies/ablations/cognitive.py`) with `plasticity_enabled = false` and `predictor_promotion = false`.
  - It is applied after restoring X and before the arm's first tick, through neutral runtime switches of existing capabilities (`set_cognitive_plasticity_enabled`, `set_predictor_promotion_enabled`).
  - It is never checkpointed and never part of `effective_config`.
  - Sensor admission and the apparatus are unchanged (`tests/unit/lab/test_cognitive_acquisition_ablation.py`).
- **C — no visual apparatus.** Not assessable in D1. Its place is transfer: an equivalent lineage without Vision against the one that went through Vision, in the same World.

**Measurement.** Evaluator-side, observation on every tick; Gate I shows observation density does not change causal state.
- **Visual target.** A sense whose sources are all visual receptors. The mapping is made evaluator-side and never enters cognition.
- **Learned loss.** The production bridge's prequential Huber loss of each predictor of the target (`prediction_errors`), averaged over its predictors.
- **Baselines.** Same activation series, same loss:
  - persistence, the previous value (the change-free baseline);
  - causal running mean since X;
  - zero.
- **Window.** The late window is the last `W = 400` ticks before H. A target counts only if it is predicted through the whole window.
- **Per seed.** Medians over those targets of `baseline_loss − learned_loss` for each baseline (`gain_persist`, `gain_mean`, `gain_zero`).

## 6. Horizon H: selection rule (fixed before any development run)

### 6.1 Candidates

`H ∈ {500, 1000, 1500, 2000}` with `W = 400`. A single development run of 2000 ticks per seed and arm contains every shorter candidate as an exact prefix (Gate H).

### 6.2 Rule

H is **the smallest candidate** for which, on **all three** development seeds:

1. the wall-clock time per arm up to H is at most 90 min and peak RSS is at most 6 GB (EW-D0 budget, 15 GB machine, strictly sequential runs);
2. arm A has at least 8 visual targets predicted through the whole late window;
3. every per-target quantity in the window is finite (numerical stability).

If no candidate satisfies the rule, D1 is not runnable as designed. That is reported, and the design returns to the owner.

**No predictive-performance quantity may be used to choose H.** The development stage runs with `report_performance = false`, so no loss or gain is even computed.

### 6.3 Freeze

After development, a `held-out/` experiment is committed with the frozen H, W, baselines, criteria, nursery, apparatus version and seeds 613/617/619, `report_performance = true`, and a single horizon. Only then, and only after explicit owner approval, are the held-out seeds run, each **once**.

### 6.4 Development result (2026-09-29): no candidate H satisfies the rule

Run `20260929T055046Z-learning-visual-acquisition-v1-5807c08-9c22`, code identical to `c3fa3235` for every file the run uses. Seeds 101, 127, 149; `report_performance = false`, so no loss or gain was computed.

| Seed | Visual predictors at X | A: visual targets predicted through the whole window (H = 500 / 1000 / 1500 / 2000) | B: same | A: wall time to H=2000 | Peak RSS |
|---|---|---|---|---|---|
| 101 | 0 | 0 / 1 / 1 / 1 | 0 / 0 / 0 / 0 | 1048 s | 158 MB |
| 127 | 0 | 0 / 2 / 3 / 4 | 0 / 0 / 0 / 0 | 1034 s | 184 MB |
| 149 | 0 | 0 / 2 / 3 / 5 | 0 / 0 / 0 / 0 | 790 s | 186 MB |

At the start of the window, 143–170 visual senses exist on every seed and horizon. All values are finite.

**Criteria 1 (budget) and 3 (stability) hold for every candidate. Criterion 2 (≥ 8 targets in A on all three seeds) holds for none.** Under §6.2, D1 is **not runnable as designed**. Nothing is frozen and no held-out seed is enabled. The design returns to the owner. Changing the candidate horizons, the target minimum, the nursery or the measurement is a new owner decision, taken before any performance quantity is computed.

### 6.5 EW-D1A audit (2026-09-29): why only 1–5 targets

Run `20260929T073605Z-learning-visual-predictor-audit-759ce5f-5b83`: development seeds, arm A, 2000 ticks, sampled every 50. It is observer-side and read-only, and it computes no evaluator metric (`studies/learning/visual_predictor_audit.py`).

| Stage (tick ≈ 1600) | 101 | 127 | 149 |
|---|---|---|---|
| Visual senses admitted | 167 | 158 | 155 |
| … of which cognitive sense nodes | 67 | 62 | 51 |
| Promotable visual shadows (the organism's own supported evidence) | ~1200 | ~340 | ~260 |
| Visual predictors / all predictors | 3 / 16 | 2 / 14 | 4 / 13 |
| Visual predictors alive at end / lasting ≥ 400 ticks | 3 / 3 | 2 / 2 | 4 / 3 |
| Visual-target churn (sum of set differences over 40 samples) | 39 | 23 | 14 |

Findings:

1. **Not an evaluator artefact, not churn, not retirement.** Once promoted, visual predictors persist (median span 1150–1500 ticks, alive at the end), and target identity is stable. The whole-window requirement does not hide intermittent predictors, because there are almost none to hide. Owner cases A and D are excluded.
2. **Promotion throughput is the dominant bottleneck (case C).** Hundreds of promotable visual shadows exist, but promotion is serial: at most one predictor nominee in structural contention at a time. That yields about one predictor per ~120 ticks *across all targets* (13–16 by tick 1650). Vision gets 20–30 % of them, although visual shadows make up the majority of the promotable pool. The mechanism is generic and not visual-specific.
3. **Graph admission limits the reachable targets.** Only 51–67 of the 155–170 admitted visual senses become cognitive sense nodes, and that number is flat after ~300 ticks.
4. **A metabolic ceiling at ~1650 ticks, a design flaw in D1.** On all three seeds the shadow, promotion and predictor state freezes from tick ≈ 1654 onward. The D1 nursery has no resource. Energy drains deterministically: reserve 25 % and "stressed" at tick 1500 in EW-D0 on the same nursery. At SEVERE pressure, homeostasis pauses plasticity. That is also the acquisition protection boundary (ADR-0008), which the D1 runner does not apply. So candidate H = 2000 lies beyond the protected acquisition envelope, and no protected D1 run can last longer than ≈ 1650 ticks as designed.

Consequence: D1 as preregistered measures the organism's generic promotion throughput and the nursery's energy budget more than visual acquisition. Any redesign (D1-v2) is an owner decision. Options must be decided before any performance quantity is computed: a nursery energy supply or a Lab-provided protected-recovery protocol (spec §6.4), the acquisition safety guard in the runner, and a generic, non-visual review of predictor promotion throughput.

## 7. Criteria (approved 2026-09-28)

D1 passes on the held-out seeds if:

1. **Assessability.** Arm A has at least 8 visual targets predicted through the window on a seed. A seed below that is not assessable. With fewer than 2 assessable held-out seeds, D1 is `not_assessable`.
2. **Utility.** On **every** assessable held-out seed, A's `gain_persist`, `gain_mean` and `gain_zero` are all strictly positive.
3. **Novelty.** On every assessable seed there were zero visual predictors at X.
4. **Acquisition.** On every assessable seed:
   - if B has at least 8 fully predicted visual targets, A's median learned loss is strictly lower than B's **on the intersection** of targets both predict through the window;
   - if B has fewer than 8, the criterion is satisfied, because the ablated arm does not reproduce A.

No minimum effect size is imposed; the requirement on every assessable seed is already demanding. Effect magnitudes are reported. No parameter changes after results.

## 8. Failure taxonomy

Evaluated per seed and overall, in this order:

- `not_assessable`: fewer than 8 predicted visual targets, or fewer than 2 assessable seeds.
- `preexisting_structure_at_X`: novelty fails.
- `no_predictive_utility`: A does not beat every baseline.
- `acquisition_not_isolated`: B matches or beats A. This means only that the ablation did not isolate the cause, not why.
- `passed`.

Negative results are kept and reported.

## 9. Seeds, cost and provenance

- **Development:** 101, 127, 149. Runner engineering and feasibility only (§6); never tuned against.
- **Held-out:** 613, 617, 619. No earlier study uses them as seeds.
- **Cost.** EW-D0 measures the vision body's long-horizon cost and budget first. Runs are strictly sequential, with nothing else running.
- **Provenance.** Each run records the commit, seed, State X, derived motion parameters (observer-side) and the ablation.
- **Comparability.** Results before EW-T are not comparable (ADR-0042).

## 10. Outlines (not preregistered)

- **D2 — coherence and source candidates.** Multi-receptor structure that improves held-out prediction, is stable across more than one stimulus configuration and is revisable when coherence fails. No row/column labels, fixture ids, coordinates or classes.
- **D3 — persistence through occlusion.** Visible → partial occlusion → absence → reappearance. Blind persistence (never revised despite contradiction) must be distinguished from evidence-supported persistence.
- **D4 — self-caused versus external change.** An acquired action or competence produces one visual transform; independent source motion produces another. The question is whether the evidence separates change explained by the current action model from change it does not explain. No `self_motion` label.

## 11. D1-v2 (owner decision 2026-09-29): supported protected nursery

D1-v1 remains a permanent result: `not_assessable`. The established causes are serial predictor promotion and a metabolic ceiling at about tick 1650 (§6.4–§6.5).

> **D1-v2 changes the protected acquisition environment, not the cognitive acquisition mechanism. Its purpose is to remove metabolic termination as a confound while preserving the organism's existing predictor-formation and promotion dynamics.**

**Declared causal changes (only these two):**

1. **Nursery `vision-nursery-d1-v2`.** Same fixtures and seeded stimulus as `-v1`, plus `metabolic_support = {kind: bounded_maintenance, rate_per_tick: 0.6, ceiling_fraction: 0.9}`.
   - It is a property of the protected environment, not a resource to find.
   - It is deterministic and independent of action and of visual performance, identical in arms A and B, and versioned with the nursery.
   - It enters through the body's ordinary intake path (`absorb_metabolic_energy`). It is not hidden from interoception, and it needs no behaviour to obtain.
   - It never refills to full. Sizing: EW-D0 measured a basal drain of about 0.80 energy per tick in `-v1`; 0.6 is 75 % of that. This keeps real cost and homeostatic variation while keeping basal metabolism from ending the Experience before 4000 ticks.
   - The supplied total is recorded per arm (`nursery_support_energy`).
2. **Mandatory acquisition guard.** `AcquisitionSafetyPolicy` via `RunGuard(acquisition.vision)` runs on every tick of X and of each arm. If the body still reaches SEVERE, the arm ends as `protected_recovery` and never continues. Horizons past that tick are `reached = false`, which counts as not assessable.

**Unchanged:**
- cognition, including serial promotion;
- the visual apparatus;
- baselines, criteria and the taxonomy (§7–§8, including ≥ 8 targets);
- seeds and the Lab-owned arm-B ablation.

**Horizon rule for D1-v2**, fixed before any D1-v2 run:
- **Candidates:** `H ∈ {500, 1000, …, 4000}`, step 500. **Technical limit:** 4000 ticks, and at most 90 min and 6 GB per arm.
- **Selection:** H is the smallest candidate that satisfies the assessability gate below on every development seed.
- **Single development run:** each seed and arm runs once to 4000 ticks, and every candidate is an exact prefix (Gate H), so all candidates are evaluated without further runs.
- **No predictive quantity is computed** (`report_performance = false`).

**Assessability gate (owner decision 2026-09-29), checked before any performance quantity.** For a candidate H, on every development seed:

1. **Protected envelope.** Both arms reach H with no acquisition-guard termination (`reached = true`).
2. **Admitted receptors.** Arm A has at least 8 visual cognitive sense nodes at the start of the window (`visual_sense_nodes_at_window_start`). This is a necessary condition derived from the 8-target criterion, not a new threshold.
3. **Stable predictors.** Arm A has at least 8 visual targets predicted through the whole window **by the same predictor identity**: the set of predictor ids for the target is non-empty and identical at the window start and at H (`visual_targets_stable_full_window`). A target whose predictor was replaced inside W does not count. This also replaces "fully predicted" in §7.1 for D1-v2.
4. **No artificial churn.** Item 3 is the gate. Whole-run visual predictor churn (sum of id-set differences, sampled every 50 ticks) is reported descriptively (`visual_predictor_churn`) without a threshold.
5. **Observation independence.** Gate I (observer density does not change the causal trajectory) passes for `vision-nursery-d1-v2`.
6. **Budget and stability.** §6.2 items 1 and 3 still apply (90 min and 6 GB per arm, finite values).

**Stop rule (owner decision 2026-09-29).** If no candidate satisfies the gate, D1-v2 is closed as a **structural negative result** (`not_assessable`). Vision is recorded as an undemonstrated capability, and work moves to the remediation roadmap (Phase A → B). There is no further D1 redesign and no threshold relaxation. The promotion-throughput draft (`docs/design/cognition/predictor-promotion-throughput-v1.md`) is **not scheduled** as a D1 follow-up.

Held-out seeds 613, 617 and 619 stay disabled until D1-v2 is frozen and the owner approves explicitly.

## 12. D1-v2 closure (2026-09-30; owner-authorized)

The development run `20260929T084348Z-learning-visual-acquisition-v1-c00846d-da19`
completed all three development seeds in both arms to 4000 ticks. It used
`report_performance = false`; no predictive-performance quantity was computed.
The run record is retained at
`.symbiont/runs/20260929T084348Z-learning-visual-acquisition-v1-c00846d-da19/`.

All arms reached every candidate horizon without acquisition-guard termination;
the run reports finite quantities throughout, maximum arm time below 90 minutes,
and peak RSS below 6 GB. At the largest candidate, Arm A had respectively 5, 4,
and 4 stable visual targets for seeds 101, 127, and 149. No candidate can satisfy
the required minimum of 8 targets on every development seed. Therefore no H is
selected: by the preregistered stop rule (§11), D1-v2 closes as a structural
negative (`not_assessable`). Visual acquisition remains undemonstrated. No
held-out seeds are enabled, and no further D1 redesign or threshold relaxation
is authorized.

Gate I for `vision-nursery-d1-v2` was verified by
`tests/integration/test_physics3d_reproduction_gates.py::test_gate_i_observer_density_does_not_change_causal_state[vision-d1-v2]`
on 2026-09-30 (1 passed). This establishes observer-density neutrality for that
mechanical test, not predictive utility or visual acquisition.

Owner authorization to record this closure: user instruction, 2026-09-30,
“procede con lo pendiente de D1-v2”.
