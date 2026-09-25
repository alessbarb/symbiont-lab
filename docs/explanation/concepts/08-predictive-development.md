---
id: explanation.web.08-desarrollo-predictivo
title: "08 Predictive Development"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Predictive development

<a id="que-es"></a>

## What it is

Beyond reacting to what it perceives, a Symbiont can develop predictive hypotheses about its own sensory flow: candidates that attempt to anticipate a future value and undergo testing before counting for anything. No laboratory metric leaks to the organism as privileged semantics — the promotion of a candidate depends only on its performance against itself.

<a id="mecanismo"></a>

## Mechanism

A predictive candidate is evaluated in shadow mode, outside the active graph: it compares its loss against a trivial persistence baseline (predicting that the next value will equal the previous one). If it accumulates eight samples with strictly positive gain, it transitions to `supported`; if in sixteen samples its performance remains below persistence, it transitions to `retired`. A `retired` candidate is not silently reactivated after a restart — its failure state persists. The promotion from `supported` to active predictor in the graph is always an explicit operation of the runtime, never an automatic decision triggered by the laboratory evaluator itself.

Structural plasticity (creation and pruning of nodes and edges) is bounded: the organism's memory usage is kept under control even after processing many different pairs over a long life, instead of growing boundlessly with residence time.

When the laboratory needs to select candidates in a continuous stream without knowing the full horizon of observations in advance, it uses a Treap structure (randomized binary tree with priorities) to maintain an online selection with expected logarithmic complexity — this lives exclusively in `symbiont_lab`, never in the organism's cognition.

<a id="implementado"></a>

## What is implemented

- Lifecycle of predictive candidates (`candidate → supported / contradicted → retired`) in shadow mode — **[implemented]**.
- Blocking of silent reactivation of a `retired` candidate after restart — **[implemented]**.
- Structural plasticity with bounded memory usage independently of the resident's duration — **[implemented]**.
- Causal streaming selection via Treap for laboratory statistical evaluation — **[implemented] [evaluator-only]**: exists only as a tool of `symbiont_lab`, never as a cognitive mechanism of the organism.

<a id="evidencia"></a>

## Evidence

It is directly proven that a predictive candidate without sustained gain is not promoted — the test constructs a candidate with performance equal to or worse than trivial persistence and confirms that it never reaches the promotable state. It is also proven that the structural reconciliation mechanism keeps memory growth bounded even when processing a large number of distinct pairs, instead of growing proportionally without limit.

<a id="abierto"></a>

## What remains open (from this mechanism)

- The real promotion of a predictor in the production runtime, beyond the longitudinal laboratory studies, remains an opt-in and bounded operation — there is no evidence of automatic generalization outside the studied synthetic regimes.
- The exact sample thresholds (8 for support, 16 for retirement) are engineering parameters documented as heuristic, not derived from an optimal stopping theory.

<a id="respaldo-formal"></a>

## Formal backing

The normative design of anti-capture attention, quantized persistence with exact zero, stranded concepts and shadow mode prediction is in
[`docs/design/sociabilidad-y-desarrollo-predictivo.md`](../design/sociabilidad-y-desarrollo-predictivo.md).
Causal streaming selection via Treaps, the Brier Score and Murphy's decomposition are formalized in
[`docs/math/10-seleccion-causal-y-evaluacion-estadistica.md`](../math/10-seleccion-causal-y-evaluacion-estadistica.md).
