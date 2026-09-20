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


---

# Resolution status update

Baseline reviewed after apparatus remediation: `aa1a77b55fddd33da094d901bbd48e78cb1ad9aa`

| Finding | Status | Resolution |
|---|---|---|
| APP-001 | **RESOLVED IN CODE** | E1 now includes exact + jittered yoking, anti-causal and independent controls, yoke break, rejection latency and lead/lag metrics. |
| APP-002 | **RESOLVED IN CODE** | E5 genuine somatic signal now comes from real `BodyPhysiology` through physical `ReceptorPort` and `EmbodimentSession`. |
| APP-003 | **RESOLVED IN CODE** | E2 now uses a real Body effector, physically attached tool dynamics, detached controllable object, uncontrolled control and explicit decoupling phase. |
| APP-004 | **RESOLVED IN CODE** | E4 now reports prediction shock, first revision latency, recovery latency, causal mapping signatures and Body-A return reacquisition comparison. |
| APP-005 | **RESOLVED IN CODE** | E7 now tests birth-state isolation plus same/permuted/renamed/expanded-morphology/reversed offspring learning conditions. |
| APP-006 | **RESOLVED IN CODE / EXECUTION PENDING** | E8 now tests both physical port-label invariance and paired canonical clean Worlds with renamed world/resource/hazard identifiers. |
| APP-007 | **RESOLVED IN CODE** | Shared `run_embodiment_integrity_gates()` exists and `ExperimentRunner` attaches its result plus `scientifically_valid` to every `embodiment.*` run. |
| APP-008 | **OPEN INFRASTRUCTURE LIMITATION** | GitHub Actions currently terminates without usable execution logs/steps. CI must not be used as scientific run evidence until account/workflow infrastructure is restored. |

## New research findings discovered while resolving apparatus gaps

### P0-HEREDITY-EXPRESSION

The new `SymbiontGenome` / `GermlineState` were initially passed into the
canonical Symbiont but did not influence operative phenotype.

Resolution in code:

```text
genome + epigenome
  -> learning_rate
  -> SensorimotorModel.learning_rate

genome + epigenome
  -> exploration_rate
  -> motor exploration dynamics
```

The genome is authoritative when present; constructor parameters remain
fallbacks only for genome-less subjects.

### P0-ACQUIRED-EPIGENETICS

Still open by design:

`capture_acquired_variation()` has no legitimate endogenous lifetime source
because the current canonical phenotype does not yet self-regulate those
expressions during life.

This must not be "fixed" by injecting evaluator-derived fitness or World
semantics. A separate metaplastic regulatory design is required.

## Current interpretation rule

No E1-E8 result may be called empirically executed merely because:
- its implementation exists;
- static reasoning predicts an outcome;
- unit-test code exists;
- GitHub Actions displays a failed infrastructure run.

A result is empirical only after the declarative runner actually produces its
manifest/metrics for the frozen commit and preregistered seeds.
