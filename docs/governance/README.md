# Repository governance

## Purpose

Define and mechanically enforce the authority boundary for coding agents and
scientific execution.

## Core files

- `constitution.md` — canonical permanent invariants.
- `agent-policy.md` — L0-L4 authority and grants.
- `decision-gates.md` — owner-decision boundaries.
- `project-state.toml` — current programme state.
- `authority-grants.toml` — owner-issued change/run grants.
- `owner-root.toml` — GitHub actor root used for grant issuance.
- `frozen-artifacts.toml` — protected surfaces.
- `active-work.toml` — active scientific work.
- `resource-policy.toml` — launcher limits.
- `validation-matrix.toml` — required validation.

## Modifying workflow

```bash
git add <files>
python scripts/agentctl.py validate --staged
python scripts/agentctl.py check --staged --manifest .agent-session.toml
python scripts/agentctl.py verify
```

## Scientific execution

Use a distinct scientific-run grant and `agentctl run exec`. The current D1-v2 run is
a tracked external exception because it started before the governed launcher existed.

## Limits

Repository policy cannot cryptographically distinguish the owner from an agent holding
the same owner credential, cannot create a global lock across unrelated machines, and
cannot provide portable filesystem quotas. Those remain external-infrastructure
boundaries.
