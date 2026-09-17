# Cultural Foundation v1

## Scope

This phase adds the smallest bounded substrate for social knowledge without
sharing private models, adapters, weights, corpora, telemetry, or host actions.
`SocialClaim` is a report in native token space. It is not an observation and
cannot enter the Private SLM corpus as a target in this phase.

## Epistemic boundary

`SocialClaim`, `SocialSupported`, and `SocialContradicted` are separate from
the private `ExperienceRecord` states. Local confirmation is an assessment
with a new local evidence id; it does not rewrite the received claim or turn it
into `OBSERVED`. Contradictions remain alongside the original claim.

## Causal genealogy

`ClaimGraph` is a bounded DAG. Every retransmission or bounded token mutation
creates a new claim id and points to its parent. Root evidence ids are carried
through all descendants. Independent evidence is counted only by distinct root
evidence ids, never by holders, hops, senders, or copies. Cycles, missing
parents, duplicate ids, malformed claims, and over-depth ancestry fail closed.

The receiving ledger imports the delivered ancestry for replay and lineage
inspection. This is metadata about claims, not the sender's private memory.

## Local social memory and transport

`SocialEvidenceLedger` is organism-owned and separate from `ExperienceLedger`.
It stores received/held claims, assessments, freshness, bounded forgetting,
checkpoint state, and explicit communication costs. `SocialChannel` is a
laboratory-controlled in-memory transport with an allow-list and delivery
ceiling. It has no sockets, peer discovery, host access, or autonomous network
behavior.

The organism runtime exposes only bounded claim operations. A clonal offspring
starts with an empty social ledger, just as it starts without acquired private
models and corpus. Observatory integration is projection-only and must never
mutate this state.

## Deferred behaviour

The mechanism supports retain, test, support, contradict, retransmit, mutate,
and forget. It does not hardcode cooperation, truth detection, consensus,
roles, reputation, or a sharing policy. Cultural utility and rumor behaviour
are study questions, not runtime assumptions.

## Closure gates

The preregistered study `learning.cultural-foundation` covers faithful
transmission (C1), anti-copy inflation (C2), independent corroboration (C3),
contradiction (C4), utility (C5), rumor control (C6), and persistence after
the discoverer disappears (C7). Cultural Foundation v1 is closed only if all
seven gates pass in the declared scope; implementation and unit tests alone
are insufficient.
