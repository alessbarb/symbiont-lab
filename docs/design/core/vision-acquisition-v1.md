# Vision Acquisition v1 (EW-D): preregistration

Status: **D1 preregistered, awaiting owner approval of the criteria. Not run on held-out seeds.**
D2 and D3 are outlines only and are **not preregistered**.

Context: Experience & World Architecture v1, gap analysis Phase 7, and the owner decision of 2026-09-28 (EW-D staged D1 → D2 → D3). Prerequisites met on `main`:

- **EW-C (ADR-0011):** causal visual apparatus substrate.
- **EW-T (ADR-0042):** deterministic causal time and sensor cost.
- **Gates H and I:** hold at engine level (`tests/integration/test_physics3d_reproduction_gates.py`).

## 1. Question (D1: temporal visual structure)

> Can Symbiont acquire predictive structure over its visual field that did not exist before the experience?

The question is not whether Symbiont sees objects. It is whether it has visual relations that predict held-out visual change better than trivial baselines.

## 2. Apparatus and nursery

- **Body.** `anthropomorphic-v6-vision`: a 12×12 luminance array on the head link, with opaque ids and no depth or entity identity (ADR-0011).
- **Nursery.** `vision-nursery-d1-v1`, a versioned recipe:
  - a uniform background panel, luminance 0.45;
  - one coherent source, luminance 0.95, 0.35 m square, that sweeps sinusoidally along the lateral axis (amplitude 0.8 m, period 96 ticks) in front of the eye.
- **Source properties.**
  - The source is kinematic and has no collision shape.
  - Its pose is a pure function of the causal tick (`fixture_position`), identical across seeds and exact on resume.
  - It reaches the organism only through the visual apparatus.
- **What Symbiont receives.** Only `rec.N → luminance`. The ids `background` and `source`, and their purpose, are observer-only.

## 3. State X

For each seed, a new Symbiont is born into the vision body in the D1 nursery and run for 4 ticks with the plasticity ablation off. The resulting bundle and body are retained as X (ADR-0009). Every arm of that seed resumes from the same X.

**D1-c precondition.** At X, no predictor targets a visual sense. If one does, the seed is recorded as invalid and D1 is not assessable on it.

## 4. Arms

- **A — acquisition.** Default behaviour.
- **B — sensors without acquisition.** A Lab-set ablation, `cognitive_plasticity_ablated`. It is off by default, set by the Lab after construction, recorded per arm in the study result, not writable by cognition, and not persisted into X or `effective_config` (`tests/unit/core/test_cognitive_plasticity_ablation.py`). It forces off:
  - cognitive plasticity (the bridge's `plasticity_enabled` gate), and
  - predictor and structure promotion (`auto_promote_predictors`).

  Sensor admission, sensory plasticity and the visual apparatus stay unchanged. B separates *having visual sensors* from *having acquired something from them*.
- **C — no visual apparatus.** Not assessable in D1, because it has no visual targets. It is reserved for transfer studies, where the same X lineage without Vision will be compared in a World.

## 5. Measurement (evaluator-side, observer reads only)

- **Visual target.** A cognitive sense node whose source ids are all visual receptors (`rec.107`–`rec.250`). The mapping is made evaluator-side from the sensory system and never enters cognition.
- **Learned loss.** For each tick and each predictor of a visual target, the Huber loss reported by the production bridge (`result.cognition.prediction_errors`). This loss is prequential: the prediction is formed before the target value is seen. A target's learned loss is the mean over its predictors.
- **Baselines.** Computed on the same target activation series (`result.cognition.activations`) with the same Huber loss, as in `predictive_utility.py`:
  - *persistence* predicts the previous activation;
  - *running mean* predicts the causal mean of all earlier activations of that target.
- **Windows.** The run lasts `H = 2000` ticks from X. The late window is the last 400 ticks. A target counts only if it has a predictor through the whole late window.
- **Per-seed statistics.** Over visual targets, the median of `persistence_loss − learned_loss` (`gain_persist`) and the median of `mean_loss − learned_loss` (`gain_mean`).
- **Observation density.** Observation runs every tick. This is justified by Gate I, since observation density does not change causal state.

## 6. Seeds

- **Development:** 101, 127, 149. These are used only to engineer and debug the runner and to check the horizon is feasible. No criterion is tuned on them, and their results are reported separately as development.
- **Held-out:** 613, 617, 619. No earlier study uses them as seeds. Each runs **once**, after owner approval of §7.

## 7. Criteria, fixed now

D1 **passes** on the held-out seeds if all of the following hold:

1. **Assessability.** Arm A has at least 8 visual targets with predictors on each seed. A seed below that is *not assessable*; that is a result, not a reason to tune. D1 is not assessable if fewer than 2 held-out seeds are assessable.
2. **Utility.** In A, `gain_persist > 0` and `gain_mean > 0` on **every** assessable held-out seed.
3. **Novelty.** D1-c holds on every assessable seed: no visual predictors at X.
4. **Acquisition, not sensors.** On every assessable seed, either B has fewer than 8 visual targets with predictors, or B's `gain_persist` is below A's.

**Outcomes.**
- All four hold → D1 passes and D2 is proposed.
- Criterion 2 or 3 fails → D1 is rejected; the negative result is kept and reported.
- Otherwise → reported, not proposed.

No parameter changes after results: not `H`, the window, the thresholds, the nursery or the body. Retuning on held-out seeds is prohibited.

## 8. Cost and provenance

- **Cost.** Measured headless: vision body ≈ 0.3–0.6 s per tick. D1 held-out is 2 arms × 3 seeds × 2000 ticks, about 1–2 h, run strictly sequentially with nothing else running on the machine.
- **Provenance.** Runs are recorded with the commit, the State-X checkpoint ids and hashes (ADR-0009), the seed and the ablation flag.
- **Comparability.** Results before EW-T are not comparable with these (ADR-0042).

## 9. Outlines (not preregistered)

- **D2 — persistence under occlusion.** Visible → partially occluded → absent → visible again. Question: does useful predictive structure survive a temporary absence of evidence? The question is not whether it "knows the object still exists". D2 is only preregistered after D1 passes.
- **D3 — self-caused versus external transformation.** Head or body action → transform A, and external motion of the source → transform B. Question: does the evidence separate changes explained by the organism's own action from those it does not explain? D3 comes after D2.
