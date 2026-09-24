# Innate Reactivity P0

Status: implementation branch.

## Purpose

Give Symbiont constitutional defensive urgency without encoding anatomy,
environment semantics, task rewards, or fixed motor responses.

The body remains a physical substrate. Symbiont owns regulation and action
selection. Reembodiment therefore preserves the innate mechanism while motor
realisation is relearned from the current body.

## Invariants

1. Innate reactivity may interrupt or prioritize, but never emits actuator
   commands.
2. A fast motor response must be an already discovered cognitive motor
   primitive.
3. Reactive memory learns only from real execution followed by physiological
   relief.
4. One observation is insufficient for fast-path admission.
5. Anatomy, body kind, Physics3D ground truth, resources, hazards and evaluator
   labels are forbidden dependencies.
6. If no learned response exists, acute pressure produces no magic action.
7. Prospective agency remains the path for longer-horizon consequence choice.
8. Pending one-tick credit is ephemeral across restart; established
   associations are checkpointed.

## Runtime path

    opaque percepts + homeostatic deviation
                    |
                    v
             InnateReactivity
                    |
              ReactiveState
                    |
           ActionArbitrator
             /           \
    no evidence        learned evidence
         |                  |
         v                  v
 ordinary agency      primitive identity
                            |
                            v
                  SensorimotorLearner
                            |
                            v
                       MotorIntent

## P0 signals

InnateReactivity exposes bounded, semantic-free intensities:

- interrupt
- withdrawal
- stabilization
- conservation
- attention

The reactive signature is deliberately coarse and contains only binned
pressure/surprise/criticality. It contains no receptor meaning or anatomy.

## Acquired fast response

Every executed learned primitive can create a one-tick causal trace when
withdrawal pressure is present.

At the next tick:

    relief = deviation_before - deviation_after

ReactiveMemory maintains bounded sufficient statistics for:

    reactive signature x opaque primitive id -> immediate relief

A primitive becomes eligible for the fast route only after repeated positive,
low-variance evidence. Negative or unstable experience prevents admission.

## Arbitration order

1. Continue an already active primitive atomically.
2. If no primitive is active and acute withdrawal is present, attempt a
   reliable reactive association.
3. Otherwise continue the existing prospective/cognitive/babbling path.

The fast route never bypasses SensorimotorLearner.

## Persistence

Checkpointed:

- InnateReactivity temporal baseline.
- ReactiveMemory sufficient statistics.

Not checkpointed:

- pending one-tick reactive causal credit.

This avoids assigning post-restart physiology to an action whose causal
continuity was broken by restart.

## P0 falsification

The implementation fails if any of the following is observed:

- a reactive action occurs without a previously learned primitive;
- one successful episode is enough to install a fast response;
- shuffled/negative outcomes still produce fast selection;
- actuator IDs or anatomical labels are hard-coded into regulation;
- reactivity imports lab/world/evaluator code;
- physiological relief is replaced by decay of the reactive filter itself.

A later matched-control study should compare full reactivity against no
reactivity, shuffled associations, prospective-only and babbling-only
conditions using latency-to-relief, peak deviation, cumulative damage and
false reactive activations.

## Validation

The implementation branch is validated by the repository CI and remains a draft until its constitutional, runtime, and regression checks are green.
