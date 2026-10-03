# Open issues

Classification follows `INSTRUCTIONS.md` §23. Nothing here was fixed silently.

## Requested by the owner during the migration

| Item | State |
| --- | --- |
| Remove import aliases and forwarders | DONE |
| Remove the legacy agent simulation and everything that ran on it | DONE |
| Remove old persisted formats | DONE: checkpoint schemas 1–10, genome schema 1 and `HeritableGenome`, telemetry v3/v4 |
| Remove the desktop workbench | DONE. `lab.app.physics3d` stays: the server uses its run store and session, and the Physics3D engine uses its Qt viewer. |
| Remove the lab demo and the Observatory front-end | DONE |
| Domain packages named after the domain, not after the organism | DONE |
| Move into `modality/` and `embodiment/` what belongs there | DONE for concrete coupling (bodies, vision array, host channels). Intrinsic organism state stays in the organism by decision |
| The four domain libraries are peers with no first-party dependency on each other or on the Lab; the Lab is the only composition root | DONE (Import Linter, hard test gate, per-library isolated tests); the organism builds no concrete source |
| Enforce the boundaries with Import Linter | DONE: three contracts in `pyproject.toml`; runs in CI, pre-commit and the test suite |

## State after the third round

Done and validated (six suites green, Import Linter 3 contracts, each library
installed alone outside the repository, organism identity 13/13):

- every domain owns its tests (`<domain>/tests`) and the organism its
  documentation (`symbiont/docs`); `tests/` holds repository-wide checks only;
- governance covers every path of the five domains; domain `pyproject.toml`
  files and the boundary checks are CONSTITUTIONAL;
- real backends are declared as extras (`embodiment[physics3d]`,
  `modality[vision]`, `environment[physics3d]`) and imported by the package
  that declares them: nothing receives the PyBullet module as a parameter any
  more. The backend ban applies to the organism only;
- returned from the Lab to their owner: the deferred-damage rule and the
  physical resource (Environment), the re-embodiment transition and its
  longitudinal memory (Symbiont);
- **OI-3, the organism and its sense sources, is closed (steps A–G):**
  - the organism resolves which senses it requires in a pure function
    (`symbiont.core.orchestration.sense_requirements`), for a fresh creation
    and for a restore; the Lab does not interpret checkpoint controls;
  - `lab.integration.organism` composes the concrete sources and creates,
    restores and loads-or-creates the canonical organism. Every caller in
    `lab/src`, `lab/tests` and `tests` goes through it;
  - `OrganismRuntime()` builds no provider and inspects no platform: on its own
    it is a minimal organism with no host source;
  - the concrete host channels live in `modality.host` with their own record
    types; `lab.integration.organism.host_sources.HostSource` converts them;
  - `symbiont.host.providers` no longer exists, and a test asserts it;
  - interoception is split by provenance: the organism's own channels stay in
    `symbiont.sensory.interoception`; host process measurements are
    `modality.host.process_telemetry` and are no longer called interoception;
  - no test in `symbiont/tests` imports the Lab. A trial with the organism's
    providers removed left 1797 of them passing unchanged; the two that asserted
    what the canonical composition picks per platform moved to `lab/tests`.

Order actually followed: A, B, restore resolution, C, interoception split, D,
F and G, E. F had to precede E: an organism that still built its own providers
could not import them from `modality`.

Equivalence with the organism that built its own sources is checked against
the pre-migration tree, not against this one: `identity_check.py` builds nine
option sets and 54 restores with overrides in both trees and compares state
hash and checkpoint.

### Decisions and remaining owner work (scientific, not structural)

The migration deferred changes that affect energy trajectories or perception.
The owner subsequently requested resolution of the consolidated audit issues;
the telemetry-cost defect below is fixed in the current worktree. Its effect on
canonical profile versioning must still be reconciled before publication.

- **Host telemetry costs the organism energy — FIXED locally (2026-10-04).**
  Perception metabolism is now charged only for organism-facing readings;
  apparatus process telemetry no longer changes energy. The former strict xfail
  is now a passing invariance test in
  `symbiont/tests/unit/sensory/test_interoception_independence.py` (7 passed).
  Canonical profile/version consequences still require checking against the
  approved profile governance before publishing this correction.
- **Interoception is only offered where host senses are.** The organism's own
  interoception is attached only when `discover_senses` is on and the Lab
  reports the host available. Kept as it was; a minimal `OrganismRuntime()`
  therefore has none.

### Still open

- **Persisted names.** Host telemetry is still published under the source id
  `interoception` and the capability ids `internal.tick_latency` /
  `internal.memory_rss`, because they are written into checkpoints. Same kind
  of debt as `APPARATUS_FIELDS`; nothing in this work touched schema, hashing
  or the envelope.
- **Residue in the organism.** `symbiont.core.embodiment.transition` keeps a
  fallback descriptor naming a concrete body kind for checkpoints older than
  embodiment epochs.
