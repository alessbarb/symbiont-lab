# Repository Guidelines

## Scope

Symbiont Lab is a Python 3.11+ **simulation-only** research prototype. `model.py` defines synthetic observations, `memory.py` bounded memory, `agent.py` local agents, `collective.py` trust-weighted population beliefs, `reasoning.py` bounded hypotheses/questions, `world.py` synthetic ecology, `simulation.py` orchestration/evaluation/snapshots, and `dashboard.py` localhost-only visualization.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
symbiont-sim --hosts 100 --steps 300 --seed 7
symbiont-dashboard --hosts 100 --steps 300 --seed 7
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust. Hypotheses must be explanatory/information-seeking, never operational. Evaluator-only metrics must never feed back into agent decisions.

## Testing

Use deterministic pytest cases for ambiguity, forgetting, disagreement, reputation, poisoning, calibration, streaming snapshots and bounded reasoning. Keep seeds explicit when comparing experiments.

## Safety boundaries

Keep every host, pathogen, reporter and intervention synthetic. Do not introduce real endpoint monitoring, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions or real user data. The reasoning layer must not generate or execute real system actions.
