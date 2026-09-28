# Footprint Precision v1

Status: **proposed; FP-0 preregistered** (owner delegated the recommendation,
2026-09-28). Prerequisite of Cross-Domain Revision Coherence v1 Wave 2.
Baseline: `main @ 0af9b286`.

## 1. Problem

E8 v3 (Factorized Effect Representation v1 §16.4) found that every intent
satisfied in the high-dimensional body under current reconciliation (8/8),
and 106/127 under chance-corrected reconciliation, were satisfied only by
atoms on receptors that drift on their own. A 600-tick pilot showed 13 of
22 footprint members on such receptors. Footprint membership (§13.7:
Wilson lower bound of the pulse hit rate > length-matched quiet rate +
0.05, at least 4 pulses) admits drift; anything built on footprints —
grounding, intent reconciliation, and the retest of Revision Coherence
Wave 2 — inherits it.

## 2. Candidate causes

- **H1 — zero-count quiet baseline.** Each atom's quiet rate is
  `q = passive_hits / passive_windows`. Drift spreads over many rare atoms
  (32 receptors × 2 directions × 3 magnitude classes), so many have
  `passive_hits = 0` and `q = 0`; the expected quiet rate is then 0 and two
  hits in four pulses (Wilson lower bound 0.15) pass the 0.05 margin.
- **H2 — small samples and sequential testing.** Membership is re-evaluated
  after every pulse across dozens of candidate atoms per source; with few
  pulses a 95% bound is crossed by chance somewhere.
- **H3 — baseline mismatch.** Passive windows are pooled over the whole
  history while pulses occur at specific times; a drifting receptor's local
  rate near pulses can differ from its global quiet rate.

## 3. FP-0 — descriptive precision study (preregistered)

**Design.** E8 body (16 actuators × 4 correlated receptors + 32 drifting),
seeds 101, 127, 149, 163, 179, 193, 211, 227, 241, 257, factorized effects
on, current reconciliation, 3 000 ticks; snapshots at ticks 500, 1 000,
1 500, 2 000, 2 500, 3 000. Nothing in the organism changes.

**Ground truth (evaluator-only).** A footprint source is a set of opaque
channels, mapped to actuators by `opaque_channel_ref`. Each member atom's
feature maps to a receptor through the runtime's signal identity. A member
is classified as:

- `own`: its receptor is driven by an actuator of the source;
- `cross`: driven by another actuator (wrong attribution);
- `drift`: a drifting receptor;
- `other`: anything else (e.g. a distractor), reported separately.

**Reported per snapshot and seed.** Member counts by class; precision
(`own / members`); recall (driven receptors of each single-channel source
represented by at least one `own` member / all its driven receptors); and,
for every member, `pulses`, `hits`, `passive_windows`, `passive_hits`,
`expected_quiet_rate`, `pulse_rate_lower_bound` and its magnitude class.

**Decision rule (fixed now; chooses the next specification, adopts
nothing).** At tick 3 000, pooled over seeds, among `drift` + `cross`
members:

1. if ≥ 50% have `passive_hits == 0` → H1 is primary: the next spec replaces
   the point estimate of the quiet rate with a conservative one (e.g. the
   Wilson upper bound of `q`, or pooling magnitude classes of a feature);
2. else if ≥ 50% have `pulses ≤ 6` → H2 is primary: the next spec requires
   more pulses and/or corrects for multiple comparisons;
3. else → H3: the next spec matches the quiet baseline in time to the
   pulses.

Precision and recall are reported as they are; no threshold is applied to
them in FP-0.

## 4. Afterwards

The fix chosen by the rule is specified, implemented behind an option and
tested in a preregistered E8 arm with a precision criterion and the E6
gate, before Revision Coherence Wave 2 can start.

## 5. FP-0 result (2026-09-28) — H3 selected

Run `20260928T070437Z-learning-footprint-precision-3b81f62-cea1` on
`3b81f62e` (a first run on `41b241c5` completed but lost its summary to a
runner defect, fixed in `3b81f62e`; nothing from it was seen).

| Tick | own | cross | drift | other | precision | mean recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 | 37 | 2 | 102 | 3 | 0.26 | 0.33 |
| 1 000 | 72 | 2 | 127 | 5 | 0.35 | 0.35 |
| 1 500 | 108 | 2 | 155 | 5 | 0.40 | 0.41 |
| 2 000 | 126 | 2 | 146 | 7 | 0.45 | 0.46 |
| 2 500 | 142 | 2 | 143 | 6 | 0.49 | 0.51 |
| 3 000 | 146 | 2 | 141 | 6 | 0.50 | 0.52 |

Decision inputs at tick 3 000 (drift + cross = 143 members): 17.5% with
`passive_hits == 0` (H1 needs ≥ 50%), 28.7% with `pulses ≤ 6` (H2 needs
≥ 50%) → **H3 (baseline mismatch) selected** by the preregistered rule.

Descriptive details, pooled at tick 3 000:

- `drift` members: median 12 pulses, pulse hit rate 0.375 against a
  length-matched expected quiet rate of 0.107, from a median of 429
  passive windows — drift atoms genuinely appear far more often during
  pulses than the pooled rest baseline predicts;
- `own` members: **all 146 have `passive_hits == 0`** (quiet rate 0),
  median 16 pulses, hit rate 0.31. True membership currently rests on a
  zero quiet estimate, so a conservative fix of the H1 kind (e.g. using
  the upper bound of the quiet rate for membership) would remove the true
  members as well; H1 was the prior favourite and is contradicted;
- precision rises with experience (0.26 → 0.50) and recall with it
  (0.33 → 0.52); only 2 `cross` members — attribution between actuators
  is not the problem, drift is.

**Next specification (per §4):** match the quiet baseline in time to the
pulses — e.g. compare each pulse with the rest windows that bracket it
(causal probing already alternates rest 4 / pulse 6 / rest 4), so that
whatever makes drift appear more often around pulses is present in both
terms. It will be preregistered with a precision criterion on the E8 body
and the E6 gate before any change to membership.
