# E5 — Somatic Correlation Trap

Preregistered falsification study for the inferred body boundary.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/somatic-correlation-trap/experiment.toml
```

The protocol compares:
- one genuinely self-caused input;
- one genuine somatic-correlated input;
- one matched external-correlated input;
- one external independent control.

Primary gates:
- true somatic detection >= 0.70;
- external correlated assimilation <= 0.10;
- deterministic replay.

A failed H1 gate is a valid negative result. Do not tune
`InferredBodySchema`, thresholds, seeds or signal generation before the
first result is frozen under `research/`.
