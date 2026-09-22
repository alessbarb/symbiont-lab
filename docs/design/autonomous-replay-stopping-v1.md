# Autonomous Replay Stopping v1 — L7.6–L7.8

Status: implementation complete; scientific gates pending execution.

## Purpose

L7.1–L7.5 established that replay can improve predictive utility from fixed
experience, but also showed that evaluator-measured marginal returns are not
strictly monotonic. The organism therefore must not receive an evaluator-loss
threshold.

The closure of L7 uses only a signal derived from the organism's own observed
experience: private temporal validation loss.

## Epistemic partition

Every private corpus remains temporally split into:

- **train** — causal episodes available for replay updates;
- **validation** — the organism's own observed episodes reserved from weight
  updates; validation loss may be returned to the organism;
- **test** — evaluator-only evidence. Test loss never crosses the organism
  boundary.

No model-generated record may become a positive causal training target.

## L7.6 — internal signal validity

Protocol: `learning.internal-learning-progress`.

Across matched replay doses, compare interval improvements in private validation
loss with interval improvements in evaluator-only test loss.

Preregistered gate:

- positive Pearson gain correlation in at least 2/3 seeds;
- aggregate interval sign agreement >= 0.75.

This gate determines whether private validation progress is scientifically
credible as an internal compute-allocation signal.

## L7.7 — organism-authored stopping

`TrainingRequest` now optionally carries:

- `autonomous_stopping`;
- `requested_patience`;
- `requested_min_validation_gain`.

Canonical autonomous replay plans request:

- patience: 2 epochs;
- minimum material validation improvement: 0.005 nats;
- the existing L7.2 maximum epochs/steps remains a hard ceiling.

When autonomous stopping is disabled, historical request identity and trainer
behavior remain unchanged.

The trainer checks only private validation loss. The evaluator test split is
not referenced by the stopping path.

### Metabolic accounting

The organism pays:

1. request/base + structural model cost when it authors the request;
2. replay-step cost only after execution, using actual `steps_completed`.

Settlement is idempotent and its request ids are checkpointed. Early stopping
therefore saves both host compute and organism-side computational metabolism.

## L7.8 — final matched causal gate

Protocol: `learning.autonomous-replay-stopping`.

Each seed receives three arms with identical causal experience, corpus,
tokenizer, architecture, objective, model seed and parameter ceiling:

- minimum: 2 epochs / 12 steps, no auto-stop;
- maximum: 8 epochs / 48 steps, no auto-stop;
- autonomous: same maximum ceiling, organism-authored stopping enabled.

Preregistered success criterion:

- at least 2/3 seeds execute fewer steps than maximum;
- those seeds retain >= 90% of maximum's held-out loss gain over minimum;
- autonomous must not be worse than minimum on those passing seeds.

Evaluator test loss is used only after training for scientific interpretation.

## Historical reproducibility

L7.3–L7.5 explicitly disable the new stopping behavior so their original
budget-only protocols retain their intended causal contrast.

Requests with `autonomous_stopping=False` retain the historical request-id
payload. Autonomous policy fields are added to identity only when stopping is
enabled.

Artifacts generated with autonomous stopping persist the policy in their
manifest; old manifests load with backward-compatible defaults.

## Activation rule

This implementation is intentionally held on a feature branch until L7.6 and
L7.8 are executed.

- If L7.6 fails, private validation progress is not licensed as an autonomous
  stopping signal and L7.7 must be revised or removed.
- If L7.6 passes but L7.8 fails, the signal is informative but the candidate
  stopping policy is not efficient enough; change the policy only under a new
  preregistered protocol.
- If both pass, merge the branch and close L7.
