# Sensorimotor development v1

Status: implemented baseline; empirical validation pending.

## Purpose

A Symbiont embodied in a physical body must not receive a gait, anatomy labels,
locomotion targets, inverse kinematics, hand-authored motor synergies, or a
reward for moving in an experimenter-selected direction.

The organism is instead given:

- a finite set of opaque physical actuator channels that exist by constitution;
- opaque sensory consequences of its body and environment;
- bounded metabolic cost for actual actuation;
- a resident developmental mechanism capable of exploring, predicting and
  compressing its own sensorimotor dynamics.

The first scientific objective is not locomotion. It is autonomous acquisition
of bodily control.

## Architectural boundary

The sensorimotor learner belongs to the organism and is checkpointed with it.
Physics3D supplies only physical consequences.

The learner never receives:

- link or joint names;
- limb identities;
- world coordinates;
- the position or direction of a resource;
- labels such as walk, crawl, stand, arm, leg, forward or balance;
- an experimenter-authored sequence of actuator commands.

Evaluator telemetry may observe those facts outside the organism.

## Innate motor capacity versus learned control

Every actuator in the motor constitution is physically available from birth.
Availability does not mean knowledge.

The organism must learn:

- which combinations produce reproducible consequences;
- how consequences unfold over time;
- which temporal chunks can be replayed;
- which learned chunks are useful under later cognitive states.

This replaces the old assumption that an actuator had to be promoted before it
could even participate in meaningful exploration.

## Developmental babbling

Babbling is organism-owned, deterministic from organism identity and tick, and
semantic-free.

Properties:

- up to four opaque channels may act concurrently;
- channel sets persist for short eight-tick epochs;
- activation moves smoothly toward endogenous targets rather than jumping as
  white noise;
- least-used channels receive priority at epoch changes, guaranteeing coverage;
- no physical direction or anatomical role is encoded.

The purpose is persistent excitation of the body's dynamics, not locomotion.

## Multi-horizon dynamics evidence

For every actual delivered motor vector, the learner compares the body state
against future body states at horizons:

- 1 tick;
- 4 ticks;
- 16 ticks;
- 64 ticks.

Statistics are separated by horizon. Evidence at different horizons is never
averaged into one number.

This allows delayed physical consequences to exist without being penalized for
not appearing in the immediately following tick.

## Temporal primitive discovery

A primitive is a temporal sequence, not a single actuator and not a static
pose.

The v1 chunk length is four cognitive ticks. A candidate therefore contains:

    vector(t)
    vector(t+1)
    vector(t+2)
    vector(t+3)

Each vector may contain several concurrent opaque actuator channels.

Candidates originate only from non-primitive organism activity. Replaying an
existing primitive may validate or falsify it but cannot recursively manufacture
new skills from itself.

The primitive id is a deterministic opaque digest of the learned temporal
sequence.

## Consequence criterion

A primitive is not accepted because it creates large motion.

For every execution the learner measures:

1. mean absolute body-state change;
2. variance of that effect across repetitions;
3. signed per-signal changes;
4. directional consistency of those signed changes.

Controllability is proportional to:

    effect magnitude
    × reproducibility
    × directional consistency

Thus a freely spinning joint that produces a large but inconsistent consequence
does not automatically dominate learning.

Evidence is reversible. If replication contradicts an earlier candidate, its
controllability falls and the primitive can be removed.

## Independent verification

One observed episode is only a candidate.

The organism sparsely replays candidates using an endogenous deterministic
verification schedule. A candidate becomes cognitively available only after at
least two independent consequence samples and after passing:

- positive controllability;
- bounded effect variance;
- directional-consistency threshold.

Verification is an organism action. It is not selected by the laboratory based
on success at locomotion or proximity to a resource.

## Cognitive promotion

Verified primitives receive their own opaque readout family:

    readout_primitive:primitive.<digest>

They are distinct from direct physical actuator readouts.

A primitive can therefore become an action available to the cognitive graph
without exposing its internal actuator sequence.

When a verification or cognitive primitive episode starts, the currently active
concepts may accumulate structural association evidence toward that primitive
readout. The association is recorded once per episode, never once per primitive
tick.

Once graph plasticity establishes a route, cognition may invoke the primitive.
The primitive then executes atomically for its learned temporal duration.

This creates the developmental hierarchy:

    physical actuator channels
        ↓
    correlated motor babbling
        ↓
    sensorimotor consequences
        ↓
    verified temporal primitives
        ↓
    opaque cognitive actions
        ↓
    later goal-dependent sequencing

## Persistence

Checkpoint state includes:

- babbling activation state and coverage;
- per-horizon sufficient statistics;
- candidate and verified primitives;
- directional-effect statistics;
- primitive verification counts;
- an in-progress primitive replay step.

Raw body-state history is deliberately not persisted. After restart, temporal
comparison windows cold-start instead of reconstructing evidence from telemetry.

This avoids fabricating action→consequence samples across a process boundary.

## Boundedness

Resident state is bounded:

- at most 1,024 horizon statistics;
- at most 256 primitive evidence records;
- at most 32 motor primitives;
- four concurrent physical outputs per cognitive tick;
- fixed four-tick primitive chunks in v1.

Eviction prefers evidence-rich and controllable hypotheses.

## Evaluator metrics

Physics3D exposes passive metrics only:

- Babbling coverage
- Known motor patterns
- Motor primitives
- Cognitive primitives
- Best controllability
- Best direction consistency
- Primitive replay
- Horizon samples 1/4/16/64
- Concurrent outputs now
- Motor origin

These metrics do not feed back into the subject.

## Empirical gates

### Gate A — whole-body exploration

Pass only if babbling coverage reaches 100% and concurrent activity is observed
across multiple actuator subsets. Repeated use of one channel is a failure.

### Gate B — temporal learning

Pass only if all four horizon counters grow and multiple motor patterns collect
evidence.

### Gate C — reproducible primitive discovery

Pass only if at least one candidate survives independent replay and directional
consistency remains above threshold.

A candidate that disappears after replication is a valid falsification, not a
failure of the experiment.

### Gate D — cognitive availability

Pass only if at least one verified primitive receives a primitive readout and
structural evidence can produce a concept→primitive path without hand wiring.

### Gate E — endogenous reuse

Pass only if cognition later initiates a primitive without an evaluator command.

### Gate F — functional control

Only after A–E pass should the laboratory reintroduce an ecological task such as
moving through space toward a resource. Success must then be compared against
matched babbling-only and shuffled-action controls.

## What this does not claim

This architecture does not establish walking, planning, agency or general
intelligence.

It establishes a falsifiable developmental path by which a physically embodied
Symbiont can discover temporal actions from its own experience and make those
actions available to later cognition without receiving human motor solutions.
