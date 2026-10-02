---
name: scientific-experiment
description: Design, preregister, execute, validate, and evaluate empirical experiments across exploratory, confirmatory, and held-out regimes with explicit falsification criteria, protocol integrity, preserved negative results, and bounded scientific conclusions.
---

# Symbiont Scientific Experiment Skill

## Purpose

Govern the lifecycle of scientific experimentation on Symbiont, its embodiment, its environment and the apparatus used to study them.

The objective is to design and execute rigorous, reproducible empirical tests that can discriminate between hypotheses, expose failure modes, preserve negative evidence and support bounded scientific conclusions.

An experiment is not a unit test.

A unit test verifies a software contract.

An experiment evaluates a scientific claim about behavior, learning, adaptation, cognition, embodiment, environment interaction, generalization or another phenomenon under uncertainty.

The experiment must preserve a strict distinction between:

```text
software mechanics
scientific protocol validity
scientific outcome
```

A successful runner does not imply a successful hypothesis.

A failed hypothesis does not imply broken software.

---

# Operating Contract

When this skill is active, the agent MUST:

1. **Declare the experimental regime before execution.**

   Current canonical regimes include:

   - exploratory;
   - confirmatory;
   - held-out.

2. **Preregister every confirmatory or held-out protocol before evaluating its scientific results.**

3. **Define the research question, hypotheses or competing explanations, variables, controls, seed budget, horizons, analysis plan and decision criteria before execution where the regime requires freezing.**

4. **Register and maintain experimental design status in the canonical design register.**

5. **Preserve experimental isolation.**

   Experimental and comparison arms must differ only in the intended intervention or in explicitly documented differences required by the design.

6. **Verify constitutional non-leakage.**

   Evaluator truth, target labels, desired outputs, fitness signals or simulator ground truth MUST NOT enter organism cognition unless explicitly part of the organism's legitimate sensory environment.

7. **Obey the Golden Invariant.**

   NEVER modify the organism merely to make an experiment pass.

8. **Distinguish apparatus validity from scientific outcome.**

9. **Preserve negative, null, inconclusive and not-testable outcomes.**

10. **Record protocol deviations explicitly.**

11. **Apply the preregistered analysis plan rather than inventing a favorable interpretation after seeing results.**

12. **Bound conclusions to the conditions actually tested.**

The agent MUST NOT:

- use exploratory observations as confirmatory evidence without a new frozen protocol;
- inspect or tune against held-out conditions during routine development;
- modify seeds, horizons, metrics, thresholds or stopping rules after observing results unless the deviation is recorded and the evidential status is downgraded appropriately;
- replace failed or `not_testable` seeds with hand-picked alternatives merely to improve the result;
- grant one arm information or resources unavailable to another arm unless that difference is the explicit intervention;
- reinterpret negative results as implementation bugs without independent evidence of apparatus or implementation failure;
- merge contradictory arms into a single post-hoc narrative;
- generalize beyond the tested population, environment, embodiment, horizon or intervention;
- treat statistical or numerical significance as scientific importance without interpreting effect size and mechanism.

---

# Normative Language

## MUST / MUST NOT

Mandatory experimental invariant.

## SHOULD / SHOULD NOT

Default scientific practice.

Deviation requires an explicit rationale, preferably preregistered where applicable.

## MAY

Optional experimental technique.

---

# Use This Skill When

Use this skill when:

- creating or reviewing an experimental proposal;
- implementing experimental runners;
- defining falsification batteries;
- performing ablations;
- comparing controlled interventions;
- testing learning, adaptation or generalization;
- evaluating stability across seeds or generations;
- testing causal effects under controlled conditions;
- validating behavior outside exploratory tuning conditions;
- executing confirmatory or held-out campaigns;
- maintaining experiment status in the design register.

---

# Do Not Use This Skill When

Do not use this skill as the primary workflow for:

- post-hoc investigation of an unexpected anomaly — use `scientific-investigation`;
- CPU, memory or latency profiling — use `performance-investigation`;
- canonical scientific documentation — use `scientific-documentation`;
- routine unit or integration testing without a scientific hypothesis;
- repository governance, validation selection, publishing or branch management.

An experiment MAY reveal an anomaly.

Do not silently switch from experimentation into debugging.

Preserve the experimental result first.

Then investigate the anomaly separately if needed.

---

