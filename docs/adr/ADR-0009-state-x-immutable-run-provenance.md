# ADR-0009: State-X and Immutable Run Provenance (ADR-EW-002)

## Status

Accepted

## Context

The specification requires `R = execute(X, Environment, Config, Seed)`. The run manifest referenced the organism slot `organisms/<ref>/organism.symbiont`, but that file is overwritten in place, so after a run the starting state X no longer existed and a result could not be reproduced from its recorded initial condition.

## Decision

1. **X is the portable organism bundle.** The `.symbiont` bundle is self-contained: `runtime.json` plus the private model artifacts it references. X is identified by the bundle manifest's `checkpoint_id` and `checkpoint_hash` (SHA-256 of the canonical runtime JSON), and the Lab additionally records the SHA-256 of the bundle bytes.
2. **Content-addressed retention.** At launch the Lab copies the starting bundle to `organisms/<ref>/checkpoints/<checkpoint_id>-<bundle-sha256-prefix>.symbiont`, and at finalization it copies the ending bundle the same way. The checkpoint id alone (organism + tick) is not unique: a re-embodiment stopped before its first tick saves different bytes at the same tick. An existing file is never rewritten. A resumed physical body is retained as `bodies/<ref>/checkpoints/<sha256-prefix>.json` and hashed.
3. **Manifest fields.** Each run manifest records `run_kind`, the observer definition, `seed`, the resolved rate plan, `software` identity, a `starting_state` (checkpoint id/hash, bundle hash, retained path, body hash, embodiment epoch) or an explicit `{"genesis": true}` for a new organism, and at the end an `ending_state`, `termination_reason` and `lifecycle`.
4. **X excludes observer state.** Atlas coordinates, UI filters, narratives, DOM state and camera state are never part of X. Only causal continuation state is retained.

## Consequences

- Runs sharing a starting checkpoint hash and seed start from the same state X. Any claim that such runs are reproducible must still meet the project's declared determinism guarantees.
- Disk use grows by one bundle per distinct checkpoint. Retention is idempotent per checkpoint id.

## Introduced in

Milestone EW-A.
