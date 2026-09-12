# Repository Guidelines

## Project Structure & Module Organization

Symbiont Lab is a Python 3.11+ simulation-only research prototype. Source lives in `src/symbiont/`: `model.py` defines observations and baseline statistics, `agent.py` handles local assessment, `collective.py` manages shared knowledge, `world.py` provides synthetic hosts, `simulation.py` coordinates runs, and `cli.py` exposes the command line. Tests live in `tests/`, currently `test_model.py`. `pyproject.toml` defines packaging and dependencies; `README.md` documents architecture and experiments. There is no separate asset directory.

## Build, Test, and Development Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'        # Editable install with pytest
symbiont-sim --hosts 100 --steps 300 --seed 7
pytest                       # Run the full test suite
pytest tests/test_model.py -q # Run focused model/agent tests
```

Without installing the CLI, run `PYTHONPATH=src python -m symbiont.cli --hosts 100 --steps 300`. Packaging uses setuptools; no dedicated build script is configured. Keep seeds explicit when comparing experiments.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions and variables, `PascalCase` classes, and `UPPER_CASE` constants. Preserve type annotations and use dataclasses for structured simulation state where appropriate. Keep statistical logic separate from orchestration and CLI output. No formatter or linter is configured; avoid unrelated formatting changes and new dependencies without a clear need.

## Testing Guidelines

Use pytest with `test_*.py` files and descriptive `test_*` functions. Existing tests exercise baseline learning, disruptive-event detection, and collective confidence. Add deterministic synthetic cases for behavior changes, including boundary conditions and false positives. No coverage threshold is configured. Run the full suite before submitting; simulation metrics are not real-world security benchmarks.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so no existing commit convention could be verified. Use concise, imperative commit subjects and keep changes focused. Pull requests should explain intent, link relevant issues, list test commands and results, and include seeds and before/after metrics when changing simulation behavior.

## Safety Boundaries

Keep all hosts, observations, and pathogens synthetic. Do not introduce real endpoint monitoring, network scanning, propagation, persistence, OS modification, or access to real user data. Share coarse behavioral fingerprints rather than raw host data. Keep experimental conclusions scoped to the simulator.
