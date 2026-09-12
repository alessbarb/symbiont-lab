# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.18 — replicated bounded-evidence studies

The bounded second-look experiment is now reproducible across paired synthetic worlds rather than judged from one seed.

`symbiont-evidence-study` runs the same selectors on a seed set and preserves the per-seed pairing against a reference strategy, normally deterministic random selection. It summarizes:

- mean, dispersion and range of Brier gain;
- entropy reduction;
- corrected and introduced error rates;
- net correction rate;
- selected threat share;
- `stealth_sim` share and correction rate;
- paired deltas versus the reference selector;
- direction agreement and number of defined pairs.

No statistical significance is implied by direction agreement. It is descriptive evidence about whether the same effect appears repeatedly across the chosen synthetic worlds.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-evidence-study \
  --seeds 3,7,11,17,23 \
  --hosts 100 \
  --steps 300 \
  --threat-rate 0.018 \
  --sensor-noise 0.18
```

With no explicit `--budget`, every seed uses the natural investigation count of the live policy in that world. Those budgets are preserved individually rather than falsely described as identical. Use `--budget N` when the research question requires a fixed absolute evidence budget across seeds.

The single-seed shadow experiment remains available:

```bash
symbiont-evidence --hosts 100 --steps 300 --seed 7
```

The equal-attention experiment remains available:

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
- attention/evidence selectors are observer-side only;
- random baselines and auxiliary sensor noise use independent deterministic seed namespaces;
- paired evidence studies keep per-seed comparisons instead of subtracting unrelated marginal means;
- longitudinal inherited and naive populations use the same canonical simulation engine;
- inherited priors do not create reporters, trust or host memory;
- research archives and interpretations never feed evaluator truth back into the species.

Historical frozen audits and protocols live under `research/2026-09-12/`.

## What v0.18 can tell us

The important question is no longer whether a selector looks good in one run. We can now ask whether, at equal evidence cost, a curiosity-like selector repeatedly obtains more useful evidence than random or risk-based selection.

A positive result would justify a later experiment in which a **bounded synthetic** second look influences an agent. A weak or inconsistent result would tell us to improve the selection or sensor model first, without adding complexity to the organism.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** experimental integrity — explicit evaluation contract, reproducible worlds, family/phase breakdowns and calibrated confidence.
- **v0.16:** equal-attention research — matched investigation budgets and observer-side efficiency curves.
- **v0.17:** bounded second look — equal-cost noisy synthetic evidence acquisition, shadow-only.
- **v0.18 — replicated evidence:** **current** — paired multi-seed second-look studies and reference comparisons.
- **next:** stale/incorrect heritage stress tests and reserved-seed evidence validation; only then consider a tightly bounded agent-side evidence interface if replicated results justify it.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
