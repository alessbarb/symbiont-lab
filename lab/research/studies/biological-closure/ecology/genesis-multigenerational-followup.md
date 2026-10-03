# Genesis multigenerational follow-up — 2026-09-17

## Objective

Check whether the bounded Genesis apparatus produces autonomous reproduction,
heritable divergence, finite-population turnover, and persistence beyond the
founder cohort without feeding evaluator metrics or regime labels back into an
organism.

## Protocol

- Apparatus: `build_genesis_harness`.
- Population: 8 identical founders; carrying capacity 32.
- Horizon: 600 ticks per configured generation, with 2 and 3 configured
  generations respectively.
- Checkpoints: every 600 ticks; random checkpoints disabled for this probe.
- Seed: 7; default synthetic opaque resource surfaces and social habitat.
- Reproduction enabled; no evaluator-controlled birth schedule.
- Metrics read only from the returned `LifeTrace` and evaluator-owned
  `HabitatBirthAuthority` snapshot.

Command shape:

```python
from symbiont_lab.studies.autonomous_life.genesis import build_genesis_harness
from symbiont_lab.studies.autonomous_life.harness import HarnessConfig

harness = build_genesis_harness(HarnessConfig(
    population=8, generations=N, ticks=600,
    checkpoint_interval=600, random_checkpoint_count=0,
))
trace = harness.run()
```

## Results

| configured generations | births | deaths | reproductions | final population | peak | extinction | offspring viability | observed genetic generations | observed genomes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 456 | 424 | 448 | 32 | 32 | 0 | 0.071429 | 0–56 | 438 |
| 3 | 674 | 642 | 666 | 32 | 32 | 0 | 0.048048 | 0–84 | 656 |

Both runs reached the bounded carrying capacity, generated live descendants,
and produced many distinct observed genomes. The lineages are not a single
fixed founder clone: mutation/recombination and mortality alter the observed
genome set while the run remains live.

## Interpretation and limits

This is positive evidence for the narrower Genesis gates: autonomous
reproduction, bounded population accounting, heritable divergence, and
multigenerational turnover. It is **not** evidence that the population is
ecologically stable or that selection is biologically meaningful yet.

`BirthRecord.generation` is genealogical depth and increments on each birth;
it is not the configured environment-generation counter. Consequently, the
observed ranges `0–56` and `0–84` must not be reported as 57 or 85 ecological
generations. The very high birth/death rate and low descendant viability also
indicate a turnover/explosion regime at the current parameters, not a closed
claim of persistence, specialization, coexistence, or useful selection.

The following remain open:

1. a predeclared ecology study separating stable coexistence from carrying-
   capacity turnover;
2. lineage-level persistence under controlled scarcity and regime shifts;
3. extinction and recovery across independent seeds;
4. replication of the causal interoception/homeostasis result across
   independent protocols; and
5. reduction of emergency homeostatic intervention over longitudinal learning,
   rather than only in the corrected damage protocol.

## Controlled pressure differential check

As a bounded follow-up, Genesis was run for 256 ticks with social interaction
enabled, reproduction enabled, contrasted resource profiles, and damage at
`32/96/160/224`, using seeds `(7, 11, 19)`. The final evaluator snapshots
reported 84, 88 and 94 observed genomes; each run had approximately 30--32
genomes with positive live-share-minus-birth-share differential and 54--62
with negative differential.

This is only partial selection evidence. It does not yet show that a
particular inherited change explains persistence under pressure.

## Evaluator-only locus follow-up

The next instrumentation tranche is now present in commit `ec0f004`. Each
`EvolutionarySnapshot` may retain a bounded `genome_loci` table keyed by
`genome_id`; the harness copies only the runtime's finite heritable locus
values into that table. The table is serialized with the evaluator trace and
is not included in observations, action selection, runtime state, or any
organism-facing input. The regression test also confirms that the existing
`fitness` key is still absent.

