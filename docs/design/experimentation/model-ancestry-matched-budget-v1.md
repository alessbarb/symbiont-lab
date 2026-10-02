---
id: design.experimentation.model-ancestry-matched-budget-v1
title: "Model Ancestry Matched-Budget Utility v1 — Preregistration Draft"
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

# Model Ancestry Matched-Budget Utility v1 — Preregistration Draft

**Status:** preregistration **draft for owner review**. Not approved, not
registered, not scheduled. It authorizes no experiment, protocol or runner.

**Roadmap item:** third "evidence follow-up after integrity remediation" —
*matched-budget utility of model ancestry* (Longitudinal Integrity v1 §17).

**Prerequisites:** the owner closes the Longitudinal Integrity v1 acceptance
gate, and gives the separate go-ahead that Private Model Learnability v1 §10
requires before any P5 re-run with ancestry exercisable.

## 1. Scientific question

Private Model Learnability v1 §10 raised the autonomous training ceiling so
that models can become ancestry-eligible, and recorded that ancestry could then
be exercised. Its mechanics-only lineage test checked that seeding a child from
a parent works; it is explicitly never evidence that ancestry helps. The open
question is:

> At equal total training budget, does a private model seeded from the
> organism's own eligible ancestor learn the organism's later experience better
> than one trained from scratch — because of what the ancestor learned?

"Equal budget" is the point. A child that starts from a trained parent has, in
effect, more training behind it. Without matching, any gain is just more steps.

## 2. Claims explicitly not made

A positive result would not show that ancestry improves behaviour (that needs
the private-model causal-contribution follow-up), that deeper lineages keep
helping, or that the result holds for another architecture, learning rate or
corpus regime. A negative result would not show ancestry mechanics are broken;
those are covered by the lineage mechanics test.

## 3. Design

### 3.1 Corpora

Each seed provides one organism lineage with two successive corpora drawn from
the organism's own experience, in order: an **earlier** corpus `C_a` and a
**later** corpus `C_b`, with a held-out split of `C_b` that no arm trains on.
The split tick between them is the tick of the organism's first
ancestry-eligible model, so it is set by the organism and not by the evaluator.

### 3.2 Arms

All arms produce a model that is then evaluated on the held-out split of `C_b`.
`S` is the step budget of one autonomous training at full replay pressure (192
under the current ceiling).

| Arm | Initialisation | Training | Total steps | Controls for |
| --- | --- | --- | --- | --- |
| **A** ancestry | the organism's own eligible ancestor, trained `S` steps on `C_a` | `S` steps on `C_b` | `2S` | — (treatment) |
| **B** budget-matched scratch | random | `2S` steps on `C_b` | `2S` | total step budget |
| **D** data-matched scratch | random | `S` steps on `C_a`, then `S` steps on `C_b`, as one model without lineage machinery | `2S` | exposure to `C_a` itself |
| **Z** foreign ancestor | an eligible model from a *different* organism, same architecture, trained `S` steps on that organism's corpus | `S` steps on `C_b` | `2S` | starting from any pretrained weights, without this organism's content |

Arm D separates "ancestry" from "having seen the earlier data": if A matches D,
the lineage mechanism adds nothing beyond data exposure. Arm Z is the sham
control: pretrained weights and vocabulary handling without relevant content.

### 3.3 Held fixed

Architecture, parameter ceiling, learning rate, tokenizer construction rule,
autonomous stopping rule (or its absence, identically in all arms), evaluation
context window, and the held-out split. Each arm is trained with the same set
of training seeds.

### 3.4 Seeds

- Development organism seeds: `101, 127, 149`.
- Confirmation organism seeds: `173, 211, 257, 307, 353, 401, 457, 503, 557,
  601, 653, 701`.
- Training seeds per arm and organism: `7, 11, 13`; the per-organism value of a
  measure is the median over training seeds.

An organism seed that produces no ancestry-eligible model within the
development horizon used by the P5 protocol is **not testable** and is reported
as such.

## 4. Outcome measures

Primary:

- **G** — held-out loss on `C_b` minus the best frequency-baseline loss on the
  same split, as defined in Private Model Learnability v1. Lower is better;
  negative means the model beats the baseline.

Secondary: training steps needed to first reach `G < 0`; vocabulary growth
between parent and child; train/held-out gap.

Manipulation check, reported first: in arm A the child's generation is the
parent's plus one and the parent's token identities and embeddings are
preserved at initialisation. A seed failing it is excluded.

## 5. Integrity conditions

A run is **contaminated**, excluded and reported if:

1. any arm trains on, or selects a stopping point from, the held-out split;
2. total steps differ from `2S` in any arm;
3. the foreign ancestor of arm Z shares an organism identity or corpus with the
   test organism;
4. checkpoints used to extract corpora or models do not verify their identity;
5. an ancestor is granted `ACTIVE` or control authority by training ancestry.

More than 2 contaminated or non-testable organism seeds of 12 makes the study
**not assessable**.

## 6. Decision rule

Let `W` be the set of organism seeds in which, in that same seed, `G(A) < G(B)`,
`G(A) < G(D)` and `G(A) < G(Z)`.

- **Ancestry utility supported at matched budget** if `|W| ≥ 10` of 12 and the
  median over seeds of `G(B) − G(A)` is at least `0.02` nats.
- **Data exposure, not ancestry** if A beats B and Z in at least 10 of 12 seeds
  but not D.
- **Pretraining, not content** if A beats B but not Z.
- **Ancestry harmful** if B beats A in at least 10 of 12 seeds.
- **No utility within scope** if the median of `G(B) − G(A)` lies within
  `±0.01` nats and neither arm wins 10 or more seeds. This is a preregistered
  practical-null criterion, not a statistical equivalence test.
- **Inconclusive** otherwise.

Under no effect a seed is in `W` with probability at most 0.5, so the
one-sided sign-test bound `P(|W| ≥ 10) ≤ 0.019` holds for the joint condition.
There is one confirmatory claim, the first. Nothing is added after confirmation
runs start.

## 7. Decisions required from the owner

1. Whether and when to schedule this follow-up, and the P5 re-run go-ahead it
   depends on.
2. The margins: `0.02` nats for support and `±0.01` for the practical-null
   criterion. Both are proposals without grounding yet; the development seeds
   should be used to check them against the seed-to-seed spread of `G` before
   the freeze.
3. Whether arm D is admissible, since it trains a model outside the organism's
   own lineage machinery purely as a control.
4. Seed counts and the three training seeds.
5. Whether lineage depth greater than one is in scope for a later version.

## 8. What approval would start

Freeze this document; add the protocol, `experiment.toml` and runner with
contract tests; run development seeds to confirm ancestry-eligible models
appear; then run the confirmation seeds. None of that exists or is started by
this draft.
