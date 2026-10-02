---
id: design.experimentation.generative-cognition-causal-contribution-v1
title: "Generative Cognition Causal Contribution v1 — Preregistration Draft"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - docs/design/core/longitudinal-integrity-v1.md
  - docs/design/cognition/generative-cognition-v1.md
language: en
---

# Generative Cognition Causal Contribution v1 — Preregistration Draft

**Status:** preregistration **draft for owner review**. Not approved, not
registered, not scheduled. It authorizes no experiment, protocol or runner.

**Roadmap item:** fourth "evidence follow-up after integrity remediation" —
*causal behavioral contribution of generative cognition*
(Longitudinal Integrity v1 §17).

**Prerequisite:** the owner closes the Longitudinal Integrity v1 acceptance
gate. Generative Cognition v1 itself is still a proposed design with a partial
implementation; this draft does not change that status.

## 1. Scientific question

The existing generative-cognition studies (`generative-cognition-planning-utility`,
`-counterfactual-utility`, `-replay-utility`, `-predictive-utility` and the
release gates) are mechanism assays. Each constructs a situation in which the
mechanism, if it works, selects the evaluator-owned better option, and each
states that it is not evidence of embodied benefit. The open question is:

> In an organism living in a Body, does generative cognition change behaviour
> and homeostatic outcome compared with the same organism without it — because
> of the content it generates, and not because it spends more computation?

## 2. Claims explicitly not made

A positive result would not show imagination, understanding or planning in any
general sense; that generated content is true; or that the benefit holds
outside the declared Body, horizon and task ecology. A negative result would
not show the mechanism assays were wrong: a mechanism can work in a constructed
situation and still not matter in the organism's actual life.

## 3. Design

### 3.1 Split point

One organism develops normally with generative cognition enabled. The split is
taken at the first tick at which the organism's own agenda has completed at
least `K = 10` generative episodes whose output entered an action selection.
The rule is fixed here. A seed that does not reach it within `W_max = 5000`
ticks is **not testable**.

### 3.2 Arms

All arms are restored from the **same** organism checkpoint and physical
checkpoint, so each passes through the same restore and reacclimation gate.

| Arm | Generative cognition in the continuation | Controls for |
| --- | --- | --- |
| **G** full | intact | — (treatment) |
| **N** none | generative provider removed; candidates, predictions and factual ledger unchanged | the mechanism as a whole |
| **C** compute-matched idle | generative episodes are scheduled and charged as in G, but their output is discarded before it can enter selection | metabolic and time cost of generating |
| **R** shuffled content | generative episodes run, and their outputs are permuted across candidates at the evaluator-side boundary before selection | generated structure without correct correspondence |

Arm C is the control the mechanism assays lack: generating costs metabolism and
ticks, so an organism that generates is not otherwise identical to one that
does not. Arm R is the sham-content control.

### 3.3 Held fixed

Private-model inference is the same in all arms (attached or not, fixed at
approval). No evaluator label, score or probe identity reaches the organism.
Generated content never becomes factual evidence in any arm; this is the
existing release invariant GC-E5 and is checked, not assumed. Session controls
are recorded and every arm must end with `changed_since_restore == []`.

### 3.4 Seeds and horizon

- Development seeds: `101, 127, 149`.
- Confirmation seeds: `173, 211, 257, 307, 353, 401, 457, 503, 557, 601, 653,
  701`.
- Horizon `H`: the smallest multiple of 50 ticks at which, on the development
  seeds, arm **N** has made at least 20 action selections in every seed, capped
  at `H_max = 1000`. The rule does not look at arm G.

## 4. Outcome measures

Primary:

- **M1** — change in organism-owned homeostatic deviation over the
  continuation: `deviation(end) − deviation(start)`. Lower is better.

Secondary: reserve change, survival to `H`, fraction of selections in which
generated content changed the chosen action relative to arm N at the same tick
while trajectories still coincide, metabolic cost attributed to generation.

Manipulation check, reported first: in arm G generated content enters at least
one selection per seed; in arms N and C it never does; in arm C the generation
charge is within 5% of arm G's. A seed failing it is excluded.

## 5. Integrity conditions

A run is **contaminated**, excluded and reported if:

1. the restored checkpoint does not verify its identity;
2. arms of one seed do not start from byte-identical organism and physical
   state;
3. any generated item appears in the factual ledger or in the experience
   ledger as observed;
4. `changed_since_restore` is not empty, or the observer schedule differs
   between arms;
5. any evaluator quantity reaches the organism.

More than 2 contaminated or non-testable seeds of 12 makes the study **not
assessable**.

## 6. Decision rule

Let `W` be the set of seeds in which, in that same seed, `M1(G) < M1(N)`,
`M1(G) < M1(C)` and `M1(G) < M1(R)`.

- **Causal contribution of generated content supported** if `|W| ≥ 10` of 12
  and the median over seeds of `M1(C) − M1(G)` is at least `δ`, where `δ` is
  20% of the median absolute `M1` of arm N on the development seeds, fixed
  before confirmation.
- **Cost, not benefit** if N beats both G and C in at least 10 of 12 seeds:
  generating costs more than it returns.
- **Generation, not content** if G beats N and C but not R.
- **No contribution within scope** if the median of `M1(G) − M1(N)` lies within
  `±δ/2` and neither arm wins 10 or more seeds. This is a preregistered
  practical-null criterion, not a statistical equivalence test.
- **Inconclusive** otherwise.

Under no effect a seed is in `W` with probability at most 0.5, so the
one-sided sign-test bound `P(|W| ≥ 10) ≤ 0.019` holds for the joint condition.
There is one confirmatory claim, the first. Nothing is added after confirmation
runs start.

## 7. Decisions required from the owner

1. Whether and when to schedule this follow-up, given that Generative
   Cognition v1 is still a proposed design with a partial implementation.
2. The apparatus and task ecology in which generation could matter at all; a
   Body in which nothing can be anticipated cannot show a benefit.
3. Whether the compute-matched idle arm C is admissible, since it deliberately
   runs the mechanism and discards its output.
4. The numbers: `K`, `W_max`, `H_max`, 10 of 12, `δ` at 20%, the 5% charge
   tolerance.
5. Whether private-model inference is attached in all arms or in none.

## 8. What approval would start

Freeze this document; add the protocol, `experiment.toml` and runner with
contract tests; run development seeds to fix `H` and `δ` by rule; then run the
confirmation seeds. None of that exists or is started by this draft.
