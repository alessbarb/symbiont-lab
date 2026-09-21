# Continuous temporal causal controls

This protocol tests the sparse ESN + NLMS challenger against causal controls.

A continuous state evolves according to previous state, an opaque signed action
and bounded noise. Three conditions share the same target trajectory:

- causal action identity;
- shuffled action identity;
- no action input.

Training occurs only on the first 70% of the trajectory. During held-out
evaluation the reservoir continues to update its recurrent state, but the
readout is frozen.

The test asks whether action-conditioned temporal structure matters. It does
not assign ESN a motor role or promote it into resident cognition.
