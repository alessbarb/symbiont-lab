# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.9 — reproducible studies

A single simulation can be misleading. v0.9 adds paired comparative studies: the same seeds are run under a baseline and a variant while changing exactly one supported synthetic parameter.

Supported comparison axes:

- `threat_rate`
- `poison_fraction`
- `heterogeneity`
- `drift_fraction`
- `drift_magnitude`

The study runner reports mean, population standard deviation, minimum and maximum for detection, precision, false positives, calibration, blind spots, drift recovery, curiosity and metacognitive metrics.

Example:

```bash
symbiont-study \
  --title "Poisoning resilience" \
  --parameter poison_fraction \
  --baseline 0.00 \
  --variant 0.12 \
  --seeds 3,7,11,17,23 \
  --hosts 100 --steps 300
```

Because baseline and variant use the same seed set, differences are less dominated by random world generation than unrelated one-off runs.

## Dashboard and research memory

```bash
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08
```

Open `http://127.0.0.1:8765`. The dashboard still launches annotated experiments, visualizes them live, stores completed runs in `.symbiont/experiments.jsonl`, compares recent results and can reload previous configurations.

Study-mode controls in the dashboard are the next UI layer; v0.9 deliberately stabilizes the paired study engine and CLI first.

## Experimental integrity

- All worlds and threats are synthetic.
- Studies vary only whitelisted simulator parameters.
- Ground truth remains evaluator-only.
- Research memory and study statistics are observer-side and never feed back into agents.
- Curiosity remains shadow-only and non-operational.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9 — reproducible studies:** **current** — paired seeds, baseline vs variant and aggregate statistics.
- **v0.10 — study dashboard:** launch and inspect paired studies from the browser.
- **v0.11 — longitudinal species:** compare learned population states across simulated generations without sharing evaluator truth.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
