# Generative Cognition model correction

This registered assay covers the mechanism-level gate for **GC-E7**.  It
starts with an opaque model prediction, supplies a changed evaluator-owned
factual outcome, reconciles the contradiction, applies the model adapter's
explicit factual-learning hook, and evaluates the next prediction.

The assay requires:

```text
wrong generated prediction
→ factual contradiction
→ corrected generated prediction
```

Generated states remain non-observed and neither the generated prediction nor
the learning hook writes factual evidence.  This is not evidence of broad
intelligence, external-world utility, or autonomous model learning; those
claims require matched environment studies and independent ablations.

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-model-correction
```
