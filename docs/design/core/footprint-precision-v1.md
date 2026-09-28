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

### 5.1 Reading after the rule (2026-09-28)

A post-hoc diagnostic (one seed, 1 200 ticks, not evidence) found the same
mean number of atoms per window in pulse and rest windows (2.65 vs 2.65),
which argues against the mechanism H3 assumes (drift appearing more often
around pulses). The observed pattern — drift members with an inflated hit
rate (0.375 vs 0.107 expected) — is what selection produces: membership
tests ~64 drift atoms per source after every pulse at a 95% bound with a
0.0 exit margin, so some cross by chance and stay. That is H2 in the broad
sense (sequential multiple comparisons); the preregistered operationalisation
of H2 (`pulses ≤ 6`) was too narrow to register it (median 12 pulses). The
rule's selection (H3) stands; FP-1 therefore tests the H3 fix **and** a
multiplicity fix, rather than replacing one with the other.

## 6. FP-1 — membership fixes against ground truth (preregistered)

**Arms** (E8 body, same 10 seeds, factorized effects, 3 000 ticks; the
organism differs only in footprint membership, behind options off by
default):

- **R** — current membership (reference);
- **T (H3, time-matched baseline)** — each atom's quiet rate is estimated
  only from passive windows within ±8 ticks of the source's pulses (the
  rest brackets of causal probing), instead of all passive windows;
- **M (multiplicity)** — the entry bound uses a Bonferroni-adjusted z for
  the number `m` of candidate atoms evaluated for that source,
  `z = Φ⁻¹(1 − 0.025 / m)`, and a member leaves when its lower bound falls
  below the expected quiet rate + 0.025 (exit margin half the entry
  margin, instead of 0);
- **TM** — both.

**Metrics** at tick 3 000, pooled over seeds: precision (own/members),
mean recall (as FP-0), member classes; plus the E6 gate per arm.

