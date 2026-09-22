# L7.9 — Structured causal experience

This gate compares two encodings of the same synthetic motor history.

Legacy:
- whole motor vector becomes one high-cardinality opaque action token;
- no reusable per-channel action structure.

Structured:
- one stable `action.motor.composite` marker;
- opaque per-channel requested/delivered classes remain in context;
- training and private validation optimize only causal outcome targets.

Both arms use the same seeds, causal dynamics, GRU family, 1M parameter ceiling,
48 replay-step ceiling and held-out promotion evaluation.

Run:

```bash
symbiont-lab experiment run experiments/learning/structured-causal-experience/experiment.toml
```
