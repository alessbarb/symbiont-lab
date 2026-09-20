# Embodiment / self-boundary falsification protocol v1

Status: **preregistered, not yet executed**

Baseline: `f9514c9e3ce56a0bc3c6c4d233e202e31c5bc10d`

## 1. Scientific question

> Can a cognitive germ with no innate body semantics infer, from causal experience alone, an operational distinction between processes attributable to its own activity and processes attributable to the external world, and revise that distinction when embodiment changes?

This protocol is deliberately adversarial. Passing ordinary port permutation, broken-effector and transplant tests is **not** sufficient evidence. The experiments below are designed to produce plausible false positives for agency and body membership.

No evaluator truth, condition label, morphology label, intervention label or success signal may enter `Symbiont`, `AgencyModel`, `InferredBodySchema`, `InferredSelfModel`, genome or germline.

## 2. Competing hypotheses

### H0 — heuristic contingency account

The present mechanism does not infer a genuine operational self/world boundary. It classifies channels primarily from local activation–delta statistics, covariance and fixed thresholds. Under adversarial correlation, delayed causation or controllable external objects it will produce systematic false agency/body attribution.

### H1 — causal agency account

The subject forms a sufficiently robust causal agency model that:
- rejects externally yoked correlations;
- distinguishes self-caused consequences from merely correlated changes;
- revises attribution after causal remapping/failure;
- does not automatically assimilate every controllable external process into body;
- preserves abstract learning while relearning body-specific contingencies after transplant.

The burden of proof is on H1.

## 3. General rules

1. All interventions are apparatus-side and invisible to cognition except through ordinary physical consequences.
2. Human-readable IDs and condition names exist only in evaluator output.
3. Seeds are fixed before execution.
4. Thresholds and primary metrics are frozen before examining experimental results.
5. Negative results are first-class outcomes and must be recorded in `research/`.
6. A study that fails an integrity gate cannot be interpreted scientifically.
7. Unit tests may validate mechanics but cannot substitute for campaign-level evidence.

## 4. Primary evaluator metrics

All metrics are computed observer-side against apparatus truth.

### 4.1 Agency false-positive rate

```text
FPR_agency =
externally-caused channels classified self-caused
/
externally-caused channels evaluated
```

Primary target: **<= 0.10** after calibration.

### 4.2 Agency true-positive rate

```text
TPR_agency =
genuinely intervention-dependent channels classified self-caused
/
genuinely intervention-dependent channels evaluated
```

Primary target: **>= 0.70**.

### 4.3 Boundary balanced accuracy

Average of true-positive rate for genuinely self-caused channels and true-negative rate for external channels.

Primary target: **>= 0.75**.

### 4.4 Causal revision latency

Ticks from a hidden causal perturbation until the old agency attribution falls below the preregistered confidence threshold.

Report median and 90th percentile.

### 4.5 Relearning latency

Ticks from perturbation until the new causal mapping reaches stable attribution for a fixed confirmation window.

### 4.6 Prediction shock and recovery

For perturbation at `t0`:

```text
shock = mean_error[t0:t0+W] - mean_error[t0-W:t0]
recovery = first t where rolling_error <= pre_perturbation_error * 1.20
```

### 4.7 Body-assimilation error

Fraction of controllable **external** channels promoted into `internal_channels`.

This metric is central: controllability alone must not be accepted as proof of body membership.

## 5. Integrity gates

Before any scientific result is accepted:

- canonical clean World has `rig.runtime is None`;
- `rig.actuation_adapter is None`;
- no condition identifier enters `Symbiont.step()`;
- no intervention schedule enters genome or germline;
- same physical run with renamed evaluator labels produces identical subject trajectory;
- Observatory disabled vs enabled produces identical subject trajectory;
- PRNG streams for subject, world and evaluator interventions are independent;
- experiment replay from the same seeds is bit-for-bit equivalent for subject-visible inputs and outputs.

Failure of any gate invalidates the run.

---

# Experiment E1 — Yoked external causation

## Objective

Test whether AgencyModel confuses correlation with self-causation.

