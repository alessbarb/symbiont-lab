# Symbiont Experimental Organism — evolution and freeze record

## Current status

**Freeze-ready for 1.0.0 — Symbiont Experimental Organism v1.**

The latest published software cut remains `v0.80.16`. The current `main` branch
contains the post-cut integration, validation and Observatory work that prepares
the organism for the semantic `1.0.0` freeze.

The final adversarial re-audit classifies the integrated subject as **class A —
integrated**: population lifecycle, physiology, individual learning, per-organism
Private SLM state, provenance-preserving culture, autonomous cultural agency,
opaque symbol grounding, structured communication, checkpoint/replay and
outbound telemetry now coexist through one canonical bounded habitat runtime.

The published `1.0.0` cut is therefore not intended to introduce another
organism capability. Its purpose is to freeze the experimental subject that has
already been built and validated.

The immutable `v0.80.16` tag remains historical software. The published `1.0.0`
freeze preserves the semantics and boundaries of the current organism while
allowing research, experiments, passive Observatory work, reproducibility fixes
and ordinary maintenance to continue around it.

New phenomena should primarily be investigated through habitats and experiments,
not by continuously expanding the organism itself.

The canonical state of the project is distributed across:

- [`docs/roadmap.md`](docs/roadmap.md) — active research roadmap;
- [`docs/history/roadmap-log.md`](docs/history/roadmap-log.md) — completed
  milestone history;
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — release-by-release implementation
  record;
- [`research/STATUS.md`](research/STATUS.md) — current evidence status, including
  positive, partial and negative results;
- [`docs/design/experimental-organism-v1-freeze.md`](docs/design/experimental-organism-v1-freeze.md)
  — freeze contract for Experimental Organism v1.

This document serves a different purpose: it explains the **evolution of the
organism as an experimental subject**. It deliberately summarizes patch-level
hardening when those patches do not represent a new biological or cognitive
capability. Exact release details remain in `docs/CHANGELOG.md`.

---

## Post-freeze experimental extension: adaptive sensory development

`main` contiene ahora una línea experimental que **no forma parte del sujeto
congelado 1.0.0 hasta validación**: un aparato sensorial organism-owned separado
de las fuentes del host.

```text
world/source -> raw sample -> sensory modality -> sensor -> percept -> SENSE -> cognition
```

Las modalidades son opacas y funcionales, no etiquetas humanas como vista u
olfato. Dos sensores pueden percibir una misma fuente de manera distinta, y un
sensor bounded puede integrar varias fuentes. `SignalKnowledge` continúa
describiendo el mundo externo.

La capacidad está implementada y preregistrada, pero sus afirmaciones de
especialización siguen abiertas hasta ejecutar los protocolos `perception.*`.
El freeze histórico permanece intacto.

---

## How to read this history

Symbiont separates three things that are easy to conflate:

1. **Organism capability** — what a Symbiont can actually sense, learn, retain,
   decide or do within its bounded runtime.
2. **Scientific evidence** — what experiments and preregistered studies have
   demonstrated about those capabilities.
3. **Apparatus and observation** — what the laboratory and Observatory can
   measure without feeding evaluator knowledge back into the organism.

A capability being implemented does not imply that it generalizes to every
environment, population size or regime. Likewise, an evaluator-side metric does
not become part of cognition merely because it is visible in a study or in
Observatory.

Throughout the project, the strongest recurring invariants are:

- host access remains bounded, read-only and explicitly authorized;
- organism-facing identities are opaque wherever host semantics are unnecessary;
- evaluator labels and ground truth do not enter organism cognition;
- learning and adaptation operate under explicit resource and structural limits;
- checkpoints preserve declared durable state, not arbitrary hidden microstate;
- death is irreversible;
- reproduction requires habitat authority and finite capacity;
- social and cultural exchange preserve provenance and local evidence;
- Private SLM weights, corpora and learned model state remain private to the
  organism that acquired them;
- Observatory is outbound-only and passive;
- network sockets, autonomous peer discovery and autonomous host remediation
  remain outside the frozen subject.

---

# Part I — from perception to a persistent individual

## Milestone A — safe real perception (`v0.30–v0.33`)

Symbiont began by replacing abstract or simulated sensing with a typed contract
for real host observations.

`SensorReading` introduced bounded readings with units, monotonic timestamps,
quality and privacy classification. The privacy type itself prevents identifying
data from being represented: only aggregate or non-identifying readings are
valid.

