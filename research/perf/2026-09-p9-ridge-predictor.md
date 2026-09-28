# P9 — Ridge Predictor Exact Precomputation

Status: implementation candidate  
Origin: corrected P8 profile, 2026-09-28

## Evidence

The second P8 full profile reported `RidgePredictor.predict()` as the largest
individual project-owned self-time function:

- 6,000 calls in 600 profiled ticks;
- approximately 1.129 seconds self time headless;
- approximately 1.159 seconds self time with Observer ON.

The predictor is genuine cognition. P9 therefore does **not** lower prediction
frequency, shorten history, change regularization, skip candidate pairs or
replace the regression model.

## Existing cost

For every prediction, the previous implementation rebuilt the normal equations
from as many as 64 historical rows.

For each row it repeatedly:

1. allocated the intercept-augmented vector `z`;
2. recomputed every `z[i] * z[j]` outer-product term;
3. recomputed every `z[i] * target` right-hand-side term.

Historical rows are immutable between their insertion and eviction, so those
multiplications are invariants of the row.

## P9

`observe()` now precomputes, once per accepted row:

- its flattened outer product;
- its right-hand-side products.

Both are stored in a bounded deque aligned with the existing bounded row deque.

`predict()` reconstructs the same normal-equation matrix in the same row,
index and addition order, but adds the precomputed products rather than
multiplying them again.

The following remain unchanged:

- 64-row maximum history;
- feature values;
- target values;
- intercept;
- ridge regularization;
- matrix accumulation order;
- Gaussian pivot selection;
- elimination order;
- final dot-product calculation;
- checkpoint schema and contents.

The precomputed values are volatile implementation state and are reconstructed
through ordinary `observe()` during checkpoint restore.

## Exactness gate

Tests compare the optimized predictor to an embedded copy of the legacy solver
after every observation across deterministic random histories and require
Python float equality with `==`, not tolerance.

Checkpoint round-trip predictions and checkpoint payloads must also remain
exactly identical.

`scripts/bench_ridge_predictor.py` performs the same exact-output check before
timing legacy and P9 prediction paths.

## Scientific boundary

This is computational common-subexpression elimination only.

P9 must not alter what the organism can predict, which evidence it learns from,
when it predicts, or how prediction evidence affects knowledge claims.
