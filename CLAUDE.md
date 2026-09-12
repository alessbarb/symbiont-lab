# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope

Symbiont Lab is a Python 3.11+ **simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic. Never add real endpoint monitoring, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions, or real user data — this boundary is load-bearing for the project's purpose, not a style preference.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

pytest                                  # full suite
pytest tests/test_causal_budget.py      # single file
pytest tests/test_causal_budget.py::test_name -v   # single test

symbiont-sim --hosts 100 --steps 300 --seed 7
symbiont-dashboard --hosts 100 --steps 300 --seed 7
```

Other experiment CLIs are registered in `pyproject.toml` under `[project.scripts]` (e.g. `symbiont-causal-budget-study`, `symbiont-evidence-noise-sweep`, `symbiont-heritage-stress-study`); each pairs with a `<name>.py` module and `<name>_cli.py` entry point in `src/symbiont/`. README.md documents current flag sets and defaults for each — check it before adding a new experiment CLI rather than guessing conventions.

## Architecture

Core simulation modules, each roughly one concern:

- `model.py` — synthetic observation/data structures
- `memory.py` — bounded per-agent memory
- `agent.py` — local agent decision logic
- `collective.py` — trust-weighted population beliefs
- `reasoning.py` — bounded hypotheses/questions (explanatory only, never operational)
- `world.py` — synthetic ecology (hosts, pathogens, drift)
- `simulation.py` — orchestration, evaluation, snapshots
- `dashboard.py` — localhost-only visualization
- `rng.py` — deterministic per-namespace RNG derivation (see below)

Research/experiment lines build on this core as separate modules + paired CLI (`experiment.py`, `budget.py`/`causal_budget.py`/`causal_budget_study.py`, `evidence.py`/`evidence_study.py`/`evidence_noise_sweep.py`, `heritage.py`/`heritage_stress.py`/`heritage_stress_study.py`, `longitudinal.py`, `campaign.py`, `study.py`/`study_archive.py`, `curiosity.py`, `interpretation.py`, `metacognition.py`). Each new experimental capability tends to follow this pattern: a `_study` or `_stress` module drives replication across seeds, wrapping a lower-level single-run module, exposed via its own CLI entry point.

### Deterministic RNG streams

`rng.py`'s `make_rng_streams(seed)` derives independent `random.Random` streams per concern (profiles, agent traits, reporters, schedule, observations, drift) via `derive_seed(seed, namespace)` (SHA-256 of `symbiont-lab:{seed}:{namespace}`). This is the mechanism that keeps unrelated randomness from perturbing other axes — e.g. changing reporter poisoning must not shift the trait sequence. When adding a new randomized mechanism, derive its own namespaced stream rather than reusing or threading through an existing one.

### Experimental integrity invariants

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may only use synthetic observations, local memory, collective reports, coarse fingerprints and derived trust — never evaluator truth. This is enforced throughout the codebase and its tests; concrete invariants (see README.md "Experimental integrity" and `research/` for frozen audits of each version) include:

- attention/evidence experiments are observer-side (shadow-only) and must not change agent decisions;
- causal attention selectors cannot inspect future scores;
- replicated studies require unique seeds per run and preserve per-world/per-seed pairing;
- same-seed comparisons must reproduce the same synthetic world;
- repeated trust recalibration without fresh reports is idempotent;
- undefined/optional longitudinal rates stay `N/A`, never silently become `0`;
- generation 1 is a parity control, excluded from mean heritage-effect estimates.

When modifying an experiment module, check whether an existing test encodes one of these invariants (e.g. `test_experimental_integrity.py`, `test_engine_integrity_v021.py`) before changing behavior.

### Research archive

`research/` holds frozen, versioned audits/protocols (e.g. `v0.13-audit/`, `v024-audit/`) of past experiment runs — treat these as historical records, not living docs. They (and evaluator truth in general) never feed back into the simulated species itself.
