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

## Follow-up: composed shadow screening

The stronger physical intervention result was also checked against the
existing `ComposedShadowPrediction` idea. For each seed, the apparatus split
the same opaque trace into an 80-tick training prefix and a held-out suffix.
It selected, **apparatus-side only**, the best three-channel chain

```text
opaque effector[t-2] -> opaque receptor[t-1] -> opaque receptor[t]
```

by training gain, then froze its two slopes before evaluating the suffix. The
held-out comparison was against receptor persistence and an independently
shuffled effector trace. Selection was deliberately not treated as organism
knowledge; no selected channel or evaluator metric entered `symbiont`.

Run: seeds `101,127,149`, 128 ticks, 2 physics substeps, 49 receptors and 28
effectors. Values are mean Huber-loss reduction over persistence on the held
out suffix:

| seed | selected chain (opaque slots) | causal gain | shuffled-action gain |
|---:|:---|---:|---:|
| 101 | effector 8 -> receptor 27 -> receptor 45 | +0.007858 | +0.007543 |
| 127 | effector 5 -> receptor 15 -> receptor 46 | +0.004580 | +0.004485 |
| 149 | effector 10 -> receptor 11 -> receptor 46 | +0.004121 | +0.005280 |

This follow-up also fails the causal gate: the candidate was selected using
the training prefix, but the held-out advantage over shuffled actions is not
reproducible and reverses sign for seed 149. The apparent positive gains are
therefore compatible with persistence, selection bias, or broad physical
correlation; they do not establish that the composed predictor discovered a
causal body relation.

## Decision

The current embodied shadow line is **invalidated as an integration candidate**
for the following reasons:

1. the recurrent reservoir does not beat both controls for every seed;
2. the composed predictor does not retain a causal advantage on held-out
   traces;
3. the separate intervention experiment still shows that the apparatus has
   real action-dependent signal, so the failure is attributable to the current
   learning protocol/model evidence, not to an empty body interface.

No neural substrate should be connected to Symbiont motor output. A future
experiment should first remove candidate-selection leakage, add repeated
intervention/replay evaluation, and pre-register a fixed low-dimensional
candidate set before increasing model complexity.