**Criteria, fixed now.** An arm qualifies if (1) pooled precision ≥ 0.80,
(2) mean recall ≥ 0.42 (80% of R's 0.52 in FP-0), and (3) E6 passes 3/3.
Among qualifying arms the highest precision is proposed (ties: the
simpler, in order T, M, TM). If none qualifies, the results are reported
and no membership change is proposed. Adoption as default is an owner
decision.

## 7. FP-1 result (2026-09-28) — no arm qualifies

Runs on `a87ba71b` (all arms and gates in `.symbiont/runs/*-a87ba71-*`):

| Arm | own | cross | drift | other | precision | recall | E6 |
|---|---:|---:|---:|---:|---:|---:|---|
| R | 356 | 47 | 330 | 9 | 0.480 | 0.529 | (reference) |
| T | 214 | 26 | 568 | 6 | 0.263 | 0.525 | 3/3 |
| M | 232 | 2 | 56 | 2 | **0.795** | 0.433 | 3/3 |
| TM | 254 | 45 | 399 | 1 | 0.363 | 0.456 | 3/3 |

By the preregistered criteria (precision ≥ 0.80, recall ≥ 0.42, E6 3/3)
**no arm qualifies** — M misses precision by 0.005 — so no membership
change is proposed and no threshold is moved. Reading: the H3 fix (T)
makes precision worse and multiplicity correction (M) removes 83% of drift
members (330 → 56) and nearly all cross members; the cause is
multiplicity, as §5.1 argued, not baseline mismatch.

**Regime caveat.** `a87ba71b` still had the causal binding invalidation
rule on by default (Revision Coherence §3.11), which changes behaviour
(R here has ~2.5× the members of FP-0's R). The arm comparison is valid
within that regime, but the default regime is now rule-off, so FP-1 is
repeated as a **replication (not blind; same criteria)** on the rule-off
commit before any proposal.

## 8. Owner decisions after FP-1 (2026-09-28)

- T (H3, time-matched baseline) is discarded as a useful hypothesis and is
  not developed further.
- M is the relevant candidate, but 0.795 < 0.80 is a failure; the
  threshold is not changed.
- The FP-1 replication on the rule-off default regime (`caed967f`) is
  completed and kept in full as **diagnostic / robustness** evidence, not
  confirmation (FP-1 was already known).
- Footprint membership and binding invalidation are studied separately
  (Binding Degradation v1); no arm combines them.

## 9. FP-2 — explicit multiple-comparison correction (preregistered)

**Rule under test (arm BH).** For each source, at every membership
update, each candidate atom `a` (with at least `min_pulses = 4` pulses) is
tested for excess over rest with an exact one-sided binomial test:
`p_a = P(X ≥ hits_a)`, `X ~ Binomial(pulses, e_a)`, where `e_a` is the
length-matched expected quiet rate computed from the Jeffreys estimate of
the per-window quiet rate, `(passive_hits + 0.5) / (passive_windows + 1)`
(so an atom never seen at rest has a small, not zero, rate). The
Benjamini–Hochberg procedure at **q = 0.05** over the source's candidate
atoms decides membership: an atom is a member exactly when its null is
rejected at that update. No entry/exit margins; nothing is tuned: q and
the Jeffreys prior are standard choices fixed here.

**Arms.** R (current membership), M (FP-1 M unchanged, as comparator),
BH. Binding invalidation off (default) in all arms.

**Data separation.** FP-0 and FP-1 seeds (101-257) were used to design
FP-2 and are not used to confirm it. FP-2 runs on new seeds: 463, 467,
479, 487, 491, 499, 503, 509, 521, 523. The E6 release gate keeps its
standard seeds (101/127/149); it is a gate, not a confirmation of
precision.

**Criteria (as FP-1, unchanged).** An arm qualifies with pooled precision
≥ 0.80 at tick 3 000, mean recall ≥ 0.42 and E6 3/3. Among qualifying arms
the highest precision is proposed (ties: M, BH). If none qualifies, the
results are reported and no membership change is proposed. Adoption as
default is an owner decision.

## 10. FP-1 replication on the default regime (diagnostic / robustness)

Runs on `caed967f` (binding invalidation off), same seeds and criteria;
FP-1 was already known, so this is not a confirmation.

| Arm | own | cross | drift | other | precision | recall | E6 |
|---|---:|---:|---:|---:|---:|---:|---|
| R | 146 | 2 | 141 | 6 | 0.495 | 0.523 | (reference) |
| T | 148 | 2 | 357 | 6 | 0.288 | 0.500 | 3/3 |
| M | 127 | 1 | 43 | 1 | 0.738 | 0.455 | 3/3 |
| TM | 129 | 1 | 286 | 2 | 0.309 | 0.458 | 3/3 |

No arm qualifies. R reproduces FP-0 exactly (determinism). The pattern is
robust across regimes: T worsens precision; M removes most drift members
(141 → 43) but stays below 0.80 (0.738 here, 0.795 with invalidation on).
FP-2 (explicit FDR correction, new seeds) is the preregistered next test.

## 11. FP-2 result (2026-09-28) — no arm qualifies

Runs on `4383a7ec`, new seeds 463-523 (disjoint from FP-2's design data):
R `...-4383a7e-5d50`, M `...-92ec`, BH `...-beea`; E6 gate for BH
`...-40a4`.

| Arm | own | cross | drift | other | precision | recall | E6 |
|---|---:|---:|---:|---:|---:|---:|---|
| R | 188 | 15 | 189 | 6 | 0.472 | 0.542 | (reference) |
| M | 122 | 1 | 44 | 0 | 0.731 | 0.512 | 3/3 (FP-1) |
| BH | 186 | 0 | 63 | 3 | 0.738 | 0.535 | 3/3 |

By the preregistered criteria (precision ≥ 0.80, recall ≥ 0.42, E6 3/3)
**no arm qualifies**; no membership change is proposed and no threshold
or parameter is changed.

Descriptive reading: on unseen seeds the explicit false-discovery-rate
correction (BH, q = 0.05) keeps nearly all of R's recall (0.535 vs 0.542)
while removing every cross member and two thirds of drift members;
multiplicity-based fixes (M, BH) converge near 0.73-0.74, well above R and
far above T. The remaining drift members (63) exceed what a 5% FDR per
update would predict, which points at repeated evaluation over time (each
update re-tests the same atoms; members accumulate across updates) as the
residual mechanism. Any further study needs its own preregistration and
new seeds; none is proposed here without an owner decision.

## 12. FP-3 — repeated evaluation over time (preregistered, owner option A)

**Rationale.** FP-2's residual drift members exceed a 5% false-discovery
rate per update. Membership re-tests the same atoms after every pulse on
overlapping, growing samples, so an atom only needs to cross once to be
admitted; this study removes the reuse of data across tests.

**Rule under test (arm BHB).** For each source, its pulses (ordered by end
tick) are partitioned into consecutive, disjoint **blocks of 8 pulses**;
a block is tested only when complete, and no pulse belongs to two blocks.
Within a block, each atom observed in it is tested exactly as in FP-2
(exact one-sided binomial test of the block's hits against the
length-matched quiet rate from the Jeffreys estimate over all passive
windows), and Benjamini–Hochberg at **q = 0.05** is applied over the
block's atoms. An atom is a member exactly when it is rejected in **both
of the two most recent completed blocks** (replication on independent
pulses). Block size 8, q and the two-block replication are fixed here.

**Arms.** R (current), BH (FP-2 unchanged, comparator), BHB. Binding
invalidation off (default) in all arms; no combination with Binding
Degradation v1.

**Data separation.** Seeds used so far (101-257, 409-461, 463-523) are
excluded. FP-3 runs on 541, 547, 557, 563, 569, 571, 577, 587, 593, 599.
The E6 gate keeps seeds 101/127/149 (a gate, not a precision
confirmation).

**Criteria (unchanged).** An arm qualifies with pooled precision ≥ 0.80 at
tick 3 000, mean recall ≥ 0.42 and E6 3/3; among qualifying arms the
highest precision is proposed (ties: BH, BHB). If none qualifies, results
are reported and no membership change is proposed.

**Disclosure (before the FP-3 runs).** During implementation a 1 000-tick
smoke test was accidentally run on confirmation seed 541 (arm BHB); the
only thing observed was that no member existed yet at tick 1 000 (BHB needs
two complete 8-pulse blocks). Further diagnostics used design seed 101. The
preregistered design and criteria are unchanged.
