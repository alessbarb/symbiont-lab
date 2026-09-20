# E4 — Causal Revision Sequence

Within-subject sequence:

```text
stable Body A
→ SHAM
→ output permutation
→ restore
→ silent effector failure
→ repair
→ transplant Body B
→ return Body A
```

The Symbiont receives no phase marker, body ID or perturbation label.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/causal-revision-sequence/experiment.toml
```

This study measures whether causal revision is selective to real physical
changes. It does not claim a correct self/world boundary; E1 and E5 already
show that stronger claim fails under matched external correlation.