A stdlib-only host provider then sampled real CPU load and disk usage through a
read-only interface. Discovery and repeated sampling were bounded and included
per-provider backoff so a failing source could not dominate the runtime.

`HostAcclimation` added the first learned baseline. It records only descriptive
statistics — count, mean, variance and standard deviation — and deliberately
contains no threat label or evaluator judgment.

The important transition was conceptual: the organism could now **observe a real
machine without being told what those observations meant**.

---

## Milestone B — adaptive host model (`v0.34–v0.37`)

Raw host readings became platform-neutral `Percept` objects. Cognition no longer
needed to import provider-specific concepts such as internal capability or source
tokens.

`RhythmModel` learned separate baselines for coarse cyclical periods of the day.
The real hour is used only to select one of four buckets and is not retained as
organism state.

`DriftAwareBaseline` distinguished:

- isolated outliers;
- gradual candidate shifts;
- confirmed regime changes.

A candidate shift is buffered before it can replace the established baseline, so
one anomalous observation cannot redefine normality.

Schema-versioned checkpoint import/export completed the milestone without storing
raw readings or wall-clock histories.

The organism had moved from “seeing values” to **maintaining a bounded model of
how its environment normally behaves**.

---

## Milestone C — autonomous inquiry and explanation (`v0.38–v0.41`)

Observation became selective rather than uniform.

`attend_to_host` allocated a hard attention budget using uncertainty relative to
cost. Attention is therefore a resource-allocation process, not a threat
classifier.

`SecondLookSession` allowed temporary higher-resolution observation of something
the organism had already been authorized to sense. A second look is local,
read-only, cancellable and bounded.

`EvidenceRevisionLedger` made belief revision explicit. New evidence can update a
baseline, but materially conflicting evidence produces a `DissentRecord` rather
than being silently averaged away.

`narrate_host` then composed belief, attention and evidence into a
classification-free explanation.

At this point Symbiont could **notice uncertainty, spend additional effort on it,
revise its own model and preserve contradiction**.

---

## Milestone D — operational embodiment (`v0.42–v0.49`)

The project then turned the cognitive components into a persistent governed
runtime.

Signed knowledge capsules enabled tamper-evident offline exchange without adding
network I/O or peer discovery. `SourceTrustModel` learned source agreement
locally from the organism's own evidence, with the resulting echo-chamber risk
documented rather than hidden.

`OrganismRuntime` replaced isolated CLI operations with one continuous cognitive
cycle. `GovernedOrganism` wrapped that cycle in live-revocable consent and hard
frequency/tick budgets.

Checkpoint persistence became atomic and schema-migratable. A constrained-host CI
path verified that the host layer remained viable on a minimal musl/Alpine
environment.

`DefensiveAdvisor` added a deliberately weak action boundary: the organism may
form a recommendation, but execution remains a human-reviewed decision. The
laboratory can evaluate that recommendation against operator judgment, but the
comparison is one-way and cannot train cognition on evaluator truth.

This milestone made Symbiont **persistent and governable without giving it
autonomous control over the host**.

---

## Milestone E — developmental embodiment (`v0.50–v0.54`)

The organism stopped depending on a hand-authored semantic sensor catalogue.

`AdaptiveSenseModel` discovers vetted, aggregate and read-only host surfaces,
assigns them opaque identities and develops them over time.

Sensory development then acquired several mechanisms:

- same-time and lagged relation learning;
- redundancy suppression;
- active, probing and dormant sensory tiers;
- rotating observation budgets;
- later revisitation of dormant senses.

`SelfModel` added an operational model of the organism's own perceptual
apparatus. It learns:

- observation cost;
- availability;
- health;
- maturity;
- confidence;
- recency.

Those values influence attention and investigation without pretending to be
conscious self-awareness.

Long-run maturation added trust decay for senses that disappear and slow-creep
detection using a fast EWMA against a **frozen** noise floor. The earlier
live-standard-deviation approach was rejected because it adapted to the very
drift it was supposed to detect.

Restart continuity was also hardened so a newly active sense is never confused
with one that has been absent since the beginning of life.

The key transition was from a fixed monitoring surface to **developmental
perception**.

---

# Part II — endogenous cognition and durable memory

## Milestone E2 — endogenous plasticity (`v0.55–v0.59.5`)

