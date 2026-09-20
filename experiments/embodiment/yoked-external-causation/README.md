# E1 — Yoked External Causation

Preregistered falsification study for the operational self/world boundary.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/yoked-external-causation/experiment.toml
```

The protocol compares one genuine intervention-dependent channel with three
external controls: yoked, anti-causal and independent. The primary gates were
frozen before execution:

- mean agency false-positive rate <= 0.10;
- mean true-positive rate >= 0.70;
- deterministic replay.

A failed H1 gate is a valid scientific result. Do not tune `AgencyModel`,
thresholds, seeds or intervention schedules before the first result is frozen
under `research/`.

Normative preregistration:

`research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md`
