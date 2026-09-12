# ADR-0002: Synthetic Ground Truth Isolation

## Status

Accepted

## Context

A simulator evaluates whether agent decisions and hypotheses match synthetic reality (benign vs pathogen, real threat level, regime shift). If ground truth leaks into agent decision functions, experimental validity is destroyed.

## Decision

Ground truth belongs exclusively to the simulator and evaluator. `Observation` (sensory signal) is separated from `EvaluationEvent` (evaluator ground truth). Cognitive layers (`Agent`, `CollectiveMemory`, `ReasoningEngine`) only receive `Observation` instances and local/collective beliefs.

## Consequences

- Ground truth cannot leak into agent heuristics.
- Evaluator metrics cannot feedback into agent decisions.

## Introduced in

v0.1.0 (Formalized in v0.25.0)

## Evidence

`tests/experimental_integrity/test_ground_truth_boundary.py`