Symbiont's “self-programming” is deliberately narrower than code generation. The
organism **changes learned data and structure under an immutable kernel**; it
does not generate, edit or execute source code.

### `v0.55` — genome kernel

A closed `NodeKind`/`EdgeKind` vocabulary and non-learnable `KernelLimits`
defined the legal cognitive substrate.

`Genome` became declarative, versioned, strictly decoded without `eval`, hashed
deterministically and checkpointed as its own namespace.

### `v0.56` — cognitive graph

`PlasticNode`, `PlasticEdge` and `CognitiveGraph.activate()` introduced a
synchronous, double-buffered graph.

Every node reads either the current tick's fresh sensory input or the previous
tick's frozen frame. Construction order therefore cannot change activation
semantics.

### `v0.57` — label-free learning

Prediction error, Huber loss, eligibility traces and bounded Oja updates enabled
learning without an external label in the loop.

### `v0.58` — metaplasticity and structural change

A five-dimensional `LearningObjective`, compared by Pareto dominance, governed
bounded adaptation of learning parameters and structural proposals.

Pruning, structural mutation and `SafetyState` introduced explicit lifecycle and
freeze semantics for cognitive change.

### `v0.59` — laboratory evolution

Genome mutation, Pareto-archive selection and append-only lineage entered the
laboratory apparatus.

This mechanism remains a laboratory process. Later organism reproduction does
not gain access to the evolution machinery and cannot invoke evaluator-side
selection.

### Adversarial hardening (`v0.59.1–v0.59.4`)

Successive adversarial passes moved safety checks from declarations to the actual
commit boundaries of the system.

Among other fixes:

- structural mutation became transactional;
- graph invariants are validated at mutation and restore time;
- attention selects the learnable subgraph;
- sensory health and availability modulate updates;
- eligibility and edge plasticity actually gate learning;
- checkpoint restoration rejects impossible lifecycle state;
- structural bookkeeping and contradiction memory are bounded;
- topology revision survives restart;
- Observatory contracts validate referenced schemas and malformed local data
  defensively.

`CognitiveBridge` connected activation, learning and structural plasticity to the
real `OrganismRuntime`, closing the gap between isolated graph code and the
living runtime.

### Biological memory consolidation (`v0.59.5`)

Persistence then changed model entirely.

Instead of serializing the complete learned microstate, the organism began to
persist **consolidated memory**:

- stable weight classes rather than arbitrary live precision;
- node-atomic consolidation of changed incoming edges;
- coarse but monotone host baselines;
- recency classes instead of exact last-seen ticks;
- bounded reacclimation after restart;
- a salient-event fast path for exceptional, attended and reliable transitions.

The design deliberately abandoned exact activation continuity across restart. A
coarsely reconstructed activation would be synthetic state that never happened;
losing that microstate is scientifically cleaner than inventing it.

This milestone completed the transition from transient adaptive software to a
**persistent developmental cognitive individual**.

---

# Part III — physiology, heredity and ecology

## Milestone F — digital physiology (`v0.60–v0.64`)

`MetabolicLedger`, `InformationAssimilator`, `DegradationQueue`,
`HomeostaticController` and `ViabilityController` introduced bounded digital
physiology.

Information and computation now have explicit consequences:

- intake;
- assimilation;
- metabolic cost;
- maintenance;
- degradation;
- repair;
- dormancy;
- irreversible death.

Physiology is functional, not anatomical. Symbiont does not simulate cells,
organs or biochemistry; it implements digital counterparts to resource-dependent
viability.

---

## Milestone G — reproduction and heredity (`v0.65–v0.69`)

`HabitatBirthAuthority` made reproduction an externally bounded ecological event,
not an unrestricted self-copy operation.

The organism gained:

- reproductive pressure;
- clonal budding;
- paired recombination;
- lineage identity;
- explicit genetic inheritance;
- separate epigenetic and cultural inheritance channels.

Birth requires habitat authorization and capacity. Acquired phenotype,
physiology and lifetime memory are not silently copied into germinal state.

The distinction between **inherited developmental potential** and **acquired
lifetime state** became explicit.

---

## Milestone H — digital ecology (`v0.70–v0.76`)

`SharedHabitat` and `EcologicalResourcePool` introduced finite carrying capacity,
shared resources and competition.

