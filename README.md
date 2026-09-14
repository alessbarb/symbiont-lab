# Symbiont Lab

A **safe, consent-gated research prototype** evolving from a synthetic-ecology laboratory into a benevolent digital organism that can reside on a real, consenting local host. Every capability it gains is bounded, local, read-only and reviewed by the project owner before it ships: no propagation, no persistence beyond an owner-installed checkpoint, no network scanning, no OS modification, no stealth/evasion, no exploitation, no collection of user content or identity.

## Architecture: Two Decoupled Packages

Symbiont Lab is structured as an epistemologically decoupled monorepo:

* **`symbiont`** (Research Subject — the organism):
  * `core/`: Agent cognition (`agent.py`), host model (`model.py`), bounded memory (`memory.py`), revisable local beliefs (`beliefs.py`), collective consensus (`collective.py`), reasoning (`reasoning.py`), curiosity planner (`curiosity.py`), metacognition (`metacognition.py`), heritage (`heritage.py`), the organism self-model (`selfmodel.py`), the continuous cognitive cycle (`runtime.py`), consent/resource governance (`governor.py`), the resident lifecycle (`resident.py`), and the bridge wiring cognition into the tick loop (`cognition_bridge.py`).
  * `host/`: Real, read-only local perception — discovery, sampling, acclimation, percepts, rhythms, drift, checkpoints, second-look investigation, and the developmental sensing layer (`adaptive.py`).
  * `cognition/`: The endogenous-plasticity kernel — closed node/edge catalogs and hard limits (`types.py`, `limits.py`), the genome schema and codec (`genome.py`), the plastic cognitive graph and its activation (`graph.py`, `activation.py`), label-free learning (`learning.py`), metaplasticity and safe-mode (`metaplasticity.py`), structural plasticity (`structure.py`), and checkpoint persistence (`checkpoint.py`).
  * `environment/`: Synthetic ecology (`world.py`), regime shifts (`regimes.py`), and deterministic orthogonal RNG streams (`rng.py`).
  * `simulation/`: Engine orchestrator (`engine.py`), sensory vs evaluator events (`events.py`), evaluation counts (`evaluation.py`), mathematical metrics (`metrics.py`), result structures (`result.py`), and streaming snapshots (`snapshots.py`).

* **`symbiont_lab`** (Scientific Apparatus — never imported by the organism):
  * `experiments/`: Declarative experiment specs, loader (`loader.py`), execution manifests (`manifest.py`), protocol registry (`registry.py`), and unified runner (`runner.py`).
  * `studies/`: Research protocols organized by domain: `attention/`, `evidence/`, `heritage/`, and `campaigns/`, backed by `common/` statistical and digest utilities.
  * `evolution/`: Laboratory-only generational evolution — declarative genome mutation (`mutation.py`), Pareto-archive selection over evaluation results (`evaluation.py`), and an append-only lineage archive (`lineage.py`). An individual organism never reproduces or deploys itself; this is entirely the apparatus's job.
  * `archive/`: Append-only research memory for runs, studies, and lineages (`.symbiont/`).
  * `cli/`: Unified command-line interface (`symbiont-lab`).
  * `dashboard/`: Localhost-only passive visualization.

### Strict Epistemological Rule

The experimental subject (`symbiont`, including its `cognition/` sub-package) **never** imports or depends on the scientific apparatus (`symbiont_lab`). Synthetic ground truth belongs exclusively to the evaluator and never feeds back into agent cognition. This boundary is enforced via continuous AST inspection in CI (`tests/experimental_integrity/`).

## Current status and changelog

Current status, milestone history, exit conditions and the full organism
changelog now live in [`ORGANISM.md`](ORGANISM.md).

## Running a real resident symbiont

