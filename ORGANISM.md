# Organism changelog — the complete evolution

## Current status

**v0.79.20.** Milestones A through E2 are complete and Milestone H is implemented through its current roadmap boundary: safe real perception, adaptive host modeling, autonomous inquiry and explanation, operational/developmental embodiment, endogenous plasticity, biological memory consolidation, bounded physiology, ecological interaction, offline exchange/replay, evidence-aware trust, dissent-preserving revision, consent-bound local communication and bounded synthetic adversarial ecology. Milestone I enters implementation with irreversible physiology state, explicit metabolic intake, habitat release and a hard post-death execution boundary. Milestone J adds anti-capture attention, evidence hypotheses and shadow prediction; promotion and longitudinal gates remain open. Milestone K adds an explicitly authorized bounded social habitat, aggregate relation memory and finite-resource exchange/competition; emergence studies remain open. Network sockets, peer discovery and autonomous remediation remain disabled.

The canonical roadmap is implemented through Milestone H. Milestones I (fisiología integrada), J (desarrollo predictivo autónomo) and K (sociabilidad emergente) are in partial implementation. I closes vital and mortal needs; J improves hypothesis and prediction formation; K provides bounded cellular interaction capabilities without imposing social objectives.

Full milestone history and design are in [`docs/roadmap.md`](docs/roadmap.md), [`docs/design/endogenous-plasticity.md`](docs/design/endogenous-plasticity.md), and [`docs/design/reproduction-death-population.md`](docs/design/reproduction-death-population.md).

## Milestone A — Safe real perception (v0.30-v0.33)

Symbiont gained a typed contract for a single host reading (`SensorReading`: unit, monotonic timestamp, quality, and a privacy class that is always aggregate or non-identifying — there is no identifying option in the type), a cross-platform stdlib-only provider sampling real CPU load and disk usage read-only, a bounded repeated discovery-and-sampling lifecycle with per-provider backoff, and `HostAcclimation` — an initial descriptive baseline (mean/stdev/count) per capability with threat classification withheld by construction, not convention: `CapabilityBaseline`'s only public fields are `count`/`mean`/`variance`/`stdev`.

## Milestone B — Adaptive host model (v0.34-v0.37)

A real reading became a `Percept`: a platform-neutral perception identified only by a stable semantic name (`system_load`, `storage_pressure`), never by the internal `capability_id`/`source` tokens — specifically so cognition never needs to import a platform provider. `RhythmModel` learned a separate baseline per (percept, time-of-day-bucket) pair using only a coarse, cyclical four-bucket day quantization (the actual hour is read only to compute the bucket and never stored). `DriftAwareBaseline` separated a one-off `isolated` outlier from an in-progress `gradual` shift from a confirmed `regime_shift`, buffering a candidate run and only committing it once confirmed so a single spike never contaminates the baseline. `export_checkpoint`/`import_checkpoint` closed the milestone: a schema-versioned JSON document carrying only what those modules already commit to exposing, never a raw reading or timestamp.

## Milestone C — Autonomous inquiry and explanation (v0.38-v0.41)

`attend_to_host` allocated a hard, bounded attention budget across known capabilities by uncertainty-per-cost — a resource-allocation mechanism, never a threat judgment (`docs/adr/ADR-0003`). `SecondLookSession` let the organism temporarily sample one already-discovered capability at higher resolution, authorized/read-only/cancellable by construction. `EvidenceRevisionLedger` folded new evidence into the baseline while keeping a `DissentRecord` whenever the evidence significantly disagreed — contradiction is preserved, not smoothed away. `narrate_host` closed the milestone by composing belief, attention and evidence into one plain-language, classification-free `NarrativeEntry` per capability.

## Milestone D — Operational embodiment (v0.42-v0.49)

Knowledge capsules (`create_capsule`/`verify_capsule`, Ed25519-signed, identity-minimized) enabled offline, tamper-evident exchange — no network I/O, no peer discovery. `SourceTrustModel` learned local, per-source agreement between a capsule's claims and the organism's own beliefs (a known echo-chamber limitation, explicitly flagged for later evidence-aware trust work). `OrganismRuntime` replaced one-shot CLI verbs with a single continuous cognitive cycle; `GovernedOrganism` wrapped it with live-revocable consent and a hard tick/frequency budget; checkpoints gained atomic disk persistence and a migration chain; a `host-constrained-environment` CI job proved the host layer survives musl/Alpine. `DefensiveAdvisor` added a decision-gated, human-reviewed recommendation — never autonomous action — built only after the project owner resolved seven design questions on delivery, trigger, vocabulary, scope, rate limiting, persistence and consent up front. `symbiont_lab.evaluation.advisory_evaluation` closed the milestone by measuring advisories against a real operator's own judgment, one-way only, enforced by the same AST boundary that protects cognition from ground truth.

