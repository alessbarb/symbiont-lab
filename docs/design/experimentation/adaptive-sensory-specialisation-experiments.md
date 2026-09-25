---
id: design.general.adaptive-sensory-specialisation-experiments
title: "Adaptive Sensory Specialisation Experiments"
document_type: design
domain: experimentation
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Adaptive Sensory Specialisation — Experimental Specification

**Status:** preregistration design  
**Depends on:** `adaptive-sensory-system.md`, `adaptive-sensory-system-integration.md`  
**Purpose:** demonstrate or refute genuine perceptual specialisation

## 1. Scientific question

The central hypothesis is not:

> Symbiont can have several sensors.

It is:

> Starting from equivalent external sources and without receiving external semantics, a Symbiont can develop functionally distinct perceptual transformations that capture different regularities and causally improve downstream performance.

A second hypothesis is:

> Modalities with different transduction constraints can occupy different perceptual niches under different environmental pressures.

## 2. Claims explicitly not made

A positive result does not demonstrate:

- vision, smell or other biological senses;
- phenomenal experience;
- consciousness;
- semantic understanding of a source;
- general intelligence;
- open-ended evolution;
- optimal sensory organization.

It demonstrates adaptive perceptual specialisation only within the declared search space.

## 3. Evaluator separation

Experimental truth lives exclusively in `symbiont_lab`.

The organism never receives:

```text
target transform type
environment label
expected sensor role
correct modality
cross-organism fitness rank
ground-truth predictive variable
human sensor names
```

Labels such as `fast`, `slow`, `delta`, `integrative` or `multichannel` are evaluator-only descriptions.

## 4. Experiment layout

Add:

```text
experiments/perception/
```

with studies under:

```text
src/symbiont_lab/studies/perception/
```

Canonical sequence:

```text
01 identity-equivalence
02 adaptive-delta-discovery
03 temporal-scale-specialisation
04 modality-specialisation
05 sensory-duplication-divergence
06 sensory-ablation
07 multisource-specialisation
08 same-world-phenotype-divergence
09 autonomous-sensory-selection
10 sensory-regime-reversal
11 sensory-null-selection
12 experience-conditioned-phenotype
```

Each study contains its preregistered `experiment.toml` and a short
`README.md`. A `results.json` is created only after a real successful
execution; an unexecuted study must not ship a fabricated or placeholder
result. Preregistered tests bind protocol and document to the runner.

## 5. Study 01 — identity equivalence

### Purpose

Show that inserting `SensorySystem` without plasticity does not create capability changes.

### Conditions

```text
A legacy path
B identity sensory path
```

### Required equivalence

With the same seed and inputs:

- equivalent source selection;
- equivalent percept values;
- equivalent `SENSE` activations within declared tolerance;
- equivalent predictions;
- equivalent cognitive changes;
- identical `SignalKnowledge` meaning;
- equivalent replay.

### Gate

If B materially changes behavior, sensory plasticity does not open.

## 6. Study 02 — adaptive delta discovery

### Environment

A scalar source exists:

[
x_t
]

The future target depends on:

[
d_t=x_t-x_{t-1}
]

The organism never receives (d_t) directly.

### Conditions

```text
A raw source → cognition
B frozen identity sensor
C adaptive parameter sensor
D duplication + adaptive divergence
```

### Positive evidence

C or D must improve out-of-sample performance over A/B in prediction loss and/or adaptation speed without an offsetting resource explosion.

### Stronger evidence

The evaluator reconstructs that an emergent sensor responds to (d_t), despite the organism never receiving the concept “difference”.

That interpretation must never feed back into the organism.

## 7. Study 03 — temporal scale specialisation

### Environment

A single source contains two simultaneously useful predictive structures:

[
F_{fast}(x)
]

and:

[
F_{slow}(x)
]

A single temporal filter is insufficient to optimize both.

### Hypothesis

Duplication yields at least two persistent sensors over the same signal:

```text
signal.x
 ├── sensor.a
 └── sensor.b
```

with functionally different temporal responses.

### Required evidence

- both survive beyond maturity;
- ablating A preferentially degrades one target dimension;
- ablating B preferentially degrades the other;
- ablating both degrades both;
- A/B redundancy is not maximal;
- the benefit exceeds added cost.

This is the first strong evidence for:

[
1 signal \rightarrow N useful perceptions
]

