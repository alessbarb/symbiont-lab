# E6 (factorized effects) — Acquisition to deliberate reuse closure

Factorized Effect Representation v1 (`docs/design/core/factorized-effect-representation-v1.md`, §14.2).

## Purpose

Preregistered release gate for footprint-grounded agency: the E6 protocol
(`learning.agency-acquisition-reuse-closure`) run with
`factorized_effects = true` — competences grounded on causal footprints,
intents reconciled by accumulated change recall, causal probing on.

## Belongs here

Preregistered protocol configurations, manifests, and execution parameters for this study arm.

## Does not belong here

No unit tests, production code, or transient run artifacts.

## Criterion for creating a file

Add only files required for this reproducible protocol definition or its registered gates; mechanical test contracts belong in `tests/experiments/`.

## Hypothesis

One fresh organism, never reset and never given a competence id, actuator or
motor pattern by the Lab, first acquires agency and then deliberately reuses
a competence it discovered itself to produce the anticipated real effect —
with effects represented as causal footprints.

## Design

Same seeds (101, 127, 149), body (4-actuator `CausalBody`) and budget (3000
ticks) as E6. Only `[ablation].factorized_effects` differs.

## Success criteria

The E6 release gate unchanged (developmental order, a SATISFIED intent from a
self-acquired competence grounded in the organism's own exploration
evidence), plus: the satisfied competence traces through causal provenance
down to the pulse commitments that established its footprint. If the gate
fails, the result goes back to the owner before any further wiring.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-acquisition-reuse-closure-factorized/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Synthetic 4-actuator body; the Physics3D acceptance (§14.2) is the real-body
test.
