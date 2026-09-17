# Genesis ecology follow-up — 2026-09-17

## Objective

Test whether the current bounded Genesis population produces measurable
resource partitioning rather than merely occupying the carrying capacity.
This is a diagnostic for the ecological-emergence gate, not a success label.

## Protocol

- `build_genesis_harness` with 8 identical founders and 600 ticks.
- Seeds: 7, 11 and 19.
- Two apparatus conditions: social boundary disabled/enabled.
- Reproduction enabled; the social boundary is the only condition changed.
- Niche overlap is computed from resources actually acquired by each subject,
  not from resource surfaces merely observed.
- All metrics are read after the run and never enter organism decisions.

## Results

| social boundary | seed | births | deaths | final population | mean population | capacity occupancy | niche overlap | rescue events | offspring viability | observed genomes | extinct genomes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| disabled | 7 | 16 | 0 | 16 | 15.960 | 0.499 | 1.000 | 0 | 1.000000 | 8 | 0 |
| disabled | 11 | 16 | 0 | 16 | 15.960 | 0.499 | 1.000 | 0 | 1.000000 | 7 | 0 |
| disabled | 19 | 16 | 0 | 16 | 15.960 | 0.499 | 1.000 | 0 | 1.000000 | 8 | 0 |
| enabled | 7 | 232 | 200 | 32 | 30.890 | 0.965 | 0.966 | 8876 | 0.142857 | 214 | 182 |
| enabled | 11 | 237 | 207 | 30 | 31.107 | 0.972 | 0.946 | 8888 | 0.131004 | 223 | 193 |
| enabled | 19 | 232 | 200 | 32 | 30.890 | 0.965 | 0.966 | 8876 | 0.142857 | 224 | 192 |

## Interpretation

The social boundary creates a real ecological pressure: population density,
birth/death turnover, lineage extinction and rescue events all change sharply.
That is useful evidence that the population is not a passive list of
independent organisms.

The specialization gate is **not met**. Resource acquisition remains highly
overlapping (`0.946–0.966`) in the social condition and completely overlapping
without social pressure. The current result is therefore competition-driven
turnover, not demonstrated resource partitioning or stable coexistence.

As a profile-separation probe, the apparatus was then run once with:

```text
(renewal=0.01, cost=0.25, usefulness=2.0, information=0.02)
(renewal=0.20, cost=1.00, usefulness=0.5, information=0.40)
(renewal=0.00, cost=2.50, usefulness=1.2, information=0.90)
```

At 256 ticks this produced 95 births, 64 deaths, 77 observed genomes, 48
extinct genomes and offspring viability `0.356322`, while acquisition overlap
remained `0.948040`. The contrast therefore changes turnover and lineage
composition but does not by itself produce specialization.

The 8,876–8,888 rescue events in the social condition are also a confound for
the interoception study. Before treating them as adaptive homeostasis, the
next experiment must distinguish pressure-induced kernel responses from
organism-selected repair/rest behavior and report rescue rates per live
organism-tick.

## Required next experiment

Run a predeclared resource-profile study with independent per-surface
abundance/renewal/usefulness profiles and measure acquisition shares,
lineage persistence and phenotype divergence over time. Keep social pressure
as a separate factor. Do not tune the runtime to force a low overlap value.
