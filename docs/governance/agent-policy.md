# Agent workflow policy

The repository uses proportional governance. Ordinary work should be cheap; scientific
and constitutional boundaries remain deliberate without a per-commit permission system.

## Operational classes

- **ORDINARY** — green, current candidates may auto-promote.
- **SCIENTIFIC** — causal equivalence may downgrade to ORDINARY; otherwise external owner review.
- **FROZEN** — completed evidence/protocol is never edited in place; create a new version.
- **CONSTITUTIONAL** — permanent governance/safety/invariant changes require an Accepted ADR and external owner review.

## Normal workflow

    python scripts/agentctl.py publish --message "..."

The command fetches/rebases, classifies the final diff, runs required equivalence,
records provenance and publishes one `agentctl/*` candidate. GitHub Actions is the sole
technical validation gate. Only ORDINARY candidates may auto-promote.

There is no active L0-L4 authority model, grant ancestry, grant consumption, session
grant manifest or scientific-run grant. The former ledger is historical provenance only.

## Scope and operating autonomy

Agents complete the requested outcome and necessary supporting work without inventing
extra approval ceremony. Unrelated work remains out of scope. FROZEN evidence, RUNNING
campaigns, scientific interpretation and constitutional boundaries still apply.

## Root of trust

The real approval root is outside the repository: operator instruction and
protected/external review. Repository records are provenance, not proof of human identity.

## Validation failure discipline

A failing check is evidence to diagnose. Do not weaken, skip or blindly rerun validation
merely to obtain green status.

## Candidate responsibility

Publishing starts validation; it does not finish the task. Follow the candidate until it
auto-promotes, requires external review, or reaches a concrete blocking condition.

## Scientific runs

    python scripts/agentctl.py run start --commit <sha> --id <run-id> \
      --scope development --snapshot-source <state-dir> -- <command>

Runs pin code, archive/hash input state and enforce resource/concurrency policy.
Held-out, confirmation and replication remain explicit owner decisions by policy; no CLI
approval flag or repository grant pretends to authenticate that decision.
