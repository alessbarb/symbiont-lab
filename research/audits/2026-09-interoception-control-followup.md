# Interoception control follow-up

**Date:** 2026-09-17  
**Status:** negative result; not a biological-closure gate  
**Commits under test:** `74ee4b1`, `18c8672`

## Purpose

Re-run the three-arm interoception control after two methodological repairs:

1. environment resource identities are permuted from the apparatus seed, so
   replicate environments are reproducible but not accidentally identical;
2. `repair` no longer disappears from the action frontier when integrity is
   intact. That disappearance would have leaked an internal-state predicate
   into the absent-interoception arm.

The control remains descriptive. No evaluator metric, damage label, regime
name, or arm label is supplied to an organism's decision path.

## Long control

Configuration: population 8, 256 ticks, matched cohort, damage pulses at
64/128/192, five seeds `(7, 11, 19, 23, 31)`, social habitat enabled.

| arm | mean stress rate | mean rescue rate | mean repair events | mean deaths |
| --- | ---: | ---: | ---: | ---: |
| real interoception | 0.5253 | 0.5340 | 6 | 7 |
| sham interoception | 0.4487 | 0.4585 | 19 | 7 |
| absent interoception | 0.3784 | 0.3840 | 8 | 7 |

The real arm does not outperform sham or absent. This is not evidence that
interoception is harmful in general; it is evidence that this implementation
and protocol do not establish the required causal benefit.

## Social-confound check

Configuration: population 8, 96 ticks, matched cohort, damage pulses at
16/32/48/64/80, five seeds, repeated with social habitat disabled.

| arm | mean stress rate | mean rescue rate | mean repair events | mean deaths |
| --- | ---: | ---: | ---: | ---: |
| real interoception | 0.0508 | 0.0508 | 249 | 0 |
| sham interoception | 0.0391 | 0.0391 | 149 | 0 |
| absent interoception | 0.0000 | 0.0000 | 96 | 0 |

Removing social interaction removes most mortality and stress, but it does not
produce the expected advantage for the real arm. The absent arm still reaches
the best measured regulation rate, so the negative result cannot be assigned
only to social exchange.

## Interpretation and next gate

The test suite is green (`1475 passed`), and the replicate harness is now
seeded and checkpoint-reproducible. The scientific objective remains open.
The next implementation must explain why the absent arm can regulate through
the remaining local action frontier and why the real arm's internal context
does not improve outcomes. It must not be addressed by adding a low-reserve
repair rule, feeding evaluator truth into decisions, or tuning the outcome
metric after inspection.

