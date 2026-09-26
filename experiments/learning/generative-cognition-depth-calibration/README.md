# Generative Cognition depth calibration

This registered assay covers the mechanism-level gate for **GC-E6**. It runs
the same opaque model at bounded rollout depths `1`, `2` and `4`, records the
model's declared uncertainty, and compares each final prediction with an
evaluator-owned factual target.

The gate checks that uncertainty and observed error increase in the declared
direction, that every comparison is paired with a prior prediction, and that
generated states remain non-observed. It is not a universal calibration curve
or evidence of external-world generalisation.

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-depth-calibration
```
