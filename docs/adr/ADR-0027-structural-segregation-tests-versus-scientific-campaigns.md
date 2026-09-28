# ADR-0027: Structural Segregation: Mechanical Test Verification vs Scientific Campaign Execution

## Status

Accepted

## Context

In computational science monorepos, developer productivity and continuous integration (CI) often suffer when long-running empirical simulations, population studies, and model training are mixed into unit test runners (`pytest`). Treating scientific experiments as test assertions leads to slow test suites, flaky CI runs due to stochastic convergence variations, or developers artificially truncating experiment parameters to appease test timeouts.

## Decision

1. **Strict root segregation.**
   - `tests/`: Mechanical contracts, software invariant checks, boundary gates, determinism verifications, and regression tests. Executable via `pytest` in standard development loops.
   - `experiments/`: Scientific campaigns, empirical parameter sweeps, ablation studies, and replication configurations. Never collected or executed by `pytest`.
2. **Pytest configuration lock.** `pyproject.toml` explicitly configures `testpaths = ["tests"]`. `experiments/` is excluded from test discovery by default.
3. **Explicit campaign entrypoints.** Scientific experiments are executed strictly through documented CLI commands (`symbiont-lab study ...`, `symbiont-lab simulate ...`) or dedicated runner scripts, outputting structured evidence bundles and manifest logs into the immutable archive.
4. **Mechanical contract tests for experimental runners.** Fast, deterministic contract tests verifying protocol schemas, configuration parsing, and runner invocation boundaries belong in `tests/experiments/` marked with `@pytest.mark.experiment_contract`.

## Consequences

- Continuous integration and developer validation run in seconds, maintaining tight feedback loops.
- Scientific experiments are allowed to run for hours or days with full sample sizes without breaking test harnesses.
- Eliminates the anti-pattern of asserting statistical hypotheses as unit test boolean passes.

## Introduced in

v0.25.0 / Repository Guidelines.

## Evidence

`pyproject.toml` (`testpaths = ["tests"]`), `AGENTS.md`, `tests/experiments/`.
