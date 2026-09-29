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

## 5. Confirmation (to be preregistered after D1)

New data only: a different organism or snapshot, arms current gate vs
new gate, measuring promotions, ACTIVE tenure, and held-out loss of the
ACTIVE over time. Criteria fixed before the run.
