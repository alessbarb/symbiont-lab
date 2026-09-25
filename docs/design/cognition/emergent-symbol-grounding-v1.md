---
id: design.general.emergent-symbol-grounding-v1
title: "Emergent Symbol Grounding V1"
document_type: design
domain: cognition
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Emergent Symbol Grounding v1

## Scope

This phase studies an opaque and bounded symbolic convention, not language. The space
`symbol.<digest>` does not contain human semantics nor a `symbol -> meaning` table.
The emitting organism decides locally between silence and a signal; the receiver only
updates its `SymbolGroundingLedger` after exposure and local experience.

The transport is `SymbolChannel`, an authorized in-memory channel. There is no real network,
peer discovery, executable payload, weight transfer, nor corpus.
Ground truth and the latent event/outcome relationship exist solely in the
evaluator-side study to measure the effect; they never enter the policy.

## Contracts

- `SymbolPolicy` produces bounded local decisions, with cost, candidates, and digest
  of available state.
- `SymbolGroundingLedger` preserves exposures, associations, support,
  contradiction, implicit freshness per tick, and checkpointable forgetting.
- `SymbolMessage` preserves emitter, receiver, tick, and depth; the ownership of the
  receiver and the authorized peers are validated fail-closed.
- The offspring receives an empty symbolic ledger: it inherits capacity and seed, not
  meanings nor history.
- Observatory exposes only opaque IDs, counters, and support bins; it does not expose the
  outcome token as a meaning translation and remains passive.

## Preregistered study

`learning.emergent-symbol-grounding`, seeds `101, 127, 149`, compares `none`,
`random`, `autonomous`, and `permuted`. `directed_label` is left outside the treatment
and, if used, is only a methodological upper-bound. The criteria ESG1--ESG10 and
replay are fixed in `experiments/learning/emergent-symbol-grounding/experiment.toml`.

The permuted condition changes the identities in the channel and verifies that the
receiver can relearn the association without depending on the symbol's spelling.
The random condition receives signals without the autonomous emitting process and serves as
a separation control, not as positive evidence.

## Result

With the preregistered seeds `101, 127, 149`, ESG1–ESG10 and replay passed.
The autonomous predictive utility was `0.125`, `0.3125`, and `0.4375`; the random
control was `-0.1875`, `0.0`, and `-0.1875`. The permuted condition maintained utility
of `0.125`, `0.3125`, and `0.4375`. The newborn acquisition occurred in `2`, `2`, and
`1` ticks. The result is closed only in this scope and does not extend to
language, grammar, or human semantics.

## Interpretation criterion

Passing the gates would solely demonstrate a grounded symbolic convention in the
scope of the protocol: an opaque signal chosen by organisms can acquire
predictive utility and transmit itself beyond the founder. It would not demonstrate language,
grammar, human semantics, nor sequence composition.