Offline exchange, replay protection, evidence-aware trust, dissent-preserving
revision and revocable local communication became available without opening
network discovery.

The laboratory could now measure ecological outcomes such as interaction,
competition or cooperation while keeping those evaluator labels outside the
organisms.

Cooperation remained an observed result, never a hard-coded objective.

---

# Part IV — integrated physiology, prediction and social development

## Milestones I–K (`v0.77–v0.79.99`)

The long `v0.77–v0.79` sequence should be read as one integration and hardening
phase rather than as dozens of independent biological inventions.

The three active lanes were:

- **Milestone I — integrated physiology**
- **Milestone J — autonomous predictive development**
- **Milestone K — emergent sociability**

### Milestone I — integrated physiology

Physiology became an irreversible runtime boundary rather than a side module.

The runtime gained:

- explicit metabolic intake;
- deterministic vital states;
- maintenance-backed repair;
- rest requests and recovery;
- dormancy coupling;
- bounded degradation and excretion;
- habitat allocation/release;
- reproductive pressure tied to real reserves and capacity;
- hard rejection of cognition, repair and social operations after death.

Population studies verified parent/child separation, capacity blocking,
exactly-once allocation release and replay across birth, repair, dormancy and
death.

The result is not a simulated metabolism. It is a runtime in which continued
operation depends on finite, checkpointed resources and irreversible lifecycle
rules.

### Milestone J — autonomous predictive development

The predictive lane introduced organism-side hypotheses without granting the
evaluator a teaching channel.

Shadow prediction can accumulate evidence, remain provisional, become supported,
be contradicted or retire.

Promotion into an active `PREDICTOR` remains explicit and bounded. A candidate
must demonstrate gain against trivial baselines; a no-gain candidate remains
unpromoted.

Checkpoint/replay preserves the evidence lifecycle and promotion decision.
Negative predictive evidence is retained rather than rewritten as success.

### Milestone K — emergent sociability

The social lane added an explicitly authorized `SocialHabitat`, local bounded
relation memory and finite-resource interaction.

The organism can:

- perceive opaque peer presence and channel state;
- record directional local evidence;
- exchange or compete for finite resources;
- retain support, harm, rejection, conflict and freshness as evidence rather than
  global labels;
- suspend and resume channels;
- select opportunities using its own bounded relation history;
- re-explore stale or previously denied options;
- preserve context by opaque channel/resource token;
- revise local choices when evidence changes.

No central social planner assigns roles, friends, enemies, niches or cooperative
goals.

Evaluator-only studies can describe reciprocity, isolation, pair diversity,
interaction entropy or niche differentiation, but those descriptions are not
available to the organism.

### What the dense `v0.79.x` hardening actually accomplished

The many patch releases in this range progressively closed four classes of gap:

1. **Runtime integration** — social, physiological and reproductive APIs became
   real `OrganismRuntime` boundaries rather than laboratory-only helpers.
2. **Replay correctness** — local relation memory, resource adaptation,
   reproduction, prediction and death retained deterministic continuation across
   checkpoints.
3. **Context preservation** — relational evidence became directional,
   freshness-aware and tied to opaque interaction context instead of being
   collapsed into a global score.
4. **Numerical and structural safety** — identifiers, resource values, weights,
   codecs and checkpoint payloads received strict finite/bounded validation.

Patch-level details remain available in `docs/CHANGELOG.md`; the organism-level
result is a **resource-bounded individual that can recover, reproduce, predict,
interact socially and revise local behavior without evaluator-defined goals**.

---

# Part V — `v0.80.x`: closure and pre-freeze hardening

## Numerical and evidence boundaries (`v0.80.00–v0.80.05`)

The first `v0.80` releases closed ambiguity around attention and predictive
evidence:

- budgets and costs reject non-finite or ambiguous numeric values;
- `NaN` cannot enter attention ranking;
- `+inf` remains reserved for genuinely unacclimated senses;
- relational hypotheses validate opaque identifiers, sample counts and bounded
  correlations;
- hypothesis lifecycle state survives checkpoint/replay;
- repeated observation receives diminishing-return pressure;
- sustained contradiction can retire a hypothesis instead of allowing later
  evidence to silently resurrect it.

A dedicated evaluator-only gate matrix then composed codec, attention,
hypothesis and shadow-promotion contracts without feeding the matrix result back
into cognition.

---

## Passive developmental observability (`v0.80.06–v0.80.13`)

