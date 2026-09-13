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

### Organism milestone: v0.29 host discovery protocol

Symbiont can now discover the safe capabilities offered by a consenting local host
through an OS-agnostic manifest. Platform-specific providers sit outside cognition,
fail independently, and are constrained by a default policy that permits only local,
read-only discovery. The built-in provider reports only Python runtime, logical CPU
and monotonic-clock capabilities; it collects no hostname, username, address, path
or user content.

### Organism milestone: v0.30 sensor reading contract

Symbiont now has a typed contract for a single sample from a discovered capability:
`SensorReading` carries a unit, a monotonic timestamp, a quality
(nominal/degraded/stale/unavailable), and a privacy class that is always aggregate
or non-identifying — there is no identifying option in the type. A reading is only
trustworthy once checked against the v0.29 discovery manifest
(`reading_matches_manifest`); this milestone defines the shape of a reading only —
no real sensor samples a host yet (that starts at v0.31).

### Organism milestone: v0.31 cross-platform resource provider

Symbiont can now sample real, read-only readings from a consenting local host:
CPU load (as a load-per-logical-core ratio) and disk usage (as a percent), using
only Python's standard library — this project keeps zero runtime dependencies.
Memory, thermal and power are intentionally reported as `unavailable` rather than
approximated, since stdlib alone has no portable, safe way to read them.
`HostSampler` only ever returns a reading for a capability/source pair v0.29's
discovery already accepted (`reading_matches_manifest` as a hard gate), and one
provider failing cannot blind the others — the same isolation guarantee v0.29's
`HostDiscovery` already gives.

### Organism milestone: v0.32 sensor lifecycle

Symbiont can now run bounded, repeated discovery-and-sampling ticks through
`HostLifecycle`: hot capability changes are observable across ticks
(`capability_changes()`), a reading provider that keeps failing is skipped for a
growing number of ticks instead of being retried every single one — and is
retried at full frequency again the moment it next succeeds — and history never
grows past a fixed `history_limit`. Nothing here changes what v0.29-v0.31 already
discover or sample; this only governs how repeatedly and resiliently they run.

### Organism milestone: v0.33 acclimation — Milestone A complete

