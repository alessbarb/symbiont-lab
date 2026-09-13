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
| v0.43 | Contextual source trust | Reliability learned by source and pattern family |
| v0.44 | Collective revision | Evidence aggregation without treating majority as truth |
| v0.45 | Consent-bound transport | Optional authenticated exchange, disabled by default and revocable |
| v0.46 | Adversarial resilience | Replay, poisoning, Sybil and stale-knowledge defenses |

## Milestone A — Safe real perception

Tracking: [#32](https://github.com/alessbarb/symbiont-lab/issues/32)

Includes v0.30–v0.33. Symbiont exits this milestone only when it can sample a
consenting local host through the same normalized contract on every supported
platform, stay within bounded resources, survive individual sensor failures and
prove that identity and user content are not collected.

Threat classification is disabled during acclimation. Network discovery, packet
inspection, command lines, file contents, process control and remediation are out
of scope.

## Milestone B — Adaptive host model

Tracking: [#34](https://github.com/alessbarb/symbiont-lab/issues/34)

Includes v0.34–v0.37. Symbiont exits this milestone when cognition remains
independent of platform providers, contextual baselines can age and adapt to regime
changes, restarts can restore only safe abstract state, and the organism can explain
why an observation is familiar, novel or uncertain.

## Milestone C — Autonomous inquiry and explanation

Tracking: [#33](https://github.com/alessbarb/symbiont-lab/issues/33)

Includes v0.38–v0.41. Symbiont exits this milestone when it can allocate a hard
attention budget before additional evidence exists, request only local, authorized,
read-only and cancellable measurements, revise beliefs from that evidence and expose
a complete uncertainty-aware narrative.

Inquiry is not remediation. Symbiont still cannot write, execute, terminate,
quarantine or reconfigure anything.

## Milestone D — Cooperative species

Tracking: [#35](https://github.com/alessbarb/symbiont-lab/issues/35)

Includes v0.42–v0.46. Knowledge exchange begins offline so its data contract and
privacy properties can be tested before transport exists. The milestone exits only
when local agents retain veto power, shared objects contain no raw telemetry or
stable host identity, transport is explicit and revocable, and adversarial
contributors cannot manufacture trust through replay or scale.

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
- weakens the separation between organism and evaluator.

## Tracking

The cross-milestone roadmap is maintained in
[#36](https://github.com/alessbarb/symbiont-lab/issues/36).
