# E4-v4 — Causal belief revision after perturbation of a consolidated relation

Follow-up investigation to Agency Acquisition & Executive Action v1
(`docs/design/core/agency-acquisition-and-executive-action-v1.md`, audit §0).
It changes the E4 protocol, not the organism: v1 remains frozen.

## Purpose

Preregistered protocol for `learning.agency-consolidated-causal-intervention`.
E4 v3 perturbed at acquisition + 64 ticks and measured one 4096-tick horizon,
where the normal twin's developmental drift erased the broken-effector
contrast. This protocol perturbs a *consolidated but still observable*
relation and reports several horizons fixed in advance.

## Hypothesis

When a relation the organism believes it causes is causally consolidated and
still observable, breaking or permuting the outputs that produce it makes the
organism revise that relation's controllability below a matched normal twin
continued from the same checkpoint.

## Design

Newborn canonical `OrganismRuntime` subjects in the opaque `CausalBody`
apparatus. After acquisition the organism develops normally. For each
perturbed condition (broken_effector, permuted) the apparatus waits until at
least one relation that condition would invalidate (apparatus ground truth:
the effect involves a receptor the dimension no longer drives) holds
`action_support >= min_support`, controllability `>= min_controllability` and
agency `>= min_agency` for `stability_ticks` consecutive ticks, within
`max_wait_ticks`. The organism is then split into a perturbed twin and a
normal control twin from one checkpoint; both are observed at every
preregistered horizon. The gate is evaluator-side and never reaches the
organism.

## Success criteria

Primary endpoint, per condition: normal-minus-perturbed residual
controllability of the gated relations at +1024 ticks. Supported when the gap
is positive in at least 75% of testable seeds and its mean is positive.
Secondary, reported without thresholds: the same gap at the other horizons,
gated-relation agency, and the E4 v3 invalidated/intact, dimension,
body-schema, affordance and intent-failure measures at every horizon. Seeds
whose gate never opens are untestable and reported as such.

The thresholds, horizons, seeds and endpoint were fixed before the first run
and must not be changed after seeing results; a change is a new protocol
version with its own run.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-consolidated-causal-intervention/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization. Only if revision stays
too slow under a genuinely consolidated relation does recency become a
modelling question, and then as recent contradiction evidence distinct from
historical support.
