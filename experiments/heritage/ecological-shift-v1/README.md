# Ecological heritage shift v1

This experiment asks when inherited species memory helps, becomes neutral, or becomes harmful after the target ecology changes.

The source generation learns at a fixed threat prevalence. Its distilled abstract heritage is then transferred into target worlds with lower, equal, and higher threat prevalence. For every target condition, inherited and naive populations receive the exact same synthetic world; only the presence of inherited priors differs.

Internal host-profile drift is disabled deliberately. The only intended ecological intervention is the source-to-target threat-rate change.

The simulator reserves steps 0–49 for threat-free host-model warmup, so that interval is not used to estimate early threat recall. Instead, the threat-eligible lifetime is split into an **early** window (`pre_drift`, with zero actual drift) and a **late** window (`post_drift`, still with zero actual drift). This allows the study to ask whether inherited priors help immediately after threats become possible and whether that effect persists after the target population has accumulated local evidence.

Primary readouts are global attention/classification deltas, false-positive and calibration-related deltas, plus separate early and late effects. Undefined rates remain `N/A` rather than being coerced to zero.

Run with:

```bash
symbiont-lab experiment run experiments/heritage/ecological-shift-v1/experiment.toml
```

The experiment is observer-side and simulation-only. It does not add propagation, persistence, stealth, OS modification, or autonomous remediation.
