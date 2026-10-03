# Open issues

Classification follows `INSTRUCTIONS.md` §23. Nothing here was fixed silently.

## Requested by the owner during the migration

| Item | State |
|---|---|
| Remove import aliases and forwarders | DONE |
| Remove the legacy agent simulation and everything that ran on it | DONE |
| Remove old persisted formats | DONE: checkpoint schemas 1–10, genome schema 1 and `HeritableGenome`, telemetry v3/v4 |
| Remove the desktop workbench | DONE. `lab.app.physics3d` stays: the server uses its run store and session, and the Physics3D engine uses its Qt viewer. |
| Remove the lab demo and the Observatory front-end | DONE |
| Domain packages named after the domain, not after the organism | DONE |
| Move into `modality/` and `embodiment/` what belongs there | PARTLY: see OI-3 |
| The four domain libraries are peers with no first-party dependency on each other or on the Lab; the Lab is the only composition root | DONE for the packages as they stand (Import Linter, hard test gate, per-library isolated tests). Not yet true of code still inside the organism: OI-3 |
| Enforce the boundaries with Import Linter | DONE: three contracts in `pyproject.toml`; runs in CI, pre-commit and the test suite |

## Architecture debt

**OI-3 — The organism still owns embodiment and modality code.**
The target is that Symbiont keeps only generic signal machinery, learning and
sensory plasticity, and receives everything concrete through a boundary of its
own, connected by the Lab. Today:

- `OrganismRuntime.__init__` must not create concrete modality implementations,
  and it does: from its own flags it chooses and constructs
  `host.providers.{stdlib, stdlib_readings, interoception, linux_surfaces,
  portable_surfaces}`. Those implementations should live outside the organism
  (host modality) and be injected by the Lab. Doing it changes how every caller
  creates an organism (`OrganismRuntime()` with no arguments is used throughout
  the tests and studies), so it was not done mechanically. Pinned by a ratchet
  test so it cannot grow.
- `symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory` and
  `symbiont.host` mix organism state with coupling and channel code, and the
  core depends on them heavily (`core.orchestration` → `actuation` 46 imports,
  → `host` 38; `core.domains` → `actuation` 48). Each has to be split by
  knowledge boundary; nothing in them may move to `embodiment` or `modality`
  while it still imports the organism.

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

**OI-8 — Tests are not split per domain.** `tests/` spans all domains, keeps its
old directory names and needs the whole workspace. Each library has only a
small test of its own that runs with nothing else installed (`symbiont/tests`,
`embodiment/tests`, `modality/tests`, `environment/tests`); the bulk of each
library's unit tests has not been moved beside it.

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
