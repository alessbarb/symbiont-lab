# P11 — RidgePredictor Width-4 Solve Specialization

Status: implementation candidate  
Origin: valid P8 baseline after P10, 2026-09-28

## Evidence

After P10, the focused RidgePredictor benchmark improved to approximately 1.94x
versus the historical solver, but `RidgePredictor.predict()` remained the
largest project-owned self-time function in the valid P8 profile.

The remaining cost was no longer normal-equation assembly alone. Every width-4
prediction still executed generic Python loops for:

- pivot search;
- row normalization;
- elimination of the other rows;
- temporary list creation and `zip()` traversal.

## P11

P11 specializes only the solve stage for the production shape:

```text
3 features + intercept = width 4
```

The generic solver remains unchanged for every other width.

The width-4 path:

1. preserves the same column order;
2. chooses the same pivot as `max(range(...), key=abs)`, including first-wins
   tie behavior;
3. normalizes the same five row cells in the same arithmetic form;
4. eliminates the same rows in the same order;
5. evaluates each cell as the same `a - factor * b` expression;
6. keeps the final built-in `sum()` dot product unchanged.

No sliding aggregate matrix is introduced, because removing old rows from an
aggregate would alter floating-point associativity.

## Exactness

The existing P9 legacy-comparison test still exercises deterministic random
width-4 histories with exact Python float equality.

P11 adds explicit coverage for:

- an exact pivot tie where the historical `max()` must retain the first row;
- a non-width-4 predictor proving the generic solver path remains unchanged.

Checkpoint format and restore semantics are untouched.

## Scientific boundary

P11 changes dispatch overhead only. It does not alter:

- evidence;
- history length;
- prediction frequency;
- model form;
- regularization;
- censoring;
- outputs;
- downstream cognition.
