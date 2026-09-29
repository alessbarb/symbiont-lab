# Symbiont roadmap — historical log

This is the extracted, verbatim historical portion of `docs/roadmap.md`:
completed milestones (A through H), the completed-development merge-sequence
table, and the per-patch tracking log. Active development state (north
star, permanent invariants, active milestones I/J/K, decision gates, merge
policy) remains in `docs/roadmap.md`.

---

## 2026-09-14 developmental restructures

### Developmental embodiment

PR #70 changed the meaning of embodiment. Symbiont no longer has to be handed a semantic list such as CPU/memory/thermal and told which senses matter. On Linux it can discover a bounded, vetted set of aggregate read-only numeric surfaces, assign opaque identities to them, learn which are useful, persist only abstract learned state and run transparently as an owner-installed user service.

That moved the project from hand-authored sensing toward organism development and created Milestone E — **Developmental embodiment** — followed by E2 — **Endogenous plasticity**.

### From cooperative species to digital ecology

After E2 and biological memory consolidation, the project closed the physiology,
reproduction and ecology gaps through v0.76. The organism now has explicit
bounded intake, metabolism, maintenance, viability, lineage and habitat
semantics, while population outcomes remain evaluator-side measurements.

The former Milestone F — **Cooperative species** — was superseded before
implementation. Its communication and trust work was preserved as bounded,
consent-aware ecological infrastructure rather than a cooperation objective.

The new sequence is:

- **Milestone F — Digital physiology**
- **Milestone G — Reproduction & heredity**
- **Milestone H — Digital ecology**
- **Milestone I — Fisiología integrada (partial implementation)**
- **Milestone J — Desarrollo predictivo autónomo (partial implementation)**
- **Milestone K — Sociabilidad emergente (partial implementation)**

This is a scientific change, not merely a renumbering.

Cooperation is no longer the prescribed endpoint. Once independently viable and reproductive organisms share a bounded habitat, cooperation should be one possible ecological relationship alongside competition, coexistence, specialization, symbiosis, conflict and indifference.

### 2026-09-15 life-cycle and reproduction refinement

Long-run resident development exposed a new transition: a Symbiont can remain healthy and `ADAPTIVE` while exhausting its bounded conceptual phenotype. The motivating resident reached `64/64` soft nodes with `32/32` concepts, `31/32` cognitive senses, one readout and 181 edges, with no orphan latent nodes.

That is not treated as failure. It motivates a reproductive signal: **persistent valid developmental pressure that cannot be expressed because the current individual has exhausted its allowed phenotype capacity**.

The first asexual mechanism is therefore changed from clonal fission to **clonal budding**. The parent remains alive; a new organism in the same authorized habitat receives the same genome but starts from the canonical empty germinal phenotype. Acquired cognition and lifetime memory are not copied.

This change also makes death and population bounds mandatory rather than optional follow-ons. Reproductive readiness never creates a process directly. Birth requires habitat authorization, a descendant slot and explicit resource allocation. Death is an irreversible closure of organism continuity and releases live habitat allocation. A full habitat blocks birth instead of silently killing another organism to make room.

Detailed design: `docs/design/fisiologia-y-reproduccion.md`.

---

## Merge sequence

### Completed development

| Release | Organism capability | Merge result |
| --- | --- | --- |
| v0.30 | Sensor reading contract | Typed readings with units, monotonic time, provenance, quality and privacy class  (implemented) |
| v0.31 | Cross-platform resource provider | Real safe resource readings where available  (implemented) |
| v0.32 | Sensor lifecycle | Hot capability changes, failure isolation, backoff and bounded buffers  (implemented) |
| v0.33 | Acclimation | Initial host baseline with threat conclusions explicitly withheld  (implemented) |
| v0.34 | Percept synthesis | Platform-specific readings become platform-neutral perceptions  (implemented) |
| v0.35 | Context and rhythms | Coarse temporal context without user identity  (implemented) |
| v0.36 | Drift-aware beliefs | Isolated novelty, gradual change and regime shifts are distinguished  (implemented) |
| v0.37 | Safe checkpoints | Explicit model export/import without raw telemetry  (implemented) |
| v0.38 | Live attention budget | Causal allocation of limited attention using uncertainty and cost  (implemented) |
| v0.39 | Read-only second look | Temporary higher-resolution sampling through authorized senses  (implemented) |
| v0.40 | Evidence revision | New evidence revises beliefs while preserving contradiction and dissent  (implemented) |
| v0.41 | Organism narrative | Inspectable explanations of attention, evidence, belief and uncertainty  (implemented) |
| v0.42 | Knowledge capsules | Signed, identity-minimized, offline exchange of abstract knowledge  (implemented) |
| v0.43 | Contextual source trust | Historical implementation; known echo-chamber limitation, superseded before ecological trust |
| v0.44 | Organism runtime | A single continuous cognitive cycle replaces one-shot CLI verbs  (implemented) |
| v0.45 | Consent and resource governor | Continuously checked permission, frequency and resource budget  (implemented) |
| v0.46 | Durable organism state | Atomic save/restore, schema migration, crash/restart recovery  (implemented) |
| v0.47 | Cross-platform proof | Cross-platform execution harness; Windows/macOS result caveat remains  (implemented) |
| v0.48 | Defensive advisory | Explainable, human-reviewed recommendation — never autonomous action  (implemented) |
| v0.49 | Real-host evaluation | Measured usefulness against operator judgment, never fed back as oracle truth  (implemented) |
| v0.50 | Resident sensory development | Opaque safe-surface discovery, learned utility, transparent residence and passive Observatory stream  (implemented) |
| v0.51 | Sensory relations | Learn bounded same-time and lagged associations; suppress redundant active senses  (implemented) |
| v0.52 | Adaptive sampling | Develop active/probing/dormant sensory tiers and spend observation effort selectively  (implemented) |
| v0.53 | Organism self-model | Learn resource cost, sensory health and confidence in its own perceptual apparatus  (implemented) |
| v0.54 | Long-run maturation | Aging/forgetting, rediscovery and bounded developmental stability over long residence  (implemented) |
| v0.55 | Genome kernel | Closed schema, hard kernel limits, validating codec, genome identity and checkpoint  (implemented) |
| v0.56 | Cognitive graph | Nodes/edges, sensory normalization, deterministic double-buffered activation and gating  (implemented) |
| v0.57 | Label-free learning | Prediction error, eligibility traces and bounded Oja weight updates  (implemented) |
| v0.58 | Metaplasticity and structure | Pareto objective, bounded parameter adaptation, structural creation/pruning and safe mode  (implemented) |
| v0.59 | Laboratory evolution | Genome mutation, Pareto-archive selection and cycle-protected lineage archive  (implemented) |
| v0.59.5 | Biological memory consolidation | Consolidated persistent memory, coarse durable state and reacclimation instead of microstate replay  (implemented) |

#### Completed: Milestone F — Digital physiology

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.60 | Metabolic accounting | Explicit finite budgets for sensing, cognition, retention and maintenance become organism-visible physiological pressure (implemented) |
| v0.61 | Information assimilation | Perceived information is evaluated for endogenous utility and either incorporated, deferred or rejected without external labels (implemented) |
| v0.62 | Degradation, waste and excretion | Low-value internal state can age, lose maintenance priority and be irreversibly discarded under bounded rules (implemented) |
| v0.63 | Homeostatic maintenance and repair | The organism reallocates effort, prunes damaged structure, recovers from local failure and preserves viable organization within kernel limits (implemented) |
| v0.64 | Dormancy, stress, viability and death | Explicit life states, irreversible `DEAD`, non-resurrection restore semantics and resource-release hooks complete organism continuity (implemented) |

#### Completed: Milestone G — Reproduction & heredity

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.65 | Organism identity, lineage and birth authority | Stable organism identity, birth/death events, parentage, generation and a minimal habitat authority with carrying-capacity/resource reservation semantics (implemented) |
| v0.66 | Reproductive pressure and clonal budding | Persistent blocked developmental growth can produce readiness; habitat-authorized budding creates a new empty-phenotype organism with the same genome while the parent continues (implemented) |
| v0.67 | Heritable genome loci | Genome fields gain explicit recombination units and inheritance semantics while remaining valid under the immutable kernel (implemented) |
| v0.68 | Paired reproduction | Two compatible parents contribute genome material to one new organism through bounded, deterministic recombination (implemented) |
| v0.69 | Inheritance and variation | Genetic mutation, optional bounded epigenetic carry-over and post-birth cultural transfer become separately testable inheritance channels (implemented) |

