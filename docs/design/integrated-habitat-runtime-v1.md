# Integrated Habitat Runtime v1

> **Integration only.** This runtime connects existing capabilities; it does
> not add cognition, social policy, symbols, rewards, sensors, or reproduction
> semantics.

## Contract

`IntegratedHabitatRuntime` is the canonical bounded population orchestrator in
`symbiont_lab.integration`. It owns population membership, tick ordering,
authorized local contact, lifecycle bookkeeping, checkpoint envelopes and
outbound telemetry. Decisions about messages, claims, composites and grounding
remain inside each `ModeledOrganismRuntime`.

The default configuration is bounded to 32 organisms and 10,000 ticks. The
sequence transport quota is a bounded per-tick window; the telemetry sink
provides the separately bounded observable history. The habitat may expose
contact opportunities but never selects a claim, symbol, sequence, receiver
content, meaning or composite.

## Tick boundary

At each tick the runtime: ticks current live organisms; removes organisms that
have reached the existing terminal physiology state; optionally executes the
explicit evaluator-only lifecycle smoke probe; refreshes the local allow-list;
invokes existing autonomous symbol, sequence and cultural entry points; then
increments the habitat tick and records a summary. Checkpoints are valid only
after this boundary. A delivery to a dead organism is not authorized after the
membership refresh.

The lifecycle probe exists solely to exercise already implemented birth and
death APIs in one integration path. It is not used as evidence of autonomous
reproduction.

## Ownership and inheritance

Every resident owns its runtime, genome, physiology, experience, model
registry, social/cultural ledgers, grounding ledgers and decision state. A
clonal bud uses the existing reproduction path and receives fresh acquired
state; only the existing heritable genome/capacity crosses the boundary.

## Determinism and checkpointing

The integrated authority uses deterministic child IDs only when explicitly
configured by the habitat; historical callers retain UUID allocation. The
habitat also supplies deterministic body-schema salts. This removes integration
identity noise but does not repair the existing lossy cognitive checkpoint
contract.

Current status: structural restore and exact continuation replay pass for the
integrated boundary contract. Replay compares the population/lifecycle,
bounded history, telemetry and transport continuation state; it does not claim
byte-identical equality for intentionally lossy descriptive internals of the
base organism checkpoint.

## Boundaries

Telemetry is outbound-only, bounded and failure-isolated. No Observatory state
is read by the runtime. No model weights or private corpus crosses organisms.
Historical runtimes and experiments remain unchanged; this is a new canonical
entry point rather than a replacement.
