# Embodied sensorimotor shadow

This is a lab-only, shadow-mode experiment. It uses the opaque 49-receptor /
28-effector Physics3D contract and a fixed 16-unit sparse recurrent reservoir
with an online linear readout to predict the next receptor vector. It does not
construct an `OrganismRuntime`, alter `symbiont`, or provide motor output to a
resident.

The causal condition receives the current opaque receptor vector and the
current opaque effector vector. Controls receive the same receptor history with
either shuffled or zeroed effector vectors. The readout is trained on the first
70% and frozen during the held-out portion. Persistence is the baseline.

## Decision gate

The hypothesis is supported only if causal action conditioning beats both
controls for every seed and has a positive mean margin over the best control.
This is a deliberately strict gate; a positive prediction gain alone is not
enough.

The first 3-seed run (seeds `101,127,149`, 320 ticks, 2 physics substeps) did
**not** pass the gate:

| seed | causal gain | shuffled gain | no-action gain | causal margin |
|---:|---:|---:|---:|---:|
| 101 | -0.008212 | -0.008283 | -0.008335 | +0.000070 |
| 127 | -0.013882 | -0.013832 | -0.013910 | -0.000050 |
| 149 | -0.011247 | -0.011307 | -0.011457 | +0.000060 |

The model therefore did not demonstrate a useful action-conditioned body model
under this protocol. This invalidates the **current experimental claim**, not
the broader possibility of a sensorimotor network. It must not be integrated
into Symbiont on this evidence.
