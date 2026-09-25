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
