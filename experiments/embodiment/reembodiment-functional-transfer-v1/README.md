# Re-embodiment Functional Transfer v1

## Purpose

Records the frozen protocol definition and, once run, the identifiable results of
the functional transfer experiment.

## Belongs here

`experiment.toml`, `horizons.json` (written by the development stage), the
results of governed runs, and superseded stages kept as history.

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

## Development stage under r8 (2026-10-03): runnable

Governed run `rft-v1-r8-development-20261003` at commit `593c2a02`, scope
`development`, protocol-generated input, nine development seeds, 29 minutes. Its
output is `horizons.json`; its launcher receipt, without host-specific paths, is
`development-receipt.json`.

| Quantity | Value | Rule |
| --- | --- | --- |
| Family chosen by rule | target `0123`, partial `0132`, unrelated `1032` and `1230` | §4.2.1 (r7) |
| Body-difficulty spread | 0.0 | at most 0.15 |
| Development ticks `D` | 1500 | smallest multiple of 100 up to `D_max = 2000` at which every development organism holds a valid binding in every source Body |
| Measurement ticks `H` | 1500 | equal to `D` |
| Runnable | **yes** | |

No confirmation seed has been run. The confirmation stage reads this file.

## Superseded: development stage under r7 (2026-10-03), not runnable

Governed run `rft-v1-r7-development-20261003` at commit `e9489915`, scope
`development`, protocol-generated input, nine development seeds. Its output and
launcher receipt are kept in `development-r7/`. Protocol r8 raised `D_max` to
2000.

| Quantity | Value | Rule |
| --- | --- | --- |
| Family chosen by rule | target `0123`, partial `0132`, unrelated `1032` and `1230` | §4.2.1 (r7) |
| Median naive ticks to a first valid binding, each member | 93 | |
| Body-difficulty spread | 0.0 | must be at most 0.15 |
| Development ticks `D` | **not reached** | smallest multiple of 100 up to `D_max = 1000` at which every development organism holds a valid binding in every source Body |
| Runnable | **no** | |

Every candidate mapping had a median of 93 or 114 ticks, so the family rule
found a family with no difficulty difference. The `D` rule failed: at no
multiple of 100 up to 1000 did all 36 development organisms (nine seeds, four
Bodies) hold a valid binding at the same time. By the frozen rule (§4.5, §11
step 1) the study is not runnable and that is the recorded result. No
confirmation seed is run.

## Superseded: development stage under r6 (2026-10-03), not runnable

Governed run `rft-v1-r6-development-20261003` at commit `cb2cda67`, scope
`development`, protocol-generated input. Its output and launcher receipt are
kept in `development-r6/`.

| Quantity | Value | Rule |
| --- | --- | --- |
| Median naive ticks to a first valid binding: target / partial / unrelated 1 / unrelated 2 | 87 / 73 / 73 / 93 | Body-difficulty check |
| Spread between mappings | 0.25 | must be at most 0.15 |
| Development ticks `D` | 800 | smallest multiple of 100 at which every development organism holds a valid binding in every source Body |
| Measurement ticks `H` | 800 | equal to `D` |
| Runnable | **no** | |

By the frozen rule (§4.2.1, §11 step 1) the Body family is outside the 15 %
difficulty spread, so **the study is not runnable and that is the recorded
result**. No confirmation seed is run. Protocol r7 rebuilt the family by rule
(§4.2.1) on nine development seeds.

Under r5 the four mappings were equally hard (91 ticks each) because, before an
organism held any binding, nothing it did depended on which receptor an actuator
drove. The canonical organism adapts its receptors from the first tick (sensory
plasticity), so the mapping now changes how quickly a newborn finds its first
binding.

## Superseded: development stage under r5 (2026-10-02)

The r5 apparatus built every subject with factorized effects enabled, which the
protocol never declared. Protocol r6 corrects the subject configuration, so this
stage is superseded; its outputs are kept in `development-r5/` as history and are
not used by any confirmation run.


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