Observatory gained additional views of development without becoming a control
surface.

Published metrics include bounded summaries such as:

- structural pressure relative to genome budgets;
- aggregate checkpoint quantization error;
- sensory-relation churn;
- session-scoped structural developmental divergence;
- attention concentration and entropy;
- physiological rest state and degradation counters;
- contextual social evidence.

These values are descriptive. They do not expose raw host semantics, learning
weights or evaluator truth, and they never drive runtime decisions.

The later integral Observatory architecture also makes provenance explicit:
what the organism observed, what the organism itself knows, and what the
observer derives are visually distinct. Canonical cognitive node kinds are
rendered from published topology and activation state rather than synthetic
“brain activity” animation.

Demo telemetry is explicitly marked as synthetic.

---

## Integrated I/J/K gates and autonomous social evidence (`v0.80.10–v0.80.15`)

The late pre-freeze releases composed previously separate studies into integrated
gate matrices.

Milestone K gained evaluator-only checks for:

- finite social boundaries;
- replay;
- generational continuity;
- resource adaptation;
- revision after denial;
- contextual evidence;
- multi-pair interaction;
- reciprocal observations;
- population-size variation.

Importantly, the autonomous social gate exercises
`OrganismRuntime.autonomous_social_step()` rather than relying only on a seeded
evaluator harness to specify interactions.

These studies demonstrate that the implemented social substrate can be exercised
by runtime-owned decisions under the tested conditions. They do not establish a
universal theory of social emergence.

---

## `v0.80.16` — Autonomous Cultural Agency v1

`v0.80.16` is the latest immutable published cut.

It adds bounded organism-side cultural policy for:

- retention;
- validation;
- transmission;
- composition;
- silence.

The laboratory still supplies topology, time windows, budgets and authorized
transport, but it no longer selects cultural content by handing the organism
claim or composite IDs.

Cultural decisions are checkpointable and costed. The preregistered
`learning.autonomous-cultural-agency` study validates the declared scope with
deterministic replay.

The release does **not** introduce sockets, host actions, model/corpus transfer or
human language.

---

# Part VI — biological closure and private learned models

## Biological Closure v1

Biological Closure v1 closed three preregistered boundaries needed before moving
from basic organism mechanics into the cultural research program:

- experienced interoception reduced later intervention needs relative to a naïve
  control with the same organism-facing surface;
- ecological differentiation remained replay-safe across the declared seeds;
- a bounded adaptive hereditary differential survived clonal descent under the
  tested environmental pressure.

These results close the declared v1 scope. They do not claim universal
generalization across arbitrary environments or evolutionary regimes.

---

## Private SLM v1

The next step was to let each organism build a **private learned sequence model**
from its own life without importing pretrained human knowledge.

The substrate provides:

- a bounded private experience ledger;
- explicit epistemic state and provenance;
- organism-isolated train/validation/test corpora;
- deterministic native tokenization;
- optional GRU and causal Transformer training in the laboratory;
- content-addressed model artifacts;
- strict ceilings on parameters, context, examples, epochs, steps and bytes;
- a lifecycle from candidate to shadow to active/degraded/retired;
- promotion based on held-out evidence;
- typed inference that cannot directly write facts or execute actions;
- explicit model lineage;
- cold restart without embedding weights inside the organism checkpoint.

The organism can incrementally adapt a private model while preserving its
identity and lineage constraints. A descendant inherits the **capacity** for
private modeling, not its parent's acquired corpus or model.

The research record also preserves negative evidence. Original regime-shift
controls did not satisfy their complete criterion and remain negative/ambiguous.
A later preregistered incremental-adaptation study demonstrated a distinct
capability and does not rewrite those earlier results.

Private SLM therefore means **organism-owned predictive learning**, not a
pretrained assistant hidden inside the runtime.

---

# Part VII — culture without model transfer

## Cultural Foundation v1

Culture begins with provenance-preserving claims, not with shared model weights.

A `SocialEvidenceLedger` keeps received social evidence separate from direct
experience. A local authorized `SocialChannel` transports bounded claims in
memory without sockets or peer discovery.

The foundation verifies that:

- copied claims do not become independent evidence merely by being copied;
- independent corroboration remains distinguishable from transmission;
- contradiction is preserved;
- provenance survives replay;
- claims can outlive their original discoverer;
- social evidence can reduce discovery cost in the declared protocol.

