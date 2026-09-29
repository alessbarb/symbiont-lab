# ADR-0046 — Proportional governance, causal-equivalence evidence and pinned runs

- **Status:** Accepted
- **Date:** 2026-09-29
- **Decision owner:** project owner

## Decision

Replace per-commit grant ceremony for normal engineering with four operational classes:
ORDINARY, SCIENTIFIC, FROZEN and CONSTITUTIONAL.

agentctl publish owns fetch/rebase, final-diff classification, bounded equivalence
evidence, validation, audit trailers and publication. Paths are screening signals, not
the sole classifier.

A sensitive diff may become ORDINARY only when every required versioned equivalence
scenario PASSes. FAIL and NOT_ASSESSABLE remain SCIENTIFIC.

Reference snapshots are immutable real-state captures with hashes and versioned
metadata. Live mutable organism state is never a reference baseline.

Long/evidentiary runs pin an exact commit in a detached worktree, archive the starting
input before execution, perform resource admission and retain one-long-run-per-machine
default concurrency.

## Root of trust

Human identity and approval live outside the repository. Repository trailers and
records provide provenance and guardrails, not cryptographic proof when agents share
owner credentials.

## Transition

Historical L0-L4 grants remain as provenance for old commits but are deprecated for
ordinary publication. Scientific and constitutional approval remains explicit.
