# Symbiont organism roadmap

This roadmap prioritizes capabilities acquired by the organism. Laboratory work is
introduced only when a new organism capability needs a new measurement instrument.
The sequence is directional rather than calendar-based.

## North star

Build a benevolent digital organism that discovers a consenting host, develops its
own safe normalized senses, learns relationships and rhythms in its local ecology,
investigates uncertainty, maintains a transparent resident life cycle and eventually
cooperates with other explicitly consenting Symbionts without propagation,
concealment or autonomous control.

## 2026-09-14 developmental restructure

PR #70 changed the meaning of embodiment. Symbiont no longer has to be handed a
semantic list such as CPU/memory/thermal and told which senses matter. On Linux it
can discover a bounded, vetted set of aggregate read-only numeric surfaces, assign
opaque identities to them, learn which are useful, persist only abstract learned
state and run transparently as an owner-installed user service.

That makes the next scientific question developmental rather than social: before
building a species, make the individual capable of constructing a coherent sensory
world. The former Milestone E (cooperative species) therefore moves to Milestone F
and v0.60-v0.64. v0.50-v0.54 are reserved for **Developmental embodiment**.

This does not relax the safety boundary. Discovery is constrained by provider-side
allowlists and permission policy. Symbiont never searches for credentials, writable
surfaces, executable opportunities, additional privilege, peers or propagation
paths. Residence is transparent, user-owned and removable.

## Merge sequence

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
| v0.43 | Contextual source trust | Historical implementation; known echo-chamber limitation, superseded before cooperation |
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
| v0.56 | Cognitive graph | Nodes/edges, sensory normalization, deterministic double-buffered activation, gating |
| v0.57 | Label-free learning | Prediction error (Huber loss), eligibility traces, bounded Oja weight updates |
| v0.58 | Metaplasticity and structure | Pareto objective, bounded parameter adaptation, structural creation/pruning, safe-mode |
| v0.59 | Laboratory evolution | Genome mutation, Pareto-archive selection, cycle-protected lineage archive |
| v0.60 | Capsule schema and replay protection | Closed shared schema, size/depth bounds, id, validity window and replay defense |
| v0.61 | Evidence-aware trust | Separate ecological compatibility, evidence quality, freshness, independence and signer/claim trust |
| v0.62 | Collective revision | Evidence aggregation without treating majority as truth |
| v0.63 | Consent-bound transport | Optional authenticated exchange, disabled by default and explicitly revocable |
| v0.64 | Adversarial resilience | Replay, poisoning, Sybil and stale-knowledge defenses |

## Milestone A — Safe real perception

Tracking: #32. Includes v0.30-v0.33. Symbiont can sample a consenting local host
through normalized contracts, with bounded resources and sensor failure isolation.
Identity, user content, packet inspection, command lines, arbitrary file contents,
process control and remediation remain outside the perception boundary.

## Milestone B — Adaptive host model

Tracking: #34. Includes v0.34-v0.37. Cognition remains independent of platform
providers, contextual baselines can adapt, and restarts restore only safe abstract
state.

## Milestone C — Autonomous inquiry and explanation

Tracking: #33. Includes v0.38-v0.41. Symbiont can allocate bounded attention,
request only authorized read-only second looks, revise beliefs and explain its
uncertainty. Inquiry is never remediation.

## Milestone D — Operational embodiment

Tracking: #55. Includes v0.44-v0.49. The organism became a governed recoverable
single-host cognitive cycle with explicit human-facing advisory output and
real-operator evaluation. The historical cross-platform CI caveat is retained as a
verification limitation, not a blocker on Linux development per owner policy.

## Milestone E — Developmental embodiment

Includes v0.50-v0.54.

The organism exits this milestone when it can enter an unfamiliar consenting host
without being handed a semantic sensor catalog, develop a bounded sensory repertoire,
learn relationships among senses, allocate sensing effort based on information and
cost, maintain a self-model of perceptual health, and remain stable through long-run
change and rediscovery.

Exit conditions:

1. Candidate surfaces are discovered only through explicitly safe local read-only
   provider boundaries; cognition sees opaque learned senses, not paths or OS APIs.
2. Sensory selection depends on learned availability/information/redundancy rather
   than a hard-coded importance list.
3. Same-time and lagged associations are descriptive only — never silently promoted
   to causal claims.