#### Completed: Milestone H — Digital ecology

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.70 | Full habitats and carrying-capacity economy | The minimal birth authority expands into a multi-organism habitat with finite shared resources, bounded population and auditable allocation/release (implemented) |
| v0.71 | Ecological resource interaction | Organisms can coexist, compete or specialize through shared resource pressure without a hard-coded requirement to cooperate (implemented) |
| v0.72 | Exchange schema and replay protection | Identity-minimized knowledge exchange gains closed schemas, bounded payloads, validity windows and replay defense (implemented) |
| v0.73 | Evidence-aware trust | Organisms evaluate compatibility, evidence quality, freshness, independence and claim/source reliability separately (implemented) |
| v0.74 | Collective revision | Knowledge from multiple organisms can influence beliefs without treating majority agreement as truth (implemented) |
| v0.75 | Consent-bound communication | Optional authenticated organism-to-organism transport exists only inside explicitly authorized habitats and remains revocable (implemented locally; network deferred) |
| v0.76 | Population and adversarial ecology | Population dynamics, poisoning, Sybil pressure, stale knowledge, reproductive success and ecological resilience can be studied experimentally (implemented) |

The version boundaries above are directional. A release may be split when the design surface proves too large, but later milestones must not be pulled forward merely because they are technically easy.

---

## Milestone A — Safe real perception

Tracking: #32. Includes v0.30-v0.33.

Symbiont can sample a consenting local host through normalized contracts, with bounded resources and sensor failure isolation.

Identity, user content, packet inspection, command lines, arbitrary file contents, process control and remediation remain outside the current perception boundary.

## Milestone B — Adaptive host model

Tracking: #34. Includes v0.34-v0.37.

Cognition remains independent of platform providers, contextual baselines can adapt, and restarts restore only safe abstract state.

## Milestone C — Autonomous inquiry and explanation

Tracking: #33. Includes v0.38-v0.41.

Symbiont can allocate bounded attention, request only authorized read-only second looks, revise beliefs and explain its uncertainty.

Inquiry is not remediation.

## Milestone D — Operational embodiment

Tracking: #55. Includes v0.44-v0.49.

The organism became a governed recoverable single-host cognitive cycle with explicit human-facing advisory output and real-operator evaluation.

The historical cross-platform CI caveat is retained as a verification limitation, not a blocker on Linux development per owner policy.

## Milestone E — Developmental embodiment

Includes v0.50-v0.54.

The organism exits this milestone when it can enter an unfamiliar consenting host without being handed a semantic sensor catalog, develop a bounded sensory repertoire, learn relationships among senses, allocate sensing effort based on information and cost, maintain a self-model of perceptual health, and remain stable through long-run change and rediscovery.

Exit conditions:

1. Candidate surfaces are discovered only through explicitly safe local provider boundaries; cognition sees opaque learned senses, not paths or OS APIs.
2. Sensory selection depends on learned availability/information/redundancy rather than a hard-coded importance list.
3. Same-time and lagged associations are descriptive only — never silently promoted to causal claims.
4. Sampling effort is bounded and adaptive; dormant senses retain a bounded chance of re-exploration so the organism cannot permanently blind itself from early mistakes.
5. Checkpoints contain aggregate learned state, never raw sample histories or the most recent raw host reading.
6. Residence remains transparent, owner-installed, least-privileged and removable.
7. Observatory remains passive: it may inspect but cannot command the organism.

## Milestone E2 — Endogenous plasticity

Includes v0.55-v0.59. Owner-authored technical design: `docs/design/cognicion-y-plasticidad.md`.

The organism's self-programming capability is implemented as **plasticity of data under an immutable kernel**, never as generated, edited or executed code.

An immutable kernel defines hard limits and a closed node/edge catalog; a declarative versioned genome configures one individual's development within those limits; a plastic phenotype learns weights and bounded structure during that individual's life; generational evolution happens only in `symbiont_lab`.

Exit conditions:

1. Two organisms born from the same genome but exposed to different experience end up with measurably different graphs deterministically, not by chance.
2. Weight adaptation reduces prediction error or representation cost on at least one preregistered protocol without receiving an external label.
3. Structure can be created and pruned, and resident memory use stays bounded regardless of runtime duration.
4. No learned or mutated field is usable as a path, module name, command or permission; hard kernel limits are not learnable.
5. Checkpoint/restart preserves consolidated phenotype without preserving the most recent raw activation.
6. A plasticity failure rolls back that tick and can trigger bounded safe mode without losing the underlying organism.
7. Generational evolution remains an explicit laboratory operation.

### v0.59.5 — Biological memory consolidation

Owner-authored technical design: `docs/design/cognicion-y-plasticidad.md`.

Persistence changed from "serialize learned state" to "persist consolidated memory": checkpoint schema v6, stability-gated weight memory, consolidated host statistics, coarse recency, bounded reacclimation and a salient-event fast path.

A restart no longer reconstructs the previous tick's activation because synthesizing a plausible microstate would be worse than honestly losing transient state.

This release closes the individual-development foundation on which physiology now builds.

---

## Milestone F — Digital physiology

Includes v0.60-v0.64.

### Research question (Milestone F)

**Can a Symbiont regulate what it acquires, transforms, retains, spends and discards in order to preserve its own viability under finite computational resources?**

### v0.60 status

Implemented `MetabolicLedger` provides bounded observation, cognition, persistence and maintenance reserves. Runtime ticks charge declared observation and attention work, account for retained learned state, replenish finite reserves and expose pressure as `normal`, `elevated`, `severe` or `unrecoverable`. The ledger is checkpointable and descriptive only; it cannot grant permissions or alter immutable kernel limits. Information assimilation, degradation, repair, dormancy and terminal death remain the next releases in this milestone.

### v0.61 status

`InformationAssimilator` scores novelty, surprise, attention, reliability and bounded cost using only organism-derived signals. Each perceived transition is classified as `incorporate`, `defer` or `reject`; deferred work has a hard queue bound and decisions/counters are checkpointable without raw observations. No evaluator label or host semantic is consulted.

### v0.62 status

`DegradationQueue` gives retained abstract state an explicit bounded lifecycle (`active` → `aging` → `waste` → irreversible `excreted`). Capacity, aging and waste windows are kernel-owned; excretion releases a countable unit and no archive receives discarded detail. State is checkpointable with strict validation.

### v0.63 status

`HomeostaticController` converts metabolic pressure and bounded local damage into explicit maintenance actions: reduced activity, paused plasticity, repair or safe mode. Integrity and activity scale remain bounded, checkpointable and cannot alter immutable kernel limits. Runtime exposes the homeostatic snapshot per tick.

### v0.64 status

`ViabilityController` distinguishes active, stressed, dormant, dying and irreversible dead continuity. Pressure/integrity transitions are explicit, death finalization is one-way and dead checkpoints cannot transition back to life. The controller carries only bounded identity/state and is ready for later habitat resource-release hooks.

### v0.65 status

`HabitatBirthAuthority` introduces explicit organism-lineage records, parentage, generation, bounded carrying capacity and transactional resource reservation/release. Birth denial leaves no partial identity or allocation, and death releases only the recorded live allocation. The authority never creates processes or broadens permissions; clonal and paired reproductive mechanisms remain the next releases.

### v0.66 status

`ReproductivePressure` requires persistent viable, adaptive and capacity-blocked growth before readiness. `clonal_bud` atomically asks the habitat authority for one descendant slot, charges a finite reproductive reserve only after success, and resets the pressure. The parent remains alive; the descendant receives only genome/lineage identity and must initialize an empty phenotype.

### v0.67 status

`HeritableGenome` defines a closed set of recombination loci and deterministic bounded selection between two parents. Locus validation rejects unknown, duplicate or non-numeric fields; permissions, paths, executable behavior and kernel limits are not representable as heredity.

### v0.68 status

`paired_reproduce` combines two distinct live parent identities through the declared deterministic locus recombination and requests exactly one habitat allocation. The child genome identity is derived from validated loci; denied or invalid pairings create no child or partial resource reservation.

### v0.69 status

`mutate_genome` applies bounded deterministic numeric variation only to declared loci. `InheritanceChannels` keeps bounded epigenetic priors and post-birth cultural artifacts in separate containers; neither channel is silently folded into genetic identity or evaluator truth.

### v0.70 status

`SharedHabitat` models finite shared resources, hard carrying capacity and auditable per-organism allocations/releases. Admission is transactional and bounded; a full or resource-exhausted habitat denies entry without evicting another organism. Checkpoints validate allocations without process or network control.

