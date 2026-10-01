# Symbiont Scientific Roadmap

> **Status:** canonical active research roadmap\
> **Scope:** Symbiont, Symbiont Lab, Physics3D, Observatory and Symbiont World\
> **Principle:** capabilities are accepted only when supported by reproducible evidence under an apparatus that does not supply the answer being tested.

This document defines the active scientific direction of Symbiont.

Completed milestone history belongs in
[`history/roadmap-log.md`](history/roadmap-log.md). Historical results remain
valid within the exact scope in which they were obtained; this roadmap does not
retroactively reinterpret a bounded result as evidence of broader
generalisation.

The sequence is capability- and evidence-driven rather than calendar-driven.

---

## 1. North star

Symbiont is an artificial-life research programme centred on a persistent
digital organism that acquires structure about itself and its environment
through experience rather than evaluator-provided semantics.

The long-term research question is not whether increasingly complex machinery
can be assembled around the organism. It is whether progressively richer
capabilities can be **acquired, retained, revised and generalised** while
preserving strict epistemic separation between:

- the organism;
- its physical substrate;
- the World;
- the experimental apparatus;
- and observer truth.

The active research sequence is:

> **Reliable apparatus → embodied causal agency → genotype-to-phenotype closure → developmental variation → out-of-distribution robustness → individual readiness → population and culture.**

This sequence deliberately does not contain an `AGI` milestone.

AGI, consciousness, intelligence, culture and Sim-to-Real are not acceptance
criteria. They may only be discussed as later interpretations of demonstrated,
falsifiable capabilities.

---

## 2. Permanent architectural invariants

These constraints remain in force regardless of future capability growth. The complete and canonical invariant set lives in [`governance/constitution.md`](governance/constitution.md); this roadmap summarizes only the constraints needed to explain the active research sequence.

### 2.1 Package and authority boundaries

- `symbiont` owns the organism.
- `symbiont_lab` owns apparatus, experiments, evaluation and orchestration.
- `symbiont_world` owns external environmental dynamics.
- Observatory is passive and owns no organism decision authority.
- `symbiont` must not import `symbiont_lab`, `symbiont_world` or Observatory.
- `symbiont_world` must not import organism cognition or Lab policy.
- Lab may connect organism and World, but evaluator truth must remain outside
  organism cognition.

### 2.2 Epistemic separation

The organism may receive physical or physiological consequences.

It must not receive:

- evaluator labels;
- object identities with supplied meaning;
- resource semantics;
- hazard semantics;
- world coordinates as privileged knowledge;
- causal ground truth;
- fitness scores;
- task rewards;
- human semantic categories;
- externally declared `body`, `tool`, `self`, `motor` or `environment` labels.

Observer truth may be used to measure a result. It may not become the mechanism
that produces that result.

### 2.3 No answer injection

A failed scientific gate must not be repaired by supplying the category that the
organism failed to discover.

For example, a failure to distinguish self-caused feedback from external
correlation cannot be repaired by adding:

```text
is_self_caused = true
source_type = motor
```

to cognition-visible state.

The remediation must introduce a generally defensible mechanism whose behaviour
is then challenged again.

### 2.4 Observation independence

Observation must not change the organism's causal future.

Observer projections, telemetry, UI rendering and scientific measurement are
apparatus functions.

Enabling or disabling them must not alter organism state, learning, action or
physical consequence except where an experiment explicitly studies observation
itself.

### 2.5 Re-embodiment continuity

A body is not the Symbiont.

Re-embodiment must preserve:

- organism identity;
- organism time;
- body-independent cognition;
- acquired causal structure;
- memories;
- model lineage;
- social knowledge;
- epistemic provenance.

Body-dependent knowledge may become uncertain or require revalidation.

It must not be silently erased.

### 2.6 Germline separation

Lifetime-acquired cognitive state must not silently cross reproduction.

The distinction between:

- genome;
- legitimate bounded epigenetic state;
- lifetime phenotype;
- acquired cognition;

must remain explicit and testable.

### 2.7 No hidden fitness optimisation

The Lab may measure viability, efficiency, survival, locomotion, learning or
reproduction.

Those measurements do not automatically become organism rewards.

### 2.8 Negative evidence is valid

A negative campaign is a successful experiment when its protocol and integrity
gates hold.

The project must never optimise its scientific protocols merely to turn a
negative result into a positive result.

---

## 3. Lifecycle semantics

The following concepts remain distinct.

- **birth** — creation of a new organism identity;
- **germinal / developing / mature** — organism developmental state;
- **active** — viable and executing its normal runtime;
- **stressed** — viable under significant physiological pressure;
- **dormant** — viable under reduced activity;
- **stopped** — process execution has stopped; this is not death;
- **restarted** — the same organism resumes from valid durable state;
- **re-embodied** — the same organism continues in a new physical body;
- **dying** — viability is failing but continuity has not yet closed;
- **dead / non-viable** — continuity of that organism identity is closed;
- **descendant** — a distinct organism created through reproduction.

A new body is not a new organism.

A descendant is not a continuation of the parent.

A dead identity is not normally resumable as though continuity never ended.

Normal restore rejects a `DEAD` identity. Reconstructing or cloning from historical artifacts, if later allowed experimentally, creates a new identity and is not resurrection.

Organism lifecycle, cognitive topology health and reproductive readiness remain separate state dimensions. For example, an organism may simultaneously be `MATURE`, `ADAPTIVE` and `REPRODUCTIVELY_READY`.

