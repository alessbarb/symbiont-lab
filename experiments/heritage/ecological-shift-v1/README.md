# Ecological heritage shift v1

This experiment asks when inherited species memory helps, becomes neutral, or becomes harmful after the target ecology changes.

The source generation learns at a fixed threat prevalence. Its distilled abstract heritage is then transferred into target worlds with lower, equal, and higher threat prevalence. For every target condition, inherited and naive populations receive the exact same synthetic world; only the presence of inherited priors differs.

Internal regime drift is disabled deliberately. The only intended ecological intervention is the source-to-target threat-rate change.

Primary readouts are global attention/classification deltas, false-positive and calibration-related deltas, plus separate warmup and post-warmup effects. Undefined rates remain `N/A` rather than being coerced to zero.

Run with:

```bash
symbiont-lab experiment run experiments/heritage/ecological-shift-v1/experiment.toml
```

The experiment is observer-side and simulation-only. It does not add propagation, persistence, stealth, OS modification, or autonomous remediation.