A resident symbiont needs two things beyond the base organism: a **genome** (declarative, validated, bounds everything the phenotype may do) and a **cognitive graph** (the actual nodes/edges — there is no genome-driven auto-generation; the master design deliberately left initial topology to be explicitly authored, the same way you'd write a config file).

`examples/cognition/` ships a real, working starter brain, already verified end-to-end against a real machine's CPU/disk telemetry:

* `examples/cognition/genome.json` — a minimal, valid genome.
* `examples/cognition/graph.json` — two `SENSE` nodes wired to the built-in `system_load`/`storage_pressure` percepts, feeding a `CONCEPT` node, feeding a `READOUT`.

### One-shot run

```bash
symbiont-lab organism run --ticks 20 --min-samples 1 \
  --genome-file examples/cognition/genome.json \
  --graph-file examples/cognition/graph.json
```

Each tick's JSON output includes a `cognition` block: `readouts` (the graph's current output), `prediction_errors`, `structural_mutations_applied`, and `frozen` (true once `SafetyState` has tripped). The final `checkpoint.cognitive_bridge` field carries the whole learned graph state.

### Resident (continuous) launch

```bash
symbiont-lab organism live \
  --state-file ~/.local/state/symbiont/organism.json \
  --semantic-bootstrap \
  --genome-file examples/cognition/genome.json \
  --graph-file examples/cognition/graph.json \
  --interval 15 --stdout
```

`--semantic-bootstrap` is required here — `live` mode defaults to developing its own opaque senses rather than the two hand-labelled ones the example graph names; pass it to make `system_load`/`storage_pressure` actually populate. Stop with Ctrl-C or `SIGTERM`; the resident lifecycle checkpoints atomically on the way out.

### Resuming

`--genome-file`/`--graph-file` are **first-launch only**. Once `--state-file` exists, the genome and the entire learned graph (weights, structure, safety state, sensory normalizers) restore automatically from the checkpoint — passing the files again is not needed and is simply ignored in favor of what was actually learned:

```bash
symbiont-lab organism run --ticks 20 --state-file ~/.local/state/symbiont/organism.json
```

### Writing your own genome/graph

A genome is validated JSON matching `docs/design/endogenous-plasticity.md` §11's schema — see `examples/cognition/genome.json` for a complete instance. A graph is a JSON object with `nodes` (`node_id`, `kind` — one of `sense`/`concept`/`state`/`predictor`/`gate`/`readout`, optional `bias`/`tau`) and `edges` (`source_id`, `target_id`, `kind` — one of `excitatory`/`inhibitory`/`predictive`/`gating`, `weight`, optional `plasticity`/`delay_ticks`). `delay_ticks=0` is only valid when the edge's source is a `sense` node. A malformed file fails loudly with a clean error message and exit code 2 — never a silent fallback to a genome-less organism.

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

# 8. Discover the safe, read-only, identity-free capabilities this host offers
symbiont-lab host discover

# 9. Sample real, typed readings for the capabilities this host discovers
symbiont-lab host sample

# 10. Run bounded, backoff-aware discovery+sampling ticks
symbiont-lab host monitor --ticks 5

# 11. Learn a descriptive baseline per capability (no threat conclusions)
symbiont-lab host acclimate --ticks 5

# 12. Synthesize platform-neutral percepts from this host's real readings
symbiont-lab host perceive

# 13. Learn a per-time-bucket baseline and co-occurrence for this host's percepts
symbiont-lab host rhythms --ticks 5

# 14. Classify each percept against its own aging baseline: isolated, gradual, creep or regime shift
symbiont-lab host drift --ticks 5

# 15. Export safe abstract beliefs (no raw telemetry) to a schema-versioned checkpoint
symbiont-lab host checkpoint export --ticks 5

# 16. Restore beliefs from a checkpoint read on stdin
symbiont-lab host checkpoint export --ticks 5 | symbiont-lab host checkpoint import

# 17. Allocate a hard attention budget across this host's capabilities by uncertainty and cost
symbiont-lab host attend --ticks 5 --budget 1.5

# 18. Temporarily sample one already-discovered capability at higher resolution
symbiont-lab host second-look --capability-id compute.logical_cpu --ticks 5

# 19. Revise a capability's baseline from a second-look evidence batch, keeping any conflict as dissent
symbiont-lab host revise --capability-id compute.logical_cpu --acclimate-ticks 5 --evidence-ticks 3

# 20. Build an inspectable narrative combining belief, attention, evidence and uncertainty
symbiont-lab host narrate --ticks 5 --budget 1.5 --evidence-ticks 3

# 21. Sign a checkpoint into an offline, identity-minimized knowledge capsule
symbiont-lab capsule create --ticks 5 --keyfile my-signing-key.json

