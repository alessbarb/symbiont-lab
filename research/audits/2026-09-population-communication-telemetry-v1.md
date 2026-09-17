# Adversarial audit — Population Communication Telemetry v1

Date: 2026-09-17

## Scope

Audit of the bounded population communication telemetry and Observatory
projection. The purpose is to prevent observability from becoming a cognitive
or causal control path.

## Checks

- `CommunicationEvent` has only bounded factual fields; no meaning, labels,
  latent state, or ground truth.
- Runtime imports no Observatory module. Telemetry is an optional outbound
  sink and sink errors are isolated from delivery and grounding.
- Population graph edges are built only from exported delivery/receive events;
  an `EMIT` record alone cannot fabricate an edge.
- Fleet aggregation namespaces instance event IDs and removes records below a
  source's explicit truncation boundary.
- Grounding is exported separately from communication and remains a local
  association update, not an external translation.
- Observatory renderers have no fetch, mutation, or runtime-state write path.
- Snapshot telemetry is top-level and schema-versioned; old snapshots without
  telemetry remain valid.
- Buffer capacities, per-tick limits, duplicate rejection, checkpoint/restore,
  and replay are tested.

## Residual limitations

The current channel exports the factual delivery operation rather than a
separate emitter intent event when no such runtime event exists. Therefore the
UI does not claim intent, teaching, or causation. Absolute first-seen/extinction
claims are not made after truncation. Browser QA remains a separate validation
step from Python/Node tests.