## 8. Study 04 — modality specialisation

### Modalities

Use at least three opaque modalities with different structural constraints.

Evaluator-side interpretation may describe them as:

```text
alpha: short temporal / high frequency
beta: long integration
gamma: bounded channel mixing
```

The organism never sees those labels.

### Environments

```text
E1 rapid-regime
E2 slow-integrative
E3 distributed-cue
```

### Hypothesis

Useful modality occupancy or contribution depends systematically on environment:

[
P(M|E_1)\neq P(M|E_2)\neq P(M|E_3)
]

### Controls

- modalities available but frozen;
- one universal modality;
- random allocation matched for cost;
- fully adaptive modalities.

### Gate

A change in sensor count is insufficient. Functional contribution by modality must change.

## 9. Study 05 — duplication and divergence

### Purpose

Separate genuine specialisation from random proliferation.

### Required sequence

Record:

```text
parent
→ duplication event
→ divergence
→ maturity
→ functional evaluation
→ survive/prune
```

### Positive evidence

A preregistered fraction of duplication events yields non-redundant branches whose incremental contribution exceeds their resource cost.

### Failure signal

If most duplicates survive despite strong redundancy, fitness/pruning is not working.

## 10. Study 06 — sensory ablation

Causality is mandatory.

For each candidate specialised sensor compare:

```text
baseline intact
target sensor silenced
matched random sensor silenced
source removed
```

A sensor counts as functionally specialised only when:

[
\Delta performance_{targeted\ ablation}
>
\Delta performance_{matched\ control}
]

reproducibly.

Function is never inferred from visual inspection of the transduction DAG alone.

## 11. Study 07 — multisource specialisation

Do not run canonically before studies 02–06 close.

### Environment

Two sources exist:

[
x_t, y_t
]

Each is individually weak.

Useful information lies in:

[
g(x_t,y_t)
]

### Conditions

```text
single-source only
multi-source frozen
multi-source adaptive
```

### Gate

The adaptive multisource treatment must discover a useful combination without the evaluator supplying the correct source pair.

All candidate opportunities must be accounted for to prevent structural cherry-picking.

## 12. Study 08 — same-world phenotype divergence

### Setup

Multiple organisms share:

- the same genome;
- the same world;
- the same available sources;
- only protocol-authorized internal stochastic variation.

### Measures

Compare `SensoryPhenotype` through:

```text
sensor count
modality occupancy
source coverage
transduction topology distance
functional response distance
downstream contribution
```

### Question

Can organisms develop different perceptual solutions in the same world while retaining comparable utility?

Convergence is also an informative result and must not be treated as failure by default.

## 13. Metrics

### Sensory diversity

Structural diversity among active sensors.

### Source coverage

[
Coverage=
\frac{sources\ with\ useful\ sensors}
{available\ sources}
]

### Perceptual redundancy

Information overlap among sensor outputs.

### Sensory efficiency

[
Efficiency=
\frac{incremental\ downstream\ utility}
{acquisition+transduction\ cost}
]

### Specialisation index

Measures whether sensors/modalities contribute differently across tasks or regimes, not merely whether their parameters differ.

### Perceptual expansion

[
Expansion=
\frac{effective\ useful\ perceptual\ dimensions}
{raw\ source\ dimensions}
]

Values above one count only when added dimensions show causal, non-redundant utility.

### Phenotype distance

Distance between sensory systems based on topology, modality, functional response and source binding. Sensor IDs themselves are not a meaningful distance metric.

## 14. Baselines

Every specialisation study includes at least:

```text
raw direct cognition
identity sensors
frozen heterogeneous sensors
random plasticity
adaptive plasticity
```

Where relevant also compare:

```text
single modality
multiple modalities
```

Improvement over a deliberately weak baseline is insufficient. The adaptive treatment must be compared against the strongest preregistered trivial control.

## 15. Costs

Every result reports:

```text
acquisition cost
transduction cost
attention cost
sensor count
mutation count
checkpoint size
runtime overhead
```

Predictive improvement achieved through uncontrolled structural growth is not a positive result.

## 16. Mutation accounting

Each sensory mutation records:

```text
mutation_id
tick
sensor_id
parent_ids
kind
pre_digest
post_digest
cost
```

Initial mutation kinds:

```text
parameter_adjust
duplicate
parameter_diverge
transduction_add
transduction_remove
source_rewire
prune
```

