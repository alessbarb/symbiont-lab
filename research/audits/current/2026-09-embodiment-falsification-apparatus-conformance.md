# Embodiment falsification v1 — implementation conformance audit

Status: **open apparatus findings**

Baseline preregistration:
`research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md`

This audit evaluates the experiment implementations, not the Symbiont mechanism.

## APP-001 — E1 incomplete relative to preregistration

Preregistration requires:
- exact yoking;
- jittered yoking;
- anti-causal ordering;
- independent control;
- yoking break / time-to-reject;
- lead-lag reporting.

Current E1 implements exact yoking, anti-causal and independent controls, but not
jittered yoking, break/rejection latency or lead-lag report.

**Required:** extend E1 before treating it as the complete preregistered campaign.
The already frozen negative result remains a valid result for the implemented
exact-yoke assay, but must not be described as the entire E1 protocol.

## APP-002 — E5 genuine somatic channel is synthetic

Preregistration requires a genuine interoceptive signal generated from Body
physiology. Current E5 creates a synthetic correlated signal in Lab.

**Required:** derive the true somatic signal from `Body.physiology` through an
actual `ReceptorPort` / body transduction path. Keep external correlated and
independent channels evaluator-owned.

## APP-003 — E2 does not yet exercise physical tool coupling

Preregistration describes body → physical effector → external object → sensory
consequence and a decoupling comparison. Current E2 generates channel deltas
directly from activation statistics.

**Required:** use a real `Body` effector consequence to drive the attached
tool, use a distinct detached remotely controllable external process, include
a decoupling phase, and measure whether inferred membership follows physical
integration rather than raw controllability.

## APP-004 — E4 reporting incomplete

E4 implements all eight phases, but preregistration also requires:
- prediction shock;
- causal revision latency;
- relearning latency;
- selective loss of old agency;
- return-to-Body-A reacquisition comparison.

Current output is phase means + revision counts only.

**Required:** add windowed pre/post error, revision/relearning latency and
return-A comparison before interpreting E4.

## APP-005 — E7 covers birth-state leakage but not transformed-offspring challenge

Current E7 strongly tests that learned parent state is absent at child birth.
Preregistration additionally requires offspring under:
- same environment;
- permuted ports;
- renamed apparatus IDs;
- different morphology;
- reversed environmental correlation.

**Required:** add post-birth transformed conditions and trace any inherited
performance advantage to genome/epigenome rather than learned payload.

## APP-006 — E8 covers port-label invariance only

Preregistration requires changing evaluator-side:
- body labels;
- port display names;
- resource names;
- hazard names;
- intervention condition names;
- world ID.

Current E8 changes body/port labels but not World/resource/hazard/condition
labels.

**Required:** add canonical clean-World paired-run invariance.

## APP-007 — campaign-wide integrity gates not yet centralized

The preregistration requires:
- clean World runtime boundary;
- no condition identifier into Symbiont;
- no schedule into germline;
- Observatory on/off equivalence;
- independent PRNG streams;
- bit-for-bit replay.

Individual studies implement pieces, but there is no single campaign gate.

**Required:** add a reusable integrity-gate harness and require its result in
every campaign report.

## APP-008 — CI currently unusable as execution evidence

GitHub Actions runs on the new commits terminate without usable steps/logs,
consistent with the repository's known Actions/billing limitation. Therefore
CI status must not be cited as scientific execution evidence.

**Required:** campaign result documents must distinguish:
- implementation committed;
- static/recomputed expectation;
- actual local/runner execution;
- frozen empirical result.

## Apparatus Definition of Done

Do not redesign AgencyModel / BodySchema until:
- APP-001 through APP-007 are resolved or explicitly scoped as separate
  mechanism-level pilots;
- E4/E2/E6/E7/E8 have actual runner outputs;
- result provenance includes commit SHA and seed ledger.

The purpose is to prevent apparatus weakness from being mistaken for subject
weakness.
