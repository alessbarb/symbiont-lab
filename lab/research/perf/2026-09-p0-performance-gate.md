# P0 — Performance Optimization Gate

Status: implementation baseline  
Baseline commit: `e8f5c60f0ec471246f9e3015fcb8eb5984d2bd8c`

## Purpose

P0 turns the performance roadmap into a reproducible acceptance contract before
any hot-path optimization begins.  It deliberately separates two questions:

1. **Did behavior change?** This is deterministic and belongs in pytest.
2. **Did throughput improve?** This is empirical and belongs in controlled
   benchmarks, not a wall-clock CI assertion.

This prevents a faster implementation from being accepted if it changes the
organism, and prevents noisy host timing from creating false CI failures.

## Deterministic gate

`lab/tests/experimental_integrity/test_performance_optimization_gate.py` runs
matched organisms with the same opaque body, seed and tick schedule.

The trace compares, tick by tick:

- `state_hash()`;
- motor intents and delivered actuations;
- causal provenance events;
- sensorimotor competence candidates;
- available competence IDs;
- representation maturity.

A second arm compares **Observer OFF** with **Observer ON**.  The observed twin
executes passive reads after each decision and before the same body consequence
is applied to both twins.  Passive observation must leave `state_hash()`
unchanged and the next causal future must remain identical.

The test therefore operationalizes gate dimensions 1, 2, 3, 5 and 6.  Resource
acquisition equality remains covered by world/physics integration tests until a
canonical resource-bearing fixture is added to this harness; P0 does not invent
a fake resource path merely to make the matrix look complete.

## Timing baseline

Run:

```bash
python scripts/bench_observability_tax.py --ticks 500 --repeats 5 --seed 127
```

The benchmark reports median ms/tick for Observer OFF and Observer ON plus the
absolute and percentage observability tax.  The result is intentionally not a
pytest threshold: host scheduling, CPU frequency and concurrent load make such
assertions unstable.

P1 acceptance should use the same command before and after the change and
preserve the deterministic gate above.

## Merge rule for P1–P8

A performance change is acceptable only when:

1. the deterministic P0 gate remains green;
2. the focused tests for the changed subsystem remain green;
3. the controlled benchmark is re-run from a fresh matched subject;
4. any claimed speedup is reported from measured runs, not summed profiler
   percentages;
5. the optimization does not reduce learning frequency, evidence collection,
   plasticity, prediction work or any other genuine organism mechanism merely
   to improve throughput.

P0 itself changes no organism runtime behavior.