## Design

Two simultaneously observed input channels have matched marginal scale and comparable temporal variation.

### Condition A — genuine self-caused

```text
out.k(t)
   ↓ physical effector
input.A(t+1)
```

### Condition B — yoked external

The apparatus observes `out.k(t)` but an **external world process**, not the body effector, changes `input.B` according to a schedule statistically yoked to the subject's activity.

The subject is never told that B is external.

### Critical manipulation

Across blocks, introduce:
- exact yoking;
- jittered yoking;
- occasional anti-causal ordering where B changes immediately before output;
- independent matched-variance control.

## Falsification criterion

Evidence supports H0 if `input.B` is persistently classified self-caused at rates comparable to A, especially in anti-causal blocks.

## Required report

- FPR/TPR;
- confidence trajectory per channel;
- intervention/baseline counts;
- lead-lag cross-correlation;
- time to reject B after yoking is broken.

---

# Experiment E2 — Controllable external tool vs body

## Objective

Test the current implicit assumption:

```text
controllable => internal/body
```

## Design

Provide an external object coupled through normal physics.

The subject can learn:

```text
out.a
  ↓
body effector
  ↓
external object moves
  ↓
sensory consequence
```

The external object is highly controllable and persistent but is **not** part of Body.

Compare:

1. direct somatic consequence;
2. attached external tool;
3. detached but remotely controllable object;
4. uncontrollable external object.

No semantic distinction is exposed.

## Primary question

Does `InferredBodySchema` classify the controllable tool as body merely because it is reliably controllable/correlated?

## Falsification criterion

H0 gains support if body-assimilation remains high for detached/remotely controlled objects and does not fall after decoupling.

## Important interpretation

Assimilation of a physically attached tool is not automatically an error; embodiment can extend. The decisive comparison is whether classification tracks **causal integration and persistence** rather than raw controllability.

---

# Experiment E3 — Temporal causality challenge

## Objective

Test whether the one-step sensorimotor model mistakes delay structure for absence of agency.

## Design

Same physical effector, four hidden delay regimes:

```text
D0: consequence t+1
D1: consequence t+2
D2: consequence t+4
DJ: variable delay 1..4
```

Include matched external distractors at t+1.

## Predictions

A robust agency mechanism should discover that some effects follow its activity with stable delay.

The current `SensorimotorModel` is explicitly one-step and therefore this experiment is expected to be difficult.

## Falsification criterion

If genuine delayed consequences are classified external while t+1 distractors become self-caused, this is evidence that current agency is a temporal heuristic rather than robust causal inference.

This experiment is allowed to fail. A failure is scientifically informative and should drive a later model redesign rather than threshold tuning.

---

# Experiment E4 — Sham, permutation, break and transplant

## Objective

Separate genuine causal revision from generic novelty/error response.

## Within-subject sequence

```text
Phase 0  stable Body A
Phase 1  SHAM intervention (no causal change)
Phase 2  output-port permutation
Phase 3  restore original mapping
Phase 4  silent effector failure
Phase 5  repair
Phase 6  transplant to Body B
Phase 7  return to original Body A
```

The subject receives no phase marker.

## Required evidence

A valid result requires:
- low revision during SHAM;
- prediction shock after actual causal changes;
- selective loss of old agency;
- acquisition of new mapping;
- faster reacquisition on return to Body A only if retained abstract/body-specific memory legitimately supports it.

## Falsification criteria

H0 is supported if:
- SHAM causes revision comparable to real perturbations;
- permutation causes no mapping-specific change;
- transplant is handled immediately without prediction shock;
- return to Body A shows no distinction from a novel body despite preserved cognitive history.

---

# Experiment E5 — Somatic-correlation trap

## Objective

Test the current `somatic_correlated_channels` rule.

## Design

Create three opaque inputs:

1. true interoceptive mixture generated from Body physiology;
2. external environmental process correlated with a self-caused channel;
3. external independent control.

Match variance and approximate autocorrelation.

The evaluator alone knows which is which.

## Falsification criterion