These lifecycle rules are adopted as permanent invariants in **Constitution §24**
under [ADR-0044](adr/ADR-0044-host-safety-and-lifecycle-invariants-in-the-constitution.md).

---

## 4. Merge and decision policy

GitHub Actions are not, by themselves, the project authority.

Scientific and architectural changes still require appropriate local or
structural evidence.

Before merging a material scientific change:

1. base/head drift must be checked;
2. known relevant regressions must not be ignored;
3. deterministic or metamorphic tests must cover new invariants;
4. ground truth boundaries must remain intact;
5. new resource use must remain bounded;
6. persistence and replay consequences must be understood;
7. claims must not exceed the evidence produced;
8. experiment changes must distinguish apparatus fixes from hypothesis changes;
9. privacy, consent and safety invariants accompany functional behavior;
10. the release documents the new organism capability;
11. lineage, death and reproduction changes are transactional and replay-testable;
12. ecological changes include aggregate carrying-capacity tests, not only per-organism limits;
13. dead-organism restore and population-over-capacity paths have explicit negative tests.

An explicit architectural decision is required before changes that:

- weaken evaluator/organism separation;
- introduce new semantic information into cognition;
- alter reproductive authority;
- create unbounded resource use;
- change lifecycle identity semantics;
- permit learned state to mutate hard kernel limits;
- expand real-host permissions;
- create new autonomous external actions.

The canonical and complete list of host-safety decision gates is
[`governance/decision-gates.md`](governance/decision-gates.md) § Host and safety.
The corresponding permanent host-safety invariants are adopted in **Constitution §23**
under [ADR-0044](adr/ADR-0044-host-safety-and-lifecycle-invariants-in-the-constitution.md).

---

## 5. Claim vocabulary

All scientific and technical claims must use explicit status language.

### 5.1 Implementation statuses

#### `NOT STARTED`

No accepted implementation exists.

#### `DESIGNED`

A reviewed specification exists but implementation is incomplete.

#### `PARTIAL`

Part of the mechanism or gate exists, but the declared acceptance condition has
not been closed.

#### `IMPLEMENTED`

The mechanism exists and its mechanical contracts pass.

This does not imply scientific validity.

---

### 5.2 Scientific statuses

#### `NOT ASSESSABLE`

The apparatus cannot yet evaluate the hypothesis under its preregistered
conditions.

#### `NEGATIVE`

The experiment was scientifically valid but did not support H1.

#### `POSITIVE — BOUNDED SCOPE`

The preregistered result supports H1 within the tested conditions.

No broader generalisation is implied.

#### `CLOSED — BOUNDED EXPERIMENTAL SCOPE`

A programme has completed its declared bounded scope.

Its generalisation status remains separate.

#### `GENERALISATION NOT ESTABLISHED`

Evidence exists under bounded conditions but has not survived the broader gates
required by this roadmap.

#### `REPLICATED`

The result has independently survived the declared replication conditions.

#### `OOD SUPPORTED`

The capability has survived preregistered out-of-distribution evaluation.

---

## 6. Evidence levels

Claims must indicate the strongest evidence level that supports them.

| Level | Evidence |
| --- | --- |
| 0 | Unit-level mechanical contract |
| 1 | Integration behaviour across subsystems |
| 2 | Experimental-integrity / non-interference evidence |
| 3 | Preregistered scientific campaign |
| 4 | Replication across declared seeds or equivalent conditions |
| 5 | Preregistered out-of-distribution replication |
| 6 | Cross-substrate or real-world replication |

A Level 3 result is not evidence of Level 5 generalisation.

A completed software implementation is not automatically scientific evidence.

---

## 7. Closed gate — Visual Acquisition D1-v2

Visual Acquisition D1-v2 closed on 2026-09-30 as a structural negative
(`not_assessable`). No candidate horizon met the preregistered minimum of eight
stable visual targets on every development seed. The complete result and run
provenance are recorded in
[`visual-acquisition-v1.md` §12](design/vision/visual-acquisition-v1.md).
No held-out run is authorized; visual acquisition remains undemonstrated. D1
will not be redesigned or have its thresholds relaxed. The roadmap proceeds to
Phase A (P0).

No new World, population, social or cognitive programme is opened by this
closure.

### 7.1 Purpose

D1-v2 asks a narrow question:

> Can Symbiont acquire stable predictive temporal structure over opaque visual
> receptors under an acquisition apparatus that remains physiologically viable
> long enough for the preregistered evaluation to become assessable?

It does not ask whether Symbiont “has vision”.

### 7.2 Development stage (completed)

Development uses only the declared development seeds.

Held-out seeds remain disabled; the development run is complete.

No predictive performance was inspected. Assessability was resolved as a
negative result: no candidate passed.

### 7.3 Assessability gate

For a candidate horizon `H`, all preregistered conditions must hold before any
performance calculation.

For each candidate horizon and every development seed, the preregistered §11 gate requires:

1. both arms reach the horizon without acquisition-guard termination;
2. arm A has at least 8 visual cognitive sense nodes at the start of the late window;
3. arm A has at least 8 visual targets predicted at **every tick of the whole window by the same predictor identity**;
4. visual predictor churn is recorded only as a descriptive diagnostic, with no threshold;
5. observer-density / Observer ON-OFF integrity remains causally neutral;
6. each arm stays within **90 minutes and 6 GB peak RSS**, and every per-target quantity used by the window is finite.