The mutation log never stores raw signal values.

## 17. Negative controls

Studies must include environments where no exploitable structure exists, such as:

```text
independent white noise
permuted target
random phase
source-target decoupled
```

Expected behavior includes:

- no persistent sensor proliferation;
- no persistent predictive utility;
- increased pruning;
- no systematic false “specialised” classification.

A system that always discovers specialisation is overfitting.

## 18. Stability tests

Evaluate at least:

- regime shifts;
- source disappearance;
- source reappearance;
- degraded sensors;
- temporarily expensive modalities;
- checkpoint restoration;
- noise;
- missing samples;
- scale changes.

A changed `source_id` is never automatically treated as continuity.

## 19. Replay and restoration

Two contracts are tested.

### Structural replay

Same checkpoint plus same inputs yields the same structure and same decisions.

### Functional continuation

After restore, sensors with explicitly persisted temporal state continue within documented semantics.

If temporal state is deliberately discarded, the discontinuity is marked and contaminated experimental windows are excluded.

## 20. Observatory scientific views

Observatory must passively expose:

```text
source → sensors → SENSE → concepts
```

and bounded sensor state:

```text
sensor lineage
maturity
cost
health
confidence
utility
redundancy
modality
```

Evaluator interpretations such as “slow integrator” must never be shown as organism self-knowledge.

If exposed to researchers they are explicitly labeled evaluator-side interpretation and kept outside Self view.

## 20b. Study 09 — autonomous sensory selection

Given several bounded candidate transforms with no evaluator label, organism-side
evidence must select the receptor carrying the strongest useful predictive
information. The candidate set is identical across adaptive, frozen and random
controls. Evaluator ranking happens only after the organism has formed its own
utility ordering.

## 20c. Study 10 — sensory regime reversal

The world changes from a fast-change regime to a slow-integrative regime.
Positive evidence requires a finite, evaluator-free change in preferred receptor
from the previously useful transform to the newly useful transform.

## 20d. Study 11 — sensory null selection

Driver and outcome are independent white noise. Predictive credit is awarded
only when a receptor beats the strongest trivial local baseline: running mean or
persistence. Merely beating persistence is explicitly insufficient.

## 20e. Study 12 — experience-conditioned phenotype

Organisms share latent world and constitution but receive small authorized
differences in sensory noise. Convergence and divergence are both valid
characterization outcomes; the study asks whether microexperience can influence
preferred sensory phenotype once selection is endogenous.

## 21. Closure criteria — Sensory Plasticity v1

The capability is not closed merely because code and tests exist.

Closure requires all of:

1. identity-bridge equivalence;
2. positive adaptive-delta result versus controls;
3. temporal specialisation with at least two useful perceptions from one source;
4. positive causal ablation;
5. negative controls without persistent false specialisation;
6. bounded costs;
7. valid checkpoint/replay;
8. passive Observatory;
9. structural absence of human semantics in learning;
10. reproducibility under preregistered seeds;
11. autonomous receptor selection against frozen/random controls;
12. regime reversal without evaluator intervention;
13. negative-control rejection of strong false specialisation.

## 22. Closure criteria — Sensory Modalities v1

Close separately when:

1. at least two modalities are structurally non-equivalent;
2. environment alters their functional occupancy or contribution;
3. the effect is not explained solely by parameter count;
4. modality ablation yields specific degradation;
5. frozen/random controls do not reproduce the effect;
6. organism receives no modality/environment labels.

Only then is the following claim warranted:

> Symbiont developed environment-conditioned perceptual specialisation within the declared sensory space.

## 23. Future work explicitly deferred

Out of scope for v1:

```text
inheritance of acquired sensors
evolution of new primitives
creation of new modalities during life
cross-organism sensory transfer
social transmission of perceptual strategies
SLM-guided perception
operator naming of sensors
semantic grounding of modality function
active sensing / host intervention
```

Each requires its own design and study.

## 24. Research interpretation

The line separates:

```text
existence discovery
        ↓
signal knowledge
        ↓
perceptual development
        ↓
sensory specialisation
        ↓
concept formation
```

This makes four questions experimentally distinct:

1. Does the world contain information?
2. Can the organism access it?
3. Has it developed a useful way to perceive it?
4. Has cognition discovered regularities over that perception?

That separation is the scientific core of this specification.
