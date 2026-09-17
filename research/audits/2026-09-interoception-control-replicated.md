# Replicated interoception control run

**Date**: 2026-09-17  
**Status**: negative result; not a biological-closure gate.

## Protocol

- `run_interoception_control_replicates`
- 8 founders, 1 generation, 256 ticks
- checkpoints every 64 ticks
- matched cohort, reproduction disabled
- seeds: 7, 11, 19, 23, 31
- damage pulses: ticks 64, 128 and 192

## Result

All five seeds produced the same aggregate values:

| arm | stress rate | rescue rate | repair events | deaths |
|---|---:|---:|---:|---:|
| real interoception | 0.839527 | 0.851351 | 3 | 7 |
| sham interoception | 0.810379 | 0.824351 | 3 | 7 |
| absent interoception | 0.339196 | 0.345059 | 19 | 7 |

## Interpretation

The current organism does not meet the proposed ablation criterion.  Removing
interoception improves short-run regulation under this protocol, while the
real and sham arms remain close.  The result is reproducible but negative.

The likely confound is not unresolved measurement noise: the sham control
retains the same provider topology and processing path.  The current action
policy spends too much of the finite metabolic budget on the richer sensory
surface and does not convert the internal signal into enough useful repair or
resource decisions.  This is a diagnosis for the next design iteration, not a
reason to relabel the result as success.

No evaluator metric, regime label, damage label or fitness value is exposed to
the organism.  No threshold or post-hoc selection was added after inspecting
the result.
