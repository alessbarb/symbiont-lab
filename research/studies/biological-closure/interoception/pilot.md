# Interoception control pilot

**Date**: 2026-09-17  
**Purpose**: separate interoceptive information from provider topology and processing cost.  
**Status**: pilot evidence only; not a biological-closure gate.

## Protocol

- Harness: `symbiont_lab.studies.autonomous_life.run_interoception_control_replicates`
- Population: 8 founders
- Generations: 1
- Ticks: 16
- Checkpoints: every 8 ticks
- Seeds: 7 and 11
- Cohort: matched, reproduction disabled
- Arms:
  - `real`: bounded internal values projected to the organism
  - `sham`: same provider manifest and processing path, neutral values projected
  - `absent`: provider removed

## Observed output

Both replicates produced the same short-horizon values:

| arm | stress rate | regulation rate | rescue rate | repairs | deaths |
|---|---:|---:|---:|---:|---:|
| real | 0.3125 | 0.6875 | 0.3125 | 0 | 0 |
| sham | 0.3125 | 0.6875 | 0.3125 | 0 | 0 |
| absent | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |

## Interpretation limits

The real and sham arms being identical in this pilot means no short-horizon
benefit from the values was observed.  The worse result relative to absent is
consistent with provider topology or workload cost, but does not establish a
causal harm from interoceptive information.  The run is too short to assess
learning, repair, survival, lineage persistence, or generalization.

The next run must use the predeclared longer replicated protocol before any
biological claim is made.
