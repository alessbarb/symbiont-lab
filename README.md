# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.21 — engine integrity

v0.21 deliberately adds **no new cognitive mechanism**. It closes scientific-integrity issues reproduced by the frozen v0.19 audit before more intelligence is added to the organism.

### Causal RNG separation

Reporter poisoning and agent personality now consume independent deterministic RNG namespaces. `_make_agents` keeps its historical single-RNG call contract through a small compatibility facade, but reporter selection uses the `reporters` stream while `risk_scale`, `curiosity_scale` and `investigation_bias` use the `agents` trait stream.

Changing `poison_fraction` can therefore change which agents invert reports without silently changing their other random traits.

### Trust consumes fresh evidence once

`CollectiveMemory.recalibrate_sources()` is now incremental. A pattern can affect source trust only when its live report count has advanced since the previous recalibration. Calling recalibration repeatedly without any new reports is idempotent, so the same votes cannot manufacture increasing confidence merely because time passes.

This does **not** turn peer consensus into ground truth. Collusion and poisoning remain legitimate experimental failure modes; v0.21 only stops evidence from being counted repeatedly when nothing new happened.

### Longitudinal `N/A` stays `N/A`

Scientific longitudinal comparisons now use the explicit optional attention/classification rates rather than the legacy aliases that coerce undefined rates to zero.

If there are no threats, recall and its inherited−control delta are `N/A`. Aggregate means use defined pairs only. Generation 1 is retained as a parity control, but it is excluded from the reported mean heritage effect because it has no inherited intervention yet.

### Re-export semantics

A re-export that crosses probability 0.5 is now called a `direction_flip`, not a correction. The observer additionally records, for re-exported fingerprints that occur in the target synthetic world:

- how many are truth-evaluable;
- how many move closer to the empirical target-world rate;
- how many move farther away;
- mean re-export MAE gain.

`corrected_reexports` remains only as a deprecated compatibility alias for `direction_flips` in serialized single-pair results.

### Replication integrity

Replicated second-look and replicated heritage-stress studies reject duplicate seed lists. Repeating seed 7 twice no longer counts as two independent replicates.

## Experimental tools

```bash
source .venv/bin/activate
pip install -e '.[dev]'

# Baseline synthetic population
symbiont-sim --hosts 100 --steps 300 --seed 7

# Longitudinal inheritance; N/A is preserved
symbiont-generations --generations 5 --hosts 100 --steps 300 --seed 7

# Equal-attention observer study
symbiont-budget --hosts 100 --steps 300 --seed 7

# Replicated shadow second-look study
symbiont-evidence-study --seeds 3,7,11,17,23 --hosts 100 --steps 300

# Replicated fixed-world heritage stress
symbiont-heritage-stress-study \
  --source-seeds 3,7,11,17,23 \
  --target-offset 1009 \
  --hosts 100 \
  --steps 300
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- host profiles, agent traits, reporter selection, event scheduling, observations and drift use separated deterministic random streams;
- same-seed agent-side comparisons preserve the same synthetic world;
- repeated trust recalibration without fresh reports is idempotent;
- longitudinal optional rates remain `N/A` rather than becoming zero;
- generation 1 is a parity control, not evidence of a heritage effect;
- attention/evidence selectors remain observer-side;
- replicated studies require unique seeds and preserve per-world pairing;
- heritage stress conditions assert an identical target-world digest;
- direction flips are separated from evaluator-measured re-export improvement;
- inherited priors do not create reporters, trust or host memory;
- inherited-only beliefs cannot be re-exported without fresh live reports;
- research archives and evaluator truth never feed back into the species.

Historical frozen audits and protocols live under `research/`.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** explicit evaluation contract and reproducible worlds.
- **v0.16:** equal-attention observer research.
- **v0.17:** bounded synthetic second look, shadow-only.
- **v0.18:** replicated paired second-look studies.
- **v0.19:** fixed-world heritage stress.
- **v0.20:** replicated source→target heritage stress.
- **v0.21 — engine integrity:** **current** — causal RNG separation, fresh-evidence trust, longitudinal `N/A`, truth-aware re-export diagnostics and unique replication seeds.
- **next:** compare attention selectors under a genuinely causal/online budget; run sensor-noise sweeps on reserved seeds; then introduce ecological change between generations. Only after those observer-side results justify it should a bounded second-look signal be allowed to influence an agent.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
