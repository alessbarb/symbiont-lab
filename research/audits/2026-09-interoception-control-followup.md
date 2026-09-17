# Interoception control follow-up

**Date:** 2026-09-17  
**Status:** negative result; not a biological-closure gate  
**Commits under test:** `74ee4b1`, `18c8672`, `d980141`, current pre-action signal correction

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

## State-dependent repair-cost follow-up

After the control above, an attempted repair on an intact body was changed to
consume bounded maintenance effort while returning zero integrity change. A
repair on a damaged body consumes the same effort and can recover integrity.
This removes the cost-free preventive-repair path without making repair
unavailable based on an integrity predicate.

The repeated long control produced:

| arm | mean stress rate | mean rescue rate | mean repair events | mean deaths |
| --- | ---: | ---: | ---: | ---: |
| real interoception | 0.5315 | 0.5402 | 6 | 7 |
| sham interoception | 0.4501 | 0.4599 | 6 | 7 |
| absent interoception | 0.3792 | 0.3848 | 7 | 7 |

The contextual cost is therefore a valid model improvement but does not yet
produce the required interoceptive advantage.

## Pre-action context correction

The action-learning checkpoint was audited after the preceding control. The
runtime was recording the interoceptive pressure after applying an action,
although the action opportunity had been selected using the pressure before
the action. The checkpoint now captures that decision-time value and a unit
test asserts that the pending observation retains it.

The controlled contrast-profile run was repeated with social interaction
disabled, damage pulses at `16/32/48/64/80/96/112`, and seeds `(7, 11, 19)`.
The aggregate result was unchanged from the preceding contrast-profile
control: real rescue `0.096354`, sham `0.257812`, absent `0.022135`; real
repairs `80`, sham `48`, absent `56`; mean integrity real `0.595508`, sham
`0.487500`, absent `0.645573`.

This correction removes a causal bookkeeping error but does not rescue the
interoception gate. The organism still has not demonstrated a benefit over
the absent control.

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

The test suite is green (`1478 passed`), and the replicate harness is now
seeded and checkpoint-reproducible. The scientific objective remains open.
The next implementation must explain why the absent arm can regulate through
the remaining local action frontier and why the real arm's internal context
does not improve outcomes. It must not be addressed by adding a low-reserve
repair rule, feeding evaluator truth into decisions, or tuning the outcome
metric after inspection.

## Contrast-profile outcome check

To separate resource pressure from social pressure, the three-arm control was
run with social interaction disabled, 128 ticks, damage pulses at
`16/32/48/64/80/96/112`, and the contrasted Genesis profiles used by the
ecology factorial study. Three seeds `(7, 11, 19)` were retained separately
before averaging.

| arm | mean stress rate | mean rescue rate | mean repair events | mean integrity | mean minimum integrity |
| --- | ---: | ---: | ---: | ---: | ---: |
| real interoception | 0.007812 | 0.096354 | 80 | 0.595508 | 0.000000 |
| sham interoception | 0.000000 | 0.257812 | 48 | 0.487500 | 0.000000 |
| absent interoception | 0.000000 | 0.022135 | 56 | 0.645573 | 0.100000 |

The real arm reduces kernel rescue relative to sham and preserves more
integrity than sham, but the absent arm still has the highest mean integrity
and no stress. This is stronger causal evidence than stress alone, yet it
still fails the gate: the real interoceptive signal has not demonstrated an
advantage over the absent control.
