# L7.3 — Adaptive replay matched control

This is the first causal study of the L7 replay mechanism.

For every seed, one organism generates a deterministic opaque causal history.
The organism then authors its normal L7.2 training plan. Treatment and control
receive exactly the same:

- causal transitions;
- training corpus and temporal holdout;
- tokenizer;
- GRU-v1 architecture;
- objective;
- parameter ceiling;
- model seed.

The only intervention is replay compute:

- **adaptive arm:** organism-authored L7.2 epochs/steps;
- **control arm:** same request clamped to 2 epochs / 12 steps.

The evaluator reads held-out outcome log loss and accuracy only after both arms
finish. These measurements never feed back into either organism or training
request.

Run:

```bash
symbiont-lab experiment run experiments/learning/adaptive-replay-matched-control/experiment.toml
```

Interpretation:

A positive result supports only the claim that additional organism-requested
replay compute extracts more predictive utility from the same causal
experience under this protocol. It does not by itself establish improved
embodied behavior, locomotion, agency, consciousness, or general intelligence.
