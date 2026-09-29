# Repository governance

This directory contains the authority model used to constrain intelligent agents and coordinate scientific work.

## Canonical files

- `constitution.md` — single source of permanent architectural and safety invariants.
- `agent-policy.md` — authority levels L0-L4 and grant semantics.
- `decision-gates.md` — changes that require an explicit owner decision.
- `project-state.toml` — machine-readable current programme state.
- `authority-grants.toml` — owner-issued, parent-commit grants for L2-L4 work.
- `frozen-artifacts.toml` — protected control-plane/scientific artefacts.
- `active-work.toml` — tracked active campaign coordination.
- `resource-policy.toml` — admission limits for governed scientific runs.
- `validation-matrix.toml` — minimum validation by change domain.
- `session-manifest.example.toml` — local untracked task-scope template.

## Root of trust

`agentctl` evaluates grants and protection metadata from the parent/base revision.
A grant or policy edited in the candidate change cannot authorise that same change.

Grant issuance itself is an owner administrative operation. Repository enforcement
cannot cryptographically distinguish a process using the owner's GitHub credentials
from the owner; server-side branch protection remains the external root-of-trust layer
where available.

## Normal modifying workflow

```bash
cp docs/governance/session-manifest.example.toml .agent-session.toml
# fill task and prior grant id when L2-L4
python scripts/agentctl.py status
python scripts/agentctl.py check --staged --manifest .agent-session.toml
python scripts/agentctl.py verify
```

Long scientific runs use `python scripts/agentctl.py run exec ... -- <command>`
unless an explicit tracked external-run exception exists.
