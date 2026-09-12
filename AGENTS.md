# Repository Guidelines

## Scope

Symbiont Lab is a Python 3.11+ **simulation-only** research monorepo containing two decoupled packages:
- **`symbiont`** (Research Subject): `symbiont.core` (agent cognition, memory, collective beliefs, reasoning, curiosity, metacognition, heritage), `symbiont.environment` (synthetic ecology, regimes, deterministic RNG streams), and `symbiont.simulation` (engine, events, evaluation, metrics, snapshots).
- **`symbiont_lab`** (Scientific Apparatus): declarative experiment runner (`experiments`), multi-seed studies (`studies`), run/study archives (`archive`), unified CLI (`cli`), and passive visualization (`dashboard`).

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Run full test suite
pytest

# Unified CLI commands
symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab dashboard --port 8765
symbiont-lab experiment run experiments/attention/causal-v0242-revalidation/experiment.toml
symbiont-lab audit verify
symbiont-lab archive list
symbiont-lab reproduce .symbiont/runs/<run_id>/manifest.json

# Legacy CLI wrappers (deprecated compatibility aliases)
symbiont-sim --hosts 100 --steps 300 --seed 7
symbiont-dashboard --hosts 100 --steps 300 --seed 7
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust. Hypotheses must be explanatory/information-seeking, never operational. Evaluator-only metrics must never feed back into agent decisions. Under no circumstances may `symbiont` import or depend upon `symbiont_lab` (enforced via AST CI tests).

## Testing

Use deterministic pytest cases across the 5 test suites:
- `tests/unit/`: fine-grained component tests (core, environment, simulation, lab)
- `tests/integration/`: multi-component pipelines and studies
- `tests/experimental_integrity/`: AST boundary, RNG isolation, identical-world determinism, paired seeds, shadow-sensor isolation
- `tests/regression/`: frozen historical audit invariants
- `tests/smoke/`: CLI and dashboard smoke tests

## Safety boundaries

Keep every host, pathogen, reporter and intervention synthetic. Do not introduce real endpoint monitoring, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions or real user data. The reasoning layer must not generate or execute real system actions.
