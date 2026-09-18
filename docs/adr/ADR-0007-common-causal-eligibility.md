# ADR-0007: Common Causal Eligibility for Attention Allocation

## Status

Accepted

## Context

In causal attention studies, selectors compete under fixed inspection budgets. An audit in v0.24 revealed that directed attention selectors (such as risk-based or novelty-based) and random baseline selectors had divergent eligibility criteria during warm-up periods, introducing an artificial startup advantage/bias.

## Decision

Directed and baseline attention selectors must share bitwise-identical eligibility filters at each step before attention ranking or random sampling occurs.

## Consequences

- Eliminates startup bias in causal attention budget studies.
- Guarantees fair paired comparisons across all budget tiers.

## Introduced in

v0.24.2

## Evidence

Audit report `research/audits/historical/v024/ANALYSIS.md`, `tests/test_audit_v024_regressions.py`.
