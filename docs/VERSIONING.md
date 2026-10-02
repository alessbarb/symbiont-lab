# Versioning policy

Symbiont Lab uses the package version as the software release identifier. The
current active development release line is package version `0.90.0`. The state
is recorded in `ORGANISM.md`, `README.md` and the release changelog; historical
milestones remain in [`history/roadmap-log.md`](history/roadmap-log.md).

## Release lanes

- **Milestone releases** (`v0.30` onward) add organism capabilities and their
  scientific contracts.
- **Post-roadmap hardening** (`v0.76.x` to `v0.80.16`) closed compatibility,
  safety, observability, and test boundaries. The prior `v0.80.16` tag is
  immutable history.
- **Agencia, Mundos y Formalización (`0.90.0`)**: consolidates the evolutionary
  arc following `v0.80.16` (Agency Acquisition, Adaptive Sensory System,
  Experience & World Architecture v1, Observability P0–P10, and the formalization
  of ADR-0001 to ADR-0041). The substrate is not prematurely frozen.
- **Milestone 1.0.0 (Transforming Learning into Execution)**: Version `1.0.0` is
  reserved for when the organism demonstrates the closure of the autonomous
  operational loop—transforming acquired causal learning into effective,
  deliberate execution. A canonical substrate freeze occurs only when this
  empirical milestone is attained.
- **Post-1.0 work**: once `1.0.0` is achieved, changes to the organism core will
  freeze by default, and new organism capabilities will require an explicit new
  design/review gate and release line.

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