If the externally correlated channel is promoted to `somatic_correlated_channels` at similar rates to genuine interoception, the current body-boundary rule is not specific enough.

This experiment directly attacks correlation-based somatic inference.

---

# Experiment E6 — Hidden common-cause confound

## Objective

Test whether a third process can create apparent activation → perception causation.

## Design

A hidden world variable `Z` independently influences:
- conditions that increase the probability of a subject activation;
- an external sensory channel.

The subject sees neither Z nor the evaluator condition.

This creates observational correlation without the subject output causing the sensory consequence.

Include a true intervention-dependent channel in parallel.

## Falsification criterion

Systematic promotion of the Z-driven channel to agency is evidence for H0.

---

# Experiment E7 — Heredity leakage challenge

## Objective

Verify that the multidimensional inheritance system transmits predisposition without body/world-specific solutions.

## Parent training

Parents experience one fixed:
- port mapping;
- morphology;
- environmental resource identity;
- causal regularity.

## Offspring conditions

Children receive:
- same environment;
- permuted ports;
- renamed apparatus IDs;
- different morphology;
- reversed environmental correlation.

## Required checks

At birth:

```text
body_schema == germinal/empty
agency evidence == empty
sensorimotor learned weights == empty
world/resource/signal IDs absent from inheritance
```

But lawful epigenetic modulation of declared loci may differ.

## Falsification criterion

Any child-specific advantage that survives a transformation which destroys the parent-specific causal mapping must be examined for direct information leakage.

A performance benefit alone is not proof of leakage; the mechanism and inherited payload must be traced.

---

# Experiment E8 — Evaluator-label invariance

## Objective

Prove non-interference beyond static AST checks.

Run physically identical campaigns while changing only evaluator-side:
- body labels;
- port display names;
- resource names;
- hazard names;
- intervention condition names;
- world ID.

Subject PRNG seed and physical equations remain fixed.

## Acceptance

Subject-visible input stream, output stream and internal state trajectory must be identical.

Any divergence is a P0 experimental-integrity failure.

---

# 6. Ablations

Every positive main result must be paired with at least these ablations:

1. **No agency update** — freeze AgencyModel.
2. **No body-schema update** — preserve agency but freeze BodySchema.
3. **No active exploration** — passive/rest-only control where viable.
4. **No baseline contrast** — diagnostic only; expected to increase false positives.
5. **No perceptual covariance contribution** — tests whether somatic classification is correlation-driven.

A claimed effect that survives removal of the mechanism supposedly responsible for it is not evidence for that mechanism.

# 7. Seeds and campaign structure

Initial pilot seeds:

```text
101
127
149
173
211
257
307
353
401
457
```

Do not change this set after seeing outcomes.

For each experiment:
- 10 seeds pilot;
- if integrity gates pass, preregister any larger confirmatory campaign before execution;
- report every seed, not only aggregate winners.

# 8. Reporting policy

Each experiment produces:

```text
experiment manifest
code commit SHA
seed ledger
raw observer-side metrics
integrity-gate result
per-seed result
aggregate result
negative findings
interpretation limits
```

Never write “self-awareness”, “consciousness”, “understands its body” or equivalent from these experiments.

Permitted claims are operational only, e.g.:

> “The system distinguished intervention-dependent from matched externally yoked channels under protocol E1.”

# 9. First implementation tranche

Implement in this order:

1. E1 Yoked external causation
2. E5 Somatic-correlation trap
3. E4 Sham/permutation/break/transplant
4. E3 Temporal causality challenge
5. E2 Tool/body distinction
6. E6 Hidden common cause
7. E8 Label invariance
8. E7 Heredity leakage

Reason: E1 and E5 attack assumptions already visible in the current `AgencyModel` / `InferredBodySchema` implementation and therefore have the highest probability of revealing a real scientific limitation quickly.

# 10. Do not repair before measurement

If E1, E3, E5 or E6 fails, first freeze and record the negative result under `research/`.

Only after the result is recorded may the mechanism be redesigned.

The purpose of this campaign is not to make Symbiont pass. It is to determine what the present mechanism actually demonstrates.
