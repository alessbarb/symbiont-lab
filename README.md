# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.24 — paired second-look sensor-noise sweep

The second-look sensor is still **shadow-only**. v0.24 does not let it influence an agent. Instead, it measures where the auxiliary evidence stops being useful as its noise increases.

`symbiont-evidence-noise-sweep` runs the same first-look selections across several sensor-noise levels and validation seeds. By default:

- validation seeds: `211,223,239,251,269`;
- sensor noise: `0.08,0.18,0.30,0.45`;
- evidence capacity: `12` second looks per 1,000 events.

For a given `seed × strategy`, the selected events and pre-measurement Brier score must remain identical across every noise level. Only the auxiliary measurement changes. The experiment refuses to continue if noise changes the selected evidence set.

The sensor RNG is deterministic per event. Re-running the same event at different noise levels reuses the same underlying random draw and changes only its amplitude, giving the sweep a paired interpretation.

Reported metrics include:

- Brier gain and the fraction of validation worlds with positive Brier gain;
- net classification-correction rate;
- entropy reduction;
- `stealth_sim` correction rate when defined;
- paired degradation relative to the lowest tested noise level.

Direction agreement remains descriptive, not statistical significance.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-evidence-noise-sweep \
  --seeds 211,223,239,251,269 \
  --noise-levels 0.08,0.18,0.30,0.45 \
  --hosts 100 \
  --steps 300 \
  --budget-per-1000 12
```

## Causal attention line

v0.22 removed hindsight from attention selection and v0.23 replicated that experiment across new seeds and several capacities:

```bash
symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 --steps 300
```

The retrospective `symbiont-budget` tool remains available as a descriptive upper-bound comparison, but it is not treated as an online policy experiment.

## Integrity foundation

The current research line builds on the v0.21 scientific-integrity corrections:

- reporter poisoning and agent personality consume independent deterministic RNG streams;
- repeated trust recalibration without fresh reports is idempotent;
- undefined longitudinal rates remain `N/A`;
- generation 1 is a parity control and is excluded from mean heritage-effect estimates;
- threshold-direction changes are separated from evaluator-measured re-export improvement;
- replicated studies reject duplicate seed lists;
- evaluator truth never feeds the organism.

## Experimental tools

```bash
# Baseline synthetic population
symbiont-sim --hosts 100 --steps 300 --seed 7

# Longitudinal inheritance
symbiont-generations --generations 5 --hosts 100 --steps 300 --seed 7

# Retrospective equal-attention score analysis
symbiont-budget --hosts 100 --steps 300 --seed 7

# Causal online attention: replicated paired study
symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 --steps 300

# Paired second-look noise sweep
symbiont-evidence-noise-sweep \
  --seeds 211,223,239,251,269 \
  --noise-levels 0.08,0.18,0.30,0.45 \
  --hosts 100 --steps 300 --budget-per-1000 12

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
- same-seed comparisons preserve the same synthetic world;
- repeated trust recalibration without fresh reports is idempotent;
- longitudinal optional rates remain `N/A` rather than becoming zero;
- attention/evidence experiments are observer-side and do not change agent decisions;
- causal attention selectors cannot inspect future scores;
- replicated causal studies preserve `seed × budget` pairing and equal capacity;
- second-look noise sweeps preserve the first-look selected set across noise levels;
- replicated studies require unique seeds and preserve per-world pairing;
- heritage stress conditions assert an identical target-world digest;
- inherited priors do not create reporters, trust or host memory;
- research archives and evaluator truth never feed back into the species.

Historical frozen audits and protocols live under `research/`.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** explicit evaluation contract and reproducible worlds.
- **v0.16:** retrospective equal-attention observer research.
- **v0.17:** bounded synthetic second look, shadow-only.
- **v0.18:** replicated paired second-look studies.
- **v0.19:** fixed-world heritage stress.
- **v0.20:** replicated source→target heritage stress.
- **v0.21:** engine-integrity corrections from the frozen audit.
- **v0.22:** causal online attention under a fixed ex-ante capacity.
- **v0.23:** replicated causal attention across validation seeds and capacities.
- **v0.24 — sensor-noise sweep:** **current** — paired evidence-quality stress on new seeds, still shadow-only.
- **next:** introduce ecological change between generations and measure whether inherited priors help early adaptation or become stale liabilities. Only after observer-side evidence is robust should a second-look signal influence an agent.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
