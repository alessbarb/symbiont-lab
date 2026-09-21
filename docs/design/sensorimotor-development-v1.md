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

Every 128 canonical ticks, beginning after initial development, the organism
also performs a four-tick **null-action probe**. All motor output, including
direct cognitive output, is suppressed during that short window.

Those probes estimate passive body dynamics:

    state(t), action=0 -> state(t+4)

Primitive effect magnitude is scored on change above that passive baseline.
Signed per-signal effects are likewise corrected by estimated passive drift.

Controllability is therefore proportional to:

    excess effect above passive drift
    × reproducibility
    × directional consistency

Thus falling, inertial drift, passive settling or a freely moving joint cannot
become a skill merely because the body happened to move while a command was
present.

Evidence is reversible. If replication contradicts an earlier candidate, its
controllability falls and the primitive can be removed.

## Autonomous hypothesis investigation

One observed episode is only a candidate — a causal hypothesis, not a skill.

The organism therefore keeps one unresolved motor hypothesis under active
investigation. On each bounded investigation epoch it may replay that same
opaque temporal chunk and compare the resulting body-state transition against
its previous evidence and against the independently learned null-action
baseline.

This is deliberately not a sparse random/hash lottery. Candidate production
must not be able to outrun verification indefinitely. The investigation target
is chosen only from organism-owned evidence:

- residual controllability above passive drift;
- directional repeatability;
- remaining uncertainty / bounded verification budget.

No locomotion score, world coordinate, resource direction, anatomical label or
task reward enters the selection.

The learner keeps testing the current hypothesis coherently until one of three
things happens:

1. repeated evidence satisfies the competence gate;
2. contradictory evidence collapses controllability and removes the candidate;
3. the bounded verification budget is exhausted, after which the unresolved
   hypothesis stops monopolising active investigation.

At most one four-tick investigation can start per 16-tick epoch, leaving the
rest of development available for continued babbling and new hypothesis
formation.

A candidate becomes cognitively available only after at least two independent
consequence samples and after passing:

- positive controllability;
- bounded effect variance;
- directional-consistency threshold.

In code this distinction is explicit:

    observed temporal chunk -> motor hypothesis
    independently reproduced controllable effect -> competence
    competence admitted into CognitiveGraph -> cognitive action

Verification is an organism action. It is never selected by the laboratory
because an evaluator likes the resulting movement.

## Cognitive promotion

Verified primitives receive their own opaque readout family:

    readout_primitive:primitive.<digest>

They are distinct from direct physical actuator readouts.

A primitive can therefore become an action available to the cognitive graph
without exposing its internal actuator sequence.

A cognitively selected primitive records state→action association evidence once
at the start of the episode, never once per primitive tick.

An autonomous verification is stricter: its starting concept context is retained
temporarily, but receives cognitive association credit only after the four motor
steps have completed, the future body state has been observed, and the
sensorimotor learner has actually gained a new independent sample that still
passes the cognitive primitive gate. Scheduling a replay is never itself
evidence of success.

If verification succeeds after the cognition phase of that canonical tick, its
new readout is not inserted out-of-band. The retained context waits until a
later normal CognitiveBridge tick admits the readout within the ordinary
structural mutation budget; only then is concept-to-primitive evidence recorded.

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
- passive-dynamics sufficient statistics;
- an in-progress primitive replay step;
- pending cognitive context for an autonomous verification, including the
  primitive sample count present before that verification began.

Raw body-state history is deliberately not persisted. After restart, temporal
comparison windows cold-start instead of reconstructing evidence from telemetry.
A pending verification can therefore receive later cognitive credit only if a
genuinely new primitive sample is acquired after restore.

This avoids fabricating action→consequence samples across a process boundary.

## Boundedness

Resident state is bounded:

- at most 512 horizon statistics;
- at most 64 primitive evidence records;
- at most 32 retained motor primitives;
- at most 8 verified primitives exposed to cognition at one time;
- four concurrent physical outputs per cognitive tick;
- fixed four-tick primitive chunks in v1.

Eviction prefers evidence-rich and controllable hypotheses.

## Evaluator metrics

Physics3D exposes passive metrics only:

- Babbling coverage
- Known motor patterns
- Motor primitives
- Unresolved motor hypotheses
- Cognitive primitives / acquired competences
- Active motor investigation and its opaque primitive id
- Best controllability
- Best direction consistency
- Primitive replay
- Horizon samples 1/4/16/64
- Passive baseline samples
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

Pass only if at least one candidate survives independent replay, produces body
change distinguishable from the null-action baseline and directional consistency
remains above threshold.

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