No predictive-performance quantity participates in horizon selection.

### 7.4 Metabolic support constraint

Acquisition support is allowed only as an apparatus-side viability mechanism.

It must:

- enter through ordinary untyped physical intake;
- depend on physiological reserve rather than task success;
- remain independent of organism action choice;
- provide no reward;
- modify no causal confidence;
- expose no resource semantics.

### 7.5 Stopping rule (triggered)

No preregistered `H` satisfied all assessability conditions:

> **D1-v2 closes as a structural negative. Visual acquisition remains not
> demonstrated. No further D1 redesign or threshold relaxation is opened. The
> roadmap proceeds to Phase A and then Phase B.**

`predictor-promotion-throughput-v1` remains unscheduled.

### 7.6 Held-out rule (not entered)

The development gate did not pass. No horizon was frozen, and no held-out
preregistration or authorisation exists for seeds `613`, `617` and `619`.

Passing assessability does not establish visual acquisition.

The held-out experiment must do that.

### 7.7 Pre-existing research lines during the transition

Before its closure, D1-v2 was the only active **capability** programme allowed
to advance ahead of Phase A. It is now closed. Pre-existing observational work
may only finish and freeze already-approved design data:

- **Promotion Stability v1 D1** — design data complete; confirmation and P5.2 are paused until P0/P1 close.
- **Agency Acquisition & Executive Action v1** — FROZEN; existing mechanism becomes subject to the Phase B falsification battery.
- **Executive Outcome Learning v1/v1.1** — FROZEN; bounded evidence retained, further mechanism work deferred to Phase B.
- **Private Model Learnability v1 / P6** — CLOSED — BOUNDED EXPERIMENTAL SCOPE; further scaling is paused.
- **Predictor Promotion Throughput v1** — UNSCHEDULED.

No follow-up implementation, confirmation programme or new cognitive line is opened merely because an older programme exists.

---

## 8. Phase A — Scientific infrastructure and reproducibility

No new major cognitive remediation begins until Phase A is closed to the level
required below.

---

### A1 — Durable persistence

**Status:** IMPLEMENTED, integrity gate closed.

The fault-injection matrix covers pre-write, partial-write, file-fsync,
replace and directory-fsync boundaries for both direct durable writes and
compound atomic replacements. The branch validation executed the complete
unit/integration suite through 2,719 passing tests; its sole software-test
failure was the unrelated pre-existing Physics3D equivalence test attempting
to run without the optional PyBullet dependency. No A1 fault-injection test
failed.

The durable-write implementation already provides:

```text
write temporary
→ flush
→ fsync temporary
→ replace target
→ fsync parent directory
```

and compound temporary replacements fsync their payload before replacement.

#### Remaining work

Add systematic power-loss/fault-injection coverage at each meaningful boundary:

```text
before write
during write
before file fsync
after file fsync
before replace
after replace
before directory fsync
during directory fsync
```

#### A1 acceptance

A simulated failure may leave:

- the complete previous state; or
- the complete new state.

It must never produce an accepted partial generation.

---

### A2 — Hermetic execution and provenance

**Status:** COMPLETE.

`ExecutionFingerprint` now represents the declared checkout, interpreter,
module origins, dependency-lock digest, effective-configuration digest,
experiment identifier and seed, and can reject a mismatching child identity.
`agentctl run start` now accepts only direct Python script/module/code entry points
using the launcher's interpreter, captures expected identity from the pinned worktree,
and executes the target
through a child bootstrap that rejects identity mismatches before study code runs.
The launcher receipt includes the declared fingerprint. The CLI requires an explicit
seed; the run ID is the default experiment identifier. Launcher-level tests exercise
all three entry-point forms, invalid-command rejection before preflight, mismatch
rejection before target execution and complete receipt provenance. This is an
enforced launcher path, not a guarantee for Python processes spawned later by the
study itself.

#### Required fingerprint

Every scientific execution must record at least:

```text
git commit
dirty state
repository root
Python executable
Python environment prefix (`sys.prefix` and `sys.base_prefix`)
Python version
symbiont module origin
symbiont_lab module origin
dependency lock hash
effective configuration hash
experiment identifier
seed
```

#### Child-process self-verification

A spawned experiment process must verify that its:

- interpreter;
- imported source;
- dependency environment;
- commit identity;

match the declared execution environment.

Merely prepending a checkout to `PYTHONPATH` is not sufficient evidence of
hermetic execution.

---

### A3 — Dependency locking

**Status:** COMPLETE — the launcher synchronizes isolated locked environments, and
ADR-0051's applicable POSIX acceptance evidence passes. Windows process-tree timeout
behavior remains explicitly unverified and is not claimed as validated.

The repository now has a canonical `uv.lock` and a pinned scientific Python
baseline in `.python-version`. Each governed scientific run creates its own
environment from the pinned worktree using `uv sync --locked --no-dev`. Optional
`modeling` and `physics3d` extras are opt-in; the compatibility environment is not
modified. The child fingerprint and execution receipt identify the isolated
interpreter and locked dependency digest.

Scientific campaigns require a reproducible dependency set.

Two separate lanes remain valid:

#### Scientific lane

Exact locked dependencies for:

- experiments;
- benchmarks;
- historical reproduction;
- scientific comparison.

#### Compatibility lane

Controlled testing against newer supported dependencies.

