# Repository governance

## Purpose

Keep ordinary engineering cheap while making scientific and constitutional boundary
crossings explicit.

## Normal workflow

Agents should use one interface:

    python scripts/agentctl.py publish --message "..."

The command fetches/rebases onto the current main, classifies the final diff, runs any
required bounded equivalence scenarios, derives validation, creates audit trailers and
pushes. Agents should not reconstruct grant ancestry by hand.

## Operational classes

- ORDINARY — publish automatically after validation.
- SCIENTIFIC — explicit owner approval unless required equivalence scenarios all PASS.
- FROZEN — version, never edit in place.
- CONSTITUTIONAL — ADR + explicit owner approval.

See agent-policy.md and change-surfaces.toml.

## Equivalence

experiments/equivalence/suite-v1 is a versioned evidence suite. PASS is strong evidence
only inside the declared scenario coverage. FAIL and NOT_ASSESSABLE remain SCIENTIFIC.

Reference snapshots must be immutable captures of real organism states. The initial
suite is intentionally capture-required until those inputs are archived.

## Scientific execution

Use:

    python scripts/agentctl.py run start --commit <sha> --id <run-id>       --scope <scope> --snapshot-source <state-dir> --owner-approved -- <command>

The launcher pins the commit in a detached worktree, archives the starting state before
execution, checks memory/disk/concurrency and writes an execution record.

The current D1-v2 run is a tracked pre-launcher exception until it completes.

## Historical grants

authority-grants.toml remains historical provenance for the previous governance model.
Per-commit grants are deprecated for ordinary publication by ADR-0046.

## Root of trust and limits

Human identity/approval lives outside the repository. Repository records are guardrails
and provenance, not cryptographic identity when agents share owner credentials.
Cross-machine locking and portable storage quotas remain external infrastructure.
