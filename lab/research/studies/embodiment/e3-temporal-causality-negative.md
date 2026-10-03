# E3 result — Temporal Causality Challenge

Status: **negative result frozen; mechanism not repaired**

## Preregistered gates

```text
immediate genuine detection       >= 0.70
delay-1 genuine detection         >= 0.70
delay-3 genuine detection         >= 0.70
variable-delay genuine detection  >= 0.70
immediate external FPR            <= 0.10
```

## Result

Across all 10 preregistered seeds:

```text
immediate genuine detected        10/10
delay-1 genuine detected           0/10
delay-3 genuine detected           0/10
variable-delay genuine detected    0/10
immediate external detected       10/10
```

Aggregate:

```text
delay0_detection_rate = 1.00
delay1_detection_rate = 0.00
delay3_detection_rate = 0.00
variable_delay_detection_rate = 0.00
immediate_external_false_positive_rate = 1.00
H1 temporal-causal robustness = NOT SUPPORTED
```

## Interpretation

The current mechanism is highly specific to contemporaneous activation/delta
contrast. It does not recover genuine causal effects when the physical
consequence is delayed even by one evaluator step under this assay.

At the same time, an immediate external process yoked to current activation is
classified as agentic.

Combined with E1 and E5:

```text
E1: activation dependence alone cannot identify bodily cause.
E5: correlation with self-caused signals cannot identify bodily membership.
E3: current temporal matching cannot recover delayed bodily cause.
```

The present stack therefore demonstrates adaptive sensorimotor contingency
tracking, but the stronger claim of robust causal self/world inference is
falsified by the preregistered adversarial controls.

Do not tune thresholds. Preserve this result before redesigning causal memory.
