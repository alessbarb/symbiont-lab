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

The support rule runs first, then the selection stage as eight governed runs of
about an hour each (36 of the 288 runs each, a fixed interleaved slice), then a
merge run that checks every part ran under the same support rate and every
(arm, seed) pair is present exactly once.

```text
python -m symbiont_lab.studies.learning.metabolic_retention_calibration support --output <work>/support.json
python -m symbiont_lab.studies.learning.metabolic_retention_calibration selection-part --support support.json --part <0..7> --output <work>/selection-part-<n>.json
python -m symbiont_lab.studies.learning.metabolic_retention_calibration select --support support.json --parts selection-part-0.json ... selection-part-7.json --output <work>/selection.json
python -m symbiont_lab.studies.learning.metabolic_retention_calibration confirmation --selection selection.json --output <work>/results.json
```

## Limits

The result is bounded to the synthetic causal Body with four actuators, the
support rule, the listed seeds and the 2000-tick horizon. The protocol is
`docs/design/experimentation/metabolic-retention-price-calibration-v1.md`.

Nothing has been run yet.
