# Organism Boundary Contracts

Status: Accepted for implementation in the `symbiont` package.

This record resolves four open contracts from the focused Symbiont audit. It
states policy and ownership; it is not evidence that every implementation
path already conforms. The API change in this same workstream is recorded
separately below.

## D-1 — Process telemetry and interoception

Process telemetry is apparatus evidence, not organism experience. It MUST NOT
become an organism-facing reading, a learned capability, a percept, a memory,
or a checkpointed cognitive fact. Provider identity, host capability metadata,
and discovery topology MUST likewise remain outside organism learning. The
organism may receive only bounded values for its explicitly admitted intrinsic
interoceptive channels; those values must be computed from organism state, not
used to smuggle host measurements across the boundary.

This decision does not prohibit the external composer from using host
capability metadata to decide which providers to attach. It prohibits that
metadata from becoming subject-accessible evidence. Existing `process_telemetry`
paths and capability discovery require behavioral tests against this contract;
the decision alone does not establish conformance.

## D-2 — `Individual` and the reduced seed

`Individual` is the embodiment-study aggregate composed from
`CleanEmbodimentSeed`, `Body`, an `EmbodimentEpisode`, and its history. It is
not an alias for `OrganismRuntime`, nor does the word “Individual” assert the
canonical re-embodiment contract.

`CleanEmbodimentSeed` remains a reduced study subject with
`REDUCED_SEED_TRANSPLANT` continuity. `OrganismRuntime` remains the full runtime
with `CANONICAL_REEMBODIMENT` continuity. Both may exist; callers and
documentation MUST name the selected contract and MUST NOT describe the seed
as interchangeable with the full runtime. In particular, “canonical” refers
to the declared longitudinal contract, not to a universal claim that one
runtime is scientifically superior.

## D-3 — Social evidence ownership

The operational interaction ledgers (`RelationLedger` and
`ResourceEvidenceLedger`) remain distinct from the modeled social/cultural
claims owner (`SocialEvidenceLedger` with `CulturalPolicy`). Their inputs and
decisions are different, so they MUST NOT be merged into a universal social
trust ledger.

`EvidenceTrust` and `SourceEvidenceState` are dormant prototypes, not live
authorities. New runtime behavior MUST NOT depend on them. They are removed
from the aggregate `symbiont.core` exports; their module definitions remain
available only as non-canonical implementation artifacts pending eventual
deletion. If source reputation is later required, it needs an explicit owner,
evidence lifecycle, decision consumer, and persistence contract before
implementation.

## D-4 — Capsule transport and claims

Knowledge capsules remain signed transport envelopes. Signature verification
establishes payload integrity relative to the included public key; it does not
establish truth, source reliability, consent to believe, or claim validity.
Capsule payloads MUST NOT be automatically ingested as social/cultural claims.
There is no capsule-to-claim adapter until a policy defines payload schema,
provenance preservation, evidence assessment, and the `SocialEvidenceLedger`
entry path.

## Public API consequence — Embodiment boundary (C-1)

`symbiont.api` exposes organism lifecycle, persistence, identity, and lineage
contracts. It does not expose body-transition operations or embodiment
descriptors. Internal organism-owned transition code may remain under
`symbiont.core.embodiment`; its internal location does not make it part of the
public organism facade.

Current external implementations that need such operations must import the
explicit internal transition contract until an owner outside `symbiont`
chooses a new public composition API. This change does not migrate or modify
those external consumers.
