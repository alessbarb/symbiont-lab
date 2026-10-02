---
id: design.experimentation.advanced-cognition-causal-efficacy-programme-v1
title: "Advanced Cognition Causal Efficacy Programme v1"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - docs/methodology/research-programme.md
  - docs/design/core/lifecycle-continuity-contract-v1.md
language: en
---

# Advanced Cognition Causal Efficacy Programme v1

**Status:** proposed programme. It groups five preregistration drafts, none of
which is approved. It authorizes no experiment.

## 1. Why this programme exists

Four advanced mechanisms are implemented, persistent and mechanically tested.
Whether they are *useful* exceeds the evidence. Existence, telemetry, unit tests
and correlation do not answer that. This programme maps each open claim to one
intervention experiment with a control that separates the mechanism's *content*
from its mere *activity* (issue #278).

## 2. Claims and experiments

| Claim | Draft | Causal intervention | Content control | Primary outcome |
| --- | --- | --- | --- | --- |
| The private model improves behaviour | [Private Model Causal Contribution v1](private-model-causal-contribution-v1.md) | own `ACTIVE` model attached (F) vs no bridge (O) | foreign model of the same size (X); own model with permuted outputs (P) | change in organism-owned homeostatic deviation |
| Generative cognition improves behaviour | [Generative Cognition Causal Contribution v1](generative-cognition-causal-contribution-v1.md) | intact (G) vs provider removed (N) | compute-matched idle generation (C); shuffled content (R) | change in organism-owned homeostatic deviation |
| Executive Outcome Learning improves decisions | [Executive Outcome Learning Causal Contribution v1](executive-outcome-learning-causal-contribution-v1.md) | evidence recorded and applied (D) vs off (C) | evidence frozen at the split (F); relation keys shuffled (S) | effect realization rate |
| Model ancestry improves later learning | [Model Ancestry Matched-Budget Utility v1](model-ancestry-matched-budget-v1.md) | child seeded from the organism's own ancestor (A) | budget-matched scratch (B); data-matched scratch (D); foreign ancestor (Z) | held-out loss on later experience at equal total budget |
| Retained knowledge helps after a Body change | [Re-embodiment Functional Transfer v1](reembodiment-functional-transfer-v1.md) | developed in the source Body (T) | sham experience in an unrelated Body (S); naive newborn (N) | ticks to the first valid execution binding in the new Body |

## 3. Per-mechanism analysis

### 3.1 Private model

- **Confounds:** compute and latency of querying any model; the act of
  attaching a bridge; maturity of the organism at attachment.
- **Mechanical preconditions:** an `ACTIVE` model exists; artifacts are packaged
  and hash-verified; inference is deterministic for a fixed checkpoint.
- **Development horizon:** fixed by rule on three development seeds from the
  no-bridge arm only.

### 3.2 Generative cognition

- **Confounds:** generating costs metabolism and ticks, so an organism that
  generates differs from one that does not even if the content is worthless.
- **Mechanical preconditions:** generated content never becomes factual
  evidence (release invariant GC-E5); the provider can be removed without
  changing candidates or the factual ledger.
- **Development horizon:** fixed by rule from the no-generation arm.

### 3.3 Executive Outcome Learning

- **Confounds:** any modulation of admission changes selection; evidence already
  held at the split differs from evidence learned afterwards; the v1.1 seeds
  shaped the mechanism.
- **Mechanical preconditions:** history hit rate at least 0.10 and no eviction
  (the mechanism's own clean-test rule); EOL writes no causal evidence.
- **Development horizon:** fixed by rule from the EOL-off arm.

### 3.4 Model ancestry

- **Confounds:** a child of a trained parent has more training behind it;
  starting from any pretrained weights may help regardless of whose they are.
- **Mechanical preconditions:** an ancestry-eligible model exists; step budgets
  are accounted exactly; lineage is recorded.
- **Development horizon:** the step budget `S`, fixed by rule on development
  seeds.

## 4. Rules common to every experiment

1. **Tests are not efficacy evidence.** A passing unit, integration or mechanics
   test shows the apparatus runs. It is never counted for or against a claim.
2. **Activation is not benefit.** Every draft reports a manipulation check
   (the mechanism was active in the treatment arm and inactive or sham in the
   controls) separately from the outcome. A seed that fails the check is
   excluded, not counted.
3. **Arms start from the same state.** All arms of a seed are restored from the
   same checkpoint and pass through the same restore and reacclimation gate.
4. **Subjects have a verified origin.** Confirmation and held-out runs refuse
   organisms of unverified legacy origin (research programme A2); the launcher
   enforces it.
5. **The contract is named.** Each run manifest records the longitudinal
   contract of its subject (Lifecycle Continuity Contract v1 §7.1).
6. **One confirmatory claim per experiment**, with a preregistered practical-null
   criterion, so a null result is a recorded outcome and not an absence of one.
7. **Negative and null results are retained** and reported with the same
   prominence as positive ones. No threshold is relaxed after results are seen.
8. **Confirmation seeds stay unrun** until the draft is approved and frozen.
   Held-out stages need separate owner authorization.
9. **Governed execution.** Every scientific run goes through
   `agentctl run start` with seed, input mode, commit and execution fingerprint
   recorded.

## 5. Order

No order is imposed. The drafts are independent. Re-embodiment Functional
Transfer v1 has had the most review (three revisions) and has the fewest
unresolved apparatus questions; the generative-cognition draft depends on a
design that is itself still proposed.

## 6. Decisions required from the owner

1. Which drafts to approve, in which order.
2. For each, the apparatus and the numbers listed in its own §7.
3. Whether the sham-content controls are admissible; each deliberately gives the
   organism content that is not its own.
4. Confirmation seed lists against existing reservations.

## 7. Claims this programme does not make

- that any of the four mechanisms is useful, or useless;
- that the five experiments exhaust the open questions about them;
- that a result in the declared Body and horizon generalizes beyond them.