# Experimental Regimes

The following are the current canonical regimes.

They are not necessarily an eternal exhaustive taxonomy.

If future scientific work requires another regime, define it explicitly rather than forcing it into an unsuitable category.

---

# Regime 1: Exploratory

## Purpose

Use exploratory work to:

- discover candidate phenomena;
- inspect parameter spaces;
- calibrate instrumentation;
- discover useful metrics;
- estimate plausible horizons;
- generate hypotheses;
- expose unexpected mechanisms.

Exploratory work MAY involve iterative tuning.

Exploratory findings are provisional.

They MUST NOT be represented as confirmatory evidence.

An exploratory result may motivate a later preregistered experiment.

---

# Regime 2: Confirmatory

## Purpose

Test a preregistered scientific claim under frozen conditions.

Before execution, freeze where relevant:

- hypothesis;
- arms;
- intervention;
- control definition;
- seeds;
- horizon;
- metric definitions;
- analysis plan;
- thresholds;
- stopping rules;
- exclusion criteria;
- `not_testable` rules.

Post-hoc changes normally invalidate confirmatory status unless explicitly handled as a protocol deviation.

---

# Regime 3: Held-Out

## Purpose

Evaluate generalization or robustness under conditions intentionally withheld from exploratory or confirmatory tuning.

Held-out data, seeds, environments, scenarios or suites MUST NOT be used to tune the organism, metrics, thresholds or experiment.

Execution requires the governance or owner authorization defined by the repository.

Held-out results are evidence.

They are not debugging input.

---

# Experimental Lifecycle

```text
FORMULATE QUESTION
        ↓
DECLARE REGIME
        ↓
PREREGISTER PROTOCOL
        ↓
REGISTER DESIGN
        ↓
VALIDATE APPARATUS
        ↓
FREEZE EXECUTION CONDITIONS
        ↓
EXECUTE CAMPAIGN
        ↓
VALIDATE RUNS
        ↓
APPLY PREREGISTERED ANALYSIS
        ↓
DETERMINE SCIENTIFIC OUTCOME
        ↓
PRESERVE RESULT
```

---

# Phase 1: Research Question

Start with a bounded scientific question.

A useful question identifies:

- phenomenon;
- population or organism scope;
- intervention;
- comparison;
- outcome;
- relevant conditions.

Poor:

> Does learning work?

Better:

> Under the preregistered environment and seed set, does mechanism A produce a measurable improvement in held-out prediction compared with the baseline arm?

Avoid questions that embed the desired answer.

---

# Phase 2: Hypothesis Structure

Use hypotheses appropriate to the scientific question.

Do not force a classical null-hypothesis format when it does not fit the experiment.

Possible structures include:

## Target hypothesis

A concrete operational claim.

Example:

```text
H1:
The intervention reduces held-out predictive loss relative to the matched baseline.
```

## Baseline expectation

A comparison against:

- unchanged behavior;
- random baseline;
- known mechanism;
- persistence baseline;
- ablated system;
- scrambled control;
- previous active model;
- another experimental arm.

## Null hypothesis

Use when statistically meaningful.

Example:

```text
H0:
The experimental and control arms do not differ beyond expected variation.
```

## Competing mechanistic hypotheses

Use when the experiment is designed to discriminate among causal explanations.

The protocol does not require a formal H0 when another baseline structure is scientifically more appropriate.

---

# Phase 3: Preregistration

A confirmatory or held-out preregistration SHOULD define the following where relevant.

## 1. Research question

The exact question being tested.

## 2. Regime

```text
EXPLORATORY
CONFIRMATORY
HELD-OUT
```

## 3. Hypothesis or competing hypotheses

Operationalized claims.

## 4. Intervention

What differs between experimental conditions.

## 5. Independent variables

Variables intentionally manipulated.

## 6. Dependent variables

Measured outcomes.

## 7. Controls / baselines

Define the appropriate comparison.

Controls may include:

- yoked control;
- ablation;
- historical baseline;
- persistence baseline;
- zero baseline;
- scrambled baseline;
- alternate mechanism;
- unchanged system.

Do not create arbitrary controls merely to satisfy a template.

## 8. Seed budget

Declare:

- exact seeds;
- number of seeds;
- generation strategy if seeds are generated deterministically.

Do not expand the budget after seeing results unless preregistered.

## 9. Horizon

Define:

- ticks;
- episodes;
- generations;
- evaluation windows;
- warmup periods.

## 10. Measurements

Define:

- metrics;
- observation frequency;
- aggregation method;
- units.

## 11. Analysis plan

Declare how evidence will be evaluated.

Where relevant specify:

- per-seed aggregation;
- population aggregation;
- effect-size calculation;
- uncertainty intervals;
- statistical tests;
- paired vs. unpaired comparison;
- treatment of missing values;
- treatment of `not_testable`;
- treatment of aborted runs.

## 12. Decision criteria

Define what outcomes map to:

```text
SUPPORTED
NOT SUPPORTED
REFUTED
INCONCLUSIVE
```

Do not define thresholds after observing the result.

## 13. Testability criteria

Define the conditions required for the run to be scientifically interpretable.

## 14. Stopping rules

Define normal completion and valid early termination.

## 15. Exclusion rules

Define exclusions before execution where possible.

---

# Design Register

Before changing or executing a governed experiment:

1. inspect the canonical design register;
2. identify the current state;
3. verify that the protocol is authorized for the intended operation;
4. update the register atomically with design changes.

Possible design states may include:

```text
Proposed
In review
Approved
Frozen
Closed
Superseded
```

Possible implementation states may include:

```text
Not started
Pending
In progress
Partial
Complete
```

Use the repository's canonical statuses if they differ.

Do not invent parallel state taxonomies.

---

# Apparatus Validation

Before interpreting scientific results, determine whether the experimental apparatus functioned correctly.

Possible mechanics checks include:

- runner starts;
- expected arms are created;
- expected seeds are loaded;
- required sensors are active;
- dimensions match;
- logging works;
- metrics are produced;
- output artifacts are persisted;
- no forbidden information leaks occur.

Mechanics tests MAY use reduced horizons or mock execution.

Passing mechanics checks proves only that the experimental machinery appears operational under those conditions.

It does not support the scientific hypothesis.

---

# Scientific Campaign

A scientific campaign executes the actual preregistered protocol.

Do not silently alter:

- seeds;
- horizons;
- arms;
- thresholds;
- instrumentation;
- metrics;
- testability rules;
- stopping rules.

Freeze what the regime requires to be frozen.

Record the exact implementation revision used for execution.

---

# Control Equivalence

Control and experimental arms SHOULD be matched on all scientifically relevant conditions except the intended intervention.

Relevant dimensions may include:

- initial state;
- world;
- body;
- embodiment;
- sensory exposure;
- runtime configuration;
- compute availability;
- evaluation window;
- instrumentation;
- randomization policy.

Exact equality is not always possible or scientifically appropriate.

Where conditions differ, determine whether the difference:

1. is the intervention;
2. is required by the protocol;
3. is a confound.

If it is a confound, the result may be invalid or weakened.

---

# Run Validity

Scientific outcome and run validity are separate dimensions.

Every run or campaign SHOULD receive a validity determination.

Possible statuses include:

## VALID

The run satisfies the protocol sufficiently for scientific interpretation.

## NOT_TESTABLE

The run completed or partially completed, but preregistered conditions required for evaluating the hypothesis were never reached.

Examples:

- organism died before reaching evaluation maturity;
- required event never occurred;
- required state was never entered;
- sample window was unavailable.

`NOT_TESTABLE` is not:

- support;
- failure;
- refutation.

Do not replace `NOT_TESTABLE` seeds with hand-picked alternatives unless the protocol explicitly allows deterministic replacement.

## INVALID

The run cannot support the intended scientific interpretation.

Possible causes:

- apparatus failure;
- evaluator leakage;
- corrupted artifact;
- wrong revision;
- protocol deviation that invalidates comparison;
- incorrect arm configuration;
- missing required instrumentation.

Invalid runs are evidence about the apparatus or execution, not evidence for or against the hypothesis.

---

# Protocol Deviations

A deviation occurs when execution or analysis differs materially from the preregistered protocol.

Examples:

- seed changed;
- horizon changed;
- metric changed;
- threshold changed;
- control modified;
- analysis method changed;
- exclusion added post-hoc;
- stopping rule changed.

Do not hide deviations.

Record:

```text
planned protocol
actual execution
reason for deviation
scientific consequence
```

A deviation MAY:

- leave validity intact;
- weaken evidence;
- convert confirmatory evidence into exploratory evidence;
- invalidate the run.

Do not preserve the `CONFIRMATORY` label merely because the original protocol was confirmatory.

---

# Stopping Rules

The preregistration SHOULD define when a run:

- completes normally;
- becomes `NOT_TESTABLE`;
- becomes `INVALID`;
- may terminate early.

Possible termination conditions include:

- organism death;
- terminal lifecycle state;
- apparatus failure;
- invalid data;
- safety limit;
- irrecoverable runtime error;
- preregistered futility rule.

Do not stop early merely because the current result looks favorable or unfavorable.

---

# Negative Results

Negative results are scientific evidence.

A negative or non-significant result MUST be preserved.

It MUST NOT automatically be reclassified as a software defect.

A negative result MAY reveal a bug only when independent evidence shows that:

```text
implementation
or
apparatus
```

violated its intended contract.

Preserve both facts separately:

```text
scientific result
apparatus / implementation finding
```

Do not rewrite the scientific history after discovering the implementation defect.

Instead determine whether the original run remains valid.

---

# Analysis Discipline

Apply the analysis plan declared before execution.

Where relevant evaluate:

- individual seeds;
- aggregate behavior;
- effect magnitude;
- variance;
- confidence or uncertainty;
- control comparison;
- baseline comparison;
- sensitivity to predefined exclusions.

Do not search across metrics, seeds, horizons or transformations until a favorable result appears.

Exploratory post-hoc analysis MAY be useful.

When performed, label it explicitly as exploratory.

It does not retroactively become confirmatory evidence.

---

# Repeated Probing and Multiple Comparisons

When many hypotheses, metrics, horizons or comparisons are evaluated simultaneously, false-positive risk increases.

Where this matters, the preregistration SHOULD define how repeated comparisons are handled.

Possible approaches include:

- primary outcome designation;
- hierarchical testing;
- correction for multiple comparisons;
- independent confirmation;
- held-out replication.

Do not mechanically apply statistical corrections when they do not fit the experimental design.

The purpose is to prevent selective interpretation, not to satisfy a statistical ritual.

---

# Experimental Outcome

After validating runs and applying the preregistered analysis, assign the strongest justified scientific outcome.

## SUPPORTED

Use when the preregistered evidence criterion is satisfied and the protocol supports the claimed interpretation.

This does not establish universal truth.

## NOT SUPPORTED

Use when the evidence fails to reach the preregistered support criterion but does not directly contradict the hypothesis strongly enough to call it refuted.

This is not equivalent to:

```text
false
```

## REFUTED

Use when the experiment was explicitly capable of falsifying the hypothesis and the observed evidence satisfies the preregistered refutation criterion.

Use this term conservatively.

## INCONCLUSIVE

Use when the valid evidence cannot discriminate sufficiently.

Possible causes:

- high variance;
- weak effect;
- insufficient statistical power;
- competing interpretations;
- measurement limitation.

## NOT_TESTABLE

Use when preregistered testability conditions were not reached.

## INVALID

Use when protocol or apparatus failure prevents scientific interpretation.

---

# Two-Dimensional Outcome Model

Always distinguish:

```text
RUN VALIDITY
```

from:

```text
SCIENTIFIC OUTCOME
```

Examples:

```text
VALID + SUPPORTED
VALID + NOT SUPPORTED
VALID + REFUTED
VALID + INCONCLUSIVE
NOT_TESTABLE
INVALID
```

Do not collapse these categories.

---

# Scope Boundedness

A positive result is valid only within the tested conditions unless additional evidence supports broader generalization.

State explicitly where relevant:

- organism population;
- generation;
- seed range;
- world;
- body;
- embodiment;
- horizon;
- developmental stage;
- intervention;
- metric.

Do not claim:

```text
Symbiont learns X
```

when the experiment only establishes:

```text
Under protocol P, across seeds S, organisms using mechanism M showed outcome Y relative to baseline B.
```

Prefer the strongest precise claim supported by evidence.

---

# Held-Out Integrity

Held-out evaluation exists to measure behavior under conditions protected from tuning.

Therefore:

- do not inspect held-out internals during routine development;
- do not tune against held-out failures;
- do not adjust thresholds after seeing held-out results;
- do not reuse held-out conditions as exploratory data without explicitly retiring their held-out status.

