# Causal Equivalence Suite v1

This suite supplies bounded evidence, not a universal classifier.

A sensitive change may be downgraded to ORDINARY only when every scenario required by
its semantic surface returns PASS. FAIL and every NOT_ASSESSABLE result remain
SCIENTIFIC.

## Deterministic training contract

Training scenarios run synchronously on CPU with one Torch compute thread, one interop
thread and deterministic algorithms in strict mode. If that contract cannot be
established, the result is `NOT_ASSESSABLE_NONDETERMINISM`, not FAIL.

Coverage is event-based. A training scenario must observe the configured number of
completed model trainings, and the promotion scenario must observe a real ACTIVE-model
transition. Merely running enough ticks is not sufficient.

## Reference snapshots

Snapshots must be captured from real organism states and are immutable/versioned. Live
organism directories are never reference baselines.

Each archive records the organism id, captured tick, body/embodiment metadata, source
commit and SHA-256 digests for the organism bundle, body state and model tree.

Do not synthesize or refresh a snapshot merely to make a candidate change pass.

Capture a real state with:

```bash
python scripts/agentctl.py snapshot capture \
  --source /path/to/state-dir \
  --destination experiments/equivalence/suite-v1/snapshots/S03-promotion-eligible \
  --body-kind anthropomorphic-v6-vision \
  --scenario promotion-eligible
```

The suite remains `capture-required` until these real state artefacts exist. That is a
deliberate NOT_ASSESSABLE state, not permission to invent fixtures.
