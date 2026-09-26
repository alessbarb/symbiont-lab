# Generative Cognition replay utility

This registered assay covers the mechanism-level gate for **GC-E8**. It
compares an online-only control with the same opaque model after one factual
episode has been materialized as bounded `REPLAYED` cognition.

The gate requires replay to improve the matched prediction while preserving
the source episode identity, leaving the factual episode count unchanged, and
keeping factual and agenda contamination at zero. It is not evidence of
general external-world utility or of benefit from replay in every task.

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-replay-utility
```
