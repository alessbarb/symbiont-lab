---
id: explanation.web.04-atencion-y-decision
title: "04 Attention And Decision"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Attention and decision

<a id="que-es"></a>

## What it is

A Symbiont has a finite observation budget per tick: it cannot sample all its senses at once with maximum resolution. Attention decides what to allocate limited observation to, and beliefs decide how that observation revises what the organism already holds as probable — without either layer ever receiving the evaluator's ground truth label.

<a id="mecanismo"></a>

## Mechanism

According to ADR-0003, attention is a limited resource optimization mechanism, explicitly **not** a classification judgment nor a threat detection. Each sensory candidate receives a dimensionless uncertainty (coefficient of variation); if the sensor has not yet completed its minimum reacclimation, its uncertainty is fixed at infinity, which guarantees that exploring unknown signals always wins against refining already established signals. The score of each candidate combines that uncertainty with a diminishing returns weighting (the more observations a sensor already has, the less urgent it is to keep insisting) and is divided by the physical cost of sampling it and by a separate ranking cost —deliberately decoupled, so that penalizing a sensor's position in the ranking does not alter how much real physical budget it consumes. The final allocation resolves a greedy 0/1 knapsack heuristic over a fixed maximum budget.

Beliefs are updated in a Bayesian manner with pseudo-observations: the accumulated evidence has an explicit upper bound that prevents epistemic paralysis — the organism always retains the capacity to revise a belief if the evidence changes drastically, no matter how many prior confirmations it had. When a batch of readings significantly disagrees with the baseline, the contradiction is not smoothed over: an immutable dissent record is generated. In persistent checkpoints only bounded counters of those conflicts are saved, never the raw numerical values that originated them — the epistemic fact that a belief was refuted survives the restart; the host data that refuted it does not.

<a id="implementado"></a>

## What is implemented

- Uncertainty calculation by coefficient of variation with infinite priority for non-acclimated sensors — **[implemented]**.
- Attention allocation by greedy knapsack with fixed budget and ranking-cost / physical-cost decoupling — **[implemented]**.
- Bayesian belief revision with bounded evidence cap — **[implemented]**.
- Explicit preservation of dissent (`DissentRecord`) without smoothing — **[implemented]**.

<a id="evidencia"></a>

## Evidence

It is directly proven that an infinite uncertainty always wins over any finite uncertainty in attention allocation. Belief revision strengthens certainty with repeated evidence without ever receiving an external truth label — the test builds the belief model and feeds it only with observations, not with evaluator truth. And conflicting evidence effectively revises the belief while recording the conflict, instead of silently discarding it.

<a id="abierto"></a>

## What remains open (of this mechanism)

- The concrete weights of the scoring function (0.65/0.35, the diminishing returns exponent) are engineering choices documented as heuristics in the mathematical compendium, not demonstrated optimal derivations.
- The collective consensus among multiple organisms that share evidence (chapter 6 of the mathematical compendium) is covered in chapter 7 of this series (ecology and sociability), not here.

<a id="respaldo-formal"></a>

## Formal backing

The greedy Dantzig heuristic for the 0/1 knapsack, the coefficient of variation as a dimensionless dispersion measure, and the formal decoupling between ranking cost and physical cost are in [`docs/math/04-atencion-causal-y-presupuestos.md`](../math/04-atencion-causal-y-presupuestos.md).
The Bayesian update with pseudo-observations, bounded evidence saturation and the dissent Z-test are in [`docs/math/05-creencias-bayesianas-y-disidencia.md`](../math/05-creencias-bayesianas-y-disidencia.md).
Collective consensus without an external oracle is in [`docs/math/06-consenso-colectivo-y-confianza.md`](../math/06-consenso-colectivo-y-confianza.md).
