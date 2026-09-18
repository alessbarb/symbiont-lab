# Versioning policy

Symbiont Lab uses the package version as the software release identifier. The
canonical frozen-organism cut is package version `1.0.0` with the annotated
scientific tag `experimental-organism-v1`. The state is recorded in
`ORGANISM.md`, `README.md` and the release changelog; historical milestones
remain in [`roadmap.md`](roadmap.md).

## Release lanes

- **Milestone releases** (`v0.30` onward) add organism capabilities and their
  scientific contracts.
- **Post-roadmap hardening** (`v0.76.x`) is limited to compatibility, safety,
  observability, test-boundary and documentation closure. It must not silently
  add a new organism capability.
- **New organism capabilities** require a new milestone and design review rather
  than another `v0.76.x` patch.
- **Experimental Organism v1 (`1.0.0`)** freezes the organism core by default.
  The prior `v0.80.16` tag is immutable history, not a moving compatibility
  alias.
- **Post-freeze work** may change experiments, habitats, research analysis,
  Observatory, performance and bug/safety/reproducibility behavior when causal
  semantics are preserved. New organism capabilities require an explicit new
  design/review gate and a new release line.

## Contract changes

Changes to an Observatory JSON contract require all of the following in one
release:

1. update the normative schema;
2. update `observatory/schemas/CONTRACT_MATRIX.md`;
3. add or revise producer and consumer compatibility tests;
4. document migration behavior in `docs/CHANGELOG.md`.

## Documentation-only changes

Pure wording, navigation or historical classification changes do not increment
the runtime version. A code, schema, adapter or behavior correction does.
