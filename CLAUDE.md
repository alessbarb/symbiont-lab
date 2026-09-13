# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope

Symbiont Lab is a Python 3.11+ research prototype for distributed defensive intelligence, evolving under [roadmap issue #36](https://github.com/alessbarb/symbiont-lab/issues/36) from a pure synthetic simulator toward a benevolent organism that can perceive a **consenting** local host through safe, normalized senses. As of 2026-09-13 (roadmap Milestone A, issues #32-#35) this is an explicit, deliberate pivot from the prior simulation-only boundary — confirmed by the project owner — not an erosion of it. Every prohibition below stays absolute; only real, read-only, non-identifying host telemetry is now in scope, and only under the invariants stated here.

**Still, unconditionally, never:** network scanning or exchange, propagation, persistence, stealth/evasion, OS modification (writes/execution), exploitation, credential access, peer discovery, quarantine or remediation actions, autonomous real-world actions of any kind, or collection of identifying/user-content data (hostname, username, addresses, paths, command lines, file contents). These are load-bearing, not a style preference, and apply identically to the synthetic simulator and to any real-perception code.

**Now in scope, narrowly:** real sensor providers reading OS-agnostic, aggregate host signals (CPU, memory, storage, thermal, power, aggregate process activity) — never identity or content — under every one of these invariants:

- Discovery and sampling are explicit, local, read-only and least-privileged; consent is checked before every sample, not just once at startup.
- Cognition (`symbiont`) consumes only normalized capabilities/perceptions — typed values, units, monotonic timestamps, provenance, quality, privacy classification — never raw telemetry and never OS APIs directly.
- Platform/sensor providers never import cognition; cognition never imports a specific platform provider. (Mirrors the existing `symbiont` never-imports-`symbiont_lab` rule below, one level down: perception providers are apparatus, not organism.)
- Raw telemetry does not enter collective knowledge; ground truth (real or synthetic) stays outside organism cognition exactly as it always has.
- Failure of one sensor cannot stop the organism; bounded CPU/memory/storage overhead; deterministic fake-provider tests are required, real-provider integration is CI-smoke-tested separately.
- No threat classification during acclimation — an initial host baseline is learned while explicitly withholding threat conclusions.

**Stop and get an explicit decision before merging** anything that would need a new permission class, could collect identifying/user-content data, enables network exchange, introduces unbounded overhead, or changes the real-world-action boundary (write/execute/quarantine/persist/discover peers/propagate). None of those are ever "just this once" — they require the same kind of explicit, recorded pivot this section itself just went through.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

pytest                                     # full suite
pytest tests/experimental_integrity/       # scientific invariants
pytest tests/smoke/                        # CLI & server smoke tests

symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab dashboard --port 8765
symbiont-lab experiment run experiments/<domain>/<name>/experiment.toml
symbiont-lab study run <protocol> --seeds 101,127,149
```

Legacy entrypoints (`symbiont-sim`, `symbiont-dashboard`, `symbiont-causal-budget-study`, etc.) remain as deprecated wrappers — prefer the unified `symbiont-lab` CLI for anything new. README.md documents current protocols, flag sets and defaults — check it before adding a new experiment or study rather than guessing conventions.

## Architecture

Two epistemologically decoupled packages under `src/`:

- **`symbiont`** (the organism / research subject): `core/` (agent cognition, host model, bounded memory, collective consensus, reasoning, curiosity, metacognition, heritage), `environment/` (synthetic ecology, regime shifts, `rng.py`'s deterministic orthogonal RNG streams), `simulation/` (engine, sensory-vs-evaluator event split, evaluation, metrics, result/snapshot structures).
- **`symbiont_lab`** (the scientific apparatus): `experiments/` (declarative TOML specs, loader, manifest, protocol registry, `runner.py`), `studies/` (`attention/`, `evidence/`, `heritage/`, `campaigns/`, `common/`), `archive/` (append-only run/study/lineage memory under `.symbiont/`), `cli/` (the `symbiont-lab` entrypoint), `dashboard/` (localhost-only visualization).

**`symbiont` never imports `symbiont_lab`.** Ground truth belongs exclusively to the evaluator/apparatus and never feeds back into organism cognition. This is enforced by AST inspection in CI (`tests/experimental_integrity/`), not just convention — the same enforcement model the real-perception carve-out above extends one level down (platform sensor providers vs. cognition).

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

When modifying an experiment module, check whether an existing test encodes one of these invariants — `tests/experimental_integrity/` (AST dependency checks, RNG independence, world digests, seed pairing, evidence replay idempotency, prefix causality) and `tests/regression/` (historical audits, e.g. `audits/v021`, `audits/v024`) — before changing behavior.

### Research archive

`research/` holds frozen, versioned audits/protocols (e.g. `v0.13-audit/`, `v024-audit/`) of past experiment runs — treat these as historical records, not living docs. They (and evaluator truth in general) never feed back into the simulated species itself.
