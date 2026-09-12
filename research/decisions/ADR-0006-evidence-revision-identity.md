# ADR-0006: Evidence Revision Identity

## Status
Accepted

## Context
When an agent or observer collects supplemental observations to revise prior classifications, tracking belief trajectories requires strict pairing between pre-revision and post-revision event identifiers.

## Decision
Every revised observation retains immutable lineage linking to the original event identifier, recording the exact score delta, uncertainty collapse, and classification change.

## Consequences
- Clean accounting of net revision benefit without orphan observations.
- Explicit detection of oscillating or unstable belief revisions.

## Introduced in
v0.23.0
