# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.22 — causal online attention budget

v0.16 showed that a simple risk ranking can beat the live policy at the same *retrospective* investigation count, but that ranking sorts the completed event stream. v0.22 removes that advantage.

`symbiont-causal-budget` gives every selector the same **ex-ante capacity** and presents events one at a time. Decisions are irrevocable: a selector may use the current event and its own history, but it cannot inspect or rank future scores.

Compared selectors:

- `risk` — current-event synthetic risk;
- `novelty` — host-relative novelty estimated causally from prior observations;
- `risk_novelty` — bounded risk/novelty combination;
- `random` — deterministic online random baseline.

Score-based selectors estimate thresholds only from previous scores. A quota guard ensures the precommitted budget is honored; any selections forced solely because remaining budget equals remaining events are counted explicitly as `forced_selections` so that catch-up behavior cannot hide inside the final metrics.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-causal-budget \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --budget-per-1000 12
```

The output reports equal selected counts, threat recall, precision, benign false-positive rate, `stealth_sim` recall and how many selections were quota-forced.

The older `symbiont-budget` command remains available because its retrospective top-k ranking answers a different question: the *upper descriptive value* of each score after the entire world is known.

## v0.21 integrity foundation

v0.22 builds on the v0.21 scientific-integrity tranche:

- reporter poisoning and agent personality consume independent deterministic RNG streams;
- repeated trust recalibration without fresh reports is idempotent;
- undefined longitudinal rates remain `N/A`;
- generation 1 remains a parity control and is excluded from mean heritage-effect estimates;
- re-export threshold flips are separated from evaluator-measured truth improvement;
- replicated studies require unique seeds.

## Experimental tools

```bash
# Baseline synthetic population
symbiont-sim --hosts 100 --steps 300 --seed 7

# Longitudinal inheritance
symbiont-generations --generations 5 --hosts 100 --steps 300 --seed 7

# Retrospective equal-attention score analysis
symbiont-budget --hosts 100 --steps 300 --seed 7

# Causal online equal-capacity attention analysis
symbiont-causal-budget --hosts 100 --steps 300 --seed 7 --budget-per-1000 12

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
- attention/evidence experiments are observer-side and do not change agent decisions;
- causal attention selectors cannot inspect future scores;
- replicated studies require unique seeds and preserve per-world pairing;
- heritage stress conditions assert an identical target-world digest;
- direction flips are separated from evaluator-measured re-export improvement;
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
- **v0.22 — causal attention budget:** **current** — irrevocable online selection under a fixed ex-ante capacity.
- **next:** replicate causal budget results across reserved seeds and budget levels; run second-look sensor-noise sweeps on reserved seeds; then introduce ecological change between generations. A second-look signal should not influence an agent until observer-side evidence is robust.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
