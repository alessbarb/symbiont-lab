# Causal Equivalence Suite v1

This suite supplies bounded evidence, not a universal classifier.

A sensitive change may be downgraded to ORDINARY only when every scenario required by
its semantic surface returns PASS. FAIL and every NOT_ASSESSABLE result remain
SCIENTIFIC.

## Reference snapshots

Snapshots must be captured from real organism states and are immutable/versioned.
Do not synthesize a snapshot merely to make a candidate change pass.

Capture a real state with:

    python scripts/agentctl.py snapshot capture       --source /path/to/state-dir       --destination experiments/equivalence/suite-v1/snapshots/S03-promotion-eligible       --body-kind anthropomorphic-v6-vision       --scenario promotion-eligible

The suite is deliberately capture-required until those real state artefacts exist.
This prevents false confidence from mutable live subjects.
