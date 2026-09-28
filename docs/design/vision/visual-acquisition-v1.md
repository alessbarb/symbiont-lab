# Visual Acquisition v1 (EW-D): preregistration

Status: **D1 criteria approved by the owner (2026-09-28). H is not frozen yet.** The development stage (seeds 101/127/149, feasibility only) has not been run. Held-out seeds 613/617/619 are disabled until the preregistration is frozen (§6.3) and the owner gives explicit approval.

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
