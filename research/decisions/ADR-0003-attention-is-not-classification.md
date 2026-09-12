# ADR-0003: Attention is Not Classification

## Status
Accepted

## Context
Attention allocation is a selection mechanism under resource constraints (e.g. allocating inspection budgets), distinct from the decision of classifying an event as benign or pathogen. Conflating selection with classification muddles evaluation metrics and creates false trade-offs.

## Decision
Separate attention allocation metrics (recall of threat events within allocated budget, selection efficiency) from downstream agent classification metrics (precision, recall, Brier score, calibration ECE).

## Consequences
- Evaluation records distinct metric blocks: `attention` vs `classification`.
- Selective filters can be analyzed under fixed budgets independently of downstream classifier thresholds.

## Introduced in
v0.22.0
