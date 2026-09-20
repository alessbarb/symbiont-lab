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
