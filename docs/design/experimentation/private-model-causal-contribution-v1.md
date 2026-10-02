---
id: design.experimentation.private-model-causal-contribution-v1
title: "Private Model Causal Contribution v1 — Preregistration Draft"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - docs/design/core/longitudinal-integrity-v1.md
  - docs/design/core/private-model-learnability-v1.md
language: en
---

# Private Model Causal Contribution v1 — Preregistration Draft

**Status:** preregistration **draft for owner review**. Not approved, not
registered, not scheduled. It authorizes no experiment, protocol or runner.

**Roadmap item:** second "evidence follow-up after integrity remediation" —
*causal behavioral contribution of the private model*
(Longitudinal Integrity v1 §17).

**Prerequisite:** the owner closes the Longitudinal Integrity v1 acceptance
gate. The design below depends on matched continuations restored from one
checkpoint being the same organism.

## 1. Scientific question

Private Model Learnability v1 established, within its bounded scope, that the
organism's private model can beat its frequency baseline on held-out sequences.
That is a statement about prediction loss. It leaves open:

> Does inference by the organism's own private model change what the organism
> does, and its homeostatic outcome, compared with the same organism without
> it — because of what that model learned?

## 2. Claims explicitly not made

A positive result would not demonstrate that a larger model, more training or
ancestry helps (separate follow-ups), that the effect generalises beyond the
declared Body and horizon, or anything about understanding or intelligence. A
negative result would not show the model failed to learn; learnability is a
separate, already bounded, result.

## 3. Relation to the existing matched-continuation study

`experiments/learning/prospective-agency-embodied/` already defines matched
continuations from one organism checkpoint and one physical checkpoint, with
arms `full`, `no_counterfactual`, `shuffled_model`, `shuffled_value` and
`babbling_only`, and a homeostatic primary outcome. This draft does not replace
it. It isolates the **model** as the manipulated cause, adds the controls that
separate learned content from the mere presence of a model, and fixes a
decision rule in advance.

## 4. Design

### 4.1 Split point

One organism develops normally, with autonomous private-model training serviced
as in the canonical runtime. The split is taken at the first tick at which all
of these hold, and the rule is fixed here so the split cannot be chosen:

- a private model is `ACTIVE` in the organism's own registry;
- that model beat its frequency baseline on the organism's own held-out
  validation at promotion;
- the organism has made at least one prospective selection.

A seed that never reaches the split within `W_max = 5000` ticks is **not
testable**; it is reported and counted neither as success nor failure.

### 4.2 Arms

All arms are restored from the **same** organism checkpoint and physical
checkpoint, so every arm passes through the same restore and the same
reacclimation gate.

| Arm | Model inference in the continuation | Controls for |
| --- | --- | --- |
| **F** full | the organism's own `ACTIVE` model | — (treatment) |
| **O** off | no inference bridge attached | the presence of any model |
| **X** foreign content | same architecture and size, weights from a model trained by a *different* organism on a different seed | compute, latency and the act of querying, without this organism's learned content |
| **P** permuted | the organism's own model with its output token identities permuted at the evaluator-side query boundary | the model's structure without correct correspondences |

Arm X is the sham control: it holds everything about "having and querying a
model" fixed and removes only what *this* organism learned.

### 4.3 Held fixed

- The outcome-value ledger and the model registry are frozen for the
  continuation, so the study measures the state at the split and not rapid
  relearning of the ablation.
- No private-model training is serviced during the continuation in any arm.
- Session controls are recorded in `runtime_provenance.session_controls`; every
  arm must end with `changed_since_restore == []`.
- Body, environment seed and observer schedule are identical across arms.

### 4.4 Seeds and horizon

- Development seeds: `101, 127, 149`.
- Confirmation seeds: `173, 211, 257, 307, 353, 401, 457, 503, 557, 601, 653,
  701`.
- Continuation horizon `H`: the smallest multiple of 50 ticks at which, on the
  development seeds, arm **O** has made at least 20 action selections in every
  seed, capped at `H_max = 1000`. The rule does not look at arm F.

Confirmation seeds are not run until this document is approved and frozen.

## 5. Outcome measures

Primary:

- **M1** — change in organism-owned homeostatic deviation over the
  continuation: `deviation(end) − deviation(start)`. Lower is better.

Secondary: reserve change, survival to `H`, number of prospective selections,
fraction of selections whose chosen action differs from arm O's choice at the
same tick while trajectories still coincide.

Manipulation check, reported before any outcome: in arm F the model is queried
and its prediction enters selection in at least one tick per seed; in arm O it
is never queried. A seed failing the check is excluded as not testable.

## 6. Integrity conditions

A run is **contaminated**, excluded and reported if:

1. the restored checkpoint does not verify its identity;
2. arms of one seed do not start from byte-identical organism state and
   physical state;
3. `changed_since_restore` is not empty;
4. the observer schedule differs between arms (exact equality);
5. any evaluator quantity reaches the organism;
6. training is serviced during the continuation.

More than 2 contaminated or non-testable seeds of 12 makes the study **not
assessable**.

## 7. Decision rule

Let `W` be the set of seeds in which, in that same seed, `M1(F) < M1(O)`,
`M1(F) < M1(X)` and `M1(F) < M1(P)`.

- **Causal contribution of learned content supported** if `|W| ≥ 10` of 12 and
  the median over seeds of `M1(X) − M1(F)` is positive and at least `δ`, where
  `δ` is 20% of the median absolute `M1` of arm O on the development seeds,
  fixed before confirmation.
- **Model presence, not content** if F beats O in at least 10 of 12 seeds but
  not X.
- **Harmful** if O beats F in at least 10 of 12 seeds.
- **No contribution within scope** if the median of `M1(F) − M1(O)` lies within
  `±δ/2` and neither arm wins 10 or more seeds. This is a preregistered
  practical-null criterion, not a statistical equivalence test.
- **Inconclusive** otherwise.

Under no effect a seed is in `W` with probability at most 0.5, so the
one-sided sign-test bound `P(|W| ≥ 10) ≤ 0.019` holds for the joint condition.
There is one confirmatory claim, the first. Secondary measures are reported and
cannot rescue it. Nothing is added after confirmation runs start.

## 8. Decisions required from the owner

1. Whether and when to schedule this follow-up.
2. The apparatus: Physics3D, as in the existing matched-continuation study, or
   the synthetic causal Body.
3. Whether a foreign-content model (arm X) may be produced by a second
   organism run solely as a control.
4. The numbers: 10 of 12, `δ` at 20%, `W_max`, `H_max`.
5. Whether the existing `prospective-agency-embodied` study is run first as
   the regression anchor.

## 9. What approval would start

Freeze this document; add the protocol, `experiment.toml` and runner with
contract tests; run development seeds to fix `H` and `δ` by rule; then run the
confirmation seeds. None of that exists or is started by this draft.
