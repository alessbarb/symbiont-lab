# ADR-0052 — Agent branch lifecycle and cleanup

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Relates to:** ADR-0043, ADR-0048, ADR-0049

## Context

Agent work is published through temporary task or `agentctl/*` candidate branches.
After integration, leaving those branches behind makes it difficult to distinguish
active work from completed work and creates avoidable repository clutter. Deleting
branches too early is also unsafe: a candidate may still need CI promotion, external
review or owner attention.

## Decision

1. Treat an agent-created task branch as temporary work, not as a second destination
   for completed code. The completed change must be integrated into trusted `main`
   through the repository publication process.
2. After integration is confirmed, verify the branch commit is an ancestor of trusted
   `origin/main`. Only then delete the corresponding local and remote task/candidate
   branches.
3. Never delete an unmerged branch or a branch still awaiting required CI promotion,
   external review or another explicit integration step. Retain it and report why it
   remains.
4. Immediately after creating/pushing an agent-owned branch, open a GitHub PR targeting
   `main` and report its URL. The PR is the review handoff; its existence does not imply
   approval, merge or permission to delete the branch. If auto-promotion wins the race
   and no diff remains against `main`, verify integration and report why a PR cannot be
   opened.
5. Before finishing, report the integration commit and confirm that completed
   agent-created branches were removed. Do not delete unrelated user branches.

## Consequences

Completed work remains in the project history on `main`, while stale agent-created
branch references are removed. In-progress or review-required candidates remain
available until their outcome is known; branch cleanup never substitutes for review,
CI validation or integration.
