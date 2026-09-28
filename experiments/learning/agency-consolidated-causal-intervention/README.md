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

## Belongs here

Preregistered protocol configurations, manifests, and execution parameters for this study arm.

## Does not belong here

No unit tests, production code, or transient run artifacts.

## Criterion for creating a file

Add only files required for this reproducible protocol definition or its registered gates; mechanical test contracts belong in `tests/experiments/`.

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

## Protocol v2 (preregistered before its first run)

v1 was underpowered: its gate opened in 1-2 of 10 seeds. From the read-only
reachability diagnostic below — normal development only, no perturbation
outcome inspected — v2 fixes:

- `min_controllability = min_agency = 0.05` (support 16 and stability 128
  unchanged): reachable in most seeds;
- `min_age_ticks = 1024`: relations are gated only once the organism is at
  least 1024 ticks past acquisition, so perturbation does not land in the
  early developmental drift that erased the E4 v3 contrast (with this age the
  diagnostic gate opens in 5/10 broken_effector and 7/10 permuted seeds, at a
  median onset of ~1150 / ~3000 ticks after acquisition);
- 20 seeds (the 10 of v1 plus 10 new) to compensate for the lower opening rate.

Horizons, primary endpoint and its criterion are unchanged from v1.

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

## Gate reachability diagnostic (read-only, after the first run)

Normal development only (no perturbation), 10 seeds, 4096 ticks after
acquisition; each candidate gate evaluated offline on the recorded
support/controllability/agency of the relations each condition would
invalidate. Seeds where the gate would open (broken_effector / permuted):

| support | controllability | agency | stability | broken | permuted | median wait (ticks) |
| --- | --- | --- | --- | --- | --- | --- |
| 16 | 0.10 | 0.10 | 128 | 1/10 | 2/10 | 314 / 221 (preregistered v1 gate) |
| 16 | 0.05 | 0.05 | 128 | 8/10 | 8/10 | 128 / 164 |
| 8 | 0.05 | 0.05 | 128 | 8/10 | 10/10 | 128 / 128 |

The v1 gate is blocked by requiring controllability and agency >= 0.10
together. A looser gate opens in most seeds, but at its earliest possible tick
(median wait = stability window, ~128 ticks after acquisition), i.e. early in
development where the E4 v3 normal twin drifted strongly. A protocol v2 should
therefore combine reachable levels with a minimum developmental age before
perturbation; choosing those values is an owner decision and a new
preregistered version.
