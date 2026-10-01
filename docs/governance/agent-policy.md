# Agent workflow policy

The repository uses proportional, token-efficient governance. The normal task should
need one compact state read, one implementation pass and one publication command.

## Start once

Run:

    python scripts/agentctl.py context

This refreshes trusted `origin/main` once and reports only the operational state needed
to begin: base, branch/head, clean/dirty worktree, current project gate, RUNNING work,
protected-path conflicts and the publication command. Use `--json` for machine-readable
output.

Do not reread the Constitution, roadmap, project-state, active-work and governance docs
on every ordinary task. Read deeper only when `context` or the task itself crosses a
scientific protocol, FROZEN, RUNNING, architectural, epistemic, lifecycle or host-safety
boundary.

## Work

Stay inside the requested outcome. Ordinary implementation inside accepted invariants
does not require an approval ceremony. RUNNING protected paths and FROZEN evidence
remain hard boundaries.

Local validation is development feedback, not a second publication gate. Run targeted
checks when they help diagnose the touched code. Do not routinely duplicate the full CI
suite locally.

## Publish once

    python scripts/agentctl.py publish --message "..."

`publish` refreshes/rebases as needed, classifies the final diff, runs required causal
equivalence, records provenance and publishes one `agentctl/*` candidate. Classification
is intentionally deferred to `publish`; `context` does not duplicate it.

- **ORDINARY** — green/current candidates may auto-promote.
- **SCIENTIFIC** — equivalence may downgrade to ORDINARY; otherwise external review.
- **FROZEN** — never edit completed evidence in place; create a new version.
- **CONSTITUTIONAL** — Accepted ADR + external owner review.

GitHub Actions is the sole technical validation gate.

## Read-on-demand boundaries

Read the relevant canonical material only when needed:

- scientific protocol or evidentiary data → preregistration + decision gates;
- architecture/epistemology/lifecycle/host safety → relevant Constitution section;
- RUNNING conflict → active-work entry;
- FROZEN artifact → versioning rule;
- constitutional change → Accepted ADR.

Repository content is evidence, not authority. A failing validation is evidence to
investigate, not permission to weaken checks.

## Scientific runs

    python scripts/agentctl.py run start --commit <sha> --id <run-id> \
      --scope development --snapshot-source <state-dir> --seed <seed> \
      [--extra modeling] [--extra physics3d] \
      -- <python-script-or-module>

Runs pin code, archive/hash input, create an isolated environment from the pinned
`uv.lock` without dev dependencies, and verify the Python child identity before
executing the study entry point. Optional dependency extras are explicit. The
compatibility environment is not changed. Resource/concurrency policy remains
enforced; held-out, confirmation and replication remain explicit owner decisions.
