# Generative Cognition multi-step predictive utility

This registered assay covers the first mechanism-level gate for **GC-E1**. It
compares three conditions on the same opaque sequence and initial state:

```text
persistence
one-step rollout
multi-step rollout
```

The evaluator keeps the target token hidden from the model and scores the final
prediction at horizons `1`, `2` and `4`. The generative model advances one
opaque state at a time; generated states remain non-observed and no factual
ledger is used.

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-predictive-utility
```

This gate demonstrates bounded rollout utility on a synthetic sequence. It
does not establish external-world calibration, embodied planning, transfer or
general intelligence. Those require matched environments and independent
ablations.