Compatibility testing must not silently replace the scientific locked
environment.

---

### A4 — Generational scientific commits

**Status:** PARTIAL.

An isolated transactional `GenerationStore` now implements immutable
`generation-N` directories, a digest-bearing `COMPLETE` seal and atomic
`CURRENT` publication with crash-boundary tests. It is deliberately not yet
wired into the active scientific launcher or D1-v2. A4 closes only after the
governed run/checkpoint path consumes this store and recovery tests cover that
integration.

Atomic files are insufficient when one scientific state consists of multiple
files.

A run or checkpoint generation must become visible as one committed generation.

Target pattern:

```text
run/
  generation-000042/
    checkpoint
    manifest
    provenance
    model-artifacts
    telemetry-index
    COMPLETE

CURRENT -> generation-000042
```

Consumers must only open committed generations.

#### A4 acceptance

Crash injection must leave either generation `N` or generation `N+1`
fully valid.

Mixed generations are invalid.

---

### A8 — Label and apparatus invariance / E8 remediation

**Status:** P0 COMPLETE — governed confirmation campaign passed; evidence
publication remains subject to external review.

E8 is an experimental-integrity failure and therefore belongs in Phase A before
the causal programme.

#### Existing result

The historical E8 label-invariance campaign failed across its ten seeds.

The historical World arm failed.

In that historical run, renaming evaluator-side resource or hazard identifiers
changed the subject trace.

Therefore label invariance was not established by that historical campaign.

The prior `APP-006: execution pending` status is superseded by the governed
confirmation result recorded below.

#### Remediation state

The reviewed implementation candidate derives receptor-transfer geometry from
apparatus-assigned source ordinals and hazard RNG namespaces from hazard slots,
not evaluator-facing labels. Focused development tests require E8 invariance
and deterministic replay. The governed confirmation campaign was run after the
candidate merged to `main`, using the unchanged preregistered ten-seed set and
300-step horizon. All ten results report `invariant_rate = 1.0`,
`integrity_pass = true`, and deterministic replay. Receipts, per-seed results,
and validated aggregation are preserved under
`experiments/embodiment/label-invariance-governed-20261001-0a901ea/`.

#### Identified contamination

World currently allows nominal identifiers to influence physical experience.

Examples include:

```text
hazard RNG namespace
    <- hazard_id

receptor transfer geometry
    <- source_id
```

Consequently:

```text
rename observer label
→ different RNG / transfer response
→ different physical experience
→ different organism trace
```

This is not necessarily cognition reading a human label.

It is nevertheless an experimental-integrity violation because the two E8 arms
are no longer physically equivalent.

#### Required architectural separation

World must distinguish:

```text
physical identity / structural slot
```

from:

```text
observer / evaluator label
```

No identifier that E8 is allowed to rename may alter:

- RNG streams;
- receptor transfer coefficients;
- collision mechanics;
- energetic consequences;
- hazard probabilities;
- resource dynamics;
- physical topology.

Physical stochastic identity must derive from stable structural coordinates,
canonical ordinals or another explicitly constitutional identifier that is not
the evaluator-facing name under test.

#### E8 acceptance

The governed confirmation campaign passed on candidate
`0a901ea273ac8cbcf8c165419e9120033f09c1f0`. The campaign record is bounded to
the preregistered protocol and seed set; external review of its scientific
evidence remains a publication requirement.

The preregistered acceptance criteria are:

1. preserve the existing preregistered E8 protocol;
2. do not change its success threshold;
3. rerun all ten seeds;
4. require `invariant_rate = 1.0`;
5. require deterministic replay.

If E8 still fails after nominal identifiers are physically inert, investigate
the remaining divergence as a deeper contamination finding.

#### E1 reporting inconsistency

The archived E1 report and `results.json` contain slightly different
false-positive summaries: mean FPR 0.3333 in the report, 0.30 in
`results.json`.

The cause is known. The report (`ce5c8190`) describes the earlier run with
three controls (exact yoke, anti-causal, independent), so the FPR is 1/3 per
seed. The archived run follows the APP-001 apparatus revision and adds a
jittered-yoke control, so the FPR is 0.25 or 0.50 per seed and the mean is
0.30. `results.json` is canonical.

Both fail the preregistered gate, so the scientific interpretation does not
change.

The discrepancy must nevertheless be reconciled as a provenance/reporting
issue. The canonical report should be mechanically derived from or explicitly
linked to the exact result artefact it summarises.

### A9 — Maintainable experimental core and apparatus

**Status:** IN PROGRESS — baseline recorded and two bounded apparatus
extractions validated; further seam mapping remains.

Clean future experiments depend on components that can be inspected, tested, and
changed without obscuring scientific behavior or weakening provenance. This work
covers the experimental organism (`src/symbiont`), laboratory apparatus and
Workbench (`src/symbiont_lab`), physical/ecological world (`src/symbiont_world`),
and the test suite. Observatory is explicitly excluded.

This is an enabling engineering gate, not authorization for broad rewrites. The
initial source-size, test-layout, boundary and artifact inventory, along with
the source-to-test mappings for the bounded telemetry worker and monitor
geometry extractions, is recorded in the [A9 maintainability baseline](development/maintainability-baseline.md).
Before each further extraction, map its public interfaces, callers, test
ownership, and scientific/state invariants. Prioritize changes that make
experimental behavior easier to isolate and verify; file length alone is not
evidence that a module needs decomposition.

