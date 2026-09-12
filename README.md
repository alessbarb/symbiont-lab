# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.23 — replicated causal attention

v0.22 removed hindsight from the attention-budget experiment. v0.23 asks whether those online results repeat across several synthetic worlds and several fixed capacities before any attention rule is allowed to influence the live agent.

`symbiont-causal-budget-study` runs the causal selectors on a paired design:

- validation seeds: `101,127,149,173,199` by default;
- budgets: `5,12,20` investigations per 1,000 events by default;
- selectors: `risk`, `novelty`, `risk_novelty`, deterministic `random`;
- reference: `random` by default.

Within each `seed × budget` world every selector receives the same absolute capacity and sees the same event stream. Each decision remains irrevocable and online. The study reports per-strategy means/dispersion plus paired deltas against the reference for threat recall, precision, benign false-positive rate, `stealth_sim` recall and the share of selections forced only by the end-of-stream quota guard.

Direction agreement is descriptive evidence across the selected worlds, not statistical significance.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 \
  --steps 300
```

Single-world causal analysis remains available:

```bash
symbiont-causal-budget --hosts 100 --steps 300 --seed 7 --budget-per-1000 12
```

The older `symbiont-budget` command remains deliberately separate: it performs retrospective top-k ranking and therefore measures descriptive score potential rather than causal online policy quality.

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

# Causal online attention: one world
symbiont-causal-budget --hosts 100 --steps 300 --seed 7 --budget-per-1000 12

# Causal online attention: replicated paired study
symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 --steps 300

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
- same-seed comparisons preserve the same synthetic world;
- repeated trust recalibration without fresh reports is idempotent;
- longitudinal optional rates remain `N/A` rather than becoming zero;
- attention/evidence experiments are observer-side and do not change agent decisions;
- causal attention selectors cannot inspect future scores;
- replicated causal studies preserve `seed × budget` pairing and equal capacity;
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
- **v0.23 — replicated causal attention:** **current** — paired validation across new seeds and several capacity levels.
- **next:** sweep second-look sensor noise on reserved seeds, then introduce ecological change between generations. A second-look signal should not influence an agent until observer-side evidence is robust.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
