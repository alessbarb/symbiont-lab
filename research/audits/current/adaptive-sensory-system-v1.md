# Adaptive Sensory System v1 — implementation audit

**Status:** implementation complete for pre-DAG stages; empirical closure pending  
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

## Validation limitation and local gate

GitHub Actions is intentionally excluded. This agent environment cannot clone
GitHub into its execution container because outbound DNS is unavailable, so it
cannot honestly claim a local pytest result.

Run locally:

```bash
pytest -q tests/unit/sensory
pytest -q tests/unit/lab/test_sensory_specialisation.py tests/unit/lab/test_sensory_protocol_registry.py
pytest -q tests/unit/host/test_checkpoint.py tests/unit/core/test_resident_continuity.py
pytest -q observatory/tests
pytest -q
git diff --check
```

Then execute the eight experiments listed in
`experiments/perception/README.md`. Only real outputs may advance
`research/STATUS.md` to a scientific closure claim.
