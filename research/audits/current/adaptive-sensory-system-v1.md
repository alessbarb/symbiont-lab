# Adaptive Sensory System v1 — implementation audit

**Status:** implementation complete and technically validated for pre-DAG stages; empirical closure pending  
**Scope:** post-freeze experimental extension

## Implemented

The runtime separates external source/sample state from organism-owned
perception. Adaptive cognition receives stable receptor identities. The system
includes bounded heterogeneous modalities, parameter adaptation,
duplication/divergence, pruning, endogenous multisource exploration, separate
perceptual attention, sensor lineage, checkpoint/replay, temporal cold-start
marking, clonal capacity inheritance without phenotype inheritance, BodySchema
integration and passive Observatory projection.

## Adversarial corrections made before empirical execution

1. mutation windows could exceed budget when adaptation and pruning coincided;
2. multisource receptors existed as API but could not arise endogenously;
3. malformed checkpoint types could be coerced;
4. custom modality constitutions restored with defaults;
5. persisted sensory plasticity could be disabled accidentally on CLI restart;
6. mutation history for later-pruned sensors was rejected;
7. receptor cognitive identity could drift with source aliases;
8. fingerprint schema was stale after constitutional payload changes;
9. healthy/novel receptors could receive utility without downstream gain;
10. predictive gain was credited to the target instead of the predictive source;
11. explicit habitat sources were excluded from adaptive perceptual attention;
12. temporal restart discontinuity was implicit rather than marked.

## Scientific gates

Eight `perception.*` protocols are registered and executable. No result is
recorded here because they have not been executed in this environment.

Structural mutation of arbitrary transduction DAGs and inherited modality
evolution remain closed until earlier gates justify expanding the search space.

## Technical validation

Local validation was executed on 2026-09-18 after the final regression fixes.

Directed regression set:

```text
59 passed in 3.61s
```

Full repository suite:

```text
1748 passed, 2 warnings in 224.11s
```

`git diff --check` completed cleanly.

The warnings are non-blocking and outside the adaptive sensory mechanism:
Python's `multiprocessing.popen_fork` warns about `fork()` in a
multi-threaded process, and PyTorch reports the existing nested-tensor
configuration warning in `TransformerEncoder`.

GitHub Actions remains intentionally excluded because of billing. The technical
implementation gate is therefore closed locally.

## Remaining empirical gate

Execute the eight experiments listed in
`experiments/perception/README.md`. Only those real outputs may advance
`research/STATUS.md` from technical validation to a scientific closure claim.
Negative, null or convergent outcomes remain valid results and must not cause
post-hoc threshold changes.