### v0.71 status

`EcologicalResourcePool` models declared finite resource types with deterministic proportional allocation. Competing requests receive the same bounded pressure-adjusted share, specialization is possible across resource types, and replenishment remains explicit and local. No cooperation, transport or host semantics are inferred by the pool.

### v0.72 status

`ExchangeEnvelope` provides a bounded canonical offline payload and digest. `ExchangeReplayGuard` accepts each sender sequence only once and exposes checkpointable local state; no network transport or peer discovery is introduced.

### v0.73 status

`EvidenceTrust` keeps compatibility, quality, freshness, independence and source reliability as bounded independent dimensions. An aggregate is derived only for reporting; no dimension is silently substituted for another.

### v0.74 status

`revise_claim` combines bounded evidence weights while preserving contributor count and dissent. Agreement changes confidence, not ground truth; no evaluator signal or majority shortcut enters cognition.

### v0.75 status

`ConsentBoundChannel` implements an authenticated in-memory channel scoped to an explicitly authorized habitat. Authorization is directional and revocation invalidates existing messages; sockets, discovery and network transport remain deliberately deferred pending a separate design/consent decision.

### v0.76 status

`AdversarialEcology` provides bounded synthetic assessments for stale records, replay, contradiction/poisoning signals and source-count Sybil pressure. `PopulationMetrics` records bounded, monotonic birth/death, resource-use, cooperation and competition outcomes strictly in `symbiont_lab`; these flags are explicit observations for experiments and do not become evaluator truth or autonomous remediation.

The v0.76.5 maintenance release also enforces monotonic evaluator ticks and keeps historical genome ranges loadable only when running forward from an older cognitive-kernel range; exact incompatible bounds remain rejected.

This milestone turns several existing mechanisms — attention budgets, pruning, forgetting, memory consolidation, health, rollback and safe mode — into parts of one explicit physiological model.

The analogy remains functional. CPU time is not declared to be literal biological energy, and deleting state is not declared to be literal digestion. The project instead studies the computational role played by resource intake, transformation, maintenance and disposal.

### Model

```text
environment
    │
    ▼
information intake
    │
    ▼
endogenous valuation
    │
    ├──► assimilation ───► activity / learning / memory / structure
    │
    └──► rejection

internal state
    │
    ▼
maintenance cost
    │
    ├── useful ─────────► retain / repair
    │
    └── low value ──────► degrade ─► waste ─► excrete

resource pressure
    │
    ├── normal ─────────► active
    ├── elevated ───────► stressed
    ├── severe ─────────► dormant
    └── unrecoverable ──► non-viable / death
```

### Exit conditions (Milestone F)

1. The organism has an explicit bounded metabolic ledger for observation, cognition, persistence and maintenance costs.
2. Information can be assimilated or rejected according to endogenous utility without evaluator labels.
3. Internal learned state has maintenance cost; retention is not free merely because memory remains below a hard maximum.
4. Low-value state can enter a degradation lifecycle before irreversible disposal.
5. Excretion actually releases bounded resources and does not secretly move discarded detail into an unbounded archive.
6. Existing pruning, consolidation and forgetting mechanisms participate in the same accounting model instead of operating as unrelated heuristics.
7. Homeostatic responses can reduce activity, change attention allocation or pause plasticity without changing immutable kernel limits.
8. Local cognitive damage can be repaired or pruned without requiring a full organism restart when recovery is possible.
9. Dormancy is distinguishable from process termination and from irreversible loss of viability.
10. Death is an explicit terminal organism state; a dead identity cannot be restored through the normal resident resume path.
11. Restart semantics preserve organism identity only when the previous organism remained viable; death and later recreation are not silently represented as one continuous life.
12. Death finalization exposes bounded resource-release and lineage hooks needed by later habitat/population work.
13. All physiological variables remain bounded and checkpointable without preserving raw telemetry history.

---

## Milestone G — Reproduction & heredity

Includes v0.65-v0.69. Owner-authored technical design: `docs/design/fisiologia-y-reproduccion.md`.

### Research question (Milestone G)

**Can organism identity, heredity and developmental divergence be made first-class computational phenomena without turning reproduction into uncontrolled software propagation?**

### Organism lineage is not genome lineage

The existing laboratory lineage tracks genome ancestry. Reproduction adds organism ancestry.

Two different organisms may share the same `genome_id` and still have independent identities, checkpoints, phenotypes, life histories and descendants. A new genome identity is created only when heritable genome material changes.

### Reproductive pressure

Reproduction is not triggered by age or by touching a resource limit for one tick.

A viable adaptive organism may accumulate **reproductive pressure** when valid structural-development evidence remains eligible but cannot be expressed because conceptual/node capacity is persistently exhausted.

Conceptually:

```text
ADAPTIVE + viable
        +
concept/node capacity exhausted
        +
eligible blocked growth persists
        +
sufficient physiological reserve
        ↓
REPRODUCTIVELY_READY
```

Saturation without blocked growth is maturity, not readiness.

A successful birth consumes the pressure that justified it, so one historical saturation event cannot be reused to generate descendants indefinitely.

### Clonal budding

The first asexual mechanism is clonal budding.

A viable parent remains alive and unchanged in identity while a descendant is materialized with:

- a new `organism_id`;
- the same genome as the parent;
- the same authorized habitat membership;
- an organism-lineage parent reference;
- the canonical empty germinal CognitiveGraph;
- no inherited lifetime cognition, learned weights, sensory baselines, beliefs, attention state or transient activation.

The parent continues with its developed phenotype. The child develops independently from birth.

Once physiology exists, the parent pays an explicit reproduction cost.

### Paired reproduction

Two compatible organisms may later contribute genome material to a new organism.

Genome recombination operates only over explicitly declared heritable loci. Every offspring genome is validated through the same immutable codec and kernel limits as a manually authored genome.

There is no special reproductive path around genome validation.

### Inheritance channels

The project keeps at least three channels experimentally separate:

1. **genetic inheritance** — genome loci transmitted at birth;
2. **epigenetic inheritance** — optional coarse, bounded developmental priors carried across generations;
3. **cultural inheritance** — knowledge transferred after birth through normal organism communication.

Lifetime memory is not automatically genetic.

### Minimal habitat birth authority

Reproductive readiness may become an organism state or decision. Process creation does not.

Before the first descendant can be materialized, a minimal authorized habitat authority must grant atomically:

- consent;
- a descendant slot under hard carrying capacity;
- bounded CPU/memory/storage budget;
- a valid placement target;
- a new organism identity;
- organism-lineage registration.

A full habitat blocks birth. It does not automatically kill or evict another organism to make room.

The organism cannot turn reproductive code into an unrestricted deployment primitive.

Milestone H expands this minimal authority into a full shared ecological resource system.

### Exit conditions (Milestone G)

1. Organism identity is distinct from PID, process lifetime, checkpoint filename, state-file path and genome identity.
2. Birth, parentage, generation and death are explicit durable organism-lineage events.
3. Organism lineage is acyclic and reproducible from durable records; genome lineage remains a separate structure.
4. Reproductive readiness requires persistent valid blocked developmental growth, not merely saturation or age.
5. A successful birth consumes the reproductive pressure that justified it.
6. Clonal budding leaves the parent alive and creates one descendant with a new identity, the same genome and an empty germinal phenotype.
7. Acquired CognitiveGraph structure, learned weights, sensory development and lifetime memory are not copied by default into a clonal descendant.
8. Parent and child evolve independently and can measurably diverge under different experience.
9. Paired reproduction combines declared genome loci from two parents under deterministic, testable recombination rules.
10. Every changed offspring genome passes normal genome validation and kernel limits.
11. Genetic mutation is bounded and cannot mutate permissions, paths, executable behavior or hard kernel limits.
12. Genetic, epigenetic and cultural inheritance are represented and measured separately.
13. Reproductive readiness cannot materialize a descendant without explicit habitat authorization and a carrying-capacity slot.
14. Failed or denied birth is transactional: no half-created organism, checkpoint, lineage edge or resource allocation remains.
15. A birth never silently kills another organism to obtain a slot.
16. Reproduction consumes finite physiological/habitat resources and therefore cannot cause unbounded population growth by construction.

---

## Milestone H — Digital ecology

Begins at v0.70.

This milestone supersedes the former **Cooperative species** roadmap.

The minimal habitat authority introduced for safe reproduction is not yet ecology. Milestone H adds persistent shared resource dynamics and organism-to-organism ecological consequences.

### Research question (Milestone H)

