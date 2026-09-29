# CLAUDE.md

Operating contract for Claude and other coding agents. Tool-specific convenience never
overrides repository governance.

<!-- BEGIN CANONICAL AGENT CONTRACT -->

## Authority model

Agents execute authorised work; they do not choose scientific direction. L2-L4 require
a grant already present in the parent commit. Grant issuance is a separate owner-root
administrative commit validated by CI actor identity and an append-only single-grant
diff; an implementation cannot grant itself authority.

The Constitution is the single canonical source for permanent invariants.

## Mandatory startup sequence

Before editing: inspect branch/head/worktree; read this contract, Constitution, roadmap,
project state, active work and relevant design/ADR; run `agentctl status`; classify
L0-L4; identify any prior grant; do not touch RUNNING campaign paths; choose the
lowest-authority valid solution.

## Mandatory validation and pre-commit gate

```bash
python scripts/agentctl.py validate --staged
python scripts/agentctl.py check --staged --manifest .agent-session.toml
python scripts/agentctl.py verify
git diff --check
```

Validation is tied to the exact staged tree.

## Scientific discipline

A negative scientific result is not a software bug. Do not change the organism merely
to satisfy an evaluator. Scientific mechanism work follows analysis -> hypothesis ->
design -> owner approval -> preregistration -> implementation -> campaign ->
interpretation.

## Frozen evidence

A completed experiment freezes runner, fixtures, protocol and results together. New
work uses a new version/directory. Held-out or confirmation data require a distinct
scientific-run grant.

## Scientific execution

```bash
python scripts/agentctl.py run exec --grant <id> --id <run-id> \
  --manifest .agent-session.toml -- <exact owner-approved argv>
```

The grant fixes code, argv, scope and resource ceilings. The manifest must set
`may_run_scientific_campaigns = true`. A code-change grant never authorizes a run.

## Concurrency and resources

The active-work registry protects RUNNING paths. The launcher shares a lock across
worktrees through Git's common directory, uses one-long-run default concurrency,
wall-time termination and POSIX hard memory/CPU limits where supported. Cross-machine
locking and portable storage quotas are not claimed.

## Protected control plane

Governance, agent hooks/rules, CI, pre-commit, CODEOWNERS, pytest/linter configuration,
validation tests and Git-ignore rules are L4. Changing the guard and then using the
changed guard to authorize the same commit is invalid.

## Stop conditions

Stop for owner authority before changing protocol criteria, held-out/confirmation
execution, PAUSED/BLOCKED work, architecture ownership, lifecycle/heredity/reproduction,
project priorities, host permissions, identifying/user-content access,
filesystem/process inspection, network/credentials/persistence/propagation,
real-world actuation, resource-ceiling ownership, evaluator isolation or global reward.

<!-- END CANONICAL AGENT CONTRACT -->


## Canonical permanent invariants

Read and obey [`docs/governance/constitution.md`](docs/governance/constitution.md).
