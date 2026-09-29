# Repository governance

This directory contains the authority model used to constrain intelligent agents and coordinate scientific work.

## Files

- `constitution.md` — permanent repository and scientific constraints.
- `agent-policy.md` — what agents may do at authority levels L0-L4.
- `decision-gates.md` — changes that require an explicit owner decision.
- `project-state.toml` — machine-readable current programme state.
- `frozen-artifacts.toml` — protected scientific and governance artefacts.
- `active-work.toml` — current work/campaign coordination records.
- `validation-matrix.toml` — minimum validation by change domain.

Human-readable policy is authoritative together with accepted ADRs and the roadmap. TOML files exist so tooling can enforce the same rules mechanically.
