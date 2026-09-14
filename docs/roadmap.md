# Symbiont organism roadmap

This roadmap prioritizes capabilities acquired by the organism. Laboratory work is introduced only when a new organism capability needs a new measurement instrument.

The sequence is directional rather than calendar-based.

The roadmap distinguishes two things that must not be conflated:

1. **developmental limitations** — capabilities the organism does not have yet but may acquire later;
2. **permanent invariants** — consent, boundedness, epistemic separation and anti-evasion constraints that remain in force even as capability grows.

## North star

Build a benevolent digital organism that can develop on a consenting host, regulate its own internal computational economy, maintain viability under finite resources, reproduce through explicit heredity mechanisms, and eventually participate in bounded digital ecologies where cooperation, competition, coexistence and specialization are observable outcomes rather than hard-coded goals.

The organizing research sequence is:

> **Development before intelligence. Physiology before ecology. Ecology before society.**

Symbiont is not intended to remain permanently solitary, read-only or non-reproductive merely because those are properties of the current release. New capabilities may be added when their semantics, consent model, resource model and experimental observability are designed first.

At the same time, increased capability must not weaken the permanent invariants: no covert persistence, no stealth or evasion, no privilege escalation, no exploitation, no hidden evaluator oracle, no learned bypass of kernel limits, and no uncontrolled propagation.

---

## 2026-09-14 developmental restructures

### Developmental embodiment

PR #70 changed the meaning of embodiment. Symbiont no longer has to be handed a semantic list such as CPU/memory/thermal and told which senses matter. On Linux it can discover a bounded, vetted set of aggregate read-only numeric surfaces, assign opaque identities to them, learn which are useful, persist only abstract learned state and run transparently as an owner-installed user service.

That moved the project from hand-authored sensing toward organism development and created Milestone E — **Developmental embodiment** — followed by E2 — **Endogenous plasticity**.

### From cooperative species to digital ecology

After E2 and biological memory consolidation, the next gap is no longer primarily social.

The organism can perceive, learn, adapt and remember, but it does not yet have a unified digital physiology: no explicit intake/assimilation economy, no organism-level metabolism, no waste/excretion process, no complete viability state model and no biological reproduction.

The former Milestone F — **Cooperative species** — is therefore superseded before implementation.

Its future communication and trust work is preserved, but moved into a later ecological stage.

The new sequence is:

- **Milestone F — Digital physiology**
- **Milestone G — Reproduction & heredity**
- **Milestone H — Digital ecology**

This is a scientific change, not merely a renumbering.

Cooperation is no longer the prescribed endpoint. Once independently viable and reproductive organisms share a bounded habitat, cooperation should be one possible ecological relationship alongside competition, coexistence, specialization, symbiosis, conflict and indifference.

---

## Permanent invariants

These constraints survive future increases in capability.

1. Real-host access remains explicit, revocable and capability-bounded.
2. Learned state cannot manufacture permissions, commands, executable code or new kernel capabilities.
3. Credentials and privilege-escalation mechanisms remain outside the organism's developmental substrate.
4. Residence and persistence remain transparent and owner-controlled.
5. No stealth, concealment or evasion is used to maintain residence or acquire resources.
6. No exploitation is used to acquire capabilities, compute, storage or access.
7. Hard CPU, memory, storage and communication ceilings remain outside learned control.
8. Reproduction never means covert or uncontrolled propagation.
9. Materializing a descendant requires an authorized habitat and an explicit resource allocation.
10. Experimental ground truth remains outside organism cognition.
11. The laboratory may observe the organism without silently becoming its controller.
12. New write, network, action or reproduction capabilities cross an explicit design and consent gate before implementation.

These invariants do **not** imply that Symbiont must remain permanently read-only, non-communicating or non-reproductive.

---

## Merge sequence

### Completed development