No Private SLM weights, adapters, corpora, raw telemetry or executable payloads
cross the channel.

---

## Cumulative Culture v1

Cumulative Culture extends the foundation from transmission to **versioned
composition**.

Cultural artifacts can combine contributions from multiple organisms while
retaining:

- contributor identity;
- independent evidence roots;
- derivation history;
- version lineage;
- bounded mutation/degradation semantics.

A composite can therefore survive beyond its founders without pretending that
copied ancestry is new evidence.

This is cumulative culture in the project's declared computational sense, not a
claim of human-like tradition or language.

---

## Autonomous Cultural Agency v1

Autonomous Cultural Agency moves the decision about **what to retain, validate,
share, combine or ignore** into the organism.

The apparatus provides only the local conditions under which those decisions can
occur. It does not choose the content.

This closes an important methodological gap: culture is no longer only a
property of a laboratory-controlled transmission schedule.

The policy remains bounded, local and checkpointable. It does not open network
discovery, reputation systems, human semantics or model transfer.

---

# Part VIII — symbols and structured communication

## Emergent Symbol Grounding v1

The organism can develop bounded associations between opaque symbols and its own
experience.

Grounding is based on organism-side evidence rather than an operator assigning a
human-readable name.

The scientific object is therefore the emergence of a stable internal
convention, not successful imitation of human vocabulary.

Human naming may remain an Observatory or future operator-facing convenience,
but it is not part of the grounding mechanism.

---

## Emergent Structured Communication v1

Communication then moved beyond isolated opaque tokens.

The channel supports bounded variable-length opaque sequences with:

- silence;
- transmission cost;
- finite memory;
- forgetting;
- cultural transmission;
- deterministic replay.

The substrate does **not** hard-code:

- grammatical slots;
- semantic roles;
- syntax;
- compositional targets;
- evaluator-selected messages.

Any structure must therefore arise from use of a generic bounded channel rather
than from a grammar hidden in the implementation.

---

## Structured Communication Characterization v1

The characterization program does not add another language capability.

It experimentally varies environmental complexity, vocabulary, sequence length,
memory and cost in order to distinguish:

- functional codes;
- holistic codes;
- more structured codes.

Evaluator-side analyses may measure those patterns, but compositionality is not
rewarded and is not a requirement for the organism to pass.

This distinction is important: the project can **measure structure without
training toward the metric used to describe it**.

---

# Part IX — population observation and longitudinal ecology

## Population Communication Telemetry v1

Population communication telemetry records bounded factual event history and
aggregates it for passive inspection.

It includes explicit truncation metadata so an observer can tell when historical
coverage is incomplete.

Telemetry may reconstruct observed exchanges, but it does not invent semantic
meaning, reconstruct missing historical edges or feed population-level
interpretation back into the organisms.

---

## Longitudinal Population Ecology v1

Longitudinal ecology is a discovery program, not another organism feature.

Progressively longer runs characterize:

- population dynamics;
- cultural persistence;
- communication patterns;
- resource behavior;
- boundedness;
- anomalies;
- candidate long-term phenomena.

Candidate patterns remain candidates until supported by a separate scientific
protocol. Exploratory discovery is not silently promoted into a capability
claim.

---

# Part X — Integrated Habitat Runtime v1

The final major architectural step was not a new cognitive mechanism. It was
integration.

Earlier audits found that many capabilities were individually implemented and
tested but were not all exercised through one canonical population lifecycle.

`IntegratedHabitatRuntime` resolves that integration gap by orchestrating the
existing APIs in one bounded habitat.

A single canonical run can now combine:

- birth and death;
- lineage;
- physiology;
- individual learning;
- Private SLM state;
- culture;
- opaque grounding;
- structured communication;
- social/resource interaction;
- checkpoint/replay;
- outbound population telemetry.

The runtime preserves private per-organism state and existing policy boundaries.
It does not add a new cognitive, social, cultural or linguistic objective.

The integration study covers deterministic replay, telemetry ON/OFF observer
equivalence and bounded long-run operation in the declared test scope.

The significance is architectural: the project now has **one reproducible
experimental subject**, rather than a collection of individually validated
subsystems.

---

# Part XI — final adversarial audit and Observatory

## Final adversarial audit v2

The first final audit identified the remaining integration defect: the organism
was scientifically rich but still modularly exercised.

