# CLAUDE.md

Operating contract for Claude and other coding agents. Tool-specific convenience never
overrides repository governance.

<!-- BEGIN CANONICAL AGENT CONTRACT -->

## Authority model

Agents execute authorised work; they do not choose scientific direction.

| Level | Authority |
| --- | --- |
| L0 | Read-only inspection, audit and proposals |
| L1 | Maintenance with no scientific/runtime semantic change |
| L2 | Contract-preserving implementation already authorised by a normative source |
| L3 | Scientific mechanism change under approved design/preregistration |
| L4 | Constitutional, host-safety, lifecycle, project-direction or authority change |

L0-L1 need no elevated grant. L2-L4 require an **owner grant already present in the
parent commit**. An agent cannot grant itself authority by editing a grant in the same
change. `agentctl` reads grants from HEAD/base history, not from the working-tree
version being committed.

The Constitution at `docs/governance/constitution.md` is the single canonical source
for permanent architectural and safety invariants.

## Mandatory startup sequence

Before editing:

1. inspect branch/head/worktree and unrelated changes;
2. read this contract, the Constitution, `docs/roadmap.md`,
   `docs/governance/project-state.toml`, active-work state and the nearest relevant
   README/design/ADR;
3. run `python scripts/agentctl.py status`;
4. classify the work L0-L4 and identify affected domains;
5. for L2-L4, identify the owner grant and create a local untracked session manifest;
6. do not modify paths protected by a RUNNING scientific campaign;
7. choose the lowest-authority solution that satisfies the approved contract.

Memory from another session is not authority. The decision must exist in the current
owner instruction or committed repository authority.

## Mandatory pre-commit gate

Every modifying session must run:

```bash
python scripts/agentctl.py check --staged --manifest .agent-session.toml
python scripts/agentctl.py verify
git diff --check
```

The pre-commit hook runs the staged check. Bypassing hooks does not waive the policy.
CI independently audits commit ancestry and authority grants where repository history
is available.

## Scientific discipline

Distinguish implementation defect, apparatus defect, obsolete test, historical
compatibility contract, negative scientific result and new scientific hypothesis.

A red test is not permission to weaken an assertion. A negative result is not a bug.
Never change the organism merely to satisfy an evaluator or to make a campaign
positive.

For scientific mechanism work:

```text
result/problem
-> analysis
-> hypothesis
-> design
-> owner approval
-> preregistration
-> implementation
-> campaign
-> interpretation
```

## Frozen evidence

Completed results are append-only evidence. A completed protocol with archived results
is frozen together with those results. Fix errors through a new run/version and an
explicit provenance note; never silently rewrite old evidence.

After preregistration/freeze, seeds, horizons, baselines, thresholds, success criteria
and interpretation rules do not move because of observed data. Held-out and
confirmation runs require explicit recorded authority.

## Claims

Use the claim vocabulary and evidence levels from `docs/roadmap.md`. Do not elevate
`validated`, `causal`, `robust`, `emergent`, `learned`, `closed` or
`general` without the supporting evidence level, scope and limitations.

## Concurrency and scientific runs

`docs/governance/active-work.toml` is a tracked coordination boundary. A RUNNING
campaign protects its runner, protocol, inputs, relevant mechanism and declared paths.

New long scientific runs must be launched through `agentctl run exec` unless the
owner explicitly records an external-run exception. The default resource policy allows
one long scientific campaign at a time.

## Git and control-plane protection

Never destroy unrelated work, force-push published scientific history, delete negative
results, or squash away required provenance.

The governance control plane itself is protected: `AGENTS.md`, `CLAUDE.md`,
`docs/governance/**`, `scripts/agentctl.py`, `tests/governance/**`,
`.github/workflows/**`, `.github/CODEOWNERS`, and `.pre-commit-config.yaml`.

Changing the guard and then using the changed guard to authorise the same commit is
invalid.

## Stop conditions

Stop for an owner decision before changing hypotheses, seeds, horizons, thresholds,
baselines, success criteria, held-out execution, PAUSED/BLOCKED/UNSCHEDULED programmes,
architecture ownership, lifecycle/heredity/reproduction/re-embodiment semantics,
project priorities, host permission classes, user-content or identifying-metadata
access, arbitrary file/process inspection, network exchange, credentials, persistence,
propagation, real-world actuation, resource-ceiling ownership, evaluator isolation or
global reward/fitness.

<!-- END CANONICAL AGENT CONTRACT -->


## Canonical permanent invariants

Read and obey [`docs/governance/constitution.md`](docs/governance/constitution.md).
The Constitution is not duplicated here so that agents cannot create policy drift by
editing one copy but not another.