**What ecological relationships emerge when independently developed, viable and heritable digital organisms share finite resources and information inside an explicitly bounded habitat?**

Cooperation is not the required answer.

The experimental system should be able to observe:

- coexistence,
- competition,
- specialization,
- resource partitioning,
- cooperation,
- mutualism,
- parasitic information strategies,
- reproductive success differences,
- lineage expansion and extinction,
- population-level adaptation.

### Habitat model

A habitat is an explicit experimental and operational boundary.

It owns:

- participant admission,
- carrying capacity,
- compute/memory/storage budgets,
- communication permissions,
- descendant slots,
- shared resources,
- organism birth/death allocation and release,
- observability and audit records.

An organism does not discover arbitrary remote machines and redefine them as habitat.

### Population model

Population remains hard-bounded by habitat carrying capacity.

Birth requires a slot and explicit allocation. Death irreversibly closes organism continuity and releases live allocation. Process stop/restart is not population turnover.

Resource scarcity should influence physiology and reproductive success through declared mechanisms rather than a hidden evaluator selecting winners. The habitat does not automatically kill the "worst" organism whenever another wants to reproduce.

### Knowledge exchange

Milestone D (v0.42) delivered the initial offline knowledge capsules and a local, historical source-trust model. Milestone H reuses those bounded artifacts as ecological exchange infrastructure and deliberately supersedes the old trust model: evidence quality, freshness, independence and source reliability are evaluated separately, rather than treating agreement with the local host as trust.

Exchange progresses from bounded offline artifacts to optional authenticated habitat transport. Transport remains explicitly enabled and revocable.

### Exit conditions (Milestone H)

1. Multiple organisms can inhabit one bounded habitat without any organism controlling the habitat authority.
2. Habitat carrying capacity places a hard upper bound on population and aggregate resource use.
3. Resource scarcity can affect organism physiology and reproductive success through explicit mechanisms rather than hidden evaluator intervention.
4. Birth allocation and death release are transactional and auditable.
5. Organisms can affect one another only through declared ecological channels.
6. Cooperation is measurable but not privileged by the implementation as the desired outcome.
7. Competition cannot escape habitat resource and consent boundaries.
8. Shared knowledge has bounded schema, size, depth, lifetime and replay protection.
9. Trust separates evidence quality, freshness, independence, ecological compatibility and source/claim reliability.
10. Collective revision does not treat majority agreement as ground truth.
11. Optional network transport is authenticated, consent-bound, revocable and unavailable to organisms outside authorized habitats.
12. Poisoning, Sybil pressure, replay and stale knowledge have explicit adversarial protocols.
13. Population studies can measure birth rate, death rate, lineage survival, resource use, cooperation, competition and extinction without feeding those evaluator labels back into organism cognition.

---

## Tracking

The cross-milestone roadmap is maintained in issue #36.

- **v0.79.26 — K measurement refinement:** the seeded evaluator harness reports
  unique interaction pairs and Shannon pair entropy so concentration and
  diversity are observable. The harness remains policy-free and external; it
  does not establish autonomous runtime emergence.

- **v0.79.27 — K pairwise scarcity evidence:** finite-resource competition
  records contextual resident-to-resident harm when requests contend for the
  same resource; solitary scarcity remains attributed to the habitat.

- **v0.79.28 — K runtime boundary:** runtimes may submit explicit social
  exchange/competition requests through an authorized local habitat; peer
  scheduling and social objectives remain outside the organism.

- **v0.79.29 — J runtime shadow observability:** `OrganismRuntime` exposes
  read-only shadow-prediction candidates so longitudinal harnesses can inspect
  evidence without granting evaluator metrics to the organism.

- **v0.79.30 — J explicit promotion boundary:** runtime promotion is exposed as
  an explicit operation over validated shadow evidence, with no automatic
  evaluator-driven promotion and a hard post-death rejection.

- **v0.79.31 — J longitudinal runtime gate:** a deterministic study exercises
  runtime shadow evidence over repeated trials and verifies gain-based explicit
  promotion versus a no-gain candidate.

- **v0.79.32 — K local relation memory:** explicit runtime interactions now
  update and checkpoint organism-owned relation evidence, preserving local
  perspective and rejecting cross-resident request impersonation.

- **v0.79.33 — K social death boundary:** runtime death releases admitted
  social membership exactly once, preserving the habitat population boundary
  without allowing post-death interaction.

- **v0.79.34 — K replay/death study:** runtime-owned social evidence and the
  shared habitat boundary are replayed together; resident death releases social
  membership without losing traceability.

Issue #56 remains historical context for the former **Cooperative species** milestone; its communication, trust and adversarial-resilience goals are now conceptually part of Milestone H — **Digital ecology** rather than the immediate next stage.

- **v0.79.35 — K reciprocidad:** los intercambios bidireccionales registran
  evidencia de reciprocidad sin imponer una preferencia social; un estudio
  determinista cubre reciprocidad, conducta unilateral, conflicto y aislamiento.

- **v0.79.36 — K Observatory social evidence:** the passive projection now
  carries bounded reciprocal-observation, conflict and last-observed-tick fields;
  resident and CLI producers publish the runtime-owned relation ledger, while
  the schema and compatibility tests remain closed and read-only.

- **v0.79.37 — K percepción social:** un hábitat autorizado expone señales
  mínimas de presencia y disponibilidad con tokens opacos; el runtime puede
  percibirlas sin descubrimiento de red ni planificador social.

- **v0.79.38 — K decisión local:** el runtime puede seleccionar de forma
  determinista una oportunidad social disponible usando únicamente presencia
  opaca y evidencia propia; la selección no ejecuta interacciones ni impone una
  meta social.

- **v0.79.39 — I Observatory fisiológico:** la proyección pasiva publica presión
  metabólica y clases discretas de reserva por función, preservando la separación
  entre necesidades observadas y decisiones del evaluador.

- **v0.79.40 — I intake competido:** el runtime puede solicitar intake explícito
  al `SharedHabitat`; la escasez limita la cantidad incorporada al metabolismo y
  no existe reposición virtual ni acción posterior a la muerte.

- **v0.79.41 — K emergencia runtime:** un estudio evaluator-only ejecuta varios
  runtimes que seleccionan oportunidades desde su memoria local y mide diversidad
  de pares y reciprocidad sin planificador social ni etiquetas devueltas al
  organismo.

- **v0.79.42 — K control de canal:** el runtime puede suspender y reanudar su
  propio canal social; el estado suspendido se conserva en checkpoint y el
  replay verifica la reanudación sin política social central.

- **v0.79.43 — K escenarios adversariales:** un estudio runtime evaluator-only
  cubre soporte, contención finita y aislamiento de canal, midiendo límites sin
  devolver etiquetas de escenario a los organismos.

- **v0.79.44 — hardening de validación:** `pytest` excluye backups locales del
  Observatory para mantener reproducible la suite sin borrar artefactos de revisión.

- **v0.79.45 — Observatory phenotype:** la vista de organismo visualiza estado
  topológico, desarrollo sensorial, errores predictivos y rutas de creencias sin
  convertir la proyección pasiva en entrada cognitiva.

- **v0.79.46 — K ciclo de vida:** replay y reinicio conservan identidad y
  evidencia social; reproducción conserva parentela y muerte libera al padre sin
  retirar al hijo vivo.

- **v0.79.47 — Observatory evidencia relacional:** soporte, daño y frescura se
  publican con límites explícitos y validación de contrato, sin realimentación.

- **v0.79.48 — Observatory UI social:** las relaciones acotadas se ingieren y
  se muestran como evidencia agregada, sin objetivos, etiquetas ni ranking.

- **v0.79.49 — Observatory accesibilidad social:** la tabla accesible incluye
  valencia, observaciones y frescura de la evidencia relacional publicada.

- **v0.79.50 — K decisión local:** la selección social pondera evidencia propia,
  frescura y exploración sin imponer una política social central.

- **v0.79.51 — K selección reproducible:** el estudio evaluator-only verifica
  preferencias locales basadas en evidencia sin devolver etiquetas al runtime.

- **v0.79.52 — K revisión longitudinal:** una contradicción de evidencia puede
  cambiar la selección local y reabrir exploración sin política social central.

- **v0.79.53 — K contexto multi-vecino:** el estudio bounded combina revisión,
  suspensión, aislamiento y competencia finita con varios vecinos.

- **v0.79.54 — K paridad live/replay:** la selección social multi-vecino y la
  suspensión conservan el mismo resultado después de restaurar checkpoint.

