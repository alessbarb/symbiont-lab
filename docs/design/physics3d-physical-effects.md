# Physics3D physical effects

Status: canonical observer-side specification.

## Purpose

A motor primitive and a physical effect are different objects.

The organism discovers opaque temporal motor structure from its own sensory and
motor history. Physics3D, as apparatus, may measure what happened physically
during the same interval. The apparatus measurement is scientific evidence; it
is not a reward, goal, semantic label or action hint.

## Boundary

Symbiont motor episode -> ephemeral identity and ticks -> Physics3D telemetry
-> immutable physical evidence -> offline study.

No value produced by the physical-effect assay feeds cognition, prospective
agency, primitive competence, motor selection or babbling.

The organism is not told what is a leg, arm, floor, gait, forward direction,
resource progress or useful locomotion.

## Primitive episode provenance

PrimitiveEpisode contains only primitive identity, start/end tick, source,
independent evidence blocks, sample ordinal, materialization state and existing
semantic-free competence state.

The event is one-observation ephemeral state and is not checkpointed.
Sensorimotor checkpoint schema remains v7.

## Physical state

Observer-side state includes world base pose, linear/angular velocity,
mass-weighted center of mass, joint configuration and contact-link signature.
Physical truth remains apparatus-owned.

## Physical consequence

For one interval, the assay derives world translation, translation in the
body's initial coordinate frame, center-of-mass translation, base/COM
agreement, orientation change, path length, horizontal path efficiency,
joint-pose change, contact changes, mechanical work and metabolic work cost.

No scalar locomotion score is defined.

## Replication

An observed primitive effect is represented as a relation between the physical
initial state, the opaque primitive identity and the measured consequence:

    (S0, primitive) -> effect

The offline assay records the episode count, independent evidence-block count,
mean/median/dispersion of translation magnitude and directional concentration.
The default replication target is eight observed episodes. This is an
observer-side study target only; it is not a materialization or competence
criterion inside Symbiont.

## Initial-state conditioning

A primitive effect is not assumed to be state-independent. Comparability is
preserved as separate dimensions: orientation, linear velocity, angular
velocity, joint RMS, contact Jaccard distance and center-of-mass height.
They are deliberately not collapsed into one hand-tuned score.

The study may define transparent tolerances for those six dimensions. Two
initial states are called comparable only when every dimension lies within its
own tolerance. Reports then keep separate effect disagreement for comparable
and non-comparable state pairs:

- body-frame translation-vector difference;
- body-frame direction-angle difference;
- center-of-mass translation-vector difference.

This lets the experiment test whether within-state effect variation is lower
than between-state effect variation without teaching state semantics to the
organism.

## Directional recurrence

For non-trivial horizontal body-frame translations, direction concentration is
the magnitude of the mean unit translation vector. It approaches 1 when effects
point consistently in the same egocentric direction and approaches 0 when they
cancel. A small noise floor excludes numerically meaningless directions.

Directional concentration is not sufficient evidence on its own. Translation
magnitude, COM motion, rotation, pose change, contacts, path efficiency and
initial-state conditioning remain separate measurements.

## Causality

The observational assay establishes association, not isolated causation.

A matched-control Physics3D study must restore one shared physical initial state
and evaluate three arms:

1. primitive: replay the discovered motor coordination;
2. passive: apply no motor command;
3. motor control: preserve a comparable actuator/duration/command budget while
   disrupting the primitive's temporal or coordination structure.

The study analyzer compares primitive-minus-passive and
primitive-minus-motor-control consequences separately. Passive dynamics are not
treated as noise to erase: the first contrast measures the active contribution
on top of the body's natural evolution, while the second asks whether the
specific coordination matters beyond injecting a similar motor command budget.

The matched-control analyzer remains in studies. It must not become an
organism-side verification scheduler.

## Generalization

After a local causal effect is demonstrated, later studies may perturb the
physical initial state and measure where the effect remains reproducible.
Generalization is therefore a separate property from discovery and local
causal efficacy.

## Interpretation rule

A recurrent motor pattern can be called a candidate translational effect when
its associated body-frame physical consequence is recurrent. It should not be
called a locomotor skill until replay from comparable initial states
demonstrates a reproducible causal translational consequence that can be reused
or composed.
