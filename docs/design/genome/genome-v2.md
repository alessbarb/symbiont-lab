---
id: design.genome.genome-v2
title: "Genome V2"
document_type: design
domain: genome
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Genome v2 — implemented architecture

**Status:** implemented in core and main adapters  
**Purpose:** separate genotype, expression, development, experience, and embodiment as distinct causal mechanisms.

## Invariants

1. There is a single operative genetic representation: `symbiont.genetics.Genome`.
2. `genotype_hash` identifies genetic content; genealogy and reproduction identity live outside the genotype.
3. The body does not modify the Genome and the Genome does not contain anatomy, number of actuators, bodily health, or age.
4. `KernelLimits` remains an external, non-heritable computational ceiling.
5. Inherited capacity is a developable ceiling; effective graph capacity grows during ontogeny.
6. `GeneExpressionState` is acquired lifetime state, persistent but not heritable.
7. Evidence observed up to tick t can only modify the effective expression of tick t+1.
8. There is no second metaplasticity regulator: `ExpressionRegulator` is the canonical path.
9. Acquired epigenetics is disabled by default and only exists under an explicit `EpigeneticProtocol`.
10. No canonical locus exists without an auditable binding to a consumer, observable projection, and causal test.
11. Re-embodiment preserves Genome and general cognition, but motor knowledge remains scoped to the opaque contract of the body.
12. A `MotorPrimitive` is only valid over the `ActuatorSurface.contract_fingerprint` in which it was learned.

## Causal flow

```text
Genome
  |
  v
ExpressionState(t)
  |
  +--> cognition / plasticity / structural development
  |
  +--> exploration
  |
  v
action A(t)
  |
  v
body + environment
  |
  v
observation S(t+1)
  |
  +--> prediction error
  +--> novelty
  +--> controllability loss
  +--> body-model contradiction
  +--> resource pressure
  |
  v
RegulatorySignals(t+1)
  |
  v
ExpressionState(t+1)
```

The technical fingerprint of the body contract does **not** enter `RegulatorySignals`. It is only used for security, persistence, and motor knowledge compatibility.

## Canonical genetic families

### Development

- `soft_node_budget`
- `soft_edge_budget`
- `sense_node_budget`
- `capacity_growth_sensitivity`
- `consolidation_interval_ticks`

The budgets are ontogenetic ceilings, not capacity granted at birth.

### Plasticity

- adaptive range of `learning_rate`
- `eligibility_decay`
- adaptive range of `structural_plasticity`

### Regulation

- `uncertainty_gain`
- `novelty_gain`
- `prediction_error_gain`
- `controllability_loss_gain`
- `embodiment_mismatch_gain`
- `regulation_smoothing`
- `regulation_decay`

### Sensorimotor

- `spontaneous_activity_baseline`
- `uncertainty_exploration_gain`
- `prediction_error_exploration_gain`
- `exploration_habituation`
- `reacclimation_sensitivity`

### Structure

- adaptive range of `growth_threshold`
- adaptive range of `pruning_threshold`
- `minimum_support`
- `tentative_lifetime_ticks`

### Evolvability

- mutation multiplier per family
- `recombination_linkage`

The effective mutation scale is:

```text
schema mutation scale
x
inherited family multiplier
```

Recombination groups belong to the schema; the heritable propensity to keep them or break them belongs to the Genome.

## Deliberately excluded loci

Genome v2 does not yet include:

- adaptive forgetting-rate;
- adaptive consolidation-sensitivity;
- genetic contingency window/sensitivity;
- genetic controllability sensitivity;
- genetic body-schema adaptation rate;
- genetic complexity pressure;
- epigenetic parameters as genes.

These ideas remain outside the schema because they do not yet have a single, verifiable causal consumer in the current runtime. They will be incorporated only when a mechanism, telemetry, and ablation study exist.

## Body and actuation

`ActuatorSurface` belongs to the embodiment.

```text
Body
  |
  v
ActuatorSurface
  |- opaque actuator ids
  |- physical cost/health/threshold
  '- contract_fingerprint
        |
        v
     Symbiont
```

There is no:

```text
Body -> MotorGenes -> Genome
```

`MotorGenes` remains solely as a fail-fast constructor to detect legacy callers.

## Persistence

Checkpoint separates:

```text
genome
gene_expression
germline
acquired cognition
body-owned actuation surface
embodiment-scoped sensorimotor knowledge
```

Genome v1 checkpoints are verified with their historical hash before being migrated. Historical `HeritableGenome` is projected only once onto v2 loci that still have causal meaning; the rest are discarded instead of becoming dead configuration.

Sensorimotor v10 adds `embodiment_fingerprint`. v9 checkpoints can be bound only once to an already validated current body. Pre-v9 fails closed.

## Re-embodiment

Change A -> B:

- Genome remains identical.
- Genealogy remains identical.
- general experience/cognition remains.
- body state is reset according to the new embodiment.
- primitives from A no longer have authority over B.
- loss of prediction/controllability raises regulation and exploration endogenously.

Return B -> A:

- longitudinal memory only recovers hypotheses from the same lifecycle contract;
- each motor hypothesis must also match the motor-surface fingerprint;
- it returns as a historical hypothesis without authority and requires new evidence.

## Constitutional rule for new genes

A new locus only enters `DEFAULT_GENOME_SCHEMA` if it simultaneously has:

1. a causal consumer;
2. a unique binding in `canonical_gene_bindings()`;
3. observable telemetry/projection;
4. a mutation/causality test;
5. a falsifiable experimental hypothesis.

The existence of a biologically plausible idea is not enough to convert it into a gene.
