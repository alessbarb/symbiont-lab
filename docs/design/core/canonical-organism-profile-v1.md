# Canonical Organism Profile v1

- **Status:** Approved
- **Implementation:** Partial — register, profile module and deviation gate exist; convergence to `v1` is the next step
- **Decision:** [ADR-0062](../../adr/ADR-0062-results-condition-the-canonical-organism-profile.md)
- **Code:** `src/symbiont/core/organism_profile.py`
- **Gate:** `tests/experimental_integrity/test_canonical_organism_profile.py`

## 1. Purpose

A closed scientific result must condition how every organism is configured, in
every scope. Before this register, results were applied launcher by launcher, and
five effective configurations of the same organism coexisted. This document is
the single register: one row per option, the value each profile version gives it,
and the result that backs the value.

The experiment determines the value. A value is never chosen so that an
experiment passes (Constitution, Golden Invariant); the two statements do not
conflict.

## 2. Rules

1. **One profile.** Every organism, in every scope, is born with `CANONICAL`.
2. **Versioned.** A profile version is immutable once an experiment has run under
   it. A result that moves a value creates a new version. A closed experiment
   stays bound to the version it ran under and remains reproducible.
3. **Deviations.** Only an arm of a study may deviate, and only as an
   intervention declared in its protocol. No launcher may deviate. The gate fails
   on any non-study module that sets a governed option without being listed.
4. **What may move a value.** Only a closed, preregistered, multi-seed
   confirmatory or held-out result. An exploratory or single-run result is
   recorded as a *candidate* and moves nothing.
5. **Every closure states its configuration consequence.** One of `adopt`,
   `reject`, `no change` (with reason), or `pending` (decided, sequenced behind
   named work). A result without a row in §4 is not closed.
6. **Restored organisms keep their own configuration.** A checkpoint carries its
   effective configuration; the profile applies to births. (Owner confirmation
   pending, question 13.)

## 3. Options

`v0-historical` is what the bare constructors produced before convergence.
`v1` is the owner-approved target (2026-10-02); it is not yet the code's
`CANONICAL`.

| Option | `v0-historical` | `v1` (approved) | Backing result | Scope and limits |
| --- | --- | --- | --- | --- |
| `discover_senses` | off | on | Decontamination P0–P2 | Linux only; other hosts need an owner decision (question 14) |
| `bootstrap_semantic_senses` | on | off | Decontamination P0–P2: no semantic labels in cognition | Integrated-habitat cultural results under `on` become historical |
| `sensory_plasticity` | off | on | Sensory Plasticity v1, closed positive | Within the regimes that study tested |
| `auto_promote_predictors` | off | on | Predictive Structure Discovery v1, positive | Known limit: promotion does not wire the predictor's input edge |
| `interoception_mode` | `enabled` | `absent` | Interoception ablation, replicated negative: real ≈ sham, absent regulates better | Short horizon; a long-horizon study may reopen it |
| `factorized_effects` | off | off | Factorized Effect Representation v1 on hold after unstable footprint evidence | — |
| `reconcile_observed_effects` | on | on | **Unsupported**: C vs B gave 4 better, 1 equal, 3 worse | Needs a complete experiment; kept, not adopted |
| `executive_outcome_learning` | on | on | EOL v1.1, small gain | — |
| `footprint_satisfaction_rule` | `recall` | `recall` | E8 v3: rule AB rejected | — |
| `symbol_seed_policy` | `shared` | `per_organism` | Independent-Seed Symbol Grounding, negative: convergence was a shared-seed artifact | Offspring derivation pending (question 15) |
| `ancestry_training` | off | off | P5.1 owner decision 2026-09-29: ancestry from DEGRADED models | `pending` behind Promotion Stability |

Not governed by the profile: `actuation_enabled` depends on whether the Body has
actuators, not on a result. The autonomous training budget
(`48 + round(144 × pressure)` steps, ceiling 192) is a constant, already applied.

## 4. Configuration consequences of closed results

| Result | Consequence | State in code |
| --- | --- | --- |
| Sensory Plasticity v1 | adopt | Physics3D only |
| Predictive Structure Discovery v1 | adopt | Physics3D only |
| Interoception ablation (replicated) | adopt `absent` | Physics3D, World, integrated habitat; not resident or base |
| Decontamination P0–P2 | adopt semantic off, discovery on | Resident and Physics3D; not base, World or integrated habitat |
| Independent-Seed Symbol Grounding | adopt per-organism seed | Not applied |
| Training budget 48 → 192 | adopt | Applied |
| Executive Outcome Learning v1.1 | adopt | Applied |
| E8 v3 (rule AB) | reject | Applied (`recall` kept) |
| Footprint Precision FP-0…FP-3 | no change — negative, membership unchanged | Applied |
| Binding Degradation BD-1 | no change — HIST not adopted | Applied |
| Factorized Effect Representation v1 | no change — on hold | Applied |
| Intent reconciliation C vs B | no change — inconclusive, needs complete experiment | On, unsupported |
| P5.1 ancestry from DEGRADED | pending behind Promotion Stability | Not applied |
| P5.1 promotion churn | pending — Promotion Stability paused | Not applied |
| E1, E3, E5 | pending — `AgencyModel` repair is Phase B | Not applied |

## 5. Current deviations

The gate's `DECLARED_DEVIATIONS` lists every non-study module that still sets a
governed option. Five families diverge today: bare constructor, resident/CLI,
Physics3D, World, integrated habitat. Convergence removes the entries one family
at a time until the list is empty.

## 6. Sequence

1. Register, profile module, gate — no behavior change (this step).
2. Introduce `v1`, make it `CANONICAL`, bind closed studies to `v0-historical`,
   remove deviations.
3. Re-embodiment functional transfer r6 runs on the canonical organism.
