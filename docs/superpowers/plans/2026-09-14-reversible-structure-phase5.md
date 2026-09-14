# Reversible Structural Plasticity — Phase 5

## Goal

Turn the worker-3 failure into permanent longitudinal regression evidence. The target is not merely that topology can be born, but that a germinal organism can grow, prune, reclaim, recover, restart and continue learning without entering an irreversible structural attractor.

## Validation matrix

### 1. Long-lived germinal cognition

Run a deterministic germinal graph for 2,000 ticks with persistent opaque coactivity, checkpoint/restore at the midpoint, and assert throughout that:

- total nodes and edges remain inside soft budgets;
- cognitive SENSE count remains inside `sense_node_budget`;
- topology never settles in `DEGENERATE`;
- a real SENSE→READOUT path survives the checkpoint boundary;
- no orphan latent nodes remain at the end.

### 2. Sensory turnover

Use a small SENSE budget and short lease retention with concept formation disabled. Repeatedly replace the complete sensory working set and assert that stale disconnected SENSE nodes are reclaimed and later senses can still be admitted. Repeat across many generations to detect cumulative leaks.

### 3. Failed hypothesis lifecycle

Create a real germinal concept/readout bundle, make its established incident edges genuinely weak and unused, and verify the complete lifecycle:

`edge quarantine/prune → orphan grace → remove_node(CONCEPT/READOUT) → capacity reclaimed`.

### 4. Exact worker-3 fixture

Restore the observed pathological topology exactly at the structural level:

- topology revision 29;
- 58 SENSE;
- 5 CONCEPT;
- 1 READOUT;
- 0 edges;
- 64/64 soft node budget;
- no historical lineage/lease metadata, matching the legacy checkpoint.

Required behavior:

1. restore as `RECOVERING`, never fabricate missing edges or ancestry;
2. remove the six orphan latent nodes and excess disconnected senses incrementally under the kernel mutation cap;
3. return to a bounded `GERMINAL` state;
4. learn a new SENSE→CONCEPT→READOUT path only from fresh post-recovery input;
5. finish `CONNECTED` or `ADAPTIVE`, never `DEGENERATE`.

### 5. Owner-authored isolation

Run an owner-authored non-developmental graph for hundreds of ticks and assert that reversible germinal maintenance does not remove or rewrite owner structure.

## Acceptance criterion

The reversible structural-plasticity program is considered behaviorally complete only when a germinal Symbiont can repeatedly:

`birth → learn → consolidate → prune → reclaim → regrow → checkpoint → restore → recover`

while remaining within kernel and genome budgets and without manual topology repair.