#### Deferred design to revisit

- [Passive Runtime Audit Trace v1](design/observability/passive-runtime-audit-trace-v1.md)
  is tracked as **Proposed / Not started** in the canonical
  [Design Status Register](design/register.md). Revisit it after the A9
  baseline inventory to determine whether its bounded, passive recorder fits
  A9 scope. This reference does not change A9 status or priority, authorize
  runtime changes, or add scientific acceptance criteria. Any change to
  organism behavior, factual authority, or scientific protocol requires its
  own owner and governance review.

#### A9 acceptance

- Record a reproducible baseline for the in-scope code and verify reported
  hotspots and cleanup claims against the checkout.
- For each proposed extraction, identify the owned responsibility, callers,
  public compatibility surface, and focused tests before changing structure.
- Make structural changes in small, behavior-preserving slices with regression
  evidence; do not change scientific mechanisms, random-number consumption,
  ordering, checkpoint/schema semantics, provenance, or authority boundaries.
- Move tests or consolidate modules only where ownership and import/reference
  evidence support the change; preserve dependency direction and keep Observatory
  out of scope.
- Report focused and full-suite validation separately. A9 completion does not
  itself close apparatus-equivalence or scientific acceptance gates.

---

## 9. Phase A (P1) — Apparatus equivalence and numerical stability

This block follows A1–A4 and E8 and precedes the causal remediation programme.

---

### A5 — Observation independence

**Status:** PARTIAL.

Observer OFF/ON equivalence infrastructure already exists.

The final contract must explicitly cover the current canonical organism path.

#### Required equality

Observer state changes must not alter:

- organism state hash;
- motor intents;
- delivered actions;
- causal provenance;
- competence state;
- model lifecycle;
- learning transitions;
- physical consequences.

#### Profiling

Performance profiling must separately measure:

```text
causal runtime
observer projections
serialization
memory copies
queueing
IPC
disk I/O
UI rendering
```

No technology migration is justified solely by aggregate timing.

---

### A6 — Equivalence harness

**Status:** PARTIAL.

Any performance or infrastructure refactor must pass a shared causal
equivalence harness.

This applies to changes in:

- `physics3d_monitor`;
- telemetry;
- queues;
- serialization;
- multiprocessing;
- shared memory;
- native extensions;
- Rust or other implementation-language changes.

#### Per-tick comparison

Where applicable:

```text
organism-state digest
motor output
physical consequence
causal provenance
learning transition
model lifecycle
observer projection
```

A faster system that changes the experiment is not an optimisation.

---

### A7 — Numerical and mechanical stability

**Status:** NOT YET AUDITED AS A COMPLETE GATE.

The objective is reproducible experimental mechanics, not universal bit-exact
physics.

The project must define and test explicit numerical tolerances.

#### Detect

- NaN;
- Infinity;
- invalid transforms;
- contact explosions;
- velocity explosions;
- unstable joints;
- non-finite energy;
- inconsistent checkpoint/restore state.

#### Canonical stress campaigns

Each canonical body should be exercised under:

```text
idle stability
actuation stress
collision stress
checkpoint/restore
re-embodiment
friction perturbation
mass perturbation
```

---

## 10. Phase B — Embodied causal agency

Phase B becomes the central scientific programme after Phase A.

The current evidence does not indicate one isolated bug.

It indicates a family of related failures in causal agency.

---

## 11. Existing embodiment falsification battery

All eight campaigns have already been executed and archived with ten seeds each.

These results are inputs to Phase B, not tasks waiting to be run for the first
time.

| Study | Roadmap role | Current result |
| --- | --- | --- |
| E1 — Yoked External Causation | B3 | H1 not supported |
| E2 — Tool / Body Distinction | B6 | H1 not supported |
| E3 — Temporal Causality | B2 | H1 not supported |
| E4 — Causal Revision | B5 | H1 not supported |
| E5 — Somatic Correlation Trap | B1 | H1 not supported |
| E6 — Hidden Common Cause | B4 | H1 not supported |
| E7 — Heredity Leakage | C1 | no learned-state leakage observed |
| E8 — Label Invariance | Phase A integrity | governed confirmation passed; see A8 evidence record |

E1–E6 therefore form a **unified falsification battery** for the next agency
architecture.

---

## 12. B0 — General causal-agency model and its components

**Status:** NOT STARTED.

B0 must not be designed to make one failed study pass.

It must define one coherent acquisition and revision mechanism capable of being
challenged by E1–E6 simultaneously.

The target is not a semantic concept named “agency”.

The target is a mechanism capable of developing distinctions from experience
that are consistent with:

```text
correlation
→ temporal contingency
→ action-conditioned predictability
→ intervention
→ controllability / modulation
→ delayed consequences
→ confound detection
→ contradiction
→ causal revision
```

None of these evaluator concepts need to be represented by the same names
inside the organism.

---

### B0 design rule

No special-case code may ask:

```text
if running_e3:
if signal_is_external:
if source_is_tool:
if hidden_common_cause:
```

The mechanism must be general.

---

### B0 acceptance rule

A candidate B0 is evaluated against the complete E1–E6 battery.

Success in one study is insufficient.

Regressions between studies are first-class results.

For example:

```text
E3 improves
but E5 worsens
```

is not closure.

---

### B1 — Somatic Correlation Trap / E5

Current result:

> H1 not supported.

The organism detects genuine somatic correlation but also assimilates matched
external correlation.

