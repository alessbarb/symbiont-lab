# ADR-0005: Shadow-Only Second-Look Evidence Probes

## Status

Accepted

## Context

Evaluating the value of extra evidence or multi-stage inspection (second-look) requires counterfactual analysis. If triggering a second-look inspection alters the runtime memory or scheduling of agents, the baseline simulation trajectory is contaminated.

## Decision

Second-look sensors and evidence probes must run strictly in shadow mode on the observer/evaluator side. The underlying world progression and agent cognitive states remain bitwise identical to an unprobed baseline.

## Consequences

- Guaranteed counterfactual validity when assessing information gain and revision deltas.
- Shadow sensors never inject state back into live hosts.

## Introduced in

v0.23.0