- **v0.79.55 — K continuidad generacional:** el runtime puede unir descendientes a un hábitat social autorizado y conservar presión reproductiva fresca; un estudio evaluator-only verifica tres generaciones, replay de checkpoint, trazabilidad de parentela y liberación de cada progenitor muerto.

- **v0.79.56 — K paso social autónomo:** el runtime puede tomar una oportunidad social acotada usando únicamente presencia opaca, memoria relacional local y tokens de recursos del hábitat autorizado; el estudio de emergencia ya ejercita ese camino sin suministrar pares ni etiquetas al organismo.

- **v0.79.57 — K competencia local:** el runtime puede proponer una contienda de recurso a partir de evidencia negativa propia; el hábitat adjudica propuestas simultáneas y conserva la escasez finita sin imponer etiquetas ni ganadores.

- **v0.79.58 — I descanso explícito:** el runtime puede solicitar y cancelar descanso; la decisión queda checkpointed, reduce la transición de presión severa a dormancia y no crea reservas ni integridad gratuitamente.

- **v0.79.59 — I recuperación explícita:** un estudio evaluator-only demuestra
  que la reparación de integridad requiere intake de mantenimiento, está
  limitada por el controlador y conserva la intención de descanso al restaurar
  un checkpoint.

- **v0.79.60 — Observatory fisiológico:** la proyección pasiva publica la
  intención checkpointable de descanso junto al estado fisiológico, con contrato
  cerrado y normalización bounded en la interfaz.

- **v0.79.61 — Observatory atención:** se publican concentración y entropía
  normalizadas de la asignación de atención como métricas externas, sin exponer
  valores de señales ni retroalimentar al Symbiont.

- **v0.79.62 — J replay predictivo:** los candidatos de predicción shadow se
  conservan en checkpoints con pérdidas y muestras bounded; el estudio de
  promoción verifica paridad de ganancia y promoción tras restauración.

- **v0.79.63 — K longitudinal runtime:** un estudio prolongado ejecuta pasos
  sociales autónomos de varios runtimes, atraviesa un checkpoint intermedio y
  mide diversidad de pares y aislamiento sin asignar roles ni objetivos.

- **v0.79.64 — K adaptación ecológica:** cada runtime conserva evidencia local
  bounded sobre la disponibilidad de tokens opacos y puede cambiar de recurso
  tras un resultado denegado; el estudio valida adaptación y replay sin imponer
  nichos ni objetivos.

- **v0.79.65 — K rechazo explícito:** la memoria relacional conserva rechazos
  direccionales y el runtime puede suspender una solicitud, restaurar el estado
  y reanudarlo explícitamente; Observatory publica el contador como evidencia.

- **v0.79.66 — K evidencia de competencia:** los resultados de contención
  también alimentan la memoria local de disponibilidad de recursos, de modo que
  adaptación e intercambio comparten evidencia bounded sin introducir premios.

- **v0.79.67 — K diferenciación de nicho:** un estudio sintético de trayectoria
  prolongada mide elecciones de recursos diferenciadas tras contención local y
  checkpoint/replay, sin asignar roles ni preferencias al runtime.

- **v0.79.68 — K paridad de proyección:** la proyección browser del Observatory
  conserva el contador bounded de rechazos direccionales, evitando perder
  evidencia social entre el snapshot validado y la visualización pasiva.

- **v0.79.69 — K reexploración ecológica:** el ledger local reintenta de forma
  determinista y acotada los tokens cuya evidencia envejeció, preservando la
  adaptación sin fijar una denegación histórica como preferencia permanente.

- **v0.79.70 — K evidencia de recursos observable:** el contrato del Observatory
  publica de forma pasiva la evidencia local de disponibilidad de recursos
  opacos, con límites, frescura y denegaciones, manteniendo la separación entre
  observación y decisión.

- **v0.79.71 — I gestión de residuos integrada:** el runtime envejece una cola
  bounded de estado retenido, excreta unidades obsoletas de forma irreversible
  y conserva sus contadores en checkpoint/replay; Observatory solo publica
  contadores agregados, nunca el contenido retenido.

- **v0.79.72 — I recuperación sostenida:** el estudio evaluator-only somete al
  organismo a déficit repetido, verifica la entrada en dormancia y demuestra
  que la vuelta a `active` requiere intake explícito; el mismo tramo se replaya
  desde el checkpoint del déficit sin alimentar la cognición con ground truth.

- **v0.79.73 — K replay de trayectoria social:** el estudio de especialización conserva las secuencias completas de elección y compara la continuación posterior al checkpoint en un hábitat independiente; sigue siendo evidencia evaluator-only y no cierra los gates de emergencia prolongada ni generalización.

- **v0.79.74 — K replay longitudinal:** el estudio prolongado compara la trayectoria completa de pares autónomos después del checkpoint en un hábitat independiente; la emergencia y especialización fuera del régimen sintético siguen abiertas.

- **v0.79.75 — K cambio de régimen ecológico:** un estudio evaluator-only altera bounded la disponibilidad de recursos opacos y verifica revisión de evidencia y replay de la continuación, sin asignar preferencias ni roles.

- **v0.79.76 — I reparación sostenida:** un estudio evaluator-only repite reparación con intake explícito, verifica límites y control sin intake y compara la continuación tras checkpoint.

- **v0.79.77 — I intake compartido:** un estudio evaluator-only verifica adquisición metabólica entre consumidores admitidos, agotamiento bounded del hábitat y replay determinista.

- **v0.79.78 — I capacidad reproductiva:** el estudio de población cubre el bloqueo de nacimientos por capacidad llena junto con la liberación transaccional tras la muerte.

- **v0.79.79 — J ciclo de hipótesis shadow:** el runtime conserva el ciclo candidate → supported/contradicted → retired, bloquea la promoción de candidatos retirados y persiste el estado en replay.

- **v0.79.80 — K revisión tras denegación:** la memoria local de recursos conserva la racha de denegaciones recientes y permite revisar un token históricamente útil durante un cambio de régimen, con checkpoint compatible y sin exclusión permanente.

- **v0.79.81 — K estudio de revisión prolongada:** un arnés evaluator-only verifica que las denegaciones consecutivas provocan revisión local del token opaco y que la continuación completa se reproduce desde checkpoint en un hábitat independiente.

- **v0.79.82 — I/K coste metabólico social:** cada intercambio o lote de competencia consume un coste cognitivo explícito, bounded y checkpointable; el coste no puede ser repuesto por el Observatory ni por el evaluador.

- **v0.79.83 — J replay longitudinal shadow:** un estudio evaluator-only continúa
  evidencia predictiva a través de checkpoint, conserva muestras y estado de
  hipótesis y demuestra promoción posterior a `PREDICTOR`; la divergencia
  numérica de pérdidas queda explícita como efecto de la cuantización bounded.

- **v0.79.84 — K relaciones contextuales:** la memoria relacional separa la
  evidencia por canal/token opaco, conserva conflictos y reciprocidad sin
  fusionar intercambios y competencia de recursos distintos; checkpoints v1-v3
  migran al canal `default` y el Observatory sigue recibiendo solo agregados.

- **v0.79.85 — K propagación contextual en runtime:** los registros locales del organismo conservan el canal opaco de cada intercambio y competencia, con replay compatible y sin introducir etiquetas semánticas.

- **v0.79.86 — K selección relacional contextual:** la decisión local de oportunidad agrupa evidencia por objetivo y considera la mejor expectativa entre canales opacos; competencia solo se propone ante evidencia negativa explícita.

- **v0.79.87 — K competencia contextual:** las propuestas locales de conflicto
  exigen evidencia negativa en una oportunidad disponible y conservan su canal
  opaco al llegar al hábitat, sin convertir el daño en una regla global.

- **v0.79.88 — K estudios contextuales:** los arneses evaluator-only de replay, suspensión y contradicción pasan el canal opaco explícito, manteniendo la comparabilidad de evidencia tras la separación contextual.

- **v0.79.89 — I matriz longitudinal:** el estudio integrado de fisiología verifica en
  una ejecución reproducible los gates independientes de reparación, reproducción
  bounded y continuidad social, incluyendo ausencia de reparación sin intake.

- **v0.79.90 — K fiabilidad contextual:** cada relación expone una medida bounded
  de fiabilidad que combina observaciones, conflictos y frescura; solo modula la
  decisión local y no se transforma en reputación global.

- **v0.79.91 — cierre documental I/J:** se sincroniza el estado de los milestones con
  la evidencia actual: la matriz fisiológica y el replay longitudinal shadow están
  cubiertos; generalización y emergencia fuera de régimen siguen pendientes.

