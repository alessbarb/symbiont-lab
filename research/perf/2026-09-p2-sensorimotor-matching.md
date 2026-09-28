# P2 — Deterministic sensorimotor matching optimization

Status: implementation candidate  
Base: P1 observability boundary on `main`

## Goal

Reduce the dominant motor-sequence recurrence cost without changing which
primitive sequence wins for any valid input.

## Changes

### 1. Allocation-light pattern distance

The previous implementation rebuilt two dictionaries, two sets, their union and
a list of per-step distances for every candidate comparison.

Current organism-generated motor patterns are canonical tuples sorted by opaque
actuator id. P2 uses a two-pointer linear merge over those tuples and computes
the same:

- union cardinality;
- support symmetric difference;
- quantized amplitude difference;
- max(amplitude distance, support distance).

No anatomy or semantics are introduced.

### 2. Historical compatibility

Checkpoint restore accepts unique actuator ids even when their order is not
canonical. Such valid historical inputs keep the previous map/set
order-insensitive formula as a fallback. The normal runtime-generated path uses
the allocation-light merge.

### 3. Deterministic argmin

`_matched_primitive_sequence` no longer sorts the entire candidate pool.

It scans candidates once and preserves the exact previous ordering rule:

```
(distance, MotorSequence lexical order)
```

Therefore equal-distance candidates still resolve to the lexicographically
smallest canonical sequence, independent of dictionary insertion order.

## Verification

Focused unit tests lock:

- exact equality with the pre-P2 distance formula;
- dense-support behavior;
- unordered historical checkpoint semantics;
- deterministic lexicographic tie-breaking;
- unchanged threshold behavior.

`scripts/bench_sensorimotor_matching.py` compares the old reference formula
against the optimized implementation on the same deterministic pool, verifies
distance/winner equivalence first, then reports timing.

The P0 whole-organism causal gate remains the higher-level acceptance contract.
