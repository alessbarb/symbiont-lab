# Metabolic Retention Price Calibration v1

## Purpose

Records the experiment definition and, once run, the results of the metabolic
retention price calibration.

## Belongs here

`experiment.toml`, `selection.json` (support rate and selection, written by the
selection stage), the confirmation result, and their launcher receipts.

## Does not belong here

No pytest-collectable tests, production code, or interpretation beyond the
preregistered decision rule.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a
result; mechanical contracts belong in `tests/experiments/`.

## Execution

Only through `agentctl run start`, after Competence Establishment Evidence v1:

```text
python -m symbiont_lab.studies.learning.metabolic_retention_calibration selection --output <work>/selection.json
python -m symbiont_lab.studies.learning.metabolic_retention_calibration confirmation --selection selection.json --output <work>/results.json
```

## Limits

The result is bounded to the synthetic causal Body with four actuators, the
support rule, the listed seeds and the 2000-tick horizon. The protocol is
`docs/design/experimentation/metabolic-retention-price-calibration-v1.md`.

Nothing has been run yet.