- **v0.79.92 — estado canónico:** README y ORGANISM se sincronizan con la
  evidencia de I/J/K y mantienen explícitas las fronteras de generalización.

- **v0.79.93 — Observatory K contextual:** snapshot, schema y proyección browser
  conservan el canal opaco y la fiabilidad relacional bounded sin introducir
  ranking, semántica de host ni control sobre el runtime.

- **v0.79.94 — Observatory UI contextual:** la vista individual muestra canal y
  fiabilidad bounded de relaciones, con valores ausentes explícitos y sin inferir
  reputación ni causas.

- **v0.79.95 — K validación relacional:** la observación y restauración de
  relaciones rechazan identificadores inválidos, valores no finitos y ticks
  ambiguos; la memoria contextual permanece bounded incluso ante checkpoints
  corruptos.

- **v0.79.96 — K límites ecológicos:** el pool de recursos valida tokens,
  cantidades finitas y solicitudes bounded al crear, asignar, reponer y
  restaurar hábitats; `NaN`, infinitos y valores ambiguos no pueden escapar a
  los límites de competencia.

- **v0.79.97 — K adversarial social:** el estudio evaluator-only de interacción
  social verifica cooperación, contención finita, aislamiento y rechazo
  direccional con reanudación explícita; la reposición bounded mantiene cada
  escenario separado y no devuelve etiquetas al runtime.

- **v0.79.98 — K matriz integrada:** un estudio evaluator-only compone los
  gates de cooperación, contención, aislamiento, rechazo reversible, replay de
  contexto y continuidad de linaje. La matriz mide límites observables sin
  inyectar etiquetas ni objetivos sociales en los organismos.

- **v0.79.99 — J codec de pesos estricto:** el checkpoint rechaza versiones de
  codec desconocidas y la cuantización no acepta pesos no finitos; el esquema
  v1 histórico sigue migrando explícitamente y v2 conserva cero exacto.

- **v0.80.06 — Observatory métricas estructurales J:** el presupuesto y los costes de ranking rechazan valores no finitos; la incertidumbre NaN queda excluida, mientras `+inf` sigue representando únicamente una capacidad sin baseline. El scheduler conserva selección determinista y presupuesto bounded. El lifecycle de hipótesis valida identificadores opacos, correlaciones en `[-1, 1]`, contadores enteros y ticks no ambiguos antes de actualizar evidencia, y sus estados/evidencia se conservan en el checkpoint de desarrollo sensorial. La selección de host conecta el número de observaciones del baseline al término de rendimiento decreciente, evitando que la política genérica quede inerte para señales ya conocidas. Una hipótesis con contradicción sostenida pasa a `retired` y no se reactiva silenciosamente tras un reinicio. La matriz evaluator-only compone codec, atención anti-captura, continuidad de hipótesis y promoción shadow positiva frente a ruido. Observatory proyecta presión estructural y error medio de cuantización de forma bounded, sin exponer pesos.

- **v0.80.07 — Observatory churn sensorial J:** se publica, de forma pasiva y
  bounded, el churn estructural de relaciones sensoriales. Solo cuenta creación
  y expulsión de pares desde la última lectura; la evidencia estadística no lo
  infla y la métrica no entra en decisiones del organismo.

- **v0.80.08 — divergencia estructural de desarrollo J:** el Observatory
  compara, solo cuando recibe una referencia topológica explícita, la distancia
  simétrica normalizada de nodos y aristas opacos respecto al primer estado de
  la sesión. La métrica es pasiva, bounded y no interpreta fitness ni causalidad.

- **v0.80.09 — contrato documental Observatory J:** la guía del aparato queda
  sincronizada con las métricas pasivas publicadas por v0.80.06–v0.80.08 y
  explicita sus límites de observación, sesión y no retroalimentación.

- **v0.80.10 — matriz integrada de desarrollo social K:** un gate evaluator-only
  compone los contratos de límites, replay longitudinal, linaje, revisión de
  recursos, denegación reversible y diferenciación de nichos sin retroalimentar
  etiquetas al organismo.

- **v0.80.11 — gate integrado I/J/K:** el laboratorio compone los gates
  independientes de fisiología, desarrollo predictivo y sociabilidad para
  verificar el estado conjunto de los nuevos milestones sin retroalimentar el
  runtime con resultados del evaluador.

- **v0.80.12 — cobertura ampliada del gate social K:** la matriz integrada
  verifica también límites adversariales reversibles, competencia con recursos
  finitos y diversidad de pares/interacciones, sin política social central.

- **v0.80.13 — panel cognitivo del Observatory:** los cuatro indicadores de desarrollo ya proyectados (presión estructural, error agregado de cuantización, churn relacional y divergencia estructural) se muestran como telemetría pasiva finita, sin pesos ni controles de intervención.

- **v0.80.14 — emergencia autónoma K:** el gate social integrado incorpora una ejecución evaluator-only de `OrganismRuntime.autonomous_social_step`, verificando interacciones multi-par, ausencia de miembros aislados y observaciones recíprocas sin inyectar etiquetas ni objetivos.

- **v0.80.15 — generalización bounded de emergencia K:** el gate evaluator-only repite la emergencia autónoma de forma determinista y la contrasta en poblaciones de 3 y 5 miembros, manteniendo el límite de ausencia de aislados sin introducir política social.


---

## Archived transition block — L8 through World v2

The following material was moved from the former active roadmap when the scientific
remediation roadmap became canonical. Wording is preserved as historical state; link
paths are adjusted only for this file's location.

## Milestone L8 — Prospective Agency (implementación en curso)

L8 conecta por primera vez el repertorio motor adquirido, el Private SLM ACTIVE
y el valor homeostático aprendido para permitir elección prospectiva de acciones
sin introducir semántica del laboratorio. La especificación normativa está en
[`history/design/prospective-agency-v1.md`](../design/prospective-agency-v1.md).

El alcance v1 es deliberadamente one-step. Una acción sólo puede entrar en
deliberación si ya es una competencia sensorimotora y su `primitive_readout`
ha sido admitido por CognitiveGraph. El modelo privado puede predecir una
consecuencia opaca, pero esa predicción nunca se convierte por sí sola en
evidencia ni valor. `OutcomeValueLedger` aprende exclusivamente de outcomes
observados después de acciones reales y de su consecuencia fisiológica
posterior.

Estado de cierre:

- L8.0 readiness/candidate repertoire — implementado; validación empírica pendiente.
- L8.1 primitive causal tokens — implementado.
- L8.2 ACTIVE counterfactual inference no mutante — implementado.
- L8.3 endogenous OutcomeValueLedger — implementado.
- L8.4 prospective policy/runtime integration — implementado baseline.
- L8.5 delayed observed-outcome credit — implementado.
- L8.6 checkpoint/fail-closed semantics — implementado baseline.
- L8.7 Physics3D passive telemetry — implementado baseline.
- L8.8 decontamination boundary — implementado por tests AST.
- L8.9 controlled shuffled/no-counterfactual studies — implementado y preregistrado; ejecución local pendiente.
- L8.10 Physics3D causal study — implementado y preregistrado; ejecución empírica pendiente.
- L8.11 adversarial re-audit — implementado baseline; full regression pendiente.
- L8.12 closure — pendiente de resultados y regresión final.

L8 no autoriza rollouts multistep, MCTS, reward externo, distancia al recurso ni
políticas de locomoción. Cualquier profundidad prospectiva >1 requiere una fase
separada después de superar los controles causales de v1.

---

## Cultural Foundation y Cumulative Culture v1 — cerradas en alcance experimental

Cultural Foundation v1 y Cumulative Culture v1 añaden claims sociales bounded,
genealogía de roots, composición cultural versionada y transporte local autorizado.
La composición puede integrar claims de varios organismos, conservar contributors y
roots, continuar tras la desaparición de los fundadores y degradarse mediante
retirada explícita. La validación actual es evaluator-side y no demuestra todavía
una política autónoma de cooperación, símbolos, selección cultural ni coevolución
con Private SLM. Pesos, adapters y corpus siguen siendo estrictamente privados.

## Autonomous Cultural Agency v1 — cerrada en alcance bounded

`CulturalPolicy` y `CulturalDecisionRecord` trasladan la selección de contenido
cultural al organismo: el arnés autónomo solo suministra topología local,
ventanas y presupuestos. El estudio preregistrado
`learning.autonomous-cultural-agency` cerró ACA1–ACA10 y replay en las semillas
101, 127 y 149. La política produjo decisiones no triviales y composiciones
multi-contributor útiles sin recibir IDs de claims/composites ni ground truth.
El transporte sigue siendo local, autorizado y en memoria; Observatory sigue
siendo pasivo. No se abren símbolos, lenguaje, selección cultural, reputación ni
transferencia de Private SLM.

