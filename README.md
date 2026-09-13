# Symbiont Lab

A **safe, simulation-only** research prototype and scientific laboratory for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## Architecture: Two Decoupled Packages

Symbiont Lab is structured as an epistemologically decoupled monorepo:

* **`symbiont`** (Research Subject):
  - `core/`: Agent cognition (`agent.py`), host model (`model.py`), bounded memory (`memory.py`), revisable local beliefs (`beliefs.py`), collective consensus (`collective.py`), reasoning (`reasoning.py`), curiosity planner (`curiosity.py`), metacognition (`metacognition.py`), and heritage (`heritage.py`).
  - `environment/`: Synthetic ecology (`world.py`), regime shifts (`regimes.py`), and deterministic orthogonal RNG streams (`rng.py`).
  - `simulation/`: Engine orchestrator (`engine.py`), sensory vs evaluator events (`events.py`), evaluation counts (`evaluation.py`), mathematical metrics (`metrics.py`), result structures (`result.py`), and streaming snapshots (`snapshots.py`).

* **`symbiont_lab`** (Scientific Apparatus):
  - `experiments/`: Declarative experiment specs, loader (`loader.py`), execution manifests (`manifest.py`), protocol registry (`registry.py`), and unified runner (`runner.py`).
  - `studies/`: Research protocols organized by domain: `attention/`, `evidence/`, `heritage/`, and `campaigns/`, backed by `common/` statistical and digest utilities.
  - `archive/`: Append-only research memory for runs, studies, and lineages (`.symbiont/`).
  - `cli/`: Unified command-line interface (`symbiont-lab`).
  - `dashboard/`: Localhost-only passive visualization.

### Organism milestone: v0.28 revisable local beliefs

Each agent now maintains a bounded, private belief model for recurring synthetic
patterns. Beliefs accumulate evidence, expose uncertainty, register contradiction,
can reverse direction, and influence later assessments only in proportion to their
certainty. The model never receives evaluator labels or laboratory results.

### Strict Epistemological Rule
The experimental subject (`symbiont`) **never** imports or depends on the scientific apparatus (`symbiont_lab`). Synthetic ground truth belongs exclusively to the evaluator and never feeds back into agent cognition. This boundary is enforced via continuous AST inspection in CI.

## Unified CLI: `symbiont-lab`

All experiments, studies, audits, and reproductions are accessible through a single entrypoint:

```bash
# 1. Run a synthetic simulation
symbiont-lab simulate --hosts 100 --steps 300 --seed 7

# 2. Launch localhost dashboard
symbiont-lab dashboard --port 8765

# 3. Run a declarative experiment from TOML spec
symbiont-lab experiment run experiments/attention/causal-v0242-revalidation/experiment.toml

# 4. Run an experimental study protocol
symbiont-lab study run attention.replicated --seeds 101,127,149

# 5. Verify laboratory experimental invariants
symbiont-lab audit verify

# 6. List and inspect recent archived runs and studies
symbiont-lab archive list

# 7. Bitwise reproduction of an execution from its manifest
symbiont-lab reproduce .symbiont/runs/<run_id>/manifest.json
```

*(Legacy entrypoints such as `symbiont-sim`, `symbiont-dashboard`, `symbiont-causal-budget-study`, etc. remain available as deprecated backwards-compatible wrappers.)*

## Declarative Experiments & Manifests

Experiments are specified declaratively in TOML (using Python 3.11's stdlib `tomllib` with zero external dependencies):

```toml
schema_version = 1

[experiment]
id = "attention.causal.v0242-revalidation"
title = "Corrected causal attention revalidation"
protocol = "attention.replicated"
protocol_version = 3

[world]
hosts = 100
steps = 300
threat_rate = 0.018
poison_fraction = 0.08
heterogeneity = 0.12

[design]
seeds = [101, 127, 149, 173, 199]

[attention]
budgets_per_1000 = [5, 12, 20]
reference_strategy = "random"
```

Each run generates an immutable execution manifest in `.symbiont/runs/<run_id>/manifest.json` recording software version, git sha, master seed, config digest, world digest, selection digests, and metric outcomes.

## Architectural Decision Records (ADRs)

Formal laboratory memory is documented in `docs/adr/` and mirrored in `research/decisions/`:
- **ADR-0001:** Two-Package Architecture Boundary
- **ADR-0002:** Synthetic Ground Truth Isolation
- **ADR-0003:** Attention is Not Classification
- **ADR-0004:** Separated RNG Streams
- **ADR-0005:** Shadow-Only Second-Look Evidence Probes
- **ADR-0006:** Evidence Revision Identity
- **ADR-0007:** Common Causal Eligibility for Attention Allocation

## Testing Taxonomy

The test suite is organized into 5 epistemological suites:
- `tests/unit/`: Component-level unit tests for organism (`core`), universe (`environment`), simulation engine (`simulation`), and lab apparatus (`lab`).
- `tests/integration/`: Multi-module pipelines and study workflows.
- `tests/experimental_integrity/`: Rigorous invariant checks: AST dependency checks, RNG stream independence, deterministic world digests, seed pairing, evidence replay idempotency, and prefix causality.
- `tests/regression/`: Historical audit regression tests (e.g. `audits/v021`, `audits/v024`).
- `tests/smoke/`: CLI commands and dashboard server execution smoke tests.

```bash
pytest                                                     # full suite
pytest tests/experimental_integrity/                      # scientific invariants
pytest tests/smoke/                                       # CLI & server smoke tests
```

## Safety Boundaries

Symbiont Lab remains strictly a synthetic laboratory simulation. Never introduce real endpoint monitoring, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions, or real user data.
