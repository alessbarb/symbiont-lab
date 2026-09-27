# Agency, action and motor learning

An actuator command is the end of a process, not the beginning. The current architecture deliberately separates discovering controllable effects, representing possible action, admitting an intention, reconciling commitments, controlling a competence and delivering a command to the body.

## Closing the previous action comes first

A crucial ordering rule appears directly in `OrganismRuntime.tick()`: after perception, the runtime calls `ActionDomain.observe_consequences()` before cognition for the current tick. This closes the previous `ActionAttempt`, learns from the body's real consequence, settles the active commitment and reconciles the active intent. New cognition therefore sees the observed outcome rather than having to wait another tick.

When a sensorimotor transition contains a competence and an observed effect, the real outcome is also passed to generative cognition through `note_factual_outcome()`. Imagined outcomes are reconciled against bodily consequence, not against another imagined state.

## From cognition to action

After cognition and memory observation, `ActionDomain.act()` performs the next executive sequence. The current design describes the broad stages as affordance resolution, executive deliberation, arbitration, control, execution and creation of the next action attempt.

The action stack includes:

- actuator candidates and evidence;
- `AgencyAcquisition` for discovering controllability;
- affordances and prospective evaluation;
- `ActionIntent` and `ActionCommitment`;
- `MotorCompetence` and competence effect models;
- composition and controller logic;
- `ActuatorSystem` for validated delivery to the surface.

## Motor competence

A motor competence is acquired organisation, not a raw actuator macro. Competence development accumulates sensorimotor transitions and evaluates recurrence, controllability, directionality and variance before promoting candidates through maturity states. The exact gates are experimentally important because they determine whether repeated movement becomes a reusable controller.

## Closed-loop control

The shift from primitive open-loop activation toward competence-based control is scientifically significant. A closed-loop controller can adjust actuation based on observed state rather than replaying a fixed command sequence. This is a prerequisite for robust behaviour in bodies where dynamics, contact and posture change continuously.

## Exploration

Exploration is not merely random motor noise. The architecture contains dedicated exploration and agency-acquisition mechanisms that can favour uncertain or learnable regions of the action space. Whether this produces useful embodied skill is an empirical question and must be evaluated through runs, not inferred from the existence of the mechanism.

### Principal sources

- `docs/design/core/agency-acquisition-and-executive-action-v1.md`
- `docs/design/core/executive-outcome-learning-v1.md`
- `docs/design/core/factorized-effect-representation-v1.md`
- `docs/design/sensorimotor/sensorimotor-development-v1.md`
- `src/symbiont/core/domains/action.py`
- `src/symbiont/agency/*`
- `src/symbiont/actuation/*`
