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
