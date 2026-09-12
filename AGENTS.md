# Repository Guidelines

## Project Structure & Module Organization

Symbiont Lab is a Python 3.11+ **simulation-only** research prototype. `model.py` defines observations/baselines, `memory.py` bounded memory, `agent.py` heterogeneous local agents, `collective.py` trust-weighted shared beliefs, `world.py` synthetic hosts/events, `simulation.py` orchestration/evaluation/live snapshots, `dashboard.py` localhost-only visualization, and `cli.py` batch experiments.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
symbiont-sim --hosts 100 --steps 300 --seed 7
symbiont-dashboard --hosts 100 --steps 300 --seed 7
```

Keep seeds explicit when comparing experiments.

## Experimental Integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents may use only synthetic observations, local memory, their own beliefs and collective reports. Source reputation must not consult truth labels. Metrics such as the honest-vs-poisoned trust gap may use ground truth only in the external evaluator/dashboard and must never feed back into agent decisions.

## Coding & Tests

Use Python type annotations and dataclasses, keep statistical logic separate from presentation, and add deterministic pytest cases for ambiguity, forgetting, disagreement, reputation, poisoning, calibration and streaming snapshots. Avoid new dependencies unless they materially improve the research model.

## Safety Boundaries

Keep every host, pathogen, reporter and intervention synthetic. Do not introduce real endpoint monitoring, scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions or real user data. Reasoning layers may propose hypotheses/questions over synthetic state only; they must not generate or execute real system actions.
