# Open issues

Classification follows `INSTRUCTIONS.md` §23. Nothing here was fixed silently.

## Requested by the owner and not done yet

| # | Item | State |
|---|---|---|
| OI-A | Remove old persisted-format support | PARTLY DONE. Done: checkpoint migrations v1→v10 and `tests/compatibility`; `normalize_checkpoint` rejects anything but schema 11. **Genome v1: tried and reverted.** It is not only an old persisted format: four live studies (`studies/continuity/recurrent_restoration`, `studies/runtime_prediction_promotion`, the developmental and predictive gate studies) and about 30 tests build their genomes from inline schema-1 payloads through `GenomeMigrationCodec`. Removing the migration made 38 tests fail. Removing it for real means converting those payloads to schema 2, which edits study code. Birth is unaffected either way: it already loads `genetics/defaults/base-genome-v2.json` with the strict codec. Not started: telemetry v3/v4 (`lab.physics3d.telemetry.{v3,v4}`, the v3/v4 branches of `telemetry/reader.py`, and a stray `lab/physics3d/telemetry.py` shadowed by the package; recorded runs in those formats would stop being readable), `core.cognition.bridge_compat`, and the legacy sequence/chunk forms kept in `actuation.sensorimotor`. |
| OI-B | Remove the desktop workbench (`app` command) | DONE: `app/{main,main_window,discovery,models,run_controller}.py`, three facades, the `app` command and the `symbiont-lab-gui` script. `lab.app.physics3d` stays: the server uses its run store and session, and the Physics3D engine uses its Qt viewer (`monitor/viewer.py`, 3386 lines), which is itself a desktop window. |
| OI-C | Keep moving elements into `modality/` and `embodiment/` | STARTED: vision channel, humanoid body, vision body. Next candidates in OI-3 and OI-4. |
| OI-D | Web workbench views still call removed endpoints | `workbench/web/views/archive.js`, `views/lab/api.js`, `views/home.js` reference `/api/experiments/start`, `/api/studies/start` or the archive. Not edited; they cannot be exercised from here. |
| OI-E | "Legacy/demo telemetry" path in `workbench/web/views/body/viewer.js` (joint-angle interpolation) | Left in place: untestable from here, and it is also the fallback for telemetry without link poses. |

## Architecture debt

**OI-3 — Embodiment and Modality are still mostly inside the organism.**
`symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory` and
`symbiont.host` mix organism state with coupling and channel code, and the core
depends on them heavily (`core.orchestration` → `actuation` 46 imports, → `host`
34; `core.domains` → `actuation` 48). The organism core also imports concrete
host modality implementations (`host.providers.{stdlib, stdlib_readings,
interoception, linux_surfaces, portable_surfaces}`), pinned by a ratchet test.
Extracting any of this needs dependency inversion in `OrganismRuntime` (default
provider construction), which changes behaviour-bearing code and needs a
decision on where the boundary sits.

**OI-4 — Physics3D and the world adapter are still in the Lab.**
`lab.physics3d` combines environment (engine, environments, resource),
embodiment (bodies, apparatus, re-embodiment) and observation (telemetry).
Modules with no Lab dependency that can move next, in order: `environments`
(→ environment; depends only on `environment.rng`), `articulated`,
`alternative_bodies`, `resource`, `bodies`, `apparatus`, `observer_semantics`,
`reembodiment` (→ embodiment). `engine`, `runtime` and `persistence` import
`lab.app`, `lab.modeling`, `lab.observation` and stay until those edges are cut.
In `lab.world`: `terrain`, `genesis_v1`, `genesis_v2` → environment; `adapter`
(+ `deferred`) → embodiment. `apparatus` and `physics3d.runtime` import
cognition internals (`symbiont.cognition.{birth, limits, generative, types}`),
pinned by a ratchet test.

**OI-5 — Consumers import organism internals, not `symbiont.api`.**
The Lab has 863 import edges into `symbiont.*`. `symbiont.api` exists and is
tested but nothing was migrated to it. Whether `symbiont.modeling` and
`symbiont.cognition.generative` (≈200 imports from the Lab) are public surface
is an open decision.

**OI-6 — PRE-EXISTING: import cycle inside the organism.**
`symbiont.cognition.checkpoint` and `symbiont.host.acclimation` fail with
"partially initialized module" unless `symbiont.core` is imported first. The
removed `symbiont.simulation` import used to hide this. `symbiont/__init__.py`
now imports `symbiont.core` explicitly to keep the previous order. The cycle
itself is not fixed.

## Other

**OI-7 — Lab scripts still at the root.** `scripts/bench_*.py`,
`characterize_kernel.py`, `aggregate_e8_*`, `run_e8_*`, `reprofile_performance.py`
are Lab analysis; `scripts/agentctl.py` and `scripts/governance/` are governance.
Not moved.

**OI-8 — Tests are not split per domain.** `tests/` still spans all domains;
only `symbiont/tests` (independence) and `lab/src/lab/observatory/tests` live
with their domain.

**OI-9 — Runner scripts of completed experiments use the old package names.**
`lab/experiments/world/genesis-v1/{run_w01_w02,run_w02_retry,run_w03,view_world}.py`
import `symbiont_lab` / `symbiont_world`. Left unmodified as evidence; they run
only against the source repository.

**OI-10 — No full scientific equivalence campaign.** The equivalence unit and
integration tests pass, but `agentctl`'s equivalence suite was not run:
governance tooling was set aside for this work at the owner's request, and it
builds its environment from committed state.

**OI-11 — Governance tooling reflects the new paths but is unverified.**
`docs/governance/*.toml`, `scripts/governance/`, `scripts/agentctl.py` and
`.github/workflows/` were path-rewritten mechanically. Frozen-evidence detection
now keys on `lab/experiments/`. None of it was exercised end to end, and
`ci_plan.py` lanes still name an `observatory` lane.

**OI-12 — Docs describe removed systems.** Links to deleted files were turned
into plain text and five source-citation rows were dropped from
`docs/explanation/concepts/SOURCES.md`, but the prose in `docs/architecture.md`
and `docs/explanation/math/*` still describes the legacy agent simulation,
`README.md` still documents removed commands, and
`migration/inventory.md` / `dependency-audit.md` were written before the
renames and removals.

**OI-13 — Generic top-level import names.** `lab`, `environment`, `modality`
and `embodiment` could collide with a third-party package of the same name.
Inside this workspace they resolve to the local members.

**OI-14 — `git status` was run once in the source repository** before the
no-touch rule was applied strictly (it can refresh the index stat cache). No
file there was created, changed or deleted; its `HEAD` and working tree are as
they were.
