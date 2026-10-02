# Re-embodiment Functional Transfer v1

## Purpose

Records the frozen protocol definition and, once run, the identifiable results of
the functional transfer experiment.

## Belongs here

`experiment.toml`, `horizons.json` (written by the development stage), and the
results of governed runs.

## Does not belong here

No pytest-collectable tests, production code, or scientific interpretation beyond
the preregistered decision rule.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a
result; mechanical contracts belong in `tests/experiments/`.

## Execution

Only through `agentctl run start`:

```text
python -m symbiont_lab.studies.embodiment.reembodiment_functional_transfer development --output <work>/horizons.json
python -m symbiont_lab.studies.embodiment.reembodiment_functional_transfer confirmation --horizons horizons.json --output <work>/results.json
```

## Limits

The result is bounded to the synthetic causal Body, four actuators, the listed
seeds and the horizons fixed by rule. The protocol is
`docs/design/experimentation/reembodiment-functional-transfer-v1.md`.

## Development stage (2026-10-02)

Governed run `rft-v1-development-20261002-r2` at commit `40c6801d`, scope
`development`, protocol-generated input. Its output is `horizons.json`; its
launcher receipt, without host-specific paths, is `development-receipt.json`.

| Quantity | Value | Rule |
| --- | --- | --- |
| Median naive ticks to a first valid binding, each of the four mappings | 91 | Body-difficulty check |
| Spread between mappings | 0.0 | must be at most 0.15 |
| Development ticks `D` | 400 | smallest multiple of 100 at which every development organism holds a valid binding in every source Body |
| Measurement ticks `H` | 400 | equal to `D` |
| Runnable | yes | |

The four mappings are equally hard on every development seed: before an organism
holds any binding, nothing it does depends on which receptor an actuator drives.

An earlier run, `rft-v1-development-20261002`, computed the same values but wrote
its output outside the run's work directory because of a mistaken output
argument; it left no artifact and is superseded by `-r2`. The protocol and the
code were identical in both.

No confirmation seed has been run.