## Milestone E — Developmental embodiment (v0.50-v0.54)

The organism stopped needing a hand-written sensor catalog. `AdaptiveSenseModel` (v0.50) discovers bounded, vetted OS surfaces, assigns them opaque identities, and runs as a transparent, owner-installed `systemd --user` resident. v0.51 learned bounded same-time and lagged relations between senses and suppressed redundant ones (pairwise correlation ≥ 0.97). v0.52 developed active/probing/dormant sensory tiers, spending a rotating observation budget selectively rather than sampling everything every tick. v0.53 gave the organism a self-model: `SelfModel` learns per-sense cost (timed at the provider-call boundary), graduated health (from reading quality, not a binary success flag), and confidence (maturity × health × quality — composed from, never duplicating, existing signals) — feeding real relative-cost ranking into attention and a health gate into second-look investigation. v0.54 closed the milestone with long-run maturation: idle decay of self-model trust for a sense that's gone quiet, slow-creep detection in `DriftAwareBaseline` (a free-running fast EWMA normalized against a *frozen* noise floor — the live-stdev version was tried and rejected empirically for self-corrupting the very signal it measured), and checkpoint continuity so a restart never mistakes a freshly-active sense for one that's been idle since tick zero.

## Milestone E2 — Endogenous plasticity (v0.55-v0.59)

The organism's self-programming capability, implemented as **plasticity of data under an immutable kernel**, never generated, edited or executed code.

* **v0.55 — Genome kernel.** A closed `NodeKind`/`EdgeKind` catalog and hard, never-learnable `KernelLimits`; a declarative, versioned `Genome` validated by a strict, non-`eval` codec; genome identity via a deterministic sha256 hash; checkpoint persistence as its own bolt-on namespace.
* **v0.56 — Cognitive graph.** `PlasticNode`/`PlasticEdge` and a synchronous, double-buffered `CognitiveGraph.activate()` — deterministic regardless of construction order, because every node reads only from this tick's fresh sense inputs or last tick's frozen frame, never from a value still being computed in the same pass.
* **v0.57 — Label-free learning.** Prediction error via Huber loss, decaying eligibility traces, and bounded Oja weight updates, with no external label anywhere in the loop.
* **v0.58 — Metaplasticity and structure.** A five-dimension `LearningObjective` compared by Pareto dominance; bounded metaparameter adaptation; structural proposals, pruning lifecycle and `SafetyState` freeze.
* **v0.59 — Laboratory evolution.** `symbiont_lab/evolution/`: declarative genome mutation operators, Pareto-archive selection and cycle-protected append-only lineage. Evolution remains confined to explicit laboratory runs; the later resident reproduction capability is implemented separately and never by granting the organism access to the laboratory evolution apparatus.

**Post-milestone hardening (v0.59.1-v0.59.3):** a first fresh adversarial audit closed defects in normalizer persistence, structural mutation application, safety-state enforcement, finite objectives, lifecycle reachability, bounded structural bookkeeping, metaplasticity bounds, eligibility traces, node ids and lineage ancestry. `CognitiveBridge` then wired graph activation, learning and structural plasticity into `OrganismRuntime`, and graph-state checkpoint persistence closed restart continuity for the learned mind.

**v0.59.4 — second adversarial hardening pass.** Kernel limits are now enforced where mutations and checkpoints are actually committed, not merely declared. Structural batches validate through the same `CognitiveGraph` invariants as normal construction and apply transactionally, preventing an invalid learned edge from partially changing or crashing the resident graph. Plastic learning is no longer unconditional: attention selects the reachable learning subgraph, sensory health × availability modulates the update, eligibility must be present and each edge's own `plasticity` scales Oja. Checkpoint restore rejects impossible lifecycle metadata and ambiguous booleans, topology revision survives restart, and contradiction memory persists only as bounded per-capability counts so numeric evidence is not turned into a history log. Observatory now publishes topology on the first cognitive tick, survives `run_id` rollover without discarding the new sequence zero, tails journals by file position, validates malformed local artifacts defensively, actually resolves referenced JSON schemas in contract tests, and runs its complete test directory in CI. The Observatory resident can also receive the same first-launch genome/graph inputs as the main live CLI. Package/runtime metadata is aligned at 0.59.4.

