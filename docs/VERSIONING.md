# Versioning policy

Symbiont Lab uses the package version as the single release identifier. The
canonical current state is recorded in `ORGANISM.md` and `README.md`; historical
milestones remain in [`roadmap.md`](roadmap.md).

## Release lanes

- **Milestone releases** (`v0.30` onward) add organism capabilities and their
  scientific contracts.
- **Post-roadmap hardening** (`v0.76.x`) is limited to compatibility, safety,
  observability, test-boundary and documentation closure. It must not silently
  add a new organism capability.
- **New organism capabilities** require a new milestone and design review rather
  than another `v0.76.x` patch.

## Contract changes

Changes to an Observatory JSON contract require all of the following in one
release:

1. update the normative schema;
2. update `observatory/schemas/CONTRACT_MATRIX.md`;
3. add or revise producer and consumer compatibility tests;
4. document migration behavior in `docs/releases/`.

## Documentation-only changes

Pure wording, navigation or historical classification changes do not increment
the runtime version. A code, schema, adapter or behavior correction does.
