# Symbiont organism roadmap

This roadmap prioritizes capabilities acquired by the organism. Laboratory work is
introduced only when a new organism capability needs a new measurement instrument.

The sequence is directional rather than calendar-based. Every release is one
reviewable merge and must pass its milestone gate before work advances to the next
stage.

## North star

Build a benevolent digital organism that discovers a consenting host, perceives it
through safe normalized senses, learns its rhythms, investigates uncertainty and
cooperates without propagation, concealment or autonomous control.

## 2026-09-13 restructure

A review of issues #32–#36 and PRs #38–#54 found that Symbiont had accumulated real
capabilities (discovery, sampling, acclimation, rhythms, drift, attention,
second-look, evidence revision, narrative, capsules, source trust) but:

1. no single process connects them into a persistent cognitive cycle — each is a
   one-shot CLI verb, state discarded on exit;
2. nothing produces an output that serves the host owner directly — the organism
   can narrate its own uncertainty but never says "this deserves a look";
3. real sensor coverage is thin (CPU and disk only; memory/thermal/power stubbed
   `unavailable`);
4. "same schema across platforms" (Milestone A's own exit gate) was asserted but
   never verified — CI ran `ubuntu-latest` only;
5. v0.43's `SourceTrustModel` conflates "agrees with my local baseline" with "is
   reliable" — an echo-chamber risk: a differently-but-correctly-configured host is
   penalized, a mimicking source is rewarded;
6. v0.42's `KnowledgeCapsule` guarantees integrity and authorship, not that its
   content is schema-bounded, fresh, replay-protected or safe to ingest.

The original "Milestone D — Cooperative species" (v0.42–v0.46) is closed and split.
v0.42–v0.43 shipped and stand as-is. What remained is replaced by two milestones:
**D — Operational embodiment** (inserted first: a single organism needs a real
lifecycle, resource governance, durable state, proven cross-platform behavior and a
defensive-advisory output before multi-Symbiont cooperation is built on top of it),
and **E — Cooperative species** (the renumbered, expanded continuation of the
original scope). Building collective/transport machinery before a single Symbiont
has an operational lifecycle would construct a society before an individual
organism exists.

## Merge sequence

| Release | Organism capability | Merge result |
|---|---|---|
| v0.30 | Sensor reading contract | Typed readings with units, monotonic time, provenance, quality and privacy class |
| v0.31 | Cross-platform resource provider | Real CPU, memory, storage, thermal and power readings where available |
| v0.32 | Sensor lifecycle | Hot capability changes, failure isolation, backoff and bounded buffers |
| v0.33 | Acclimation | Initial host baseline with threat conclusions explicitly withheld |
| v0.34 | Percept synthesis | Platform-specific readings become platform-neutral perceptions |
| v0.35 | Context and rhythms | Time, workload and co-occurrence context without user identity |
| v0.36 | Drift-aware beliefs | Isolated novelty, gradual change and regime shifts are distinguished |
| v0.37 | Safe checkpoints | Explicit model export/import without raw telemetry |
| v0.38 | Live attention budget | Causal allocation of limited attention using uncertainty and cost |
| v0.39 | Read-only second look | Temporary higher-resolution sampling through authorized senses |
| v0.40 | Evidence revision | New evidence revises beliefs while preserving contradiction and dissent |
| v0.41 | Organism narrative | Inspectable explanations of attention, evidence, belief and uncertainty |
| v0.42 | Knowledge capsules | Signed, identity-minimized, offline exchange of abstract knowledge |
| v0.43 | Contextual source trust | Reliability learned by source and pattern family (**known limitation: conflates agreement with reliability — superseded by v0.51**) |
| v0.44 | Organism runtime | A single continuous cognitive cycle replaces one-shot CLI verbs |
| v0.45 | Consent and resource governor | Explicit, continuously-checked policy, permission, frequency and resource budget |
| v0.46 | Durable organism state | Atomic save/restore, schema migration, crash/restart recovery |
| v0.47 | Cross-platform proof | Real CI verification on Windows, Linux, macOS and a constrained environment |
| v0.48 | Defensive advisory | Explainable, human-reviewed recommendation — never autonomous action |
| v0.49 | Real-host evaluation | Measured usefulness against real operator judgment, never used as an oracle by cognition |
| v0.50 | Capsule schema and replay protection | Closed content schema, size/depth bounds, id, validity window, replay defense |
| v0.51 | Evidence-aware trust | Separates ecological compatibility, consistency, evidence quality, freshness, independence, cryptographic vs. epistemic trust |
| v0.52 | Collective revision | Evidence aggregation without treating majority as truth, on the corrected trust model |
| v0.53 | Consent-bound transport | Optional authenticated exchange, disabled by default and revocable |
| v0.54 | Adversarial resilience | Replay, poisoning, Sybil and stale-knowledge defenses |

## Milestone A — Safe real perception

Tracking: [#32](https://github.com/alessbarb/symbiont-lab/issues/32)

Includes v0.30–v0.33. Symbiont exits this milestone only when it can sample a
consenting local host through the same normalized contract on every supported
platform, stay within bounded resources, survive individual sensor failures and
prove that identity and user content are not collected.

Threat classification is disabled during acclimation. Network discovery, packet
inspection, command lines, file contents, process control and remediation are out
of scope.

**Caveat carried forward:** "same schema across platforms" was verified only on
Linux; Windows/macOS behavior is asserted from code inspection, not CI. Closed by
Milestone D's v0.47.

## Milestone B — Adaptive host model

Tracking: [#34](https://github.com/alessbarb/symbiont-lab/issues/34)

Includes v0.34–v0.37. Symbiont exits this milestone when cognition remains
independent of platform providers, contextual baselines can age and adapt to regime
changes, restarts can restore only safe abstract state, and the organism can explain
why an observation is familiar, novel or uncertain.

The final exit-gate item was satisfied retroactively by v0.41's `narrate_host`
(Milestone C), not by this milestone's own releases — see #34's closing comment.

## Milestone C — Autonomous inquiry and explanation

Tracking: [#33](https://github.com/alessbarb/symbiont-lab/issues/33)

Includes v0.38–v0.41. Symbiont exits this milestone when it can allocate a hard
attention budget before additional evidence exists, request only local, authorized,
read-only and cancellable measurements, revise beliefs from that evidence and expose
a complete uncertainty-aware narrative.

Inquiry is not remediation. Symbiont still cannot write, execute, terminate,
quarantine or reconfigure anything.

## Milestone D — Operational embodiment

Tracking: [#55](https://github.com/alessbarb/symbiont-lab/issues/55)

Includes v0.44–v0.49. Symbiont exits this milestone when it runs as one continuous,
governed, recoverable process on a single host — not disconnected one-shot
commands — proves its cross-platform claims in CI rather than asserting them, and
produces a consultative defensive-advisory output a human can act on.

v0.48 (defensive advisory) is **decision-gated**: it touches CLAUDE.md's
"no threat classification" boundary and requires the same explicit
architectural/safety sign-off v0.42's signing scheme received, before
implementation — a recommendation output is not "just this once."

v0.49's evaluation measures real usefulness without ever exposing that evaluation
back to cognition as an oracle — the same evaluator/organism separation this
project has held since its synthetic-simulation origins.

## Milestone E — Cooperative species

Tracking: [#56](https://github.com/alessbarb/symbiont-lab/issues/56)

Includes v0.50–v0.54. The renumbered, expanded continuation of the original
"cooperative species" scope (formerly v0.44–v0.46 under #35), gated on Milestone D's
exit. Knowledge exchange begins offline so its data contract and privacy properties
can be tested before transport exists. The milestone exits only when shared objects
conform to a closed, versioned, replay-protected schema, trust separates ecological
compatibility from actual reliability (superseding v0.43), aggregation never treats
a majority as truth, local agents retain veto power, transport is explicit and
revocable, and adversarial contributors cannot manufacture trust through replay,
scale or mimicry.

v0.51 must supersede v0.43's `SourceTrustModel` before v0.52 (collective revision —
already drafted on branch `wip/v0.44-collective-revision-paused`, paused pending
this rework) is allowed to build on it again.

There is no autonomous peer discovery and no propagation.

## Merge gate

A planned release may merge only when all of these are true:

1. The full CI matrix is green for the exact PR HEAD.
2. The base branch has not moved, or the branch was updated and CI reran.
3. There are no unresolved review threads or requested changes.
4. New resource use is bounded and tested.
5. Platform independence and provider failure isolation are tested where relevant.
6. Privacy and safety invariants are executable tests, not documentation alone.
7. The release documents what the organism can now perceive, remember, reason,
   decide, communicate or learn.
8. Ground truth remains outside organism cognition.

## Decision gates

Work pauses for an explicit architectural and safety decision before any merge that:

- requests write, execute, elevated or remote permissions;
- collects identifying metadata or user content;
- enables network exchange;
- introduces durable background execution;
- permits autonomous real-world action;
- creates unbounded CPU, memory, storage or network use;
- weakens the separation between organism and evaluator;
- produces any advisory, warning or recommendation intended to influence a
  host-security or operational decision.

## Tracking

The cross-milestone roadmap is maintained in
[#36](https://github.com/alessbarb/symbiont-lab/issues/36).
