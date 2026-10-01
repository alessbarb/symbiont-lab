# ADR-0049 — Token-efficient agent context and read-on-demand governance

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Extends:** ADR-0047 and ADR-0048

## Context

After removing operational grants, ordinary agent work still paid a substantial context
cost by repeatedly reading the Constitution, roadmap, project-state, active-work and
governance documentation before implementation. Most of that text does not change the
decision for an ordinary task, while final classification already belongs to
`agentctl publish`.

## Decision

1. Add `agentctl context` as the canonical start-of-task interface.
2. The command refreshes trusted `origin/main` once and emits only operational state:
   base/head, branch, worktree state, current gate, RUNNING work/conflicts and the
   publication action.
   The default human-readable form stays intentionally compact; `--json` is available
   when a machine-readable snapshot is preferable.
3. Final-diff classification is deliberately not duplicated in `context`; it remains
   owned by `agentctl publish`.
4. AGENTS.md and CLAUDE.md require one normal context read. Deeper governance documents
   are read on demand only when the task crosses scientific protocol, FROZEN, RUNNING,
   architectural, epistemic, lifecycle or host-safety boundaries.
5. Local checks are proportional development feedback. GitHub Actions remains the sole
   technical validation gate; agents should not routinely duplicate the full CI suite.
6. Publication remains one `agentctl publish` operation followed by CI/promotion or
   external review.

## Consequences

Ordinary tasks consume less context and perform fewer repeated repository inspections.
The scientific and constitutional protections are unchanged: the optimization removes
interpretive duplication, not gates.
