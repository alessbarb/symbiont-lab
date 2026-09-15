# Organism changelog — the complete evolution

## Current status

**v0.76.3.** Milestones A through E2 are complete and Milestone H is implemented through its current roadmap boundary: safe real perception, adaptive host modeling, autonomous inquiry and explanation, operational/developmental embodiment, endogenous plasticity, biological memory consolidation, bounded physiology, ecological interaction, offline exchange/replay, evidence-aware trust, dissent-preserving revision, consent-bound local communication and bounded synthetic adversarial ecology. The organism can discover an unfamiliar consenting host, maintain a self-model, compete or specialize over finite resources, validate and exchange bounded records through authorized local channels, preserve dissent and expose stale/replay/poisoning/Sybil-pressure observations for experiments. Network sockets, peer discovery and autonomous remediation remain disabled.

The next developmental stage is now **Milestone F — Digital physiology (v0.60-v0.64)**, followed by **Milestone G — Reproduction & heredity** and **Milestone H — Digital ecology**. The former "cooperative species" milestone has been superseded before implementation: cooperation remains a future ecological possibility, not a hard-coded destination.

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
* **v0.59 — Laboratory evolution.** `symbiont_lab/evolution/`: declarative genome mutation operators, Pareto-archive selection and cycle-protected append-only lineage. Evolution happens only in explicit laboratory runs. The current resident organism does not reproduce; future organism reproduction is a separate Milestone G capability and will not be implemented by granting the resident access to the laboratory evolution apparatus.

**Post-milestone hardening (v0.59.1-v0.59.3):** a first fresh adversarial audit closed defects in normalizer persistence, structural mutation application, safety-state enforcement, finite objectives, lifecycle reachability, bounded structural bookkeeping, metaplasticity bounds, eligibility traces, node ids and lineage ancestry. `CognitiveBridge` then wired graph activation, learning and structural plasticity into `OrganismRuntime`, and graph-state checkpoint persistence closed restart continuity for the learned mind.

**v0.59.4 — second adversarial hardening pass.** Kernel limits are now enforced where mutations and checkpoints are actually committed, not merely declared. Structural batches validate through the same `CognitiveGraph` invariants as normal construction and apply transactionally, preventing an invalid learned edge from partially changing or crashing the resident graph. Plastic learning is no longer unconditional: attention selects the reachable learning subgraph, sensory health × availability modulates the update, eligibility must be present and each edge's own `plasticity` scales Oja. Checkpoint restore rejects impossible lifecycle metadata and ambiguous booleans, topology revision survives restart, and contradiction memory persists only as bounded per-capability counts so numeric evidence is not turned into a history log. Observatory now publishes topology on the first cognitive tick, survives `run_id` rollover without discarding the new sequence zero, tails journals by file position, validates malformed local artifacts defensively, actually resolves referenced JSON schemas in contract tests, and runs its complete test directory in CI. The Observatory resident can also receive the same first-launch genome/graph inputs as the main live CLI. Package/runtime metadata is aligned at 0.59.4.

**v0.59.5 — Biological memory consolidation.** A full technical design ([`docs/design/biological-memory-consolidation.md`](docs/design/biological-memory-consolidation.md)) changed the persistence model from "serialize learned state" to "persist consolidated memory": checkpoint schema v6, a `WeightStabilityTracker` that commits an edge's weight class only after epoch-spaced stability (node-atomic — a node's changed incoming edges commit together or not at all), a consolidated-baseline codec for host statistics (signed-log center, a constant sentinel plus log buckets for scale, a monotone maturity table over real observation support), and `SelfModel`'s `RecencyClass` replacing the exact `last_observed_tick`. A bounded reacclimation period after restart keeps the cold-start transient itself from ever being misread as a salient or structural event. PR #76's earlier continuity guarantee is deliberately superseded here, not silently dropped: a restart no longer reconstructs the previous tick's activation, because seeding one from a coarse class would synthesize a microstate that never actually occurred — worse than genuinely losing continuity. `MemoryConsolidator`'s salient-event fast path — a one-shot durable trace for one exceptional, attended, reliable transition, distinct from the ordinary slow path's epoch-spaced support requirement — is wired into the real `OrganismRuntime.tick()` loop, closing the one piece of the design that had no caller in the organism until this release. All eleven exit conditions in the design's §25 are satisfied.

## Next developmental direction

### v0.60 — Metabolic accounting

`MetabolicLedger` introduces four explicit, bounded reserves (observation, cognition, persistence and maintenance). Runtime ticks charge declared work, replenish finite reserves, charge retained-state maintenance and expose a normal/elevated/severe/unrecoverable pressure classification. The ledger is checkpointable without raw telemetry and is descriptive only: it never changes permissions or kernel limits. This is the first tranche of Milestone F; assimilation, degradation, repair, dormancy and death remain pending.

### v0.61 — Information assimilation

`InformationAssimilator` evaluates each bounded transition from endogenous signals and chooses `incorporate`, `defer` or `reject`. Deferred work is capped and decisions/counters survive checkpoint/restore without raw observations. Degradation, repair, dormancy and death remain pending.

### v0.62 — Degradation, waste and excretion

`DegradationQueue` ages retained abstract items, demotes them to waste and irreversibly excretes them after bounded windows. Capacity and lifecycle are checkpointed; only released counts survive, never discarded detail. Homeostatic repair, dormancy and death remain pending.

