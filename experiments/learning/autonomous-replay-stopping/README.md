# L7.8 — Autonomous replay stopping final gate

This is the final causal gate for the L7 replay line.

Three matched arms receive identical causal experience, corpus, tokenizer,
architecture, objective, seed and parameter ceiling:

- **minimum:** 2 epochs / 12 steps, no autonomous stopping;
- **maximum:** 8 epochs / 48 steps, no autonomous stopping;
- **autonomous:** same 8 / 48 ceiling, but the organism's request enables
  stopping after two consecutive epochs that fail to improve private validation
  loss by at least 0.005 nats.

Only the autonomous arm may stop early. It never sees evaluator test loss.

Run:

```bash
symbiont-lab experiment run experiments/learning/autonomous-replay-stopping/experiment.toml
```

The preregistered gate requires at least two of three seeds to save compute while
retaining at least 90% of the maximum arm's held-out gain over the minimum arm.