#### B1 research target

Develop experience-derived evidence that separates:

```text
predictable because correlated
```

from:

```text
predictable because my intervention changes it
```

Candidate mechanism classes may include:

- intervention history;
- action-conditioned prediction;
- effect modulation;
- cancellation evidence;
- counterfactual discrepancy;
- confidence revision.

No motor/environment labels may enter cognition.

---

### B2 — Temporal Causality / E3

Current result:

> H1 not supported.

Immediate consequences are detected; delayed and variable-delay consequences
are not reliably attributed.

#### B2 research target

Introduce temporally extended causal eligibility without introducing reward
learning or evaluator labels.

Relevant mechanisms may include:

- bounded eligibility traces;
- temporally distributed causal candidates;
- evidence accumulation over repeated intervention;
- uncertainty over delay;
- competing explanations;
- contradiction-driven decay.

Longer memory alone is not sufficient.

---

### B3 — Yoked External Causation / E1

Current result:

> H1 not supported.

E1 is not future work to be newly invented.

It becomes a permanent challenge for B0.

#### B3 research question

Can the organism distinguish:

```text
B usually follows my action
```

from:

```text
my action causally influences B
```

when external apparatus creates a matched temporal relationship?

---

### B4 — Hidden Common Cause / E6

Current result:

> H1 not supported.

The current mechanism confuses shared-cause correlation with direct causal
relation.

#### B4 research challenge

For:

```text
Z -> A
Z -> B
```

the organism must not automatically infer:

```text
A -> B
```

solely from observed association.

Again, the latent variable `Z` remains evaluator truth.

The organism must infer uncertainty from experience rather than receive the
causal graph.

---

### B5 — Causal Revision / E4

Current result:

> H1 not supported.

Current evidence shows inadequate revision under permutation, break and
transplant conditions.

#### B5 required capability

The organism must be able to:

```text
form relation
→ accumulate support
→ encounter contradiction
→ reduce confidence
→ deactivate or replace relation
```

without an evaluator declaring which old belief is wrong.

Revision is a required part of learning.

---

### B6 — Tool / Body Distinction / E2

Current result:

> H1 not supported.

A remotely controllable object can currently be assimilated as body.

#### B6 research target

Body membership must become an acquired, revisable hypothesis rather than a
static correlation threshold.

Relevant experience may include:

- controllability;
- latency;
- persistence;
- coupling stability;
- sensory continuity;
- loss and reconnection;
- dependence on intervening external dynamics.

The organism must not be given a `tool` label.

---

Sections 13–18 are intentionally unused: B1–B6 are components of B0 and are
listed under §12. Later section numbers are kept stable because other documents
and tests cite them.

---

## 19. Phase C — Genotype to phenotype to physical consequence

Phase C verifies that heredity is not merely a serialisation mechanism.

---

### C1 — E7 heredity regression

**Status:** POSITIVE — BOUNDED SCOPE.

The existing E7 campaign found no transfer of acquired:

- agency state;
- body schema;
- perceptual state;
- sensorimotor state.

Its preregistered no-leak gate passed across its tested seeds.

This is evidence, not an eternal guarantee.

E7 remains a permanent regression requirement for changes affecting:

- genome;
- germline;
- epigenetics;
- reproduction;
- phenotype construction.

---

### C2 — Full causal expression chain

A genetic difference should be able to produce:

```text
genotype difference
    ↓
expression difference
    ↓
phenotype difference
    ↓
physical consequence
    ↓
different experienced evidence
```

A stored genetic field that never affects the organism is not meaningful
heredity.

---

### C3 — Controlled genetic intervention

Evaluate paired organisms under:

```text
same environment
same causal schedule
same seed policy
same initial conditions
one declared genetic difference
```

and measure resulting differences in:

- learning dynamics;
- physiology;
- mechanics;
- perception;
- development.

---

### C4 — No evaluator fitness injection

The Lab may measure viability and consequence.

It may not turn those measurements into hidden organism reward merely to make
evolution efficient.

---

## 20. Phase D — Developmental morphogenesis

The next heredity step is not arbitrary body mutation.

It is a developmental mapping from inherited constitution to physical
morphology.

---

### M1 — Development as physical law

Target:

```text
genome
→ developmental process
→ morphology
```

not:

```text
genome
→ human quality filter
→ approved body
```

---

### M2 — Invalid representation vs. non-viable organism

The apparatus may reject only structures that cannot be represented coherently,
for example:

- non-finite masses;
- impossible joint references;
- invalid dimensions;
- broken topologies;
- numerically undefined constraints.

A physically representable organism may still be:

- inefficient;
- asymmetric;
- fragile;
- immobile;
- metabolically expensive;
- reproductively unsuccessful;
- non-surviving.

Those are legitimate outcomes.

---

### M3 — No morphology fitness filter

No rule may reject a body simply because it appears mechanically poor or unlike
a desired morphology.

Physics and physiology determine consequence.

### M4 — Marginal morphology campaign

Developmental studies must deliberately include physically representable phenotypes
that are marginal, unstable, inefficient, malformed or non-surviving. The Lab may
reject simulator-unrepresentable states, but it must not silently filter difficult
phenotypes out of the scientific population.

The campaign reports consequence rather than assigning human quality: viability,
mechanical stability, metabolic cost, sensory reach, developmental persistence and
failure mode are evaluator measurements, not organism reward.

---

