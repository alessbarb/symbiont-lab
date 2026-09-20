# E1 result — Yoked External Causation

Status: **negative result frozen; mechanism not repaired**

Protocol preregistration:
`research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md`

Study implementation:
`src/symbiont_lab/studies/embodiment/yoked_external_causation.py`

Preregistered seeds:

```text
101, 127, 149, 173, 211, 257, 307, 353, 401, 457
```

Tick budget: 600 per seed.

## Preregistered gates

```text
mean FPR_agency <= 0.10
mean TPR_agency >= 0.70
deterministic replay required
```

## Result

The current `AgencyModel` reliably recognizes the genuine activation-dependent
channel, but it also recognizes the perfectly yoked external channel as agentic
on every preregistered seed.

| seed | genuine confidence | yoked confidence | anti-causal confidence | independent confidence | FPR |
|---:|---:|---:|---:|---:|---:|
| 101 | 0.6096 | 0.6116 | 0.3157 | 0.2891 | 0.3333 |
| 127 | 0.6017 | 0.6065 | 0.2891 | 0.2891 | 0.3333 |
| 149 | 0.6031 | 0.6003 | 0.2946 | 0.2891 | 0.3333 |
| 173 | 0.6107 | 0.6023 | 0.2891 | 0.2891 | 0.3333 |
| 211 | 0.6122 | 0.6132 | 0.2891 | 0.2891 | 0.3333 |
| 257 | 0.6097 | 0.6078 | 0.2982 | 0.2891 | 0.3333 |
| 307 | 0.6115 | 0.6090 | 0.2891 | 0.2916 | 0.3333 |
| 353 | 0.6065 | 0.6096 | 0.2926 | 0.2925 | 0.3333 |
| 401 | 0.6065 | 0.6067 | 0.2891 | 0.2891 | 0.3333 |
| 457 | 0.5981 | 0.5930 | 0.2891 | 0.2891 | 0.3333 |

Aggregate:

```text
TPR_agency = 1.00
mean FPR_agency = 0.3333
FPR gate = FAIL
TPR gate = PASS
H1 strong causal-discrimination claim = NOT SUPPORTED
```

## Interpretation

This does **not** show that AgencyModel is useless. It distinguishes:
- genuine intervention dependence from independent noise;
- current intervention dependence from the anti-causal control.

It does show an identifiability limitation:

```text
reliably follows my activation
            !=
physically caused by my body
            !=
part of my body
```

A perfectly externally yoked process is observationally indistinguishable to
the present model from a genuine bodily consequence because the mechanism has
only activation/delta contrast and no richer causal intervention model.

Therefore E1 supports the preregistered H0 **under this assay**.

## Research consequence

Do not repair `AgencyModel` yet.

The next preregistered study is E5 (somatic-correlation trap), which asks whether
this false agency / correlated structure is further promoted into
`InferredBodySchema.internal_channels`.

Only after E5 is frozen should the mechanism be redesigned.
