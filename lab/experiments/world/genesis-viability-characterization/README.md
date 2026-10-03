# Genesis Viability Characterization

This campaign characterizes whether Genesis admits viable trajectories without
requiring any particular survival outcome.

It measures, per founder:

- lifespan and terminal physical cause;
- material absorbed;
- motor and basal energy cost;
- basal, deferred and hazard structural damage;
- movement count;
- hazard exposure count;
- final position.

Population-level outputs include extinction tick, survivor fraction and final
dispersion.

Run:

```bash
symbiont-lab experiment run experiments/world/genesis-viability-characterization/experiment.toml
```

The campaign must not be used as a target function for tuning World parameters.


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
