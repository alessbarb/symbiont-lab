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

The first three preregistered protocols were executed locally on 2026-09-18
over seeds 101, 127 and 149.

- **Identity equivalence: positive.** All three runs report exact
  `max_absolute_error = 0.0`, one identity receptor and
  `all_equivalent = true`.
- **Adaptive delta characterization: positive in protocol scope.** The alpha
  receptor reduces MAE from `3.6352/2.9957/1.7587` to
  `0.0171/0.0151/0.0183`, with positive improvement in every seed.
- **Temporal-scale specialisation: positive in protocol scope.** Alpha is
  consistently better on the fast evaluator target and beta on the slow target;
  fast gains are `0.4637/0.4790/0.4816`, slow gains
  `0.4370/0.4557/0.4587`.

These results establish functional heterogeneity inside the declared sensory
search space, not open-ended discovery. The modality substrates already expose
different operator families and the initial developmental exploration is
deterministic. Therefore autonomous selection, causal contribution,
multisource advantage and phenotype divergence remain open gates.

The remaining five protocols were executed locally on 2026-09-18.

- **Modality characterisation:** all declared niches are observed, but the
  distributed gamma result is construction-matched: the gamma MIX primitive
  computes the evaluator target exactly, so its zero MAE is not evidence of
  learned selection.
- **Duplication/divergence:** positive for bounded structural divergence and
  lineage accounting in all seeds.
- **Ablation:** positive causal support in protocol scope; targeted removal
  causes large degradation in all seeds.
- **Multisource specialisation:** negative against the frozen multisource
  control. Adaptive MAE and frozen MAE are both exactly 0.0 in all three seeds;
  the adaptive system only beats single-source.
- **Same-world phenotype study:** complete convergence. Three organisms produce
  one unique phenotype in every seed. This is a valid characterization result,
  not a protocol failure.

The v1 substrate therefore demonstrates bounded heterogeneous transduction,
causal usefulness and reproducible structural specialization, but does not yet
demonstrate autonomous selection of a superior sensory transform over a
structurally matched control. Scientific closure remains open.

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
