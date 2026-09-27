# Evidence status and scientific claims

Use the following language consistently when documenting claims.

| Status | Meaning |
| --- | --- |
| Implemented | A current code path realises the mechanism |
| Covered by tests | Tests exercise the stated behaviour under defined conditions |
| Observed | A recorded runtime/experiment exhibited the behaviour |
| Supported | Multiple observations or a controlled study support an interpretation |
| Intended | Present in a specification but not established as current behaviour |
| Historical | Describes a previous architecture or superseded behaviour |
| Unresolved | Available evidence is insufficient or contradictory |

Avoid “proves”, “guarantees”, “always” and “never” unless the claim is genuinely established by the relevant contract and all reachable code paths.

A scientifically strong statement should make its scope visible. Prefer:

> In the current Physics3D runtime, a fresh body is assigned a distinct physical body identity while the restored organism keeps its organism identity.

rather than:

> Symbiont always preserves identity perfectly across bodies.