## Emergent Symbol Grounding v1 — cerrada

La línea posterior a `v0.80.16` cerró la convención simbólica opaca,
organismo-side y aprendida por experiencia dentro de sus gates preregistrados.
No abrió lenguaje, gramática ni semántica humana.

## Structured Communication Characterization v1 — cerrada

Línea posterior a Emergent Structured Communication v1. No añade capacidades
lingüísticas: caracteriza el canal general ya cerrado mediante un sweep pequeño
de complejidad ambiental, vocabulario, longitud, memoria/coste y controles.
Observatory expone únicamente telemetría pasiva bounded; las métricas de
estructura son evaluator-side. Véase
[`design/structured-communication-characterization-v1.md`](../design/communication/structured-communication-characterization-v1.md).

## Population Communication Telemetry v1 — cerrada

Trabajo posterior al corte congelado `v0.80.16`; añade únicamente telemetría
factual bounded y vistas Observatory read-only; no modifica la política ni el
canal cognitivo de comunicación.

## Longitudinal Population Ecology v1 — cerrada como discovery

Línea de discovery posterior al corte congelado `v0.80.16`. Ejecutó stages
progresivamente largos sobre el simulador existente y reporta por separado el
sondeo multigeneracional del runtime social existente. No añade capacidades al
organismo ni convierte patrones descubiertos en claims confirmados. Véase
[`history/design/longitudinal-population-ecology-v1.md`](../design/longitudinal-population-ecology-v1.md).

## Integrated Habitat Runtime v1 — P0 de integración resuelto

`symbiont_lab.integration.IntegratedHabitatRuntime` es ahora el entrypoint
canónico y bounded para ejercer en un mismo habitat las capacidades existentes
de población, fisiología, aprendizaje, model registry privado, cultura,
grounding, comunicación y telemetría. El habitat solo orquesta ciclo, identidad,
contactos autorizados, checkpoint y contabilidad; no elige claims, mensajes,
receptores, significados ni composites.

El smoke técnico preregistrado cubre births/deaths, comunicación, grounding,
restore y replay en seeds `101, 127, 149`. La prueba larga ejecutada cubre
`1,000` ticks para esos invariantes en seed `101` y `10,000` ticks en seed
`101`; sus límites de historial, telemetría y transporte son explícitos. La
clasificación de integración pasa de C a **A — INTEGRATED** en sentido
arquitectónico y de smoke técnico. Esto demuestra coexistencia técnica, no
fenómenos poblacionales emergentes. La auditoría adversaria posterior y la
aprobación del owner congelan ahora el sustrato en `1.0.0`.

## Symbiont Experimental Organism v1 — frozen in 1.0.0

La auditoría adversaria final v2 no encontró P0 ni P1 materiales: integración
**A**, replay integrado, equivalencia con telemetría activada/desactivada,
boundedness y QA interactiva de Observatory pasan. Véase
[`../research/audits/current/experimental-organism-v1/final-v2.md`](../../research/audits/current/experimental-organism-v1/final-v2.md).
El corte publicado usa el tag anotado `experimental-organism-v1` y la versión
de paquete `1.0.0`; el tag histórico `v0.80.16` no se modifica. La publicación
del tag y del release se completa como operación administrativa separada.

```text
CAPABILITY DEVELOPMENT: FROZEN BY DEFAULT
EXPERIMENTAL RESEARCH: ACTIVE
```

Después del freeze, el organismo core solo cambia por bugs, seguridad,
boundedness o reproducibilidad demostrados. New phenomena should primarily be
investigated through habitats and experiments, not by continuously adding
organism capabilities.

## Symbiont World v1 — W0 (package boundary y kernel foundation) implementado

Nuevo paquete `symbiont_world`, un hábitat espacial persistente y opaco para
el organismo ya congelado en `1.0.0` — exactamente el tipo de trabajo que el
freeze permite explícitamente ("new habitats and experiments"). Especificación
normativa en
[`design/symbiont-world-v1.md`](../design/archive/symbiont-world-v1.md); razonamiento y
bibliografía de ALife en
[`design/symbiont-world-v1-rationale.md`](../design/world/symbiont-world-v1-rationale.md).

W0 entrega solo el fundamento estructural, sin fields, resources, hazards ni
organismos viviendo dentro: `WorldConstitution` (fingerprint versionado),
contratos `WorldObservation`/`WorldAction` inmutables y sin ground truth,
topología hexagonal con frontera reflectante y `OccupancyGrid` (una celda, un
organismo), RNG namespaced sin importar `symbiont`, `WorldEvent` con
`causal_parent_ids`/`contributing_event_ids` separados sobre un journal
append-only, y commit/rollback atómico de tick vía `TickTransaction`
(`symbiont_world/state.py`). 43 tests unitarios en `tests/unit/world/`
cubren estos invariantes; dos tests AST nuevos en
`tests/experimental_integrity/test_ground_truth_boundary.py` fijan la
frontera de paquetes en ambas direcciones (`symbiont` no importa
`symbiont_world`; `symbiont_world` no importa `symbiont` ni `symbiont_lab`).
Suite completa: 1817 passed (los 3 fallos restantes son deriva preexistente
de Observatory, no relacionada).

Siguiente paso declarado por la spec: W1 añade movimiento y observación
local por organismo sobre este kernel; W2 incorpora las leyes de Genesis
(`world-ground-truth.toml`). No se ejecuta ningún gate de falsación (W01–W07)
hasta que exista implementación real de fields/resources y al menos un
organismo viviendo en el mundo.

## Symbiont World v1 — W1, W2, W2.1 y preset Genesis v1 implementados

Sobre el kernel de W0: `symbiont_world/observation.py` (percepción local,
señal opaca de densidad de ocupación) y `symbiont_world/movement.py`
(resolución de movimiento determinista con desempate RNG-namespaced) cierran
W1 (§12 de la spec). Un bug real se encontró y corrigió durante el TDD:
`WorldState` solo hacía rollback de `occupancy`, no del registro
`WorldBody`; un tick abortado dejaba posiciones mutadas a medias. Se movió
`bodies` a `WorldState` para que ambas mutaciones compartan la misma
transacción atómica.

W2 (§13) añade `symbiont_world/laws.py`
(`PeriodicFieldLaw`/`ResourceLaw`, parámetros genéricos sin nombre de
dominio) y `symbiont_world/genesis.py` (`GroundTruth` + `WorldEnvironment`:
propagación de fields, renovación/decaimiento de recursos por celda con
inicialización perezosa, adquisición que nunca deja el pool negativo).
W2.1 (§14) añade `HazardLaw`, sin estado propio, función de exposición
acoplada a la densidad local que ya calculaba W1 — cierra el conteo
congelado de Genesis v1 (4 fields, 4 resources, 2 hazards) del lado del
kernel. `observation.py` extiende sus signals con fields/resources/hazards
reales cuando se le pasa un `WorldEnvironment`, sin romper el
comportamiento W1 cuando no se le pasa ninguno.

Un nuevo paquete `symbiont_lab.world` (único autorizado a conocer semántica
real, según §2/§13) instancia el primer mundo reproducible completo:
`genesis_v1.py` construye el `GroundTruth` congelado de Genesis v1 con
parámetros numéricos reales y su `WorldConstitution` correspondiente
(fingerprint determinista), manteniendo las etiquetas humanas
(`GENESIS_V1_METADATA`) fuera de `symbiont_world` en todo momento.

92 tests nuevos en `tests/unit/world/` y `tests/unit/lab/world/`. Suite
completa: 1866 passed (mismos 3 fallos preexistentes de Observatory sin
relación).

### Lo que falta para ejecutar W01/W02 (aún no iniciado)

Esto es deliberadamente honesto: todavía no existe ningún organismo viviendo
en el mundo. El preset Genesis v1 y el kernel completo de campos/recursos/
hazards no equivalen a un experimento ejecutable. Falta:

1. El adaptador real `symbiont_lab` que traduzca `WorldObservation` hacia el
   pipeline `ObservableSource → Sensor → Percept` existente de un
   `ModeledOrganismRuntime`, y sus decisiones de vuelta hacia `WorldAction`
   — esto es una integración de tamaño comparable a
   `IntegratedHabitatRuntime`, no una extensión menor.