| Release | Organism capability | Merge result |
| --- | --- | --- |
| v0.30 | Sensor reading contract | Typed readings with units, monotonic time, provenance, quality and privacy class |
| v0.31 | Cross-platform resource provider | Real safe resource readings where available |
| v0.32 | Sensor lifecycle | Hot capability changes, failure isolation, backoff and bounded buffers |
| v0.33 | Acclimation | Initial host baseline with threat conclusions explicitly withheld |
| v0.34 | Percept synthesis | Platform-specific readings become platform-neutral perceptions |
| v0.35 | Context and rhythms | Coarse temporal context without user identity |
| v0.36 | Drift-aware beliefs | Isolated novelty, gradual change and regime shifts are distinguished |
| v0.37 | Safe checkpoints | Explicit model export/import without raw telemetry |
| v0.38 | Live attention budget | Causal allocation of limited attention using uncertainty and cost |
| v0.39 | Read-only second look | Temporary higher-resolution sampling through authorized senses |
| v0.40 | Evidence revision | New evidence revises beliefs while preserving contradiction and dissent |
| v0.41 | Organism narrative | Inspectable explanations of attention, evidence, belief and uncertainty |
| v0.42 | Knowledge capsules | Signed, identity-minimized, offline exchange of abstract knowledge |
| v0.43 | Contextual source trust | Historical implementation; known echo-chamber limitation, superseded before ecological trust |
| v0.44 | Organism runtime | A single continuous cognitive cycle replaces one-shot CLI verbs |
| v0.45 | Consent and resource governor | Continuously checked permission, frequency and resource budget |
| v0.46 | Durable organism state | Atomic save/restore, schema migration, crash/restart recovery |
| v0.47 | Cross-platform proof | Cross-platform execution harness; Windows/macOS result caveat remains |
| v0.48 | Defensive advisory | Explainable, human-reviewed recommendation — never autonomous action |
| v0.49 | Real-host evaluation | Measured usefulness against operator judgment, never fed back as oracle truth |
| v0.50 | Resident sensory development | Opaque safe-surface discovery, learned utility, transparent residence and passive Observatory stream |
| v0.51 | Sensory relations | Learn bounded same-time and lagged associations; suppress redundant active senses |
| v0.52 | Adaptive sampling | Develop active/probing/dormant sensory tiers and spend observation effort selectively |
| v0.53 | Organism self-model | Learn resource cost, sensory health and confidence in its own perceptual apparatus |
| v0.54 | Long-run maturation | Aging/forgetting, rediscovery and bounded developmental stability over long residence |
| v0.55 | Genome kernel | Closed schema, hard kernel limits, validating codec, genome identity and checkpoint |
| v0.56 | Cognitive graph | Nodes/edges, sensory normalization, deterministic double-buffered activation and gating |
| v0.57 | Label-free learning | Prediction error, eligibility traces and bounded Oja weight updates |
| v0.58 | Metaplasticity and structure | Pareto objective, bounded parameter adaptation, structural creation/pruning and safe mode |
| v0.59 | Laboratory evolution | Genome mutation, Pareto-archive selection and cycle-protected lineage archive |
| v0.59.5 | Biological memory consolidation | Consolidated persistent memory, coarse durable state and reacclimation instead of microstate replay |

### Milestone F — Digital physiology

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.60 | Metabolic accounting | Explicit finite budgets for sensing, cognition, retention and maintenance become organism-visible physiological pressure |
| v0.61 | Information assimilation | Perceived information is evaluated for endogenous utility and either incorporated, deferred or rejected without external labels |
| v0.62 | Degradation, waste and excretion | Low-value internal state can age, lose maintenance priority and be irreversibly discarded under bounded rules |
| v0.63 | Homeostatic maintenance and repair | The organism reallocates effort, prunes damaged structure, recovers from local failure and preserves viable organization within kernel limits |
| v0.64 | Dormancy, stress, viability and death | Explicit organism-level life states distinguish healthy activity, resource stress, dormancy, recovery and irreversible loss of viability |

### Milestone G — Reproduction & heredity

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.65 | Organism identity and lineage | Stable organism identity, birth event, parentage, generation and acyclic lineage semantics independent of process/checkpoint identity |
| v0.66 | Clonal fission | One viable parent can divide into two daughter organisms with identical inheritable state at the division boundary and independent identities afterwards |
| v0.67 | Heritable genome loci | Genome fields gain explicit recombination units and inheritance semantics while remaining valid under the immutable kernel |
| v0.68 | Paired reproduction | Two compatible parents contribute genome material to one new organism through bounded, deterministic recombination |
| v0.69 | Inheritance and variation | Genetic mutation, optional bounded epigenetic carry-over and post-birth cultural transfer become separately testable inheritance channels |

### Milestone H — Digital ecology

| Release | Organism capability | Intended result |
| --- | --- | --- |
| v0.70 | Habitats and carrying capacity | Multiple organisms inhabit an explicitly authorized environment with finite shared resources and bounded population size |
| v0.71 | Ecological resource interaction | Organisms can coexist, compete or specialize through shared resource pressure without a hard-coded requirement to cooperate |
| v0.72 | Exchange schema and replay protection | Identity-minimized knowledge exchange gains closed schemas, bounded payloads, validity windows and replay defense |
| v0.73 | Evidence-aware trust | Organisms evaluate compatibility, evidence quality, freshness, independence and claim/source reliability separately |
| v0.74 | Collective revision | Knowledge from multiple organisms can influence beliefs without treating majority agreement as truth |
| v0.75 | Consent-bound communication | Optional authenticated organism-to-organism transport exists only inside explicitly authorized habitats and remains revocable |
| v0.76 | Population and adversarial ecology | Population dynamics, poisoning, Sybil pressure, stale knowledge, reproductive success and ecological resilience can be studied experimentally |

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