Once held-out information influences development, it is no longer clean held-out evidence for the same question.

Preserve that provenance.

---

# Reproducibility

Record enough information for another researcher to rerun or evaluate the experiment.

Where relevant preserve:

- Git revision;
- protocol revision;
- runner version;
- seeds;
- initial state;
- organism identity;
- world;
- body;
- embodiment;
- horizon;
- metric definitions;
- thresholds;
- exclusions;
- stopping rules;
- runtime configuration;
- output artifacts.

Do not claim reproducibility if required execution state is missing.

---

# Experimental Report

A substantial experiment SHOULD produce a report containing:

```markdown
# Scientific Experiment: [Title]

## 1. Research Question

Exact empirical question.

## 2. Regime

EXPLORATORY / CONFIRMATORY / HELD-OUT

## 3. Preregistered Protocol

- hypotheses;
- intervention;
- controls;
- seeds;
- horizon;
- metrics;
- analysis plan;
- decision criteria;
- stopping rules;
- testability criteria.

## 4. Execution Provenance

- revision;
- runtime configuration;
- artifacts;
- deviations.

## 5. Run Validity

- VALID;
- NOT_TESTABLE;
- INVALID.

Explain invalid or not-testable runs.

## 6. Results

Report observations without interpretation first.

Include:
- per-arm results;
- seed-level behavior;
- aggregates;
- uncertainty;
- relevant effect sizes.

## 7. Scientific Outcome

One of:

- SUPPORTED;
- NOT SUPPORTED;
- REFUTED;
- INCONCLUSIVE.

## 8. Scope and Limitations

State exactly where the result applies.

## 9. Protocol Deviations

List deviations and their consequences.

## 10. Follow-up Status

Distinguish:

- required replication;
- exploratory follow-up;
- confirmatory follow-up;
- held-out validation.
```

A small exploratory experiment MAY use a shorter report.

It must still preserve regime, evidence, validity and interpretation.

---

# Experimental Integrity Gate

Before declaring an experiment scientifically valid, verify:

- [ ] The experimental regime was declared before execution.
- [ ] Confirmatory or held-out hypotheses were preregistered.
- [ ] Seeds were selected according to the frozen protocol.
- [ ] Horizon and stopping rules were fixed where required.
- [ ] Analysis rules were defined before seeing the results.
- [ ] Testability criteria were defined.
- [ ] Control arms were appropriate to the question.
- [ ] Relevant conditions were matched across arms.
- [ ] Evaluator ground truth did not leak into the organism.
- [ ] No global reward or forbidden scalar objective was introduced.
- [ ] The organism was not modified to make the experiment pass.
- [ ] Negative results were preserved.
- [ ] `NOT_TESTABLE` runs were preserved.
- [ ] Invalid runs were not counted as evidence for or against the hypothesis.
- [ ] Protocol deviations were recorded.
- [ ] Held-out conditions remained uninspected during tuning.
- [ ] Outcome claims remain bounded to the tested conditions.
- [ ] Mechanics-test success was not confused with scientific support.
- [ ] Design register state is current.

If important conditions fail, downgrade or invalidate the scientific interpretation.

Do not hide the failure.

---

# Stop Rule

Stop the experiment lifecycle when one of the following occurs:

1. the preregistered campaign completes;
2. a preregistered stopping rule triggers;
3. all remaining runs are `NOT_TESTABLE`;
4. apparatus failure makes further runs invalid;
5. the protocol itself is discovered to be invalid;
6. the experiment requires redesign before further evidence can be interpreted.

Do not continue adding seeds or extending the horizon merely because the current result is inconvenient.

A redesigned experiment is a new protocol.

---

# Final Principle

The purpose of an experiment is not to obtain a positive result.

The purpose is to expose a scientific claim to a fair possibility of failure.

A valid result may be:

```text
SUPPORTED
```

or:

```text
NOT SUPPORTED
```

or:

```text
REFUTED
```

or:

```text
INCONCLUSIVE
```

or:

```text
NOT_TESTABLE
```

or:

```text
INVALID
```

Each outcome carries information.

Preserve it.

Do not tune retrospectively.

Do not rescue failed hypotheses with ad-hoc explanations.

Do not modify the organism to satisfy the experiment.

Do not confuse apparatus success with scientific success.

Freeze what must be frozen.

Measure what was declared.

Interpret only what the evidence supports.