- **Units inside the organism still mix state and coupling.**
  `symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory` and the
  generic machinery in `symbiont.host` were kept in the organism on purpose
  (body schema, physiology, metabolism, homeostasis, sensory and motor
  learning are intrinsic). Only concrete external coupling left.
- **Design documents.** `docs/design/` stays at the root: preregistrations, a
  frozen artefact and a path protected by running work. `embodiment`,
  `modality`, `environment` and `lab` have no documentation of their own beyond
  a README.

The sections below predate this round; where they disagree, this section is
current.

## Architecture debt

**OI-3 — CLOSED.** See "State after the third round".

**OI-4 — What remains in `lab.physics3d` and `lab.world`.**
Engine, runtime and persistence compose organism, body and environment; they
are Lab composition and stay. `resource` is environment code but imports
`SurfaceMaterial` from the humanoid body; since environment must not import
embodiment, it needs its own material description and the Lab to map one onto
the other. `observer_semantics` is observer-only labelling and belongs to the
Lab. `lab.world` keeps the population runtime, transactions and persistence.

**OI-5 — The Lab imports organism internals, not `symbiont.api`.**
This applies to the Lab only. The other three libraries import nothing from
Symbiont, and the fix for them was never to widen the API: code that needed the
organism moved to `lab.integration`. The Lab has 843 import edges into
`symbiont.*`; `symbiont.api` exists and is tested but nothing uses it yet.
Whether `symbiont.modeling` and `symbiont.cognition.generative` are public
surface is an open decision.

**OI-17 — Domain contracts are implicit.**
The libraries meet in the Lab through plain values and callables (a receptor
array factory, opaque receptor ids, `Mapping[str, float]` samples), not through
named protocols. `lab.integration.physics3d.apparatus` still builds organism
types (`SensorReading`, `Capability`, `ActuatorConstitution`) directly from
body internals. Giving each library small contracts of its own, as the target
describes, is not done.

**OI-6 — PRE-EXISTING: import cycle inside the organism.**
`symbiont.cognition.checkpoint` and `symbiont.host.acclimation` fail with
"partially initialized module" unless `symbiont.core` is imported first. The
removed `symbiont.simulation` import used to hide this. `symbiont/__init__.py`
now imports `symbiont.core` explicitly to keep the previous order. The cycle
itself is not fixed.

**OI-15 — `core.cognition.bridge_compat`.**
A 478-line mixin that forwards 42 private attributes of `CognitiveBridge` to
its collaborators. It is internal API indirection, not an old data format: the
organism itself uses it in 25 places, tests in 85. Left as is.

## Other

**OI-7 — Lab scripts still at the root.** `scripts/bench_*.py`,
`characterize_kernel.py`, `aggregate_e8_*`, `run_e8_*`, `reprofile_performance.py`
are Lab analysis; `scripts/agentctl.py` and `scripts/governance/` are governance.

**OI-8 — CLOSED.** Each domain's tests live in `<domain>/tests`; `tests/` holds repository-wide checks.

**OI-9 — Runner scripts of completed experiments use the old package names.**
`lab/experiments/world/genesis-v1/{run_w01_w02,run_w02_retry,run_w03,view_world}.py`
import `symbiont_lab` / `symbiont_world`. Left unmodified as evidence; they run
only against the source repository.

**OI-10 — No full scientific equivalence campaign.** The equivalence unit and
integration tests pass, but `agentctl`'s equivalence suite was not run.

**OI-11 — Governance tooling is path-rewritten but not exercised.**
`docs/governance/*.toml`, `scripts/governance/`, `scripts/agentctl.py` and
`.github/workflows/` point at the new paths, and their unit tests pass.
Frozen-evidence detection keys on `lab/experiments/`. No `agentctl publish` or
CI run was done, `ci_plan.py` still names an `observatory` lane, and
the CI job names (`observatory-tests`, …) are unchanged.

**OI-12 — Docs still describe removed systems.** `README.md` was updated to the
new layout. Links to deleted files were turned into plain text and five rows
dropped from `docs/explanation/concepts/SOURCES.md`, but the prose of
`docs/architecture.md` and `docs/explanation/math/*` still describes the legacy
agent simulation and the old package names.

**OI-13 — Generic top-level import names.** `lab`, `environment`, `modality`
and `embodiment` could collide with a third-party package of the same name.
Inside this workspace they resolve to the local members.

**OI-14 — `git status` was run once in the source repository** before the
no-touch rule was applied strictly (it can refresh the index stat cache). No
file there was created, changed or deleted; its `HEAD` and working tree are as
they were.

**OI-16 — Small web leftovers.** `workbench/web/app.js` still aliases the
routes `#lab` and `#experiments` to Home, and `views/body/viewer.js` keeps a
joint-angle interpolation path commented as "Legacy/demo telemetry". Neither
could be exercised in a browser from here, so neither was touched.