Includes v0.55-v0.59. Owner-authored technical design: `docs/design/endogenous-plasticity.md`.

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

Owner-authored technical design: `docs/design/biological-memory-consolidation.md`.

Persistence changed from "serialize learned state" to "persist consolidated memory": checkpoint schema v6, stability-gated weight memory, consolidated host statistics, coarse recency, bounded reacclimation and a salient-event fast path.

A restart no longer reconstructs the previous tick's activation because synthesizing a plausible microstate would be worse than honestly losing transient state.

This release closes the individual-development foundation on which physiology now builds.

---

## Milestone F — Digital physiology

Includes v0.60-v0.64.

### Research question

**Can a Symbiont regulate what it acquires, transforms, retains, spends and discards in order to preserve its own viability under finite computational resources?**

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
    └── unrecoverable ──► non-viable
```

### Exit conditions

1. The organism has an explicit bounded metabolic ledger for observation, cognition, persistence and maintenance costs.
2. Information can be assimilated or rejected according to endogenous utility without evaluator labels.
3. Internal learned state has maintenance cost; retention is not free merely because memory remains below a hard maximum.
4. Low-value state can enter a degradation lifecycle before irreversible disposal.
5. Excretion actually releases bounded resources and does not secretly move discarded detail into an unbounded archive.
6. Existing pruning, consolidation and forgetting mechanisms participate in the same accounting model instead of operating as unrelated heuristics.
7. Homeostatic responses can reduce activity, change attention allocation or pause plasticity without changing immutable kernel limits.
8. Local cognitive damage can be repaired or pruned without requiring a full organism restart when recovery is possible.
9. Dormancy is distinguishable from process termination and from irreversible loss of viability.
10. Restart semantics preserve organism identity only when the previous organism remained viable; death and later recreation are not silently represented as one continuous life.
11. All physiological variables remain bounded and checkpointable without preserving raw telemetry history.

---

## Milestone G — Reproduction & heredity

Includes v0.65-v0.69.

### Research question

**Can organism identity, heredity and developmental divergence be made first-class computational phenomena without turning reproduction into uncontrolled software propagation?**

### Reproduction model

Symbiont will study two primary reproductive mechanisms.

#### Clonal fission

A viable parent divides into two daughter organisms.

At the division boundary:

- both daughters receive the same genome;
- both daughters receive the same inheritable consolidated phenotype;
- both receive new organism identities;
- both reference the same parent lineage event;
- transient activation is not invented or replayed merely to fabricate bitwise process identity;
- the parent lifecycle closes after successful fission.

The daughters are developmentally equivalent at birth and may diverge immediately through different experience.

#### Paired reproduction

Two compatible organisms contribute genome material to a new organism.

Genome recombination operates only over explicitly declared heritable loci. Every offspring genome is validated through the same immutable codec and kernel limits as a manually authored genome.

There is no special reproductive path around genome validation.

### Inheritance channels

The project will keep at least three channels experimentally separate:

1. **genetic inheritance** — genome loci transmitted at birth;
2. **epigenetic inheritance** — optional coarse, bounded developmental priors carried across generations;
3. **cultural inheritance** — knowledge transferred after birth through normal organism communication.

Lifetime memory is not automatically genetic.

### Habitat-mediated birth

Reproductive readiness may become an organism state or decision. Process creation does not.

A birth can occur only when an authorized habitat grants:

- consent,
- a descendant slot,
- bounded CPU/memory/storage budget,
- a valid placement target,
- lineage registration.

The organism cannot turn reproductive code into an unrestricted deployment primitive.

### Exit conditions

1. Organism identity is distinct from PID, process lifetime, checkpoint filename and host path.
2. Birth, parentage, generation and death are explicit lineage events.
3. Lineage is acyclic and reproducible from durable records.
4. Clonal fission produces two daughter organisms with identical inheritable birth state except identity/lineage metadata.
5. After birth, daughters evolve independently and can measurably diverge under different environments.
6. Paired reproduction combines declared genome loci from two parents under deterministic, testable recombination rules.
7. Every offspring genome passes normal genome validation and kernel limits.
8. Genetic mutation is bounded and cannot mutate permissions, paths, executable behavior or hard kernel limits.
9. Genetic, epigenetic and cultural inheritance are represented and measured separately.
10. Reproductive readiness cannot materialize a descendant without explicit habitat authorization.
11. Failed birth is transactional: no half-created organism, lineage edge or resource allocation remains.
12. Reproduction consumes finite habitat resources and therefore cannot cause unbounded population growth by construction.

---

## Milestone H — Digital ecology

Begins at v0.70.

This milestone supersedes the former **Cooperative species** roadmap.

### Research question

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
- observability and audit records.

An organism does not discover arbitrary remote machines and redefine them as habitat.

### Knowledge exchange

Historical knowledge-capsule work from v0.42 and the former cooperative-species roadmap returns here.

Before collective revision, the old v0.43 trust model must be superseded so agreement with the local host is not confused with source reliability.

Exchange progresses from bounded offline artifacts to optional authenticated habitat transport. Transport remains explicitly enabled and revocable.

### Exit conditions

1. Multiple organisms can inhabit one bounded habitat without any organism controlling the habitat authority.
2. Habitat carrying capacity places a hard upper bound on population and aggregate resource use.
3. Resource scarcity can affect organism physiology and reproductive success through explicit mechanisms rather than hidden evaluator intervention.
4. Organisms can affect one another only through declared ecological channels.
5. Cooperation is measurable but not privileged by the implementation as the desired outcome.
6. Competition cannot escape habitat resource and consent boundaries.
7. Shared knowledge has bounded schema, size, depth, lifetime and replay protection.
8. Trust separates evidence quality, freshness, independence, ecological compatibility and source/claim reliability.
9. Collective revision does not treat majority agreement as ground truth.
10. Optional network transport is authenticated, consent-bound, revocable and unavailable to organisms outside authorized habitats.
11. Poisoning, Sybil pressure, replay and stale knowledge have explicit adversarial protocols.
12. Population studies can measure birth rate, death rate, lineage survival, resource use, cooperation, competition and extinction without feeding those evaluator labels back into organism cognition.

---

## Birth, identity, dormancy and death

The physiology and reproduction milestones require explicit life-cycle semantics.

The project will use the following distinctions unless a later design document supersedes them:

- **birth** — creation of a new organism identity with a valid genome and initial inheritable state;
- **active** — viable and executing its normal cognitive cycle;
- **stressed** — viable but physiologically constrained by resource or integrity pressure;
- **dormant** — viable but intentionally running a minimal maintenance cycle;
- **stopped** — process not running; this is not by itself death;
- **restarted** — the same organism identity resumes only if its durable viable state is valid;
- **dead / non-viable** — organism continuity is explicitly closed and cannot be resumed as though no death occurred;
- **descendant** — a new organism identity created through a reproductive event, even when genetically or phenotypically identical at birth.

This prevents process management concepts from silently standing in for biological ones.

---

## Merge policy

The project owner has explicitly instructed that GitHub Actions are not a merge gate.

A release can therefore merge after local/structural review even when hosted CI is unavailable.

The remaining gates are:

1. base/head drift is checked before merge;
2. no unresolved requested changes are knowingly ignored;
3. new resource use is bounded by construction and covered with deterministic tests;
4. privacy, consent and safety invariants accompany functional behavior;
5. ground truth remains outside organism cognition;
6. the release documents the new organism capability;
7. lineage and reproduction changes are transactional and replay-testable;
8. ecological changes include aggregate carrying-capacity tests, not only per-organism limits.

---

## Decision gates

Work pauses for an explicit architectural and safety decision before any merge that:

- requests new write, execute, elevated or remote permissions;
- expands perception into identifying metadata or user content;
- enables network exchange;
- introduces hidden or non-removable persistence;
- permits autonomous real-world action;
- materializes descendants outside an existing authorized habitat;
- changes reproductive authority or carrying-capacity ownership;
- creates unbounded CPU, memory, storage, population or network use;
- weakens the separation between organism and evaluator;
- allows learned state to alter immutable kernel limits or permissions;
- materially expands a human-facing security/operational advisory beyond the already approved consultative boundary.

Transparent owner-installed residence and bounded current read-only sensory development are already explicitly approved and do not reopen those decisions.

---

## Tracking

The cross-milestone roadmap is maintained in issue #36.

Issue #56 remains historical context for the former **Cooperative species** milestone; its communication, trust and adversarial-resilience goals are now conceptually part of Milestone H — **Digital ecology** rather than the immediate next stage.