2. El mapeo de efecto fisiológico real: `acquire`/hazard exposure aún no
   tocan `MetabolicLedger`; el "beneficio inmediato con daño diferido" que
   §7 exige de al menos un recurso de Genesis sigue sin implementación —
   `ResourceLaw` solo gobierna el pool, no el efecto sobre el organismo.
3. Colocación determinista de founders (`seed → founder placement`, §7) —
   sin implementar; los 8 founders de Genesis v1 no tienen todavía una
   regla de colocación inicial.
4. Solo entonces W01/W02 (§8) pueden preregistrarse y ejecutarse contra
   datos reales, no contra el contrato descrito en la spec.

Este es un punto de control natural: el siguiente incremento (el
adaptador) es una pieza de integración grande y merece su propio
diseño/plan dedicado, no continuación ad hoc.

## Symbiont World v1 — W3 (adaptador real) y W01/W02 ejecutados: v1 cerrado

`symbiont_lab.world.adapter.SingleOrganismGenesisRuntime` (§15) conecta un
`ModeledOrganismRuntime` real al kernel sin modificar `symbiont` en
absoluto: percepción vía `DiscoveryProvider`/`ReadingProvider`
(`symbiont/host/contracts.py`, `symbiont/host/readings.py`, ya diseñados
para exactamente esto), adquisición vía `resource_habitats` +
`SharedHabitat.set_environment_resources` (ya pública, decisión de
adquirir sigue siendo de la cognición vía `autonomous_action_step()`), y
daño de hazard vía `apply_environmental_damage` (ya existente, acotado a
`(0, 0.25]`). No se añadió ningún `ActionKind`; `grep` de
`symbiont/core/behavior.py` no cambia — verificado por test.

Descubrimiento clave que redujo el alcance: releyendo §8, **W01 y W02 no
necesitan movimiento ni founders múltiples** — ambos usan un organismo
estacionario. Eso hizo tratable el adaptador (una celda, sin comunicación
ni reproducción) en vez de requerir la pieza completa de colocación de
founders/movimiento real que el punto de control anterior asumía
necesaria.

**W01/W02 se ejecutaron de verdad** contra datos reales (no simulados ni
inventados): `experiments/world/genesis-v1/run_w01_w02.py`, resultados en
`results.json`, análisis honesto en `audit.md`. Resultado:

```
W01: H0 se mantiene (no rechazada). cognitive_wins = 0/3 seeds.
     Mecanismo observado (no confirmado): la política cognitiva satura
     INTAKE y nunca elige REPAIR en ninguna semilla; el control aleatorio
     sí repara por muestreo uniforme y termina con mayor integridad.
     El daño de hazard no está causalmente conectado a ningún
     ExpectedOutcome de REPAIR en el modelo de acción actual.

W02: H0 se mantiene (no rechazada), más un hallazgo metodológico real:
     con exploration=0.0, discover_senses=False y sin reproducción,
     organism_seed no tiene ningún camino causal hacia la selección de
     acción de un organismo solitario — dos réplicas con distinto
     organism_seed producen una trayectoria bit-a-bit idéntica. No es un
     resultado fabricado de "convergencia"; es una limitación real de esta
     build para poner a prueba divergencia por historia estocástica.
```

Ninguno de los dos gates rechaza su H0. Por diseño (§11, §15): **esto es
lo que cierra v1**, no un resultado positivo fabricado. `docs/design/
symbiont-world-v1.md` §11 lo dice explícitamente: "W01–W02 operacionalizan
[la pregunta científica]... su resultado — sea cual sea, incluida
convergencia trivial como H0 — es lo que cierra v1". Con ambos gates en
H0, no hay base para avanzar a W03+ (ecología de nichos, evolución,
cultura, open-endedness, §8 barrera formal entre programas) interpretando
adaptación que los datos no muestran.

166 tests nuevos/actualizados en `tests/unit/lab/world/` y
`tests/unit/world/`; suite completa: 1878 passed (mismos 3 fallos
preexistentes de Observatory, verificados independientes de este trabajo
vía `git stash`).

### Qué queda fuera de v1, explícitamente

Movimiento real, founders múltiples/colocación determinista, comunicación,
reproducción, el efecto de "beneficio inmediato con daño diferido" de un
recurso (`ResourceLaw` sigue sin modelar ese daño retardado), y cualquier
mecanismo de divergencia estocástica genuina para un organismo solitario
(el hallazgo de W02 arriba). Todo eso es material legítimo para W03+, no
una deuda de v1.

## Symbiont World v2 — implementado; W03 ejecutado y rechaza H0

Especificación en [`design/symbiont-world-v2.md`](../design/archive/symbiont-world-v2.md).
Todo aditivo sobre v1: ningún test de W0–W3 dejó de pasar (gate V02-08
verificado por la suite completa).

**Heterogeneidad regional** (`GroundTruth.region_of`/`regional_resources`/
`regional_hazards`, `symbiont_world/genesis.py`): opcional, default `None`/
`{}` reproduce exactamente el comportamiento de v1. Corrección honesta
encontrada al implementar: los pools de recurso son por-celda, no
por-región — la región solo comparte la *ley*, nunca el pool; no hay
contención real de recursos entre founders en v2 (documentado en el spec,
§4). `hazard_exposures()` se mantiene sin cambios por compatibilidad;
`hazard_exposures_at(cell, density)` es la versión consciente de región.

**Multi-organismo** (`symbiont_lab.world.population`): `founder_placement()`
determinista, `PopulationGenesisRuntime` sostiene 8 `ModeledOrganismRuntime`
sobre un mismo `WorldState`/`WorldEnvironment`, orden de tick por
`organism_id` ordenado. `resolve_movement`/intents simultáneos siguen sin
ejercitarse con más de un organismo (V02-04 marcado N/A: v2 no tiene
movimiento aprobado, §7).

**Retry de W02 con plasticidad real** (`sensory_plasticity=True`,
`discover_senses=True`): **H0 se mantiene otra vez**, pero con diagnóstico
más preciso que v1 — dos réplicas observan una trayectoria de mundo
idéntica (mismo `world_seed`), así que no hay nada de lo que plasticidad
pueda divergir; `organism_seed` solo llega a `mutation_seed`, que solo
importa si hay reproducción. Ver
`experiments/world/genesis-v1/audit-w02-retry.md`.

**Daño diferido** (`symbiont_lab.world.deferred.DeferredEffectQueue`,
acotada a 32 entradas): verificado end-to-end disparando exactamente una
vez por adquisición cualificada, dentro del rango `(0, 0.25]` ya exigido
por `apply_environmental_damage`.

**Observatory CLI** (`symbiont_lab.world.cli_view.render_world`, función
pura, solo lectura): render de organismos/campos/recursos/hazards con
etiquetas reales de `GENESIS_V1_METADATA`; confirma honestamente que
ningún `EventJournal` está todavía conectado a los runtimes (gap real, no
fabricado). Launcher delgado en `experiments/world/genesis-v1/view_world.py`.

**Gate de capacidad de movimiento (§7): sin implementar, a propósito.**
Decisión de abrir la puerta registrada con el owner; diseño concreto de
`ActionKind.MOVE` explícitamente pendiente de su propia revisión antes de
tocar `symbiont/core/behavior.py`.

### W03 ejecutado de verdad: **rechaza H0**, con hallazgo honesto sobre el mecanismo

`experiments/world/genesis-v1/run_w03.py` (Genesis v2:
`symbiont_lab.world.genesis_v2`, dos regiones con `ResourceLaw` distinta
para 2 de 4 recursos). Dos founders comparten región (misma ley) y
**difieren en su recurso dominante de adquisición** — diferenciación
ecológica real sin variación genética. `reject_h0 = True`.

Hipótesis inicial (`hazard-density-coupled` genera presión posicional) —
**descartada por su propio control**: con `density_coupling=0` para ambos
hazards, el mismo patrón de desacuerdo aparece idéntico
(`mechanism_supported = False`). El mecanismo real sigue abierto —
candidato: el percept crudo de densidad de ocupación local ya difiere por
posición independientemente del hazard, y dado que v2 confirmó que la
cognición es una función determinista de su flujo de percepts, un flujo
distinto basta para producir trayectorias distintas. Se registra como
`OBSERVED, NEEDS_REPLICATION` — ver `experiments/world/genesis-v1/
audit-w03.md` — no como fenómeno confirmado.

54 tests nuevos en `tests/unit/lab/world/`, `tests/unit/world/`. Suite
completa: 1920 passed (mismos 3 fallos preexistentes de Observatory).

