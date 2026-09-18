# Structured Communication Characterization v1 — report

## Question and preregistration

This study asks what codes emerge when the existing bounded opaque channel is
placed under different environmental, vocabulary, sequence-length, and cost
pressures. It does not design a language. The preregistration is
`experiments/learning/structured-communication-characterization/experiment.toml`;
seeds are `101, 127, 149` and the trace length is 64 ticks.

The literal design principle is:

> Give Symbionts capabilities and constraints, not linguistic answers.

## Results

The complete per-seed/per-condition artifact is
`experiments/learning/structured-communication-characterization/results.json`.
All 27 treatment rows replayed deterministically. The autonomous conditions
produced non-trivial silence and emission decisions and used multiple opaque
sequences. The no-signal control produced no messages; the random control was
not treated as autonomous evidence. The evaluator-side classification was
`no_functional_code` for the three no-signal rows and one random row, and
`functional_partially_structured_code` for the remaining rows under the
conservative current classifier. Novel message occurrence is recorded only as
descriptive trace data; this study does not assess useful heldout
generalization and therefore does not assign `productive_structured_code`.

The autonomous rows had prediction gains above their no-signal baseline in
this bounded protocol. The result is evidence of functional communication in
the characterization harness, not evidence of grammar, syntax, language, or
productive compositionality. The study did not tune seeds, thresholds, or
conditions after observing results.

## Interpretation

The correct current description is **functional emergent structured
communication**, limited to this characterization protocol and its generic
channel. The classifier is descriptive and should not be read as proof that
messages factorize environmental states. No productivity closure is declared.

## Controls and limitations

No-signal and random-signal controls were run; sequence-disabled and pressure
conditions were included. The study preserves opaque IDs and records
evaluator-only state association separately. It is not a fleet-level population
study and does not yet provide a population graph or information-theoretic
claim beyond the recorded trace metrics. Communication cost is accounted for,
but cost-sensitive adaptation is outside this report.

## Validation

Targeted characterization and Observatory tests passed before the full suite.
The exact final local suite and diff-check results are recorded in the delivery
log accompanying this commit; GitHub Actions was not used because of the
billing incident.