Symbiont can now learn an initial descriptive baseline (mean, stdev, sample count)
per capability from real readings via `HostAcclimation`, closing
[Milestone A — Safe real perception](https://github.com/alessbarb/symbiont-lab/issues/32)
(v0.30-v0.33). Threat classification is withheld by construction, not just by
convention: `CapabilityBaseline`'s only public fields are `count`/`mean`/`variance`/
`stdev` — there is no deviation, novelty or anomaly signal anywhere in this
milestone's surface. `baseline()` itself returns `None` until enough samples exist,
so even a two-point average is never treated as something to act on. Distinguishing
novelty from gradual change is explicitly [Milestone B](https://github.com/alessbarb/symbiont-lab/issues/34)'s
job (v0.36), not this one's.

### Organism milestone: v0.34 percept synthesis — Milestone B begins

Symbiont can now turn a real sensor reading into a `Percept`: a platform-neutral
perception identified only by a stable semantic name (`system_load`,
`storage_pressure`), never by the `capability_id`/`source` tokens discovery and
sampling use internally. This is the first step of
[Milestone B — Adaptive host model](https://github.com/alessbarb/symbiont-lab/issues/34)
(v0.34-v0.37), and it exists specifically so that a future cognition component
can consume percepts without ever importing a platform provider — the milestone's
own exit gate. A capability with no entry in the percept-name mapping is skipped
rather than guessed at, so an unrecognized signal never reaches cognition under
an invented name.

### Organism milestone: v0.35 context and rhythms

Symbiont can now learn a separate descriptive baseline per (percept, time-of-day)
pair via `RhythmModel` — e.g. "system_load tends to run lower at night than in
the afternoon" — plus which percepts co-occur within a given time bucket. Time of
day is quantized into four coarse, cyclical buckets (night/morning/afternoon/
evening) by `time_bucket_for_hour`; the actual hour is read only to compute the
bucket and is never stored or exposed, so nothing here can reveal a calendar date
or exact schedule — only a recurring phase of day. Reuses v0.33's bounded,
O(1)-per-context statistics machinery, and keeps the same guarantee: a baseline's
only public fields are `count`/`mean`/`variance`/`stdev`, no deviation or anomaly
signal anywhere.

### Organism milestone: v0.36 drift-aware beliefs

Symbiont can now separate three ways a percept can relate to its own baseline:
a one-off `isolated` outlier, an in-progress but unconfirmed `gradual` shift,
and a `regime_shift` confirmed after enough consecutive deviations in the same
direction. `DriftAwareBaseline` buffers a candidate run and only commits it to
the baseline once confirmed — discarding it if the run breaks first — so a
single spike, or a revert back to normal after one, never contaminates the
baseline (an earlier continuously-tracking design was tried and rejected for
exactly this failure mode; see the class docstring for the full account).
Known limitation: this detects a sustained *step*, not slow creep — a value
drifting by a tiny increment every tick never crosses the deviation threshold
on any single observation, so true gradual creep is out of scope for this
release. `DriftObservation` keeps the same discipline as every other host
module: it exposes only a classification label and a z-score, never a threat
or security verdict.

### Organism milestone: v0.37 safe checkpoints

Symbiont can now export and re-import the abstract beliefs learned by
v0.33/v0.35/v0.36 (acclimation baselines, per-time-bucket rhythms, drift
baselines) as a single schema-versioned JSON document, via
`export_checkpoint`/`import_checkpoint`. A checkpoint carries only what
those modules already commit to exposing — count/mean/variance per
capability, context or percept — never a raw reading, a capability detail
or a timestamp; `import_checkpoint` refuses anything not written by the
current schema version outright rather than guessing at a migration. A
drift baseline's pending, unconfirmed streak buffer (raw recent values) is
deliberately never exported — a restored drift baseline always resumes
with a clean slate for any in-progress candidate shift, only the already-
committed baseline carries over. This completes Milestone B (#34): restarts
can now restore only safe abstract state, never raw telemetry.

### Organism milestone: v0.38 live attention budget

Symbiont's cognition (`symbiont.core`) now depends on `symbiont.host` for the
first time: `attend_to_host` allocates a hard, bounded attention budget across
a host's known capabilities via `AttentionBudget`, weighted by
`uncertainty_from_baseline` — an unacclimated capability always outranks an
established one; among established ones, higher coefficient-of-variation
(more relatively-uncertain) wins. Selection is a greedy uncertainty-per-cost
heuristic, not an exact knapsack solve, with deterministic name tie-breaks.
Same discipline as `docs/adr/ADR-0003-attention-is-not-classification.md`:
this is a resource-allocation mechanism, not a threat or classification
judgment — `AttentionAllocation` exposes only `name`/`uncertainty`/`cost`.
Begins Milestone C (#33); "the organism can state why a pattern is uncertain"
now has a number attached to it, though the full inspectable narrative is
v0.41's job, not this release's.

### Organism milestone: v0.39 read-only second look

`SecondLookSession` lets the organism temporarily sample one already-
discovered capability at higher resolution — e.g. the capability v0.38's
attention allocation ranked most uncertain — for a bounded number of ticks.
Three properties hold by construction, not caller discipline: **authorized**
(the constructor rejects any capability id the host's own manifest doesn't
already report as available — it can request a closer look, never a new
kind of measurement), **read-only** (every tick delegates to `HostSampler`,
which never writes), and **cancellable** (`cancel()` ends a session early;
`is_active` reflects both the cancellation and the `max_ticks` bound).
Continues Milestone C (#33).

### Organism milestone: v0.40 evidence revision

`EvidenceRevisionLedger` folds a batch of new evidence (e.g. a v0.39 second
look) into an existing acclimation baseline via `HostAcclimation.observe`,
the same way any other reading would be — a conflicting batch is never held
back or discarded, since a belief should still move toward what was
actually observed. What "preserving contradiction and dissent" adds is
narrower: when the evidence's mean is `conflict_z` or more standard
deviations from the prior baseline, a `DissentRecord` is appended to a
bounded, inspectable ledger (`dissent_history`) — the fact that a revision
was contested is kept, not smoothed away as if the evidence had agreed all
along. A zero-stdev prior is never flagged (no basis to compute a z-score
from). `DissentRecord` exposes only statistical fields, the same
classification-free discipline as everything else here. Continues
Milestone C (#33); v0.41 (organism narrative) remains.

### Organism milestone: v0.41 organism narrative — Milestone C complete

`narrate_host`/`narrate_capability` are the capstone of Milestone C: for
each capability, they gather v0.33's baseline, v0.38's `AttentionAllocation`
and v0.40's evidence count/`DissentRecord` into one `NarrativeEntry` with a
plain-language `summary` — e.g. *"compute.logical_cpu is familiar, with a
relative uncertainty of 0.000; it received attention this tick, 3 new
reading(s) were gathered as evidence."* An unacclimated capability is
reported `unfamiliar` with infinite uncertainty rather than omitted. Every
field is already something those three earlier releases commit to exposing
— this only composes them; `NarrativeEntry` carries no raw reading and no
threat or classification verdict (ADR-0003 applies here too). This directly
answers the gap flagged when Milestone B closed ("the organism can state
why a pattern is familiar, novel or uncertain") — it now can, per capability,
in one inspectable object.

**Milestone C (#33, v0.38–v0.41) is complete.**

### Strict Epistemological Rule
The experimental subject (`symbiont`) **never** imports or depends on the scientific apparatus (`symbiont_lab`). Synthetic ground truth belongs exclusively to the evaluator and never feeds back into agent cognition. This boundary is enforced via continuous AST inspection in CI.

## Organism roadmap

Development from real perception through cooperative intelligence is defined in
[the organism roadmap](docs/roadmap.md) and tracked in
[GitHub issue #36](https://github.com/alessbarb/symbiont-lab/issues/36).

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

# 14. Classify each percept against its own aging baseline: isolated, gradual or regime shift
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

Symbiont cognition and all threats remain synthetic. Real-host interaction is limited to explicit, local, read-only, identity-free capability discovery. Never introduce remote discovery, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions, or collection of user content.