### v0.63 — Homeostatic maintenance and repair

`HomeostaticController` turns pressure and bounded damage into reduced activity, paused plasticity, repair or safe mode. Integrity and activity scale remain bounded and checkpointable; immutable kernel limits are untouched. Dormancy and terminal death remain pending.

### v0.64 — Dormancy, stress, viability and death

`ViabilityController` distinguishes active, stressed, dormant, dying and irreversible dead continuity. Death finalization is one-way and dead checkpoint state cannot be resumed as the same life. Habitat resource-release hooks remain for Milestone G.

### v0.65 — Organism identity, lineage and birth authority

`HabitatBirthAuthority` allocates bounded descendant slots and resource reservations transactionally, records organism parentage/generation separately from genome identity and releases live allocation at death. Birth never starts a process or broadens permissions; clonal and paired reproduction remain pending.

### v0.66 — Reproductive pressure and clonal budding

`ReproductivePressure` requires persistent blocked developmental growth before readiness. `clonal_bud` requests one authorized slot, consumes finite reserve only after successful allocation and leaves the parent alive; descendants receive no acquired phenotype or lifetime memory.

### v0.67 — Heritable genome loci

`HeritableGenome` adds a closed, validated set of genetic recombination units and deterministic parent selection. Unsafe capabilities cannot be encoded as loci; kernel validation remains mandatory.

### v0.68 — Paired reproduction

`paired_reproduce` combines two distinct live parent identities through bounded deterministic loci and one habitat allocation. Invalid or denied pairings leave no child or partial reservation.

### v0.69 — Inheritance and variation

`mutate_genome` applies bounded deterministic mutation only to declared loci. `InheritanceChannels` keeps epigenetic priors and post-birth cultural artifacts separately bounded and testable; lifetime cognition is not silently treated as genetic inheritance.

### v0.70 — Hábitat compartido y economía de capacidad

`SharedHabitat` añade recursos finitos, capacidad poblacional dura y asignaciones/liberaciones auditables. La admisión denegada no expulsa organismos existentes ni crea procesos.

### v0.71 — Interacción ecológica de recursos

`EcologicalResourcePool` añade asignación proporcional determinista para recursos finitos declarados. Las solicitudes concurrentes reciben una cuota acotada bajo presión; distintos recursos permiten especialización y la reposición es explícita y local, sin introducir transporte, cooperación obligatoria ni semántica del host.

### v0.72 — Intercambio y replay offline

`ExchangeEnvelope` serializa payloads declarados dentro de un límite fijo y produce un digest estable. `ExchangeReplayGuard` rechaza secuencias repetidas o atrasadas por emisor y permite checkpoint local; todavía no existe transporte ni descubrimiento de pares.

### v0.73 — Confianza consciente de la evidencia

`EvidenceTrust` mantiene separadas compatibilidad, calidad, frescura, independencia y fiabilidad de la fuente, con un agregado derivado únicamente para informar. Ninguna dimensión se usa como sustituto silencioso de otra.

### v0.74 — Revisión colectiva

`revise_claim` combina informes ponderados por evidencia y conserva el desacuerdo explícito. La convergencia modifica la certeza, no convierte la mayoría en verdad ni introduce información del evaluador.

### v0.75 — Comunicación ligada al consentimiento

`ConsentBoundChannel` ofrece transporte autenticado en memoria, limitado a un hábitat autorizado y con consentimiento direccional revocable. La revocación invalida mensajes existentes; no se habilitan sockets ni descubrimiento de pares.

### v0.76 — Ecología adversarial sintética

`AdversarialEcology` mantiene límites explícitos para edad, replay, contradicción y presión de identidades sintéticas. Las evaluaciones son observaciones experimentales acotadas, no acciones automáticas ni verdad del evaluador.

The individual organism now has enough developmental machinery to expose the next missing layer: it can acquire and retain information, but it does not yet regulate those flows as a unified physiology.

The roadmap therefore continues with:

1. **Digital physiology** — intake, assimilation, maintenance cost, degradation, excretion, homeostasis, dormancy, viability and irreversible death semantics;
2. **Reproduction & heredity** — explicit organism identity and lineage, developmental-pressure readiness, habitat-authorized clonal budding, paired genome recombination and distinct genetic/epigenetic/cultural inheritance channels;
3. **Digital ecology** — bounded habitats, hard carrying capacity, finite shared resources, birth/death resource accounting, knowledge exchange, competition, coexistence, cooperation and population dynamics.

A saturated phenotype is not itself a reproduction command. The intended signal is persistent valid developmental evidence that can no longer be expressed within the current individual's bounded capacity. The parent may become reproductively ready, but only an authorized habitat with a free population/resource slot may materialize a descendant. The descendant receives the same genome and a new identity but begins with an empty germinal phenotype; acquired cognition is not copied.

Death is likewise not process exit. It is an explicit irreversible closure of organism continuity. A dead identity cannot be normally resumed, and releasing its live habitat allocation is part of the future population loop.

The project now treats capabilities such as reproduction and ecological interaction as developmental frontiers rather than permanent prohibitions. Permanent constraints remain consent, boundedness, transparency, no privilege escalation or exploitation, no hidden evaluator oracle, and no uncontrolled propagation.
