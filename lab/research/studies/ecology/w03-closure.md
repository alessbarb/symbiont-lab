# W03 closure — within-region differentiation without mutation

Status: **closed by owner decision, 2026-10-02 — exploratory, observed once,
not replicated, mechanism unidentified**

Protocol and run: `experiments/world/genesis-v1/run_w03.py`

Original audit: `experiments/world/genesis-v1/audit-w03.md`

Stored result: `experiments/world/genesis-v1/w03_results.json` (run at commit
`3a536753`)

This record supersedes the "Status" section of the original audit. The original
audit and its result file are completed evidence and are not edited.

## What W03 found

One world seed (101), eight founders, 300 ticks, no mutation. Two founders in the
same region, under an identical `ResourceLaw`, came to rely on different
resources. Under the preregistered rule that is a rejection of H0.

The only mechanism tested, hazard density-coupling, was falsified by its own
control: the same disagreement appeared with the coupling zeroed. The remaining
candidate, a position-dependent occupancy percept, was never isolated.

## Final status

```text
EXPLORATORY · OBSERVED · NOT REPLICATED · mechanism unidentified
```

The follow-up controls named in the original audit — occupancy-percept ablation,
more seeds, a larger population, replication — are not scheduled and not owed.

W03 does not support any claim of ecological differentiation, niche formation or
social ontogeny, and must not be cited as one.

## The stored result is not reproducible on current code

At `main@56d2b53f` the unchanged script, with the same seed and placement,
produces no resource intake for any founder: every `dominant_resource` is `None`
and `reject_h0 = False` in both the treatment and the control arm.

| Arm | Stored (`3a536753`) | Current code (`56d2b53f`) |
| --- | --- | --- |
| treatment `reject_h0` | `True` | `False` |
| control `reject_h0` | `True` | `False` |
| south-region dominant resources | two distinct resources | none (no intake) |
| `mechanism_supported` | `False` | `False` |

The run uses `PopulationGenesisRuntime` with `experimental_clean=False`, the
pre-decontamination population path, which has drifted with later World and
organism changes. The cause of the drift was not investigated. The regression
test meant to lock the protocol
(`tests/unit/lab/world/test_w03_experiment.py`) asserted only determinism and
result types, so it did not detect that the result itself had changed.

`w03_results.json` therefore stands as the historical record of the run at
`3a536753` and nothing else. `run_w03.py` overwrites that file when executed as a
script; it must not be run to regenerate it.

## Consequences

- The lock test is retired.
- W03 no longer constrains the legacy population path. What still constructs
  that path is listed in
  [World Responsibility Map v1](../../../../docs/design/world/world-responsibility-map-v1.md).
- No World or organism change is required to keep W03 reproducible.

## Claims this closure does not make

- that the observed differentiation was an artefact;
- that it was real;
- that the legacy population path should be removed.
