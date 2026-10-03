# Competence Establishment Evidence v1

## Purpose

Records the experiment definition and, once run, the results of the competence
establishment gate study.

## Belongs here

`experiment.toml`, `selection.json` (written by the selection stage), the
confirmation result, and their launcher receipts.

## Does not belong here

No pytest-collectable tests, production code, or interpretation beyond the
preregistered decision rule.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a
result; mechanical contracts belong in `tests/experiments/`.

## Execution

Only through `agentctl run start`:

The selection stage runs as six governed runs of about an hour each (36 of
the 216 runs each, a fixed interleaved slice), then one cheap merge run that
checks every (arm, seed) pair is present exactly once and applies the selection
rule. Each part rewrites its output after every run, so a stopped part keeps
what it finished.

```text
python -m symbiont_lab.studies.learning.competence_establishment selection-part --workers 4 --part <0..5> --output <work>/selection-part-<n>.json
python -m symbiont_lab.studies.learning.competence_establishment select --parts selection-part-0.json ... selection-part-5.json --output <work>/selection.json
python -m symbiont_lab.studies.learning.competence_establishment confirmation --selection selection.json --output <work>/results.json
```

A first attempt as one run (`cee-v1-selection-20261003`) was stopped by the
operator after two hours: a measured 106-111 s per run put the whole stage at
about 6.5 hours, beyond the 360-minute wall limit, and that version wrote its
output only at the end. It produced no result.

With `--workers 4` (the policy's `max_cpu_threads`), a part runs its pairs in
four processes; runs are independent and deterministic, so the result is
identical to a serial part, and the launcher is started with `--cpu 4`. All parts
then fit in one governed run.

## Limits

The result is bounded to the synthetic causal Body with four actuators, the
listed seeds and the 2000-tick horizon. The protocol is
`docs/design/experimentation/competence-establishment-evidence-v1.md`.

## Selection stage (2026-10-03): no change

Governed run `cee-v1-selection-parallel-20261003` at commit `7d669432`: the six
parts with four workers each, 73 minutes. The parts are in `selection-parts/`
and the receipt, without host-specific paths, is `selection-receipt.json`. The
merge (`select`) is a pure, deterministic function of the six part files and was
applied to them outside the launcher; its output is `selection.json`.

**The selection rule picked the current gate `(2, 0.60)`.** By the
preregistration this is the result **no change**, and the confirmation stage is
not run.

| Gate `(S, C)` | Median `T_stable` | Median holding fraction | Median false establishment |
| --- | --- | --- | --- |
| (2, 0.60), current | 392 | 0.935 | 0.473 |
| (3, 0.60) | 814 | 0.874 | 0.360 |
| (2, 0.70) | 849.5 | 0.751 | 0.407 |
| (4, 0.60) | 899.5 | 0.873 | 0.408 |
| (5, 0.60) | 1224 | 0.936 | 0.310 |
| 16 of the 27 gates | 2000 (no stable binding within the horizon) | | |

Every stricter gate delays the first stable binding. Stricter gates do reduce
false establishment, but they do not make the binding stable sooner, which is
the preregistered measure. The full per-arm table is in `selection.json`.

A first attempt as one serial run (`cee-v1-selection-20261003`) and a serial
part 0 (`cee-v1-selection-part0-20261003`) were stopped by the operator before
completion and produced no result.
