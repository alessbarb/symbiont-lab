# Canonical Organism Profile v1

- **Status:** Approved
- **Implementation:** Implemented — `v1` is canonical; every launcher starts from it
- **Decision:** [ADR-0062](../../adr/ADR-0062-results-condition-the-canonical-organism-profile.md)
- **Code:** `src/symbiont/core/organism_profile.py`
- **Gate:** `tests/experimental_integrity/test_canonical_organism_profile.py`

## 1. Purpose

A closed scientific result must condition how every organism is configured, in
every scope. Before this register, results were applied launcher by launcher, and
five effective configurations of the same organism coexisted (bare constructor,
resident/CLI, Physics3D, World, integrated habitat). This document is the single
register: one row per option, the value each profile version gives it, and the
result that backs the value.

The experiment determines the value. A value is never chosen so that an
experiment passes (Constitution, Golden Invariant); the two statements do not
conflict.

## 2. Rules

1. **One profile.** Every organism, in every scope, is born with `CANONICAL`.
   Governed constructor options have no default of their own: an option left
   unset comes from the profile.
2. **Versioned.** A profile version is immutable once an experiment has run under
   it. A result that moves a value creates a new version.
3. **Closed experiments keep their version.** Studies of closed experiments are
   bound explicitly to `v0-historical` (`profile=HISTORICAL_V0`), so their
   evidence stays reproducible. Nothing new uses that version.
4. **Deviations.** Only an arm of a study may deviate, and only as an
   intervention declared in its protocol. No launcher may deviate. The gate fails
   on any non-study module that sets a governed option without being declared;
   what remains declared is study-arm plumbing (§5).
5. **What may move a value.** Only a closed, preregistered, multi-seed
   confirmatory or held-out result. An exploratory or single-run result is a
   *candidate* and moves nothing.
6. **Every closure states its configuration consequence.** One of `adopt`,
   `reject`, `no change` (with reason), or `pending` (decided, sequenced behind
   named work). A result without a row in §4 is not closed.
7. **Restored organisms keep their own configuration.** A checkpoint records the
   profile version the organism was born with (`effective_config.profile_version`)
   and restore uses it; a checkpoint written before profiles existed is
   `v0-historical`. The profile applies to births. (Owner decision 2026-10-02.)
8. **The host is one sense source among others.** The organism's senses are the
   union of what its host, Body and other sources expose. Where the host cannot be
   read (any platform other than Linux today) the organism is still born, with
   the remaining sources, and `effective_config.host_sense_source` says
   `unavailable`. It is `embodied` when a Body supplies the sensory surface,
   `available` on a readable host and `not_requested` for an explicit study arm
   without discovery. (Owner decision 2026-10-02.)
9. **Superseded tests leave the canonical run.** A test asserting behavior that
   no longer applies moves to `tests/archive/` with
   `@pytest.mark.superseded(by=..., reason=...)`; pytest does not collect it. A
   test of a mechanism that still exists is migrated, not archived.

## 3. Options

| Option | `v0-historical` | `v1` (canonical) | Backing result | Scope and limits |
| --- | --- | --- | --- | --- |
| `discover_senses` | off | on | Decontamination P0–P2 | Host discovery is Linux only; rule 8 elsewhere |
| `bootstrap_semantic_senses` | on | off | Decontamination P0–P2: no semantic labels in cognition | Integrated-habitat cultural results under `on` are historical |
| `sensory_plasticity` | off | on | Sensory Plasticity v1, closed positive | Costs energy through retained structure (§6) |
| `auto_promote_predictors` | off | on | Predictive Structure Discovery v1, positive | Known limit: promotion does not wire the predictor's input edge |
| `interoception_mode` | `enabled` | `absent` | Interoception ablation, replicated negative: real ≈ sham, absent regulates better | Short horizon; a long-horizon study may reopen it |
| `factorized_effects` | off | off | Factorized Effect Representation v1 on hold after unstable footprint evidence | — |
| `reconcile_observed_effects` | on | on | **Unsupported**: C vs B gave 4 better, 1 equal, 3 worse | Needs a complete experiment; kept, not adopted |
| `executive_outcome_learning` | on | on | EOL v1.1, small gain | — |
| `footprint_satisfaction_rule` | `recall` | `recall` | E8 v3: rule AB rejected | — |
| `symbol_seed_policy` | `shared` | `per_organism` | Independent-Seed Symbol Grounding, negative: convergence was a shared-seed artifact | Seed derived from the organism's own identity, offspring included |
| `ancestry_training` | off | off | P5.1 owner decision 2026-09-29: ancestry from DEGRADED models | `pending` behind Promotion Stability |

