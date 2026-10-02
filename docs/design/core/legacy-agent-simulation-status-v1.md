---
id: design.core.legacy-agent-simulation-status-v1
title: "Legacy Agent Simulation Status v1"
document_type: reference
domain: core
status: proposed
canonical: false
implementation_status: implemented
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
source_audit: research/audits/current/2026-10-02-current-state-architecture-audit.md
language: en
---

# Legacy Agent Simulation Status v1

## 1. Purpose

The repository contains an executable cognitive stack that predates the canonical
`OrganismRuntime`: `symbiont.core.cognition.agent.Agent` driven by
`symbiont.simulation.engine`. It assesses externally labelled host observations —
CPU, network, file changes, new processes, persistence changes — and reasons in
terms of threat, risk and curiosity. Issue #275 asks for one explicit
architectural status, a complete consumer inventory, and isolation from the
canonical organism.

Consumers were traced by import at `main@1c0c806b`.

## 2. Status

**Legacy-supported apparatus.**

- *Legacy*: it is not the modern epistemic model. Its inputs carry semantic
  labels, which the canonical organism is constitutionally forbidden to receive.
- *Supported*: it stays executable, because recorded studies and their registered
  protocols run on it.
- *Apparatus*: it is experimental machinery of those studies, not the organism.

It is not canonical, not superseded in the sense of having a drop-in replacement,
and not removable while its consumers remain.

The status is recorded in code as `symbiont.simulation.ARCHITECTURE`
(`"legacy-agent-simulation"`).

## 3. What the stack is

| Part | Location |
| --- | --- |
| Subject | `symbiont.core.cognition.agent.Agent` |
| Its cognition | `symbiont.core.cognition.{beliefs, curiosity, metacognition, reasoning}`, `AgentMemory` in `cognition.memory` |
| Its observation model | `symbiont.core.foundation.model` (`Observation`, `HostModel`, `Assessment`, `fingerprint`) |
| Its social evidence | `symbiont.core.social.ledger` (`SocialEvidenceLedger`, `SocialClaim`) |
| Engine, evaluation, metrics, snapshots | `symbiont.simulation.*` |
| Synthetic host events and regimes | `symbiont.environment.{world, regimes}` |

`symbiont.environment.rng` is shared infrastructure (namespaced seed derivation)
and is not part of the legacy stack.

## 4. Consumers

**Protocols** (`symbiont_lab.experiments.registry`), each declaring
`SUBJECT_ARCHITECTURE = "legacy-agent-simulation"`:

`simulate`, `attention.retrospective`, `attention.causal`,
`attention.replicated`, `evidence.second-look`, `evidence.replicated`,
`evidence.noise-sweep`, `evidence.causal-budget`, `heritage.stress`,
`heritage.replicated`, `heritage.longitudinal`, `heritage.ecological-shift`,
`learning.longitudinal-population-ecology`, `campaign.comparative`.

**Source modules that import it directly:**
`symbiont_lab.studies.attention.{causal, retrospective}`,
`symbiont_lab.studies.evidence.{causal_budget, second_look}`,
`symbiont_lab.studies.heritage.{ecological_shift, longitudinal, stress}`,
`symbiont_lab.studies.campaigns.comparative`,
`symbiont_lab.studies.longitudinal_population_ecology`,
`symbiont_lab.cli.{simulate, audit}`, `symbiont_lab.archive.runs`,
`symbiont_lab.workbench.runs`, `symbiont_lab.experiments.registry`.

**Source modules that reach it through another study:**
`symbiont_lab.studies.attention.replicated`,
`symbiont_lab.studies.evidence.{noise_sweep, replicated}`,
`symbiont_lab.studies.heritage.replicated`.

**Public re-exports:** `symbiont` (`run_simulation`, `SimulationConfig`,
`SimulationResult`, `SimulationSnapshot`, `EventContext`) and `symbiont.core`
(`Agent` and its cognition classes).

**Experiment directories:** `attention/causal-v0242-revalidation`,
`ecology/regime-shift-adaptation`, `evidence/causal-budget-v027`,
`evidence/second-look-sweep`, `heritage/cross-generational-stress`,
`heritage/ecological-shift-v1`, `learning/longitudinal-population-ecology`.

**Tests:** `tests/regression/audits/v021`, `tests/regression/audits/v024`,
`tests/unit/lab/test_archive.py`, `tests/unit/environment/test_drift.py`,
`tests/experimental_integrity/test_{shadow_sensor_isolation, same_seed_same_world,
experimental_integrity}.py`, `tests/integration/studies/test_evidence.py`.

## 5. Can its output enter the canonical organism?

No. No module under `symbiont.core.orchestration`, `symbiont.core.domains`,
`symbiont.core.embodiment`, `symbiont.modeling`, `symbiont.cognition`,
`symbiont.agency`, `symbiont.actuation`, `symbiont.genetics` or `symbiont.host`
imports any legacy module. The two architectures share no state, checkpoint
schema or ledger: ARCH-1 removed the core social ledger from the organism
runtime, leaving `core.social.ledger` as the model of this simulation only.

## 6. Contamination risks

| Risk | State |
| --- | --- |
| A canonical module starts importing a legacy module | Blocked by test |
| One study builds both a legacy population and a canonical organism and compares them as the same subject | Blocked by test |
| A legacy result is read as an organism result | Each protocol declares the architecture, recorded in the run manifest (with issue #273) |
| Semantic labels (CPU, threat, risk) leak into organism perception | Not possible through this stack: there is no path from it into `OrganismRuntime` |
| The names `Agent`, `symbiont.simulation` and `symbiont.core` exports suggest it is the organism | Open: the public re-exports remain (§8) |

## 7. Silent-failure review

`Agent.receive_communication` swallowed every exception while ingesting a claim.
It now tolerates only a malformed claim, counts it in `Agent.malformed_claims`,
and lets any other failure propagate.

`Agent.broadcast_claims` read its sender identity from `HostModel.host_id`, an
attribute that does not exist, so any agent with a channel attached failed on its
first broadcast. It now uses `agent_id`.

Both methods are unreachable in practice: nothing attaches a communication
channel to an `Agent`, and the population simulation does not call them. They
were corrected rather than removed because removal is a decision for §8.

`broadcast_claims` also catches `PermissionError` per target; that is the
documented refusal of an unauthorized recipient, not a swallowed failure.

## 8. Isolation and removal plan

Done here:

1. one recorded status (`ARCHITECTURE`);
2. every protocol on the stack declares it (`SUBJECT_ARCHITECTURE`). The
   experiment runner writes declared subject architectures to the run manifest;
   that recording is introduced with issue #273;
3. import isolation enforced in both directions.

Not done, and each is an owner decision:

1. **Drop the public re-exports** from `symbiont` and `symbiont.core`, so the
   legacy names stop reading as the organism's API. Mechanical, but it changes
   the import surface used by tests and scripts.
2. **Remove the unreachable communication methods** of `Agent` together with its
   channel, ledger and replay-guard fields.
3. **Move the stack out of the organism package** (to the Lab), in line with
   the placement rule of ADR-0060 (issue #280).
4. **Retire it.** Only after each study in §4 is closed or re-based on the
   canonical organism. Nothing is deleted while a consumer remains.

Tests: `tests/experimental_integrity/test_legacy_agent_isolation.py`.

## 9. Claims this document does not make

- that the studies built on this stack are invalid;
- that their results transfer to the canonical organism;
- that the stack should be removed.
