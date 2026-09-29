# Promotion Stability v1

Status: **proposed — design phase** (owner, 2026-09-29; prerequisite of
P5.2, Cross-Domain Revision Coherence v1 §8.9). Baseline: `main`.

## 1. Problem

With the 192-step budget (Private Model Learnability v1 §10), P5.1 trained
44 private models in 1 379 ticks and **all 44 were promoted to ACTIVE**,
each displacing the previous one. The promotion gate asks "does the
candidate beat the non-neural baselines on held-out data?", not "does it
beat the model that already controls?". Every competent candidate
therefore replaces the ACTIVE model: churn even when all models are good.

## 2. Candidate rule (to be preregistered)

A candidate may become ACTIVE only if (1) it beats the canonical baseline
(unchanged) **and** (2) it beats the current ACTIVE on the **same**
held-out evaluation by a preregistered minimum margin, not by a
noise-sized amount. Production is unchanged until the study decides.

## 3. D0 — what the archived P5.1 data can describe

Design data only; it can never confirm the new gate.

- One training every 32 ticks; 44/44 promoted.
- Proxy only: the successor's loss on its own corpus was higher than its
  predecessor's on the predecessor's corpus in 19/43 replacements (median
  change −0.018 nats, range −0.338 to +0.226). This is **not** the paired
  quantity the rule needs.
- The paired quantity (candidate vs current ACTIVE on the candidate's
  held-out split) cannot be recovered: model weights were not archived and
  each training's corpus cannot be rebuilt from the final state.

## 4. D1 — paired design data (proposed)

Regenerate the P5.1 arm A trajectory (same snapshot `org-2df92a9d8fda` at
tick 768, same code, synchronous training, Level 0 sparse telemetry) with a
lab-side, observational instrument: at each adoption, evaluate the
candidate **and** the current ACTIVE on the candidate's held-out split and
record both losses and outcome-token counts. Nothing is fed back to the
organism; the equivalence harness checks that the organism's trajectory is
unchanged by the instrument. The distribution of (ACTIVE − candidate)
paired differences fixes the margin, before any confirmation run.

**D1 as run (2026-09-29).** The tick-768 snapshot was not archived (it
lived only in the deleted P5.1 copies), so D1 uses a new snapshot of the
same organism at tick 1 105 (stressed; checkpoint sha256 `7490de26…`, body
`8c8bf460…`, archived with its models in `.symbiont/archive/d1/input/`).
Code `247dca7f` (instrument, off by default). Two copies run in parallel to
death or 6 000 ticks: *on* logs paired evaluations, *off* does not; their
final organism state, provenance and body must be byte-identical. The
paired value is logged for every training whose current ACTIVE has a
tokenizer on disk, promoted or not.

**D1 result (2026-09-29; design data only).** The *on* copy was first
killed by systemd-oomd (memory pressure from two parallel runs; 7 rows
kept in `archive/d1/on-oomkilled/`) and rerun alone. *on* and *off* then
ended byte-identical (organism `runtime.json`, provenance, body and
measurement at tick 2 090): the instrument is observational. 31 trainings
in 985 ticks, **all 31 promoted**; candidates beat the baseline by a median
0.44 nats.

Paired difference ACTIVE − candidate on the candidate's held-out split
(> 0: candidate better): min −0.161, p10 −0.076, p25 −0.036, **median
+0.002**, p75 +0.069, max +0.775. **15/31 promoted candidates were worse
than the ACTIVE they replaced.** The fraction of held-out targets unknown
to the ACTIVE's tokenizer ranges 1.4-8.6 % (median 2.7 %) and correlates
with the difference (r = 0.63): part of the candidate's apparent advantage
is vocabulary mismatch, not better prediction.

Candidates that would pass a margin *m*: 16/31 at 0, 13 at 0.02, 11 at
0.05, 4 at 0.10, 2 at 0.20.

**Proposal (owner decision before confirmation).** (1) Compare candidate
and ACTIVE on a common footing: loss restricted to held-out outcome targets
known to both tokenizers (reported alongside the full losses), because the
current paired value favours the candidate when the ACTIVE lacks tokens.
(2) Fix the margin on that fair metric. D1 was measured on full losses, so
a margin fixed now would be calibrated on a biased quantity; the cheapest
correct route is to extend the instrument with the restricted loss and
repeat D1 *on* once (≈ 45 min, same archived input), then fix the margin
from the interquartile half-width of the fair differences. A provisional
value from the current data would be ≈ 0.05 nats (half the interquartile
range, 11/31 promotions).

## 5. Confirmation (to be preregistered after D1)

New data only: a different organism or snapshot, arms current gate vs
new gate, measuring promotions, ACTIVE tenure, and held-out loss of the
ACTIVE over time. Criteria fixed before the run.