A short contrasted-profile pilot (`ticks=128`, population 8, reproduction and
social interaction enabled, seeds 7 and 11) produced 42--46 observed genomes,
genealogical depths 0--6/7, and locus ranges of approximately `0.0--0.142`
for `learning_rate` and `0.0--0.187` for `forgetting_rate`. This demonstrates
heritable divergence and evaluator coverage, but not selection by either
locus: many surviving genome cohorts had point persistence `1.0`, while the
selection differential varied with cohort size and turnover. The present
per-genome snapshot is therefore an instrumentation result, not closure of the
evolution gate.

The next required study is a predeclared cohort-level analysis across
independent seeds and longer horizons, relating inherited loci to descendant
survival, reproduction, and resource use. It must report null and adverse
results as well as positive associations, and must remain evaluator-only.

The first implementation of that analysis is now available as
`summarize_locus_associations`. On the same contrasted profiles, with
population 8, reproduction and social interaction enabled, `ticks=128`, and
seeds `(7, 11, 19)`, the evaluator reported the following Pearson
associations between locus value and point lineage persistence:

| seed | `forgetting_rate` | `learning_rate` | observed genomes |
| ---: | ---: | ---: | ---: |
| 7 | 0.314308 | 0.234739 | 46 |
| 11 | 0.333152 | 0.266319 | 42 |
| 19 | 0.099837 | 0.305731 | 53 |

The positive signs are a hypothesis-generating observation, not a selection
claim. The effect size varies by locus and seed, the horizon is short, and the
point persistence measure is tied to a terminal snapshot. The mean selection
differential is zero by construction when aggregated across all observed
genomes, so its per-locus correlation is not independent evidence. Longer
cohort and descendant-level studies remain necessary before the evolution gate
can be closed.

## Horizon and no-turnover control

The same evaluator analysis was repeated at `ticks=256` with the contrasted
profiles and social interaction enabled. The persistence correlations were:

| seed | `forgetting_rate` | `learning_rate` | observed genomes | deaths |
| ---: | ---: | ---: | ---: | ---: |
| 7 | 0.337929 | 0.244276 | 77 | 64 |
| 11 | 0.255525 | 0.163122 | 82 | 64 |
| 19 | 0.235265 | 0.109450 | 87 | 64 |

As a bounded no-turnover control, the same 256-tick protocol with social
interaction disabled produced 0 deaths, 7--8 observed genomes, only
genealogical generations 0--1, and undefined correlations because every
observed genome had persistence `1.0`. This confirms that the association
calculation is sensitive to an outcome with variation, but it does not isolate
which ecological mechanism causes the positive association. The result
remains an observational lead rather than proof of adaptive selection.

An additional neutral-surface control kept social interaction and reproduction
enabled but assigned the same synthetic resource profile to all three opaque
surfaces. At `ticks=256`, it still produced 64 deaths and positive
locus/persistence associations:

| seed | `forgetting_rate` | `learning_rate` | observed genomes |
| ---: | ---: | ---: | ---: |
| 7 | 0.351713 | 0.225361 | 78 |
| 11 | 0.255525 | 0.163122 | 82 |
| 19 | 0.215833 | 0.117886 | 88 |

The near-match to the contrasted-profile run is evidence against attributing
the association to ecological contrast alone. It is more consistent with a
generic turnover/mutation or terminal-snapshot effect. A controlled founder
locus intervention, followed by descendant-level measurements, is therefore
required before claiming that the inherited loci themselves cause the
observed persistence difference.

## Controlled founder-locus intervention

To separate inherited-locus effects from mutation drift, the apparatus now
accepts an explicit founder-locus tuple for a matched study. This is a causal
control parameter owned by Genesis; it is not an evaluator metric and is never
selected by an organism during the run. The intervention was replicated at
`ticks=256` with contrasted profiles, seeds `(7, 11, 19)`, and two founder
cohorts:

- `low`: `learning_rate=0.001`, `forgetting_rate=0.0`;
- `high`: `learning_rate=0.08`, `forgetting_rate=0.005`.

| cohort | seed | final live | deaths | observed genomes | max genealogical generation |
| --- | ---: | ---: | ---: | ---: | ---: |
| low | 7 | 31 | 64 | 76 | 11 |
| low | 11 | 32 | 64 | 78 | 11 |
| low | 19 | 31 | 64 | 86 | 11 |
| high | 7 | 31 | 64 | 84 | 11 |
| high | 11 | 32 | 64 | 87 | 11 |
| high | 19 | 31 | 64 | 88 | 11 |

The matched intervention changed observed genetic diversity but did not change
final population, deaths, or genealogical depth in this protocol. Its
locus/persistence associations were not stable enough to establish a survival
effect. This is a negative mechanistic result, not evidence that plasticity is
irrelevant in general; the current Genesis pressure is not discriminating
these founder values at the population-outcome level.

## Descendant-outcome instrumentation

To avoid relying only on terminal population persistence, the evaluator
snapshot now also groups bounded outcomes by genome: individual lifespan
windows, accumulated resource use, and reproduction counts. These values are
derived from the harness trace and authority records after organism actions;
they are not available to cognition and are not combined into a runtime
fitness scalar. `summarize_locus_associations` reports descriptive
correlations for these outcomes alongside persistence.

A smoke protocol (`ticks=64`, seed 7) produced non-empty lifespan and
reproduction cohorts. Resource-use values were present where the observation
surface reported intake and remained zero otherwise; no assumption is made
that missing intake is zero resource need. This closes the measurement gap,
not the scientific gate: the next study must use these outcomes under a
predeclared pressure regime and replicate across seeds.

## Validation

The probe completed for both horizons after the bounded repair-opportunity
correction and reproduced the prior lifecycle figures exactly. The locus
mapping regression and experimental harness tests passed; the full repository
suite remains the required final validation for this tranche. This document
records observational evidence only; no evaluator metric is added to organism
inputs.

## Founder phenotype projection correction

The controlled founder-locus runner previously recorded founder loci in the
heredity authority but only projected them into descendant operational genomes.
Genesis now projects the declared founder values into the initial operational
phenotype as well, with the same bounded kernel clamps used at reproduction.
This removes a causal instrumentation defect: a founder-locus intervention
must affect founders before any descendant outcome can be interpreted.

The correction is validated by the founder/genesis harness tests. The first
post-correction probe still found no reproducible population differential for
`soft_node_budget` or `initial_concepts` under the existing social pressure.
The heritable adaptive gate therefore remains open; this correction improves
the experiment rather than constituting a positive result.

## Heritable adaptive differential: exploration locus

A bounded behavioral locus was added: `behavior_exploration`. It is projected
into founders and inherited by clonal descendants; it remains a local action
bias, not a role assignment or evaluator signal. The predeclared study used
values `0.0` and `0.1`, social interaction enabled, 128 ticks, and seeds
`(7, 11, 19)`. The comparison pressure was the default Genesis environment;
the altered pressure was `stale_resources`.

| pressure | trait | live population by seed | deaths by seed | offspring viability |
|---|---|---|---|---|
| default | 0.0 | 32, 32, 32 | 5, 5, 0 | 0.827586, 0.827586, 1.000000 |
| default | 0.1 | 32, 32, 32 | 26, 28, 25 | 0.640000, 0.615385, 0.653061 |
| stale resources | 0.0 | 6, 6, 6 | 15, 15, 15 | 0.461538, 0.461538, 0.461538 |
| stale resources | 0.1 | 6, 6, 6 | 15, 15, 15 | 0.461538, 0.461538, 0.461538 |

The differential is reproducible in all three default-pressure seeds and
vanishes under the altered pressure. This satisfies the current heritable
differential criterion for this bounded experiment. It does not imply that
exploration is universally advantageous; its effect is explicitly pressure
conditional.
