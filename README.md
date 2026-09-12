# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.10 — unified study dashboard

The localhost dashboard now launches both **single experiments** and **paired comparative studies**.

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --no-autorun
```

Open `http://127.0.0.1:8765`.

### Single experiment

The existing launcher records title, hypothesis, success criteria, notes and all synthetic-world parameters. Runs are visualized live and completed results can be stored in `.symbiont/experiments.jsonl`.

### Comparative study

The new study panel reuses the visible single-experiment configuration as the base world, then asks for:

- study title;
- one whitelisted comparison parameter;
- baseline value;
- variant value;
- a shared seed list.

Baseline and variant use the same seeds. The dashboard shows live progress through the paired runs and, when complete, displays means, deltas and population standard deviations for detection, precision, false positives, calibration, blind spots, drift recovery, curiosity and metacognition.

Only one experiment or study can run at a time from the dashboard.

The CLI remains available:

```bash
symbiont-study --parameter poison_fraction --baseline 0 --variant 0.12 --seeds 3,7,11,17,23
```

## Research integrity

- All hosts, threats, drift and counterfactuals are synthetic.
- Study statistics are observer-side and never feed back into the species.
- Comparative studies vary only whitelisted simulator parameters.
- Ground truth remains evaluator-only.
- Curiosity remains shadow-only and cannot execute probes.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9:** reproducible paired studies from CLI.
- **v0.10 — unified study dashboard:** **current** — single runs and paired studies from one browser UI.
- **v0.11 — study memory:** persist aggregate study results and reload full study definitions.
- **v0.12 — longitudinal species:** simulated generations and inheritance of bounded abstract knowledge.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
