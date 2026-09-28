# P1 — Extract observability from the organism hot path

Status: implementation candidate  
Base: P0 performance gate on `main`

## Boundary introduced

`OrganismRuntime.tick(..., include_observability=...)` now distinguishes the
causal organism step from passive observer projections.

With observability disabled the tick still performs every causal operation:
perception, learning, cognition, action, BodySchema updates, physiology,
development, causal provenance and the bounded life journal.

It does not materialize:

- the full human-readable host narrative;
- the full sensory phenotype projection used by CLI/telemetry;
- the aggregate representation-maturity histogram.

Those projections remain available when `include_observability=True`.

## Semantic preservation

The previous sensory phenotype was also used as an input to BodySchema.  P1 does
not remove that causal information.  `SensorySystem.body_schema_view()`
provides only the fields BodySchema actually consumes: sensor id, maturity,
health, confidence and cost.  Numeric rounding remains identical to the old
phenotype projection before BodySchema discretization.

The life journal previously built a full narrative for every known capability
and then retained at most three attended summaries.  P1 uses
`narrate_attended()` to build exactly that bounded attended subset directly,
preserving known-capability ordering and journal content while avoiding the
unused narratives.

Representation maturity itself is unchanged.  Only the reporting histogram is
conditional; `CognitiveBridge.representation_maturity_counts()` derives the
same histogram on demand.

## Gate

The P0 matched-twin gate now runs the silent twin with
`include_observability=False` and the observed twin with
`include_observability=True`.

It requires identical:

- `state_hash()`;
- motor intents and actuations;
- causal provenance;
- competence candidates and availability;
- derived representation maturity.

A focused test also asserts that the silent result omits only passive
projections while the complete organism state remains equal.

## Measurement

`scripts/bench_observability_tax.py` now times only the difference between the
causal tick and the same tick with observer projections enabled. External
observer reads such as `state_hash()` are kept outside the timed region.

`scripts/bench_organism_tick.py` explicitly uses the causal/headless tick so
the canonical organism benchmark no longer charges observer projections.

## Compatibility

The public tick default remains `include_observability=True` for compatibility.
Headless experiments and benchmarks can opt into the causal-only path now. P4
will later separate simulation, observation sampling and UI render frequencies
at the runner level rather than relying on every caller to choose a mode.
