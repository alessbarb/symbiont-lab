# Prospective Agency v1 — matched Physics3D gate

This is the embodied causal stage of L8.

A newborn canonical Physics3D subject develops without evaluator intervention.
The study services organism-authored Private SLM training requests exactly as
the normal Physics3D runtime does. It waits until the organism itself produces
a `prospective_selected` event. Only then are the organism checkpoint and
physical checkpoint captured.

Five continuations start from that exact matched state:

- **full** — intact L8;
- **no_counterfactual** — prospective model-based selection disabled;
- **shuffled_model** — opaque primitive identities are rotated only at the
  evaluator-side model-query boundary;
- **shuffled_value** — opaque outcome-value identities are rotated in the
  experimental twin;
- **babbling_only** — prospective selection and cognitive motor output are
  removed from the matched twin, leaving sensorimotor exploration/body physics.

The acquired outcome-value ledger is frozen during the short causal horizon so
the study measures the causal effect of the state present at the split rather
than rapid relearning of the ablation.

Primary outcome:

```text
end_homeostatic_deviation - start_homeostatic_deviation
```

Lower is better, but the study reports effect sizes rather than manufacturing a
per-seed pass direction after observing data.

Secondary evaluator-only outcomes include reserve change, survival, displacement,
resource progress and energy absorption. These never enter the organism.

Example:

```python
from symbiont_lab.studies.learning.prospective_agency_embodied import (
    run_prospective_embodied_study,
)

result = run_prospective_embodied_study(
    seeds=(101, 127, 149),
    warmup_ticks=5000,
    horizon_ticks=256,
    physics_substeps_per_tick=10,
)
print(result.as_dict())
```

The canonical protocol uses 10 physics substeps per cognitive tick, matching\nPhysics3D's normal 240 Hz physics / 24 Hz cognition cadence. Reducing this ratio\nchanges the motor-to-body causal dynamics and is not a valid L8 comparison.\n\nThis study is intentionally not part of the fast default test suite because it\nuses PyBullet and real Private SLM training.


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