# 22. Verify a knowledge capsule's signature, read as JSON on stdin
symbiont-lab capsule create --keyfile my-signing-key.json | symbiont-lab capsule verify

# 23. Verify a capsule and learn per-source reliability against this host's own beliefs
symbiont-lab capsule create --keyfile their-key.json | symbiont-lab capsule ingest --ticks 5

# 24. Run the organism's continuous cognitive cycle: discover, observe, acclimate,
#     perceive, track drift, attend, investigate, revise, explain — repeatedly
symbiont-lab organism run --ticks 5 --attention-budget 1.5 --investigate-ticks 2

# 25. Run it under an explicit, revocable consent and resource budget
symbiont-lab organism run --ticks 10 --max-ticks 5 --min-seconds-between-ticks 1.0

# 26. Run it with durable state: resumes from --state-file if present, saves atomically after
symbiont-lab organism run --ticks 5 --state-file organism-state.json

# 27. Run it with defensive advisories enabled (separate, explicit consent required) and logged
symbiont-lab organism run --ticks 10 --advisory-consent --advisory-log advisories.json

# 28. Record a real operator's judgment of one fired advisory (laboratory apparatus, not cognition)
symbiont-lab evaluate advisories label --advisory-log advisories.json --labels-file labels.json \
  --tick 3 --capability-id compute.logical_cpu --judgment useful

# 29. Summarize usefulness/false-alarm rate against those real judgments
symbiont-lab evaluate advisories summary --advisory-log advisories.json --labels-file labels.json

# 30. Run it with a real cognitive graph: genome + hand-authored starting brain (first launch only)
symbiont-lab organism run --ticks 20 --min-samples 1 \
  --genome-file examples/cognition/genome.json --graph-file examples/cognition/graph.json

# 31. Live, resident, with cognition: developed senses off, semantic bootstrap on so the
#     example graph's sense names actually populate, checkpointed atomically on exit
symbiont-lab organism live --state-file ~/.local/state/symbiont/organism.json \
  --semantic-bootstrap --genome-file examples/cognition/genome.json \
  --graph-file examples/cognition/graph.json --interval 15 --stdout
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

* **ADR-0001:** Two-Package Architecture Boundary
* **ADR-0002:** Synthetic Ground Truth Isolation
* **ADR-0003:** Attention is Not Classification
* **ADR-0004:** Separated RNG Streams
* **ADR-0005:** Shadow-Only Second-Look Evidence Probes
* **ADR-0006:** Evidence Revision Identity
* **ADR-0007:** Common Causal Eligibility for Attention Allocation

## Testing Taxonomy

The test suite is organized into 5 epistemological suites:

* `tests/unit/`: Component-level unit tests for organism (`core`), real-host perception (`host`), endogenous plasticity (`cognition`), universe (`environment`), simulation engine (`simulation`), and lab apparatus including laboratory evolution (`lab/evolution`).
* `tests/integration/`: Multi-module pipelines and study workflows.
* `tests/experimental_integrity/`: Rigorous invariant checks: AST dependency checks (`symbiont` never imports `symbiont_lab`, `cognition` never imports `symbiont_lab`, `symbiont` never contains evolution code), RNG stream independence, deterministic world digests, seed pairing, evidence replay idempotency, and prefix causality.
* `tests/regression/`: Historical audit regression tests (e.g. `audits/v021`, `audits/v024`).
* `tests/smoke/`: CLI commands and dashboard server execution smoke tests.

```bash
pytest                                                     # full suite
pytest tests/experimental_integrity/                      # scientific invariants
pytest tests/smoke/                                       # CLI & server smoke tests
```

## Safety Boundaries

Real-host interaction is limited to explicit, local, read-only, identity-free capability discovery and the bounded developmental sensing and endogenous plasticity this document describes. Every learned or mutated value stays data under an immutable kernel — never generated, edited, or executed code, never a path, module name, command or permission. Still unconditionally prohibited: remote discovery, network scanning, propagation, persistence beyond an owner-installed checkpoint, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world action, and collection of user content or identifying metadata. See `CLAUDE.md` for the complete, authoritative boundary.
