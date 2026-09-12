# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.16 — equal-attention research

The main research question is no longer simply “how many synthetic threats were investigated?”. Symbiont Lab now distinguishes:

- **attention allocation** — which events receive investigation budget;
- **classification** — which events are believed to be threats;
- **calibration** — whether confidence matches evaluator outcomes;
- **research cost** — how many investigations are spent per 1,000 events.

The v0.15 experimental-integrity layer also separates deterministic RNG streams for world generation, agent variation, event scheduling, observations and drift. Agent-side interventions such as reporter poisoning or heterogeneity therefore cannot silently change the same-seed synthetic world.

### Equal-budget analysis

`symbiont-budget` compares multiple observer-side ranking strategies using exactly the same investigation budget as the live policy:

```text
same synthetic event stream
          │
          ├── live policy
          ├── sensor-risk ranking
          ├── host-relative novelty ranking
          ├── risk + novelty ranking
          └── deterministic random baseline

all compared at the same number of selected events
```

The observer reports:

- investigations per 1,000 events;
- threat recall;
- attention precision;
- benign false-positive rate;
- recall by synthetic threat family (`ransom_sim`, `bot_sim`, `stealth_sim`);
- share of attention spent on benign updates, backups and builds;
- simple budget curves for alternative rankings.

This is evaluator-side analysis only. None of these rankings feed back into the agents.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-budget \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --threat-rate 0.018 \
  --poison-fraction 0.08
```

The existing longitudinal experiment remains available:

```bash
symbiont-generations \
  --generations 5 \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --heritage-limit 24
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- zero-denominator rates are `N/A`, not zero;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- same-seed agent-side comparisons preserve the same synthetic world;
- longitudinal inherited and naive populations use the same canonical simulation engine;
- inherited priors do not create reporters, trust or host memory;
- research archives and interpretations never feed evaluator truth back into the species.

Historical frozen audits and protocols live under `research/2026-09-12/`.

## Research questions

The current laboratory can now ask more causal questions:

- Does curiosity buy useful threat coverage at the same attention cost?
- Which strategy spends too much budget on benign builds, backups or updates?
- Does any ranking improve `stealth_sim` recall without exploding benign cost?
- Does inherited knowledge improve classification, or only change attention?
- How quickly can later generations reject stale or incorrect priors?
- At what attention budget do different strategies saturate?
- Is a global gain hiding deterioration in one threat family?

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9–0.14:** reproducible studies → dashboard studies → interpretation → study lineage → campaigns → bounded longitudinal heritage.
- **v0.15:** experimental integrity — explicit evaluation contract, reproducible worlds, family/phase breakdowns and calibrated confidence.
- **v0.16 — equal-attention research:** **current** — matched investigation budgets and observer-side efficiency curves.
- **next:** synthetic second-look evidence at bounded cost, stale/incorrect heritage stress tests, and dashboard visualization of the new research metrics.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
