# Agent workflow policy

The repository uses proportional governance. Ordinary work should be cheap; crossing
scientific or constitutional boundaries should be deliberate.

## Operational classes

- **ORDINARY** — engineering work that does not change the organism causal trajectory
  or a frozen scientific contract. Publish automatically after validation.
- **SCIENTIFIC** — a change that may alter learning, agency, model promotion, physical
  experience, protocol or scientific interpretation. Owner decision required unless the
  required Equivalence Suite scenarios all PASS.
- **FROZEN** — completed experiment evidence/protocol. Never edit in place; create a new
  version.
- **CONSTITUTIONAL** — governance, host permissions, identity/lifecycle, evaluator
  boundary or equivalent permanent invariants. ADR + explicit owner approval.

Path is only a screening signal. Classification uses path, sensitive diff content and
Equivalence Suite evidence. A PASS is valid only within the scenario coverage.

## Normal workflow

Agents should not reconstruct grant ancestry. Use:

    python scripts/agentctl.py publish --message "..."

The command fetches/rebases, classifies the final diff, runs required equivalence and
validation, creates audit trailers and publishes. If it says BLOCKED, do not bypass it.

Historical L0-L4 grants remain provenance for older commits but are deprecated for
ordinary publication.

## Root of trust

The real identity/approval root is outside the repository (operator instruction and
protected review). Repository audit records are provenance and guardrails; they are not
a cryptographic substitute for external identity when agents share owner credentials.

## Scientific runs

Long/evidentiary runs must pin an exact commit in a detached worktree, archive and hash
the starting input before execution, pass memory/disk/concurrency preflight and keep one
long campaign per machine by default.

Use:

    python scripts/agentctl.py run start --commit <sha> --id <run-id>       --scope development --snapshot-source <state-dir> --owner-approved -- <command>

D1-v2 remains a tracked pre-launcher exception until its current run finishes.