Not governed by the profile: `actuation_enabled` depends on whether the Body has
actuators, not on a result. The autonomous training budget
(`48 + round(144 × pressure)` steps, ceiling 192) is a constant, already applied.

## 4. Configuration consequences of closed results

| Result | Consequence | State in code |
| --- | --- | --- |
| Sensory Plasticity v1 | adopt | Applied in every scope (`v1`) |
| Predictive Structure Discovery v1 | adopt | Applied in every scope (`v1`) |
| Interoception ablation (replicated) | adopt `absent` | Applied in every scope (`v1`) |
| Decontamination P0–P2 | adopt semantic off, discovery on | Applied in every scope (`v1`) |
| Independent-Seed Symbol Grounding | adopt per-organism seed | Applied (`v1`) |
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

## 5. Declared deviations

Only study-arm plumbing remains in the gate's `DECLARED_DEVIATIONS`:

- `experiments/runner.py` — a protocol's ablation block selects `factorized_effects`.
- `physics3d/cli.py` — `--factorized-effects` and `--ancestry-training`, used to run
  declared arms; off unless a protocol passes them.
- `physics3d/equivalence.py` — the causal-equivalence scenario that exercises
  factorized state.

## 6. Findings made while converging

Converging to `v1` exposed defects that only the plastic configuration reached.
Physics3D already ran that configuration, so these affected it before `v1`.

| Finding | Fix |
| --- | --- |
| Drift baselines of receptors whose source left the host were never released; under source churn they grew without bound and starved the organism | Released when every source of the receptor leaves the manifest; restarted if it returns |
| Sensory selection lost its last sample at restore, so the first tick after restore was a hidden cold start | Saved under the exact-continuation (replay) contract of deterministic hosts only |
| Memory consolidation rebuilt its own percept-to-source map and missed receptor-named percepts: attention 0 and default reliability, so fast salient traces could never form | Uses perception's map, which covers receptor names |
| Integrated habitat restored organisms on the real host instead of its deterministic surface | Restore uses the same empty surface as birth |

Decisions taken while converging (owner, 2026-10-02):

- **Reacclimation does not hold receptors.** The post-restore gate holds
  concepts and connections only. An organism restored into a new Body must be
  able to adapt its sensors at once. Under sensory plasticity the sensory system
  and the body schema are downstream of cognition and are part of the declared
  restart-sensitive surface.
- **Re-embodiment requirement.** An organism re-embodied in a new Body must
  learn to manage it sooner than a newborn. The re-embodiment functional transfer
  experiment is the acceptance test of this requirement; a negative result is a
  finding that the organism does not yet meet it, not a reason to change the
  experiment.

## 7. Metabolic prices: pending calibration

Sensory plasticity costs energy through retained structure: one drift baseline
costs 0.001 per tick and one cognitive node 0.0005. With stable senses the cost
is small (about 10 % of basal spend); at full sensory capacity (256 receptors)
retention alone would be 0.256 per tick against a basal spend of about 0.055.
No result backs these prices. They are `pending` a preregistered, multi-seed
calibration experiment over a grid of prices, measuring survival and learning,
with reduced retention during dormancy as one arm. Until then the prices do not
change, and `tests/experimental_integrity/test_metabolic_cost_coherence.py` keeps
the incoherence declared as a strict expected failure.