4. Sampling effort is bounded and adaptive; dormant senses retain a bounded chance
   of re-exploration so the organism cannot permanently blind itself from early
   mistakes.
5. Checkpoints contain aggregate learned state, never raw sample histories or the
   most recent raw host reading.
6. Residence remains transparent, owner-installed, least-privileged and removable.
7. Observatory remains passive: it may inspect but cannot command the organism.

## Milestone E2 — Endogenous plasticity

Includes v0.55-v0.59. Owner-authored technical design:
`docs/design/endogenous-plasticity.md`. The organism's self-programming
capability is implemented as **plasticity of data under an immutable
kernel**, never as generated/edited/executed code: an immutable kernel
defines hard limits and a closed node/edge catalog; a declarative,
versioned genome configures one individual's development within those
limits; a plastic phenotype (a `CognitiveGraph`) learns weights and
bounded structure during that individual's life; generational evolution
(genome mutation, multi-environment evaluation, Pareto-archive selection)
happens only in `symbiont_lab`, never inside the resident organism itself.

Exit conditions:

1. Two organisms born from the same genome but exposed to different
   experience end up with measurably different graphs — deterministically,
   not by chance.
2. Weight adaptation reduces prediction error or representation cost on at
   least one preregistered protocol without ever receiving an external label.
3. Structure can be created and pruned, and resident memory use stays
   bounded regardless of how long the organism runs.
4. No learned or mutated field is ever usable as a path, module name,
   command or permission; the kernel's hard limits are never themselves
   learnable.
5. Checkpoint/restart preserves the phenotype without preserving the most
   recent raw activation.
6. A plasticity failure rolls back that tick and can trigger a bounded
   safe mode without losing the underlying organism.
7. Generational evolution happens only in explicit laboratory runs, never
   as something the resident organism does to itself.

**v0.59.5 — Biological memory consolidation (completed follow-on hardening).**
Owner-authored technical design: `docs/design/biological-memory-consolidation.md`.
Changes the persistence model from "serialize learned state" to "persist
consolidated memory": checkpoint schema v6, a `WeightStabilityTracker` that
commits an edge's weight class only after epoch-spaced stability (node-atomic —
a node's changed edges commit together or not at all), a consolidated-baseline
codec for host statistics (signed-log center, constant-sentinel scale,
monotone maturity), `SelfModel`'s `RecencyClass` replacing the exact
`last_observed_tick`, and a bounded reacclimation period after restart so a
cold start itself is never misread as a salient or structural event. PR #76's
prior continuity guarantee is deliberately superseded: a restart no longer
reconstructs the previous tick's activation, on the reasoning that seeding
from a coarse class would synthesize a microstate that never occurred, which
is worse than genuinely losing it. `MemoryConsolidator`'s salient-event fast
path — a one-shot durable trace for one exceptional, attended, reliable
transition — is wired into the real `OrganismRuntime.tick()` loop, closing
the one piece of the design (§23 PR5) that had no caller until this release.
All eleven exit conditions in design §25 are satisfied.

## Milestone F — Cooperative species

Tracking: #56. Includes v0.60-v0.64. This is the postponed cooperative-species
milestone. Knowledge exchange begins offline; transport remains decision-gated.
Before collective revision resumes, the old v0.43 trust model must be superseded so
agreement with the local host is never confused with source reliability.

There is no autonomous peer discovery and no propagation.

## Merge policy

The project owner has explicitly instructed that GitHub Actions are not a merge gate.
A release can therefore merge after local/structural review even when hosted CI is
unavailable. The remaining gates are:

1. base/head drift is checked before merge;
2. no unresolved requested changes are knowingly ignored;
3. new resource use is bounded by construction and covered with deterministic tests;
4. privacy/safety invariants accompany functional behavior;
5. ground truth remains outside organism cognition;
6. the release documents the new organism capability.

## Decision gates

Work pauses for an explicit architectural and safety decision before any merge that:

- requests write, execute, elevated or remote permissions;
- collects identifying metadata or user content;
- enables network exchange;
- introduces hidden or non-removable persistence;
- permits autonomous real-world action;
- creates unbounded CPU, memory, storage or network use;
- weakens the separation between organism and evaluator;
- materially expands a human-facing security/operational advisory beyond the already
  approved consultative boundary.

Transparent owner-installed residence and bounded read-only sensory development are
already explicitly approved and do not reopen those decisions.

## Tracking

The cross-milestone roadmap is maintained in issue #36.