After `IntegratedHabitatRuntime` and the final Observatory work, the re-audit
classified the canonical runtime as **class A — integrated**.

The audit verifies, within its declared scope:

- joint population lifecycle;
- physiology and learning;
- per-organism private model state;
- culture, grounding and communication;
- checkpoint/replay;
- bounded telemetry;
- observer equivalence with telemetry enabled or disabled;
- bounded extended runs;
- real browser QA of Observatory.

No material P0 or P1 issue remains in the audited scope.

The correct interpretation is **freeze readiness**, not proof that every possible
population, environment or timescale has been characterized.

---

## Observatory at freeze readiness

Observatory remains an apparatus around the organism, not part of its decision
loop.

Its current architecture is explicitly passive and provenance-aware.

It can display:

- individual and population state;
- canonical cognitive topology;
- published activation classes;
- learning and structural summaries;
- physiological state;
- relation and resource evidence;
- communication history;
- model/cultural lifecycle summaries;
- truncation and freshness information.

It visually distinguishes organism-observed state, organism-owned knowledge and
observer-derived interpretation.

The six canonical cognitive node kinds retain distinct visual and inspection
semantics, and demo data is explicitly identified as synthetic.

Nothing in the Observatory UI writes cognition, assigns semantics or selects
behavior.

---

# Part XII — the Experimental Organism v1 freeze

## What the freeze means

The `1.0.0` freeze is intended to stabilize the experimental subject, not to end
the project.

The frozen core includes:

- bounded organism runtime;
- perception and developmental sensing;
- cognition and structural plasticity;
- consolidated memory;
- physiology and homeostasis;
- lifecycle, heredity and reproduction;
- individual predictive learning;
- per-organism Private SLM;
- provenance-preserving culture;
- autonomous bounded cultural agency;
- opaque symbol grounding;
- structured communication;
- checkpoint/replay contracts;
- the canonical integrated habitat orchestration required to exercise those
  capabilities together.

## What remains allowed

The freeze still permits:

- bug and safety fixes;
- boundedness and reproducibility fixes;
- checkpoint and integration corrections that preserve semantics;
- new habitats and experiments;
- scientific analysis;
- preservation of negative results;
- passive Observatory and telemetry improvements;
- performance improvements that do not alter causal behavior.

## What does not silently enter the frozen organism

New capabilities require a new design/review gate.

In particular, the freeze does not silently permit:

- new cognitive or learning mechanisms;
- new social, cultural or language policies;
- new inherited abilities or rewards;
- evaluator truth entering cognition;
- transfer of private models, weights or corpora;
- autonomous host actions;
- relaxed security or resource boundaries.

---

# What remains open after the freeze

The organism is complete only in the sense defined by the freeze contract.

Several questions remain scientific rather than missing implementation:

- How well do the observed phenomena generalize across larger populations,
  longer timescales and different habitats?
- Which apparent social or cultural patterns persist under stronger controls?
- Under what pressures do opaque symbol systems stabilize, fragment or disappear?
- When does structured communication become more compositional, if at all?
- How do private learned models and cultural evidence coevolve without collapsing
  the distinction between individual and social knowledge?
- Which long-run ecological phenomena are reproducible rather than seed-specific?
- What new behavior appears when the same frozen organisms are placed in richer
  but still bounded habitats?

Those questions should be investigated **around the frozen organism**, not
answered by repeatedly adding a mechanism whose behavior the experiment was
supposed to discover.

---

## Summary

Symbiont evolved through a sequence of increasingly integrated transitions:

```text
real perception
    ↓
adaptive host model
    ↓
attention and inquiry
    ↓
developmental sensing
    ↓
plastic cognition
    ↓
consolidated memory
    ↓
physiology and viability
    ↓
reproduction and heredity
    ↓
ecology
    ↓
predictive and social development
    ↓
private learned models
    ↓
provenance-preserving culture
    ↓
autonomous cultural agency
    ↓
opaque grounded symbols
    ↓
structured communication
    ↓
integrated population runtime
    ↓
Experimental Organism v1
```

The final subject is not claimed to be alive in the biological sense, conscious,
generally intelligent or socially human-like.

It is a reproducible experimental digital organism whose perception, learning,
memory, viability, heredity, interaction, private modeling, culture and
communication are implemented as bounded computational processes and can now be
studied together without making the evaluator part of the organism's cognition.
