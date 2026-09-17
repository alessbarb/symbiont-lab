# Genesis multigenerational follow-up — 2026-09-17

## Objective

Check whether the bounded Genesis apparatus produces autonomous reproduction,
heritable divergence, finite-population turnover, and persistence beyond the
founder cohort without feeding evaluator metrics or regime labels back into an
organism.

## Protocol

- Apparatus: `build_genesis_harness`.
- Population: 8 identical founders; carrying capacity 32.
- Horizon: 600 ticks per configured generation, with 2 and 3 configured
  generations respectively.
- Checkpoints: every 600 ticks; random checkpoints disabled for this probe.
- Seed: 7; default synthetic opaque resource surfaces and social habitat.
- Reproduction enabled; no evaluator-controlled birth schedule.
- Metrics read only from the returned `LifeTrace` and evaluator-owned
  `HabitatBirthAuthority` snapshot.

Command shape:

```python
from research.autonomous_life.genesis import build_genesis_harness
from research.autonomous_life.harness import HarnessConfig

harness = build_genesis_harness(HarnessConfig(
    population=8, generations=N, ticks=600,
    checkpoint_interval=600, random_checkpoint_count=0,
))
trace = harness.run()
```

## Results

| configured generations | births | deaths | reproductions | final population | peak | extinction | offspring viability | observed genetic generations | observed genomes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 456 | 424 | 448 | 32 | 32 | 0 | 0.071429 | 0–56 | 438 |
| 3 | 674 | 642 | 666 | 32 | 32 | 0 | 0.048048 | 0–84 | 656 |

Both runs reached the bounded carrying capacity, generated live descendants,
and produced many distinct observed genomes. The lineages are not a single
fixed founder clone: mutation/recombination and mortality alter the observed
genome set while the run remains live.

## Interpretation and limits

This is positive evidence for the narrower Genesis gates: autonomous
reproduction, bounded population accounting, heritable divergence, and
multigenerational turnover. It is **not** evidence that the population is
ecologically stable or that selection is biologically meaningful yet.

`BirthRecord.generation` is genealogical depth and increments on each birth;
it is not the configured environment-generation counter. Consequently, the
observed ranges `0–56` and `0–84` must not be reported as 57 or 85 ecological
generations. The very high birth/death rate and low descendant viability also
indicate a turnover/explosion regime at the current parameters, not a closed
claim of persistence, specialization, coexistence, or useful selection.

The following remain open:

1. a predeclared ecology study separating stable coexistence from carrying-
   capacity turnover;
2. lineage-level persistence under controlled scarcity and regime shifts;
3. extinction and recovery across independent seeds;
4. replication of the causal interoception/homeostasis result across
   independent protocols; and
5. reduction of emergency homeostatic intervention over longitudinal learning,
   rather than only in the corrected damage protocol.

## Validation

The probe completed for both horizons after the bounded repair-opportunity
correction and reproduced the prior lifecycle figures exactly. The full
repository suite passed with `1480 passed`. This document records
observational evidence only; no evaluator metric is added to organism inputs.
