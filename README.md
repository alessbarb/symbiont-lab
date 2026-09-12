# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.17 — bounded synthetic second look

Symbiont Lab can now ask a stricter version of the curiosity question:

> If only a limited number of events may receive one extra measurement, which selector spends that evidence budget most usefully?

The new `symbiont-evidence` experiment is **shadow-only**. It does not alter an agent, collective memory or a live decision. It runs the normal synthetic world, chooses an equal number of events using several first-look selectors and gives those events one extra noisy synthetic measurement.

Compared selectors:

- sensor risk;
- host-relative novelty;
- risk + novelty;
- `shadow_curiosity` — novelty × ambiguity × relevance, without evaluator truth;
- deterministic random baseline.

All selectors receive exactly the same second-look budget. The study reports pre/post Brier score, Brier gain, entropy reduction, corrected versus introduced classification errors, selected threat share and how many `stealth_sim` events received/corrected by the second look.

### The second-look sensor

The auxiliary sensor returns only a scalar in `[0, 1]`. Synthetic benign and threat families have deliberately overlapping noisy distributions. The selector never sees the family label, and one measurement cannot force certainty. Noise is deterministically derived per event so changing selector order cannot change the measurement itself.

In v0.17 **the sensor output never feeds back into Symbiont**. This version exists only to establish whether bounded evidence acquisition is worth integrating later.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-evidence \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --threat-rate 0.018 \
  --sensor-noise 0.18
```

By default the second-look budget equals the natural investigation count of the live policy. It can be fixed explicitly with `--budget`.

The equal-attention study remains available:

```bash
symbiont-budget --hosts 100 --steps 300 --seed 7
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- zero-denominator rates are `N/A`, not zero;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- same-seed agent-side comparisons preserve the same synthetic world;
- alternative attention and evidence selectors are observer-side only;
- the random baselines and auxiliary sensor use independent deterministic seed namespaces;
- longitudinal inherited and naive populations use the same canonical simulation engine;
- inherited priors do not create reporters, trust or host memory;
- research archives and interpretations never feed evaluator truth back into the species.

Historical frozen audits and protocols live under `research/2026-09-12/`.

## Research questions

The laboratory can now distinguish three separate questions:

1. **Where should attention go?** Compare selectors at the same investigation budget.
2. **Where is extra evidence valuable?** Compare second-look selectors at the same measurement budget.
3. **Does extra evidence actually improve decisions?** Measure Brier/error changes before integrating any mechanism into an agent.

This lets us ask whether curiosity is useful because it notices unusual things, because it identifies ambiguous things worth measuring, or merely because it spends more resources.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** experimental integrity — explicit evaluation contract, reproducible worlds, family/phase breakdowns and calibrated confidence.
- **v0.16:** equal-attention research — matched investigation budgets and observer-side efficiency curves.
- **v0.17 — bounded second look:** **current** — equal-cost noisy synthetic evidence acquisition, still shadow-only.
- **next:** run second-look comparisons across paired seeds; stress stale/incorrect heritage; only then consider a tightly bounded agent-side evidence interface if the shadow study demonstrates value.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
