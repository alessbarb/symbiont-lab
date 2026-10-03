# P6 — private-model learnability under the training budget

Private Model Learnability v1 (`docs/design/core/private-model-learnability-v1.md`, §8).

## Purpose

Learning curves of from-scratch `gru-v1` private models over the training
budget (48 … 1 536 steps) on two frozen corpora, against the non-neural
baselines, plus the current regime as a reference arm.

## Belongs here

The preregistered `experiment.toml` and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (instrumentation tests live in
`lab/tests/integration/test_private_model_learnability.py`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

See `experiment.toml` and the spec §8. Training seeds are derived from each
corpus hash (`p6_seed`); `[design] seeds` is unused by this protocol.

## Execution

From the repository root (the corpora are local, abstract checkpoint state
outside version control):

`symbiont-lab experiment run experiments/learning/private-model-learnability/experiment.toml`

## Limits

One organism lineage, two corpora, three seeds each; architecture, parameter
ceiling, corpus construction, baselines and promotion gate are frozen. No
result changes the production training budget automatically.
