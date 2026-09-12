# Repository Guidelines

## Project Structure & Module Organization

Symbiont Lab is a Python 3.11+ **simulation-only** research prototype. Source lives in `src/symbiont/`: `model.py` defines observations and adaptive baseline statistics, `memory.py` implements bounded episodic/semantic memory, `agent.py` handles local assessment, `collective.py` manages shared beliefs and open questions, `world.py` provides synthetic hosts/events, `simulation.py` coordinates runs and keeps ground truth in the evaluator, and `cli.py` exposes the command line. Tests live in `tests/`.

## Build, Test, and Development Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-sim --hosts 100 --steps 300 --seed 7
pytest
```

Without installing the CLI, run `PYTHONPATH=src python -m symbiont.cli --hosts 100 --steps 300 --seed 7`. Keep seeds explicit when comparing experiments.

## Experimental Integrity

Ground truth belongs to the simulator/evaluator, never to the agent. `Observation` must not expose labels such as benign/pathogen. Agents may learn only from perceived synthetic features, their own beliefs, bounded memory, and collective reports. Metrics must be calculated outside the agent. When adding an experiment, preserve a deterministic seed and document before/after behavior.

## Coding Style & Testing

Use four-space indentation, `snake_case`, `PascalCase`, type annotations, and dataclasses for structured state. Keep statistical logic separate from orchestration and CLI output. Use pytest with deterministic synthetic cases, including ambiguity, false positives, false negatives, forgetting, disagreement, poisoning, and calibration as those capabilities are introduced.

## Commit & Pull Request Guidelines

Use concise imperative commit subjects and focused PRs. PRs should explain intent, list test commands/results, and include deterministic seeds plus before/after metrics when simulation behavior changes.

## Safety Boundaries

Keep all hosts, observations, pathogens and interventions synthetic. Do not introduce real endpoint monitoring, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, or real user data. Share coarse behavioral abstractions rather than raw host data. Reasoning layers may propose hypotheses/questions over synthetic state only; they must not generate or execute real system actions.
