# ADR-0024: High-Frequency Binary Telemetry and Decimated Observation Transport

## Status

Accepted

## Context

High-fidelity 3D embodied simulation operates at 60–120 Hz causal physics rates. Emitting full JSON payloads or string-serialized objects on every tick creates severe garbage collection pauses, memory thrashing, and I/O bottlenecks. This breaches the fundamental performance invariant that observation apparatus must not distort physical simulation dynamics.

## Decision

1. **Binary telemetry for causal execution.** Causal simulation and physics engines log state using packed, fixed-layout binary structures (`.bin`, compact byte buffers) with zero dynamic memory allocation or string serialization on the hot execution path.
2. **Decoupled observation cadence.** Observer pipelines sample simulation state at an independent, decimated frequency (e.g. 10–20 Hz) rather than mirroring causal physics frequencies.
3. **Anchor and differential delta transport.** Web and UI observation layers receive sparse updates structured as periodic keyframe anchors followed by compact differential deltas (`LiveDelta`), minimizing bandwidth and browser render overhead.
4. **Single serialization for multi-subscriber SSE.** Server-Sent Events (SSE) serialize observation payloads exactly once per transport tick, broadcasting pre-encoded byte buffers to all connected clients without per-client JSON encoding.
5. **No feedback into physics.** Telemetry serialization and transport errors fail silent or drop frames without backpressuring or stalling causal physics steps.

## Consequences

- Causal simulation maintains deterministic real-time performance regardless of observer attachment.
- Enables long-running, multi-hour physics campaigns with minimal disk footprint and zero latency jitter.

## Introduced in

Milestone P (Physics3D Telemetry v4.1 / P0–P7 Observability Optimization).

## Evidence

`docs/design/telemetry/physics3d-telemetry-v4.1.md`, `lab/tests/unit/lab/physics3d/telemetry/test_telemetry_binary.py`, `tests/experimental_integrity/test_live_delta_boundary.py`.
