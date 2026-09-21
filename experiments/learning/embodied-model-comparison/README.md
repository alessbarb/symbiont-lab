# Embodied model comparison

The intervention study established that the opaque body surface contains causal
action signal. This protocol tests whether the failed recurrent challenger is
better than a transparent linear NLMS predictor on the same traces.

Configuration: seeds `101,127,149`, 320 ticks, 2 physics substeps, 32 recurrent
units. Both models receive the same 49 opaque receptors and 28 opaque
effectors, train on the first 70%, and are evaluated against persistence on the
held-out segment.

The gate is not whether either model beats persistence. It asks whether the
recurrent substrate provides a reproducible advantage over the simpler linear
control in the causal condition.

Observed results:

| seed | recurrent causal gain | linear causal gain | recurrent advantage |
|---:|---:|---:|---:|
| 101 | -0.008639 | -0.009879 | +0.001240 |
| 127 | -0.014069 | -0.017779 | +0.003710 |
| 149 | -0.012403 | -0.015340 | +0.002937 |

The recurrent model beats the linear control on all three seeds, but it does
not beat persistence and its advantage is not action-specific: the recurrent
advantage is also present for shuffled and zero-action controls. Therefore the
result is a model-class result, not evidence that the network learned the
body's action-conditioned dynamics.
