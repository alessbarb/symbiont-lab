# E5 result — Somatic Correlation Trap

Status: **negative result frozen; mechanism not repaired**

Protocol:
`research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md`

## Preregistered gates

```text
true somatic detection rate >= 0.70
external correlated assimilation rate <= 0.10
deterministic replay required
```

## Result

Across the preregistered 10 seeds:

```text
self-caused channel detected           10/10
genuine somatic-correlated detected    10/10
external correlated assimilated        10/10
external independent assimilated        0/10
```

Aggregate:

```text
true_somatic_rate = 1.00
external_assimilation_rate = 1.00
independent_assimilation_rate = 0.00

true-somatic gate = PASS
external-rejection gate = FAIL
H1 body-boundary discrimination = NOT SUPPORTED
```

The result is highly specific rather than a general tendency to classify
everything as body: the independent external control remains external, while
the matched external-correlated channel is promoted into
`somatic_correlated_channels` just like the genuine somatic channel.

## Interpretation

The current rule:

```text
low direct controllability
+
strong correlation with a self-caused channel
        ↓
somatic-correlated / internal
```

does not contain enough evidence to distinguish genuine bodily coupling from
environmental coupling.

Together with E1:

```text
E1: reliable dependence on my activation != bodily causation
E5: correlation with a self-caused signal != bodily membership
```

This falsifies the strong claim that the current `AgencyModel +
InferredBodySchema` stack is sufficient to infer a robust self/world body
boundary under adversarial controls.

## Research consequence

Do not tune thresholds.

The next study should be E4 (SHAM / permutation / break / transplant) to measure
whether the mechanism nevertheless performs **causal revision** correctly when
its existing embodiment changes. That distinguishes a weak but adaptive
contingency model from a static classifier.
