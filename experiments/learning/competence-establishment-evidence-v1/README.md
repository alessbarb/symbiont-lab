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

```text
python -m symbiont_lab.studies.learning.competence_establishment selection --output <work>/selection.json
python -m symbiont_lab.studies.learning.competence_establishment confirmation --selection selection.json --output <work>/results.json
```

## Limits

The result is bounded to the synthetic causal Body with four actuators, the
listed seeds and the 2000-tick horizon. The protocol is
`docs/design/experimentation/competence-establishment-evidence-v1.md`.

Nothing has been run yet.
