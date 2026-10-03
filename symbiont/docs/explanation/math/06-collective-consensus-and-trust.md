---
id: explanation.math.06-consenso-colectivo-y-confianza
title: "06 Collective Consensus And Trust"
document_type: explanation
domain: math
status: unclassified
canonical: false
implementation_status: not_implemented
migrated_on: 2026-09-25
last_reviewed: 2026-10-03
language: en
---
# Collective Consensus and Trust

> **Implementation status:** The source-reputation and collective-consensus
> algorithms previously described here are not part of the active Symbiont
> social-evidence path. This page no longer specifies runtime behavior.

The active modeled social/cultural owner is `SocialEvidenceLedger` together
with `CulturalPolicy` in `symbiont.modeling`. The base runtime separately owns
`RelationLedger` and `ResourceEvidenceLedger` for interaction outcomes and
resource availability. These systems have different inputs and decisions; no
single reputation score connects them.

`EvidenceTrust` and `SourceEvidenceState` are dormant prototypes. They are not
exported by the aggregate `symbiont.core` package and have no active runtime
writer, decision consumer, or checkpoint owner. Their existence does not
establish source reputation, consensus, capsule ingestion, or epistemic trust
in the organism.

Signed knowledge capsules are transport envelopes only. Signature
verification establishes integrity relative to the key carried by the
capsule; it does not validate claims or source reliability. No automatic
capsule-to-claim ingestion is defined.

Any future trust or consensus mechanism requires a separate decision defining
its evidence inputs, source identity, independence semantics, decision
consumer, persistence owner, and validation limits before it is treated as
implemented.