## 21. Phase E — Out-of-distribution robustness

Sim-to-Real is not an active claim.

The immediate target is whether acquired cognition survives controlled mismatch
inside simulation.

---

### O1 — Sensor perturbation

Evaluate:

- bias;
- drift;
- latency;
- jitter;
- dropout;
- quantisation;
- saturation;
- degradation.

---

#### O2 — Actuator perturbation

Evaluate:

- latency;
- reduced authority;
- nonlinearity;
- dead zones;
- backlash-like effects;
- partial failure.

---

#### O3 — Physics-domain variation

Vary:

- friction;
- mass;
- damping;
- contact properties;
- surface compliance;
- gravity within declared experimental ranges.

---

#### O4 — Unseen environments

Test environments whose:

- geometry;
- obstacle layout;
- surface properties;
- sensory statistics;
- resource distribution;
- physical conditions;

were not used during mechanism development.

---

#### O5 — Re-embodiment robustness

A mature Symbiont must be evaluated across:

```text
same body type
modified instance
different morphology
partially degraded body
```

while preserving organism identity and body-independent cognition.

#### Desired response to mismatch

Not:

```text
body changed
→ erase knowledge
```

but:

```text
body changed
→ detect inconsistency
→ increase uncertainty
→ revalidate body-specific relations
→ retain general knowledge
```

### O6 — OOD exit gate

Phase E closes only if the organism can, under preregistered moderate distribution
shift:

```text
detect mismatch
-> increase uncertainty where prior assumptions no longer fit
-> reacquire/relearn from experience
-> recover useful prediction/control
-> avoid treating stale beliefs as certain
```

Passing requires bounded degradation, explicit uncertainty response and recovery across
the declared sensor, actuator, physics, environment and re-embodiment shift classes.
A reset that merely erases the conflicting knowledge does not satisfy this gate.

---

## 22. Individual Readiness Gate

Population research may become active again only when an individual satisfies
the declared readiness criteria.

The gate must be based on evidence, not development chronology.

Required dimensions:

### Causal self/world discrimination

The individual reliably reduces externally induced causal false positives.

### Delayed attribution

Delayed physical consequences can be acquired under the accepted causal model.

### Hidden-cause robustness

Strong correlation alone is insufficient for direct causal commitment.

### Causal revision

Contradicted relations are weakened or replaced.

### Tool/body revision

Controllability alone is insufficient for permanent body membership.

### Persistent acquired structure

Body-independent acquired knowledge survives appropriate checkpoint and
re-embodiment boundaries.

### Re-embodiment continuity

Changing body does not reset the organism.

### Reacclimation

Body-specific prior knowledge becomes uncertain when appropriate and is updated
through experience.

The existing `experiments/embodiment/reembodiment-reacclimation-v1/` A-B-A study is
retained as bounded evidence and as a regression anchor; it does not by itself establish
general OOD re-embodiment robustness.

### Epistemic invariance

Nominal relabeling and other semantically irrelevant apparatus transformations
do not change the organism's physical experience or acquired trace.

### Moderate OOD robustness

The organism detects and adapts to bounded mismatch rather than blindly applying
stale certainty.

Only after this gate is supported may Phase F become an active capability
programme.

---

## 23. Symbiont World status before Individual Readiness

Until the readiness gate passes:

> **Symbiont World is maintenance / experimental substrate only.**

Allowed work:

- bug fixes;
- reproducibility fixes;
- deterministic replay fixes;
- E8 integrity remediation;
- completion of already preregistered experiments;
- apparatus maintenance required by Phases A-E.

Not opened:

- new population capabilities;
- new ecological complexity for its own sake;
- new social mechanisms;
- new cultural mechanisms;
- new emergent-society claims.

World is not deprecated.

It is temporarily prevented from driving the research agenda ahead of the
individual organism's demonstrated capabilities.

---

## 24. Existing cultural and grounding lines

The following historical programmes remain valid in their exact preregistered
scope:

- Cultural Foundation v1;
- Cumulative Culture v1;
- Autonomous Cultural Agency v1;
- Emergent Symbol Grounding v1.

Their canonical status is:

```text
CLOSED — BOUNDED EXPERIMENTAL SCOPE
GENERALISATION NOT ESTABLISHED
```

Their historical evidence is not deleted or downgraded.

The roadmap changes only the scope of the claims that may currently be made.

They do **not** yet establish:

- general social cognition;
- open-ended cultural evolution;
- robust symbol grounding across environments;
- population-level intelligence;
- autonomous society;
- language;
- general communication competence.

Those broader questions reopen only after Individual Readiness.

---

## 25. Phase F — Population, communication and culture

Phase F is inactive until Individual Readiness is met.

---

### F1 — Multiple individuals

Study bounded coexistence involving:

- competition;
- cooperation;
- local social observation;
- resource interaction;
- social learning.

---

### F2 — Emergent specialisation

Roles must not be preassigned.

The evaluator may later describe functional differentiation.

The organism must not receive role labels.

---

### F3 — Communication without semantics

Communication channels may have:

- finite bandwidth;
- energetic or computational cost;
- production;
- reception;
- local transport.

They may not ship predefined human meanings.

Allowed:

```text
opaque signal 17
```

Not allowed:

```text
signal 17 = danger
```

---

### F4 — Grounding

A signal is considered grounded only when organism-side behaviour demonstrates
an acquired relation between that signal and experienced consequences.

Grounding claims must survive at least:

- symbol permutation;
- identifier renaming;
- changed context;
- changed sender;
- changed receiver;
- controlled meaning drift.

---

### F5 — Social epistemology

Investigate acquisition of:

- source reliability;
- contradiction;
- corroboration;
- independence;
- trust revision;
- misinformation resistance.

No evaluator reliability score enters the organism.

---

### F6 — Cultural transmission

A stronger cultural claim requires evidence for:

```text
knowledge acquired during lifetime
→ transmitted socially
→ acquired by another organism
→ retained without genetic encoding
→ affects later behaviour
```

---

### F7 — Negative cultural result

If communication or culture does not emerge without semantic scaffolding, that
is a valid result.

The canonical scientific line will not inject a human-designed language merely
to satisfy a cultural milestone.

A separate explicitly scaffolded comparison may exist as a control, but it must
never be confused with spontaneous emergence.

---

## 26. Permanent decontamination programme

Epistemic isolation is never considered permanently “finished”.

Every major capability should be challenged with semantically irrelevant
transformations where applicable.

Examples:

```text
identifier renaming
port permutation
channel reordering
observer-label changes
apparatus relabeling
equivalent morphology remapping
observer enabled / disabled
alternative apparatus implementation
```

A transformation that preserves physical experience should not alter acquired
knowledge merely because its metadata changed.

Verification should combine:

- AST/dependency boundaries;
- runtime contracts;
- metamorphic tests;
- paired experiments;
- causal equivalence;
- provenance inspection.

The project does not claim mathematical proof that no conceivable side channel
exists.

It claims only the bounded invariance classes that have actually been tested.

---

## 27. Scientific metrics

No single “intelligence score” is canonical.

Metrics remain capability-specific.

### Causal agency

- causal true-positive rate;
- causal false-positive rate;
- delayed attribution;
- confidence calibration;
- revision latency;
- contradiction sensitivity.

### Body acquisition

- genuine somatic assimilation;
- external false assimilation;
- boundary uncertainty;
- reacclimation time;
- tool/body revision.

### Genetics

- genotype-expression consistency;
- phenotype divergence;
- inherited-state isolation;
- mutation consequence;
- epigenetic provenance.

### OOD

- degradation under shift;
- uncertainty response;
- recovery time;
- stale-belief persistence;
- transfer across bodies/environments.

### Social

- signal use;
- behavioural dependency;
- cross-individual acquisition;
- source calibration;
- persistence of non-genetic knowledge.

---

## 28. Operational priority order

The current execution order is:

```text
P0 — SCIENTIFIC INFRASTRUCTURE
A1 fault-injection durability gate
A2 hermetic execution fingerprint
A3 dependency lock
A4 generational scientific commits
A8 E8 label/physical invariance
A9 maintainable experimental core and apparatus
    ↓

P1 — APPARATUS VALIDITY
A5 observation independence
A6 equivalence harness
A7 numerical/mechanical stability
    ↓

P2 — EMBODIED CAUSAL AGENCY
B0 general causal-agency model
E1–E6 unified falsification battery
    ↓

P3 — GENETIC CAUSAL CLOSURE
C1–C4
    ↓

P4 — DEVELOPMENTAL MORPHOGENESIS
M1–M4
    ↓

P5 — OOD ROBUSTNESS
O1–O6
    ↓

INDIVIDUAL READINESS GATE
    ↓

P6 — POPULATION / COMMUNICATION / CULTURE
F1–F7
```

---

## 29. Explicitly out of scope for the current roadmap

The following are not current objectives:

- rewriting Physics3D in fixed-point arithmetic merely for determinism;
- rewriting `physics3d_monitor` in Rust without profiling evidence;
- adopting SDIF merely because telemetry is expensive;
- introducing a global reward;
- introducing evaluator fitness into cognition;
- adding semantic motor/environment masks;
- giving communication predefined meanings;
- resetting cognition on re-embodiment;
- using population complexity to hide unresolved individual causal failures;
- declaring AGI as a development milestone;
- claiming Sim-to-Real before OOD and later cross-substrate evidence exists;
- reopening failed experiments repeatedly until they become positive.

---

## 30. Roadmap success criterion

The roadmap succeeds if Symbiont Lab can produce trustworthy answers to
questions such as:

- Can an organism distinguish causal influence from correlation?
- Can it attribute delayed consequences?
- Can it reject hidden-common-cause confounds?
- Can it revise a previously useful but now false causal relation?
- Can it distinguish body membership from remote controllability?
- Can it preserve itself across re-embodiment?
- Can it recognise when body-specific knowledge is stale?
- Can inherited differences produce real physical consequences?
- Can it adapt under conditions not used during mechanism development?
- Can knowledge pass between organisms without evaluator semantics?
- Can non-genetic knowledge persist socially?

Each answer must be:

```text
bounded
reproducible
auditable
falsifiable
provenance-preserving
```

---

## 31. Final research principle

Symbiont should not progress by accumulating features faster than it can justify
them.

The governing sequence is:

```text
reliable measurement
    ↓
clean experimental boundary
    ↓
falsifiable mechanism
    ↓
negative or positive evidence
    ↓
replication
    ↓
generalisation challenge
    ↓
only then broader capability
```

The strongest property of Symbiont Lab is not that it can produce increasingly
complex simulated behaviour.

It is that it can be made capable of proving when its own hypotheses are wrong.

That property is the foundation of the roadmap.
