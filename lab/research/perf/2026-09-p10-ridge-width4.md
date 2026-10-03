# P10 — RidgePredictor Width-4 Hot Path

Status: implementation candidate  
Origin: valid P8 baseline after P9, 2026-09-28

## Evidence

The valid P8 baseline reports:

- overall validity: VALID;
- Observer OFF median: 6.3381 ms/tick;
- Observer ON median: 6.5919 ms/tick;
- observability tax: 4.00%;
- RidgePredictor focused benchmark after P9: only 1.043x;
- RidgePredictor.predict(): about 1.094 s self time across 6,000 calls.

P9 proved that row-product multiplication was not the dominant remaining cost.

## Current bottleneck

SignalKnowledgeEngine always constructs RidgePredictor inputs as three features:

1. target delta;
2. previous target delta;
3. source delta.

With the intercept, production prediction therefore solves a fixed width-4
normal equation.

The generic P9 implementation still rebuilt those 20 matrix cells with nested
Python loops for every historical row and every prediction.

At 64 rows and 6,000 predictions this is millions of Python-level loop
iterations even though the matrix shape is statically known.

## P10

For width == 4 only, matrix assembly is unrolled explicitly.

The optimization preserves exactly:

- historical row order;
- per-cell addition order;
- prepared outer-product values;
- prepared RHS values;
- regularization;
- pivot search;
- Gaussian elimination;
- final dot product.

No aggregate matrix is maintained across observations because sliding-window
subtraction would alter floating-point associativity and could break exact
historical outputs.

Other feature widths retain the generic loop implementation unchanged.

## Exactness

The existing P9 bit-exact regression compares optimized predictions against the
legacy solver after every observation on deterministic random histories using
Python float equality (==), not tolerance.

That test exercises the production width-4 path.

Checkpoint schema and restore behavior are unchanged.

## Scientific boundary

P10 changes only how identical arithmetic operations are dispatched in Python.
It does not change prediction frequency, history, model structure, evidence,
or outputs.
