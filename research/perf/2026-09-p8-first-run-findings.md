# P8 First Full Run — Findings and Corrections

Date: 2026-09-28  
Host: Python 3.12.3, Linux 7.0.0-34-generic x86_64  
Seed: 127  
Run mode: full

## Status

The first full P8 run produced useful subsystem evidence but is **not a valid
whole-system baseline**.

Three independent issues were discovered:

1. the causal-equivalence pytest file was deselected by the repository-wide
   default `-m "not slow"` configuration;
2. the P2 focused benchmark found a one-ULP difference in sequence-distance
   accumulation under Python 3.12;
3. the P7 2D spatial-bucket benchmark was slower than its brute-force reference
   at 2,000 nodes and the benchmark did not apply equal callback work to both
   arms.

A fourth apparent issue — Observer ON/OFF final hashes differing — came from the
P8 runner itself constructing the two subjects with different organism ids.
Those hashes were therefore not comparable.

## Evidence that remains useful

### Observability

The run measured:

- Observer OFF: 4.1565 ms/tick median;
- Observer ON: 4.3031 ms/tick median;
- observed-minus-headless: 0.1466 ms/tick, 3.53%.

This is consistent with P1 materially reducing the pre-program observability
tax. It must still be re-measured after the corrected matched-id run.

### World journal

At 1,000 versus 100,000 accumulated events:

- indexed current-tick lookup remained approximately 0.145–0.176 microseconds;
- bounded tail remained approximately 0.397–0.434 microseconds;
- indexed page remained approximately 0.800–0.905 microseconds;
- full replay current-tick reference grew from approximately 15.7 microseconds
  to 4,474.9 microseconds.

This is strong evidence that P3 removed age-dependent journal work from the live
bounded-access path.

### SSE

For 10,000 approximately 4 KiB payloads:

- legacy framing: 0.0643 s;
- P6 framing: 0.0311 s;
- speedup: 2.07x.

Wire reduction was only 0.437%, as expected: P6 primarily removes CPU/parsing
and write overhead. P5 owns payload-size reduction.

### Organism scaling

The separate canonical tick benchmark reported:

- 1 organism: 1.9059 ms/tick, 524.7 ticks/s;
- 10 organisms: 2.2758 ms/tick/organism, 439.4 aggregate-equivalent ticks/s.

This remains useful scaling evidence, although it exercises a different
canonical benchmark subject than the P8 CausalBody profile.

## P2 correction

The P2 allocation-light per-pattern distance is mathematically identical to the
historical formula.

The failing benchmark was caused by sequence aggregation:

- historical implementation: `sum(step_distances)`;
- P2 implementation: repeated `total += distance`.

Python 3.12's built-in `sum` for float iterables can produce a result one ULP
different from manual incremental accumulation.

P2 now keeps the allocation-light pattern distance and deterministic O(N)
candidate argmin while restoring built-in `sum` at the four-step sequence
boundary.

A regression test reproduces the benchmark seed and requires exact equality.

## P7 correction

The first P7 benchmark at 2,000 nodes measured the spatial index slower than
brute force.

The renderer now uses an adaptive strategy:

- small/medium graphs: direct pair loop;
- larger graphs: spatial buckets.

The bucket path now stores integer node indexes instead of repeated object-index
Map lookups and uses cells at least as large as the interaction radius, reducing
neighbour-cell probing to 3x3 in 2D and 3x3x3 in 3D.

The benchmark now applies the same callback work to brute-force and adaptive
arms.

## P8 runner correction

The corrected runner:

- uses the same organism id for Observer OFF and ON subjects;
- explicitly clears pytest's default `addopts` when executing the P0
  experimental-integrity gate;
- records a deterministic `validity` section separately from wall-clock
  performance;
- marks a report valid only when:
  - ON/OFF final state hashes match;
  - the causal-equivalence gate actually executes and passes;
  - the sensorimotor equivalence benchmark passes.

No timing threshold participates in validity.

## Preliminary current hotspot

The invalid first profile still identifies one likely investigation target:
`RidgePredictor.predict()` was the largest individual Python self-time entry,
with 6,000 calls in the 600-tick profile.

This is only a **candidate for the post-P8 optimization phase**. No predictor
optimization should be implemented until the corrected P8 full run is valid,
because prediction behavior is genuine cognition and must not be weakened or
sampled less frequently merely for speed.

## Required rerun

After these corrections are merged:

```bash
python scripts/reprofile_performance.py
```

The next optimization target must be selected from that corrected report.
