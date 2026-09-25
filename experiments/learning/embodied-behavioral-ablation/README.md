# Matched-twin cognitive motor behavioral ablation

This study is the strong causal gate for learned cognitive motor structure.

A fresh Physics3D subject develops normally until it first shows an **actually
used** cognitive motor contribution: direct cognitive/mixed motor origin or a
learned primitive replay whose source is cognition. The mere existence of a
cognitively eligible primitive or `readout_primitive:*` node is not sufficient. At that exact completed tick the study captures both:

- the portable organism checkpoint;
- the aligned physical-body checkpoint.

Two twins are then reconstructed from those identical states.

All twins have cognitive learning frozen during the evaluation horizon. The
control twin keeps its learned graph. Three causal controls are derived from the
same checkpoint when structurally applicable:

- **removed**: delete graph edges feeding cognitive motor/primitive readouts;
- **shuffled**: rotate readout identities within the motor family and within the
  primitive family, never across families.

A further graph-tick delay is not manufactured here. Learned resident
motor/primitive associations already use the canonical maximum
`delay_ticks=1`; adding another tick would require noncanonical graph
semantics or an experiment-specific runtime hook and would confound this
matched-twin comparison.

Actuator constitution, sensorimotor learner, body, physiology, sensory state,
other cognitive structure and the physical world remain identical.

The study does **not** claim success when no cognitive motor output develops.
Such a seed is reported as `not causally testable`.

Effect sizes are descriptive for every applicable control:

- displacement delta difference;
- resource-progress delta difference;
- motor-origin counts.

A shuffle with fewer than two distinct targets is reported as structurally
inapplicable rather than treated as a negative result.

No effect direction is selected after observing results.


## Live Mind interpretation

The unified Mind view exposes two different readiness signals and they must not
be conflated:

- `motor-output edges > 0`: learned cognitive graph structure reaches a
  `readout_motor:*` or `readout_primitive:*` target. This is structural
  readiness only.
- `motor_origin=cognition|mixed` or
  `motor_origin_detail=primitive_cognition`: the learned cognitive path was
  actually used for embodied motor output. This is the causal-study trigger.

The study deliberately waits for the second condition. Merely seeing a
cognitive→motor edge in Mind is not evidence that cognition controls behavior.

Run the preregistered matched-twin study with:

```bash
symbiont-lab experiment run experiments/learning/embodied-behavioral-ablation/experiment.toml
```

A seed that never reaches actual cognitive motor use is reported as
`not causally testable`; it must not be reclassified as a negative causal
effect.


## Purpose

This README defines this location's scope within the experiment hierarchy.

## Belongs here

Protocols, configuration, documentation, and identifiable results from reproducible runs.

## Does not belong here

No pytest-collectable tests, production code, or final scientific interpretation.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a result; mechanical contracts belong in `tests/experiments/`.

## Execution

Use the explicit command documented by the protocol or CLI; do not execute this folder through pytest.

## Limits

The contents are evidence bounded by the protocol and do not demonstrate generalization by themselves.
