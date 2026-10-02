---
id: design.experimentation.executive-outcome-learning-causal-contribution-v1
title: "Executive Outcome Learning Causal Contribution v1 — Preregistration Draft"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - docs/design/core/executive-outcome-learning-v1.md
  - docs/design/core/agency-acquisition-and-executive-action-v1.md
language: en
---

# Executive Outcome Learning Causal Contribution v1 — Preregistration Draft

**Status:** preregistration **draft for owner review**. Not approved, not
registered, not scheduled. It authorizes no experiment, protocol or runner.

**Regime when approved:** confirmatory. Executive Outcome Learning v1 is frozen;
this draft does not reopen its mechanism.

## 1. Scientific question

Executive Outcome Learning (EOL) v1.1 recorded, on ten seeds of which eight were
testable, that an organism using reconciled intent outcomes for future admission
(arm D) realized more commitments than one that did not (arm C) on two seeds,
the same number on six, and fewer on none. That result was obtained on the seeds
used while the relation key was being diagnosed and changed, and it compares EOL
only against its own absence. Two questions stay open:

> On seeds never used to shape the mechanism, does using the organism's own
> executive outcome evidence improve what its intents achieve — and is that
> because of *which* outcomes it recorded, rather than because admission is
> being modulated at all?

## 2. Claims explicitly not made

A positive result would not show that the organism learns from consequences in
general, that EOL is a reward mechanism (it is constructed not to be), or that
the benefit holds outside the declared Body and horizon. A negative result would
not show the v1.1 runs were wrong; they stand as recorded, exploratory with
respect to this question.

## 3. Design

### 3.1 Split point

One organism develops with EOL enabled, as it is by default. The split is taken
at the first tick at which the ledger holds real, non-neutral outcome evidence
for at least `K = 5` distinct relation keys. A seed that does not reach it within
`W_max = 5000` ticks is **not testable**.

### 3.2 Arms

All arms are restored from the **same** organism checkpoint, so each passes
through the same restore and reacclimation gate, and each starts with the same
recorded evidence.

| Arm | Executive outcome evidence in the continuation | Controls for |
| --- | --- | --- |
| **D** full | recorded and applied to admission | — (treatment) |
| **C** off | `executive_outcome_learning = False`: neither recorded nor applied | the mechanism as a whole |
| **F** frozen | applied from the evidence held at the split; new outcomes are not recorded | learning during the continuation, as opposed to evidence already held |
| **S** shuffled keys | recorded and applied, with the relation keys of the held evidence permuted at the evaluator-side boundary at the split | modulation of admission without the correct correspondence between relation and outcome |

Arm S is the sham-content control: admission is modulated by real evidence that
belongs to other relations. Suppression evidence is permuted with its key.

### 3.3 Held fixed

Intent reconciliation is on in every arm (the C/D distinction of EOL v1 §11, not
the B/C one). No evaluator label reaches the organism. EOL never writes causal
evidence, controllability, agency or competence evidence in any arm; this is the
existing release test and is checked, not assumed. Session controls are recorded
and every arm must end with `changed_since_restore == []`.

### 3.4 Seeds and horizon

- Development seeds: `101, 127, 149`. These overlap the EOL v1.1 seeds on
  purpose: they are used here only to fix `H` and `δ` by rule.
- Confirmation seeds: `733, 739, 743, 751, 757, 761, 787, 797, 809, 811, 821,
  823`. None was used in any EOL v1 or v1.1 run, and none appears as a seed in
  an experiment definition, study or design document at the time of drafting.
  Approval must re-check them against reservations made since.
- Horizon `H`: the smallest multiple of 50 ticks at which, on the development
  seeds, arm **C** has terminated at least 15 commitments in every seed, capped
  at `H_max = 3000`. The rule does not look at arm D.

## 4. Outcome measures

Primary:

- **M1** — effect realization rate over the continuation: realized commitments
  divided by terminated commitments. Higher is better.

Secondary: realized commitments, energy per realized effect, switches per
realized effect, failed commitments, intent satisfaction rate.

Manipulation check, reported first: the ledger instrumentation of EOL v1 §8. In
arms D, F and S the history hit rate over the continuation is at least 0.10 and
no key is evicted; in arm C no lookup meets history. A seed failing it is **not a
clean test** and is excluded, by the rule EOL v1 already preregistered.

## 5. Integrity conditions

A run is **contaminated**, excluded and reported if:

1. the restored checkpoint does not verify its identity, or has an unverified
   legacy origin;
2. arms of one seed do not start from byte-identical organism state apart from
   the declared intervention;
3. any causal, controllability, agency or competence evidence differs between
   arms at the first tick of the continuation;
4. `changed_since_restore` is not empty, or the observer schedule differs
   between arms;
5. any evaluator quantity reaches the organism.

More than 2 contaminated, non-testable or not-clean seeds of 12 makes the study
**not assessable**.

## 6. Decision rule

Let `W` be the set of seeds in which, in that same seed, `M1(D) > M1(C)`,
`M1(D) > M1(S)` and `M1(D) ≥ M1(F)`.

- **Causal contribution of executive outcome evidence supported** if
  `|W| ≥ 10` of 12 and the median over seeds of `M1(D) − M1(C)` is at least `δ`,
  where `δ` is 20% of the median absolute deviation of `M1` in arm C across the
  development seeds, floored at 0.02, fixed before confirmation.
- **Modulation, not evidence** if D beats C but not S in at least 10 of 12 seeds.
- **Held evidence, not continued learning** if F matches or beats D in at least
  10 of 12 seeds while both beat C.
- **Harmful** if C beats D in at least 10 of 12 seeds.
- **No contribution within scope** if the median of `M1(D) − M1(C)` lies within
  `±δ/2` and neither arm wins 10 or more seeds. This is a preregistered
  practical-null criterion, not a statistical equivalence test.
- **Inconclusive** otherwise.

Under no effect a seed is in `W` with probability at most 0.5, so the one-sided
sign-test bound `P(|W| ≥ 10) ≤ 0.019` holds for the joint condition. There is one
confirmatory claim, the first. Nothing is added after confirmation runs start.

## 7. Decisions required from the owner

1. Whether to schedule this at all: EOL v1 is frozen and further mechanism work
   is deferred to Phase B.
2. Whether arm S is admissible: it deliberately gives the organism evidence that
   belongs to other relations.
3. The Body. EOL v1 ran on the default organism of the agency-acquisition
   studies; the same apparatus is assumed here and must be confirmed.
4. The confirmation seed list, against existing reservations.
5. The numbers: `K`, `W_max`, `H_max`, 10 of 12, `δ` at 20% with a 0.02 floor.

## 8. What approval would start

Freeze this document; add the protocol, `experiment.toml` and runner with
contract tests; run development seeds to fix `H` and `δ` by rule; then run the
confirmation seeds through `agentctl run start`. None of that exists or is
started by this draft.