**v0.59.5 — Biological memory consolidation.** A full technical design ([`docs/design/biological-memory-consolidation.md`](docs/design/biological-memory-consolidation.md)) changed the persistence model from "serialize learned state" to "persist consolidated memory": checkpoint schema v6, a `WeightStabilityTracker` that commits an edge's weight class only after epoch-spaced stability (node-atomic — a node's changed incoming edges commit together or not at all), a consolidated-baseline codec for host statistics (signed-log center, a constant sentinel plus log buckets for scale, a monotone maturity table over real observation support), and `SelfModel`'s `RecencyClass` replacing the exact `last_observed_tick`. A bounded reacclimation period after restart keeps the cold-start transient itself from ever being misread as a salient or structural event. PR #76's earlier continuity guarantee is deliberately superseded here, not silently dropped: a restart no longer reconstructs the previous tick's activation, because seeding one from a coarse class would synthesize a microstate that never actually occurred — worse than genuinely losing continuity. `MemoryConsolidator`'s salient-event fast path — a one-shot durable trace for one exceptional, attended, reliable transition, distinct from the ordinary slow path's epoch-spaced support requirement — is wired into the real `OrganismRuntime.tick()` loop, closing the one piece of the design that had no caller in the organism until this release. All eleven exit conditions in the design's §25 are satisfied.

## Milestone F — Digital physiology (v0.60-v0.64)

Implemented. `MetabolicLedger`, `InformationAssimilator`, `DegradationQueue`, `HomeostaticController` and `ViabilityController` provide bounded intake, metabolism, maintenance, degradation, repair, dormancy and irreversible death semantics.

## Milestone G — Reproduction and heredity (v0.65-v0.69)

Implemented. `HabitatBirthAuthority` governs identity and lineage; reproductive pressure, clonal budding, paired recombination and separated genetic, epigenetic and cultural inheritance remain bounded and habitat-authorized.

## Milestone H — Digital ecology (v0.70-v0.76)

Implemented through v0.76. `SharedHabitat` and `EcologicalResourcePool` provide finite carrying capacity and resource competition. Offline exchange, replay protection, evidence-aware trust, dissent-preserving revision, revocable local communication and synthetic adversarial/population measurements are available without network discovery or evaluator leakage.

## Mantenimiento posterior a v0.76

Releases **v0.76.1-v0.76.46** are historical hardening and closure releases. v0.77.0 starts the next milestone lane. Milestones I (Fisiología integrada), J (Desarrollo predictivo autónomo) and K (Sociabilidad emergente) require their respective integration, safety and study gates. Both require design, safety and consent gates before new capabilities are enabled.

The scientific progression is now explicit: **development → physiology → ecology → society**. Cooperation remains an observable ecological outcome, never a hard-coded objective.

## Milestones I–K — implementation increments (v0.77.0-v0.79.20)

* **v0.77.0-v0.77.1 — I:** physiology became an irreversible runtime boundary:
  explicit intake, deterministic vital states, habitat release and a hard
  post-death execution stop.
* **v0.78.0 — J:** the predictive-development lane added bounded attention and
  evidence-driven shadow prediction without evaluator feedback.
* **v0.79.0-v0.79.4 — K/J:** an explicitly authorized `SocialHabitat`, aggregate
  relation ledger, finite-resource exchange/competition and deterministic
  milestone study harnesses were added; comparative study imports were made
  collection-safe.
* **v0.79.5 — K:** social habitat checkpoints preserve members, resources and
  relation evidence together for deterministic restart/replay.
* **v0.79.6 — I:** `OrganismRuntime.repair()` performs bounded, maintenance-backed
  repair and rejects actions after death.
* **v0.79.17 — laboratory integrity:** comparative protocol configuration now
  fails with its declared validation error when required parameters are absent.
* **v0.79.18 — K evaluation baseline:** a seeded, evaluator-only social-emergence
  study now replays finite-resource exchange and competition and reports relation
  valence plus isolated members without imposing social goals.
* **v0.79.19 — I dormancy coupling:** dormant runtime physiology now scales declared
  observation, cognition and persistence costs without generating free reserves.
* **v0.79.20 — I reproduction boundary:** runtime reproductive pressure and authorized
  clonal budding now enforce parent identity, reserve consumption and habitat capacity.

These releases remain incremental: I still requires integrated dormancy and
reproduction gates; J requires longitudinal promotion evidence; K requires
reciprocity and emergence studies. None introduces network discovery, social
objectives or evaluator semantics into the organism.
