# Visual Acquisition v1 — development

Preregistration: `docs/design/vision/visual-acquisition-v1.md`.

## Purpose

Development stage: runner engineering and horizon feasibility only (seeds 101, 127, 149). No predictive performance is computed.

## Belongs here

- `development/`: runner engineering and horizon feasibility on seeds 101, 127, 149. Only feasibility is computed; no predictive performance.
- `held-out/`: created only when the preregistration is frozen (H, late window, baselines, criteria, nursery, seeds). It runs seeds 613, 617, 619 once, after explicit owner approval.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the reading goes to the preregistration), and pytest files (contracts live in `tests/experiments/protocols/`).

## Criterion for creating a file

Only a preregistered protocol element, committed before its runs.

## Execution

`symbiont-lab experiment run experiments/learning/visual-acquisition-v1/<stage>/experiment.toml`. Run strictly sequentially, with nothing else running on the machine.

## Limits

Measures predictive structure over opaque visual receptors only. It makes no object, persistence or self/external claim; those belong to D2–D4. The visual-target mapping is evaluator-side and never enters cognition.
