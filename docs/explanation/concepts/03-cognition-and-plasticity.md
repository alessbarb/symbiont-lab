---
id: explanation.web.03-cognicion-y-plasticidad
title: "03 Cognition And Plasticity"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Cognition and plasticity

<a id="que-es"></a>

## What it is

A Symbiont's cognition is a recurrent neural graph that changes its own structure and weights with experience, without any external process generating, editing or injecting code. The organism does not learn "what to do" against an external truth label: it learns to predict its own sensory stream, and that predictive capacity is the learning signal.

<a id="mecanismo"></a>

## Mechanism

The graph operates on a closed catalog of node types — `SENSE`, `CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT` — and edge types — `EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`. Deliberately there is no `ACTION` node: `READOUT` readings feed external circuits, but the graph never executes a system action on its own. Weights, plasticity and time scales are bounded by fixed range (`w ∈ [-2.0, 2.0]`, for example), and `KernelLimits` imposes hard limits on nodes, concepts and edges — already described in chapter 1 as the immutable kernel under which any phenotype develops.

Activation is synchronous and double-buffered: each node reads only from the current tick or the already frozen previous frame, never from a half-calculated state in the same tick — this eliminates circular dependencies and makes the result not depend on the order in which nodes and edges were built.

Learning is label-free. `PREDICTOR` nodes are trained against Huber loss (quadratic near zero, linear far away, so as not to let a large error dominate the update). Weights are adjusted with an Oja rule modulated by sensory availability and health, which avoids Hebbian weight explosion without needing explicit global normalization. Before a predictive candidate enters the active graph, it is evaluated in shadow mode comparing its loss against a trivial persistence baseline — it is only promoted after accumulating evidence of sustained gain, never automatically.

Metaplasticity decides whether a structural adaptation is consolidated by evaluating a five-objective vector (prediction error, representation cost, instability, retained information, calibration) under Pareto dominance. Three consecutive failures trigger a safe mode that freezes any hyperparameter change until someone explicitly acknowledges it.

<a id="implementado"></a>

## What is implemented

- Closed catalog of nodes/edges and kernel limits — **[implemented]**.
- Deterministic double-buffered activation, independent of build order — **[implemented]**.
- Label-free learning via Huber loss and modulated Oja rule — **[implemented]**.
- Predictor life cycle in shadow mode (`candidate` → `supported` / `retired`) with explicit promotion, never automatic by the evaluator — **[implemented] [evaluator-only]** in its longitudinal verification (the studies that exercise the full cycle live in the laboratory, outside the organism's cognition).
- Metaplasticity with Pareto objective and safe mode after consecutive failures — **[implemented]**.

<a id="evidencia"></a>

## Evidence

Independence regarding graph build order is verified by direct proof. The modulated Oja rule is proven in both directions: it does not move when it is frozen, not eligible, or the modulation is zero, and it does move the weight toward the correlated activity when all three conditions are met. The metaplasticity safe mode is explicitly proven: three consecutive failures activate it, and once active it is not released without an explicit reset action — there is no silent recovery.

<a id="abierto"></a>

## What remains open (of this mechanism)

- The promotion of a predictor from `candidate` to `supported` in the real runtime remains as an explicit and bounded operation; its generalization outside the synthetic regimes studied in the laboratory is not demonstrated — the roadmap itself declares it open.
- The five objectives of metaplasticity are an engineering design (Pareto heuristic), not a mathematical property demonstrated as optimal against other possible objective combinations.

<a id="respaldo-formal"></a>

## Formal backing

The causal delay activation dynamics, the discretized Oja rule, eligibility traces and the bounding invariant in `[-1, 1]` are formalized in [`docs/math/09-plasticidad-endogena-y-redes-recurrentes.md`](../math/09-plasticidad-endogena-y-redes-recurrentes.md).
The organism's self-model and the non-linear cost quantization are in [`docs/math/08-automodelo-y-sensores-adaptativos.md`](../math/08-automodelo-y-sensores-adaptativos.md), and agent cognition and metacognition in [`docs/math/07-cognicion-agentes-y-metacognicion.md`](../math/07-cognicion-agentes-y-metacognicion.md).
