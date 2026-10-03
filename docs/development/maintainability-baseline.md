# A9 Maintainability Baseline

**Captured:** 2026-10-02  
**Repository commit:** `60eb9a04896408dcf2c39c811252d431f4fc142b`  
**Status:** Initial source-verified inventory; no refactor authorized or performed.

## Scope and method

The inventory covers Python source under `src/symbiont`, `src/symbiont_lab`,
and `src/symbiont_world`, plus Python tests under `tests`. Every path component
named `observatory` is excluded, including `tests/unit/observatory`; generated
bytecode and cache directories are excluded. Line counts use physical lines
from the checkout at the commit above. They are a reproducible size baseline,
not complexity or refactor thresholds.

## Size baseline

| Area | Python files | Physical lines |
|---|---:|---:|
| `src/symbiont` | 251 | 64,073 |
| `src/symbiont_lab` (excluding Observatory) | 309 | 73,039 |
| `src/symbiont_world` | 12 | 1,019 |
| **In-scope source total** | **572** | **138,131** |
| **In-scope tests** | **523** | **67,392** |

The test total excludes Observatory and empty directories; two test files are
at the `tests/` root. Test ownership is
already organized into `unit` (335 files), `integration` (81),
`experimental_integrity` (54), `docs` (17), `smoke` (9), `experiments` (7),
`governance` (5), `compatibility` (4), and `regression` (7). `contract` is
currently empty. Unit tests have topical areas including `core`, `actuation`,
`cognition`, `modeling`, `sensory`, `lab`, `world`, and `workbench`; the
existence of root-level test files or a topical directory alone does not
establish that any move is safe.

## Largest source files

| Lines | Module |
|---:|---|
| 3,386 | `src/symbiont_lab/app/physics3d/monitor/viewer.py` |
| 3,319 | `src/symbiont/core/orchestration/runtime.py` |
| 2,954 | `src/symbiont/core/domains/action.py` |
| 2,556 | `src/symbiont_lab/physics3d/runtime.py` |
| 1,967 | `src/symbiont/actuation/sensorimotor.py` |
| 1,859 | `src/symbiont/modeling/runtime.py` |
| 1,590 | `src/symbiont/core/embodiment/body_schema.py` |
| 1,576 | `src/symbiont_lab/physics3d/telemetry/v41.py` |
| 1,509 | `src/symbiont/modeling/episodic.py` |
| 1,459 | `src/symbiont/modeling/culture.py` |

These counts corroborate large-file hotspots, not the proposed responsibility
boundaries. Call graphs, public compatibility surfaces, state ownership and
focused test mappings remain to be established before selecting an extraction.

## Boundaries and repository hygiene

- The constitutional dependency direction remains: Lab may depend on Symbiont;
  Symbiont must not depend on Lab or World; World must not depend on either.
- Focused import-boundary tests passed: `tests/experimental_integrity/test_ground_truth_boundary.py`
  and `tests/experimental_integrity/test_runtime_import_boundary.py` — **9 passed**.
  These are targeted checks, not a complete dependency graph audit.
- Two `*.egg-info` directories exist in the checkout: `./symbiont_lab.egg-info`
  and `./src/symbiont_lab.egg-info`. No tracked `*.pyc` files were found. The
  generated directories were not removed in this inventory.
- Observatory source, tests, and design remain outside the A9 inventory and
  implementation scope.

## Next A9 step

Select one candidate seam only after recording its owned responsibility,
callers, public compatibility surface, state/provenance invariants and focused
tests. Prefer a small apparatus-only seam if those facts support it. Do not
change mechanisms, ordering, random-number consumption, checkpoint semantics,
or authority boundaries. The proposed passive runtime trace remains unapproved
and is not selected by this inventory.

## First bounded extraction: asynchronous telemetry worker lifecycle

The first selected seam is the identical bounded FIFO worker lifecycle shared
by `AsyncTelemetryV4Writer` and `AsyncTelemetryV41Writer` in
`src/symbiont_lab/physics3d/telemetry/v4.py` and `telemetry/v41.py`. Their
`_run`, `append`, `flush`, `close`, and worker-error handling were duplicated;
the V4.1 snapshot policy is distinct and remains in its versioned adapter.

- **Owned responsibility:** bounded queue, worker thread lifecycle, persistence
  delegation and worker-error propagation. The new private
  `physics3d/_async_telemetry.py` helper owns no telemetry format or tick policy.
- **Callers:** the Physics3D engine constructs the V4.1 adapter; V4/V4.1 async
  behavior is exercised in
  `tests/unit/lab/physics3d/telemetry/test_telemetry_v4.py` and
  `test_telemetry_v41.py`. Telemetry tools consume the versioned writers and
  readers; their interfaces are unchanged.
- **Compatibility surface:** public class names, modules, constructor
  signatures, delegated `run_id`/`root`/`manifest`, snapshot policy and worker
  thread names remain version-specific and stable. Invalid queue size is
  rejected before creating the run directory.
- **Preserved invariants:** FIFO ordering, bounded backpressure, append
  arguments, close/drain behavior, non-daemon worker lifecycle, exception
  propagation and all on-disk schemas remain unchanged. The shared helper does
  not inspect, reorder, or mutate scientific state.
- **Focused evidence:** all in-scope Physics3D unit tests passed after the
  extraction: **280 passed, 1 skipped**. Ruff check and format check passed.
  The full repository suite was not run; no performance claim is made.

This is one behavior-preserving apparatus slice, not a decision to merge
telemetry formats or move their public APIs. Further extractions require their
own source-to-test mapping and regression evidence.

## Second bounded extraction: monitor geometry primitives

The second selected seam is the two pure 2D geometry functions used to
calculate the monitor's support polygon: `_convex_hull_2d` and
`_point_in_polygon_2d`. They now live in
`src/symbiont_lab/app/physics3d/geometry.py`; the monitor imports them and keeps
its historical names available through the `symbiont_lab.physics3d.monitor`
compatibility facade.

- **Owned responsibility:** convex hull and ray-casting containment over 2D
  points. The module has no UI, IPC, PyBullet, or organism dependencies.
- **Callers:** the monitor's support-polygon rendering path is the only source
  caller; `lab/tests/unit/lab/physics3d/test_monitor.py` exercises both algorithms
  through the compatibility facade.
- **Compatibility surface:** function names, signatures, geometry semantics,
  import facade and rendering call sites are unchanged.
- **Preserved invariants:** no inputs are mutated, geometric ordering and
  containment behavior are unchanged, and the extraction does not affect
  simulation state or the monitor's observer-only role.
- **Focused evidence:** monitor tests passed: **13 passed, 1 skipped**. Ruff
  check and formatting passed for both changed modules. The full Physics3D
  directory and repository suite were not rerun for this slice.

This isolates pure geometry only; IPC, camera behavior and widgets remain in
the monitor until separate mappings demonstrate safe boundaries.

## Third bounded organization slice: modeling unit-test ownership

Six modeling-focused unit-test modules previously at `tests/unit/` root now
reside in `tests/unit/modeling/`: modeled-organism runtime, corpus, tokenizer,
sequence characterization/substrate, and training ancestry. Source ownership
is the modeling subsystem, and the existing modeling test-area contract already
defines this location for small deterministic tests.

- **Callers/importers:** the three test modules that reused
  `_transition` now import it from the moved runtime test module; no production
  module imports tests. A repository search found no other active code
  references to the old module path.
- **Compatibility surface:** production APIs and fixtures are unchanged. The
  test helper module path changed only where the three known test consumers
  were updated.
- **Preserved invariants:** no tests, assertions, fixtures or runtime behavior
  were intentionally altered; files were relocated as-is apart from those
  imports.
- **Focused evidence:** all six moved modules and both dependent integration
  modules passed: **42 passed, 4 deselected**. This does not establish a full
  suite result.

This only relocates the six modeling-owned tests. Other root-level tests remain
until each has a verified owner, consumer map and regression plan.

## Fourth bounded organization slice: host sensing and cognition tests

Two more root-level tests are now grouped by their direct source ownership:
`test_adaptive_senses.py` moved to `tests/unit/host/`, where the adaptive sense
model's host readings and development behavior are tested, and
`test_shadow_prediction.py` moved to `tests/unit/cognition/`, alongside the
related cognition learning contracts.

- **Consumers:** repository search found no Python importers of either test
  module. The active concepts source index referenced both test node IDs; its
  paths were updated to the new locations.
- **Compatibility surface:** test names and test function IDs are unchanged;
  only paths changed. No production code or test assertions changed.
- **Focused evidence:** both moved modules and the repository-layout test
  passed: **35 passed**. Ruff check and format check passed.

Other root-level tests remain unmoved pending equally direct ownership and
reference checks.

## Fifth bounded organization slice: laboratory experiment-store tests

`tests/unit/test_scientific_generations.py` tests the deterministic
`GenerationStore` software contract, not a scientific campaign. It now resides
under `tests/unit/lab/experiments/`, whose existing README explicitly owns
bounded tests for experiment preparation and recorded state.

- **Consumers:** repository search found no external test-module imports or
  documentation links to its old path.
- **Compatibility surface:** test functions, assertions and production APIs are
  unchanged; only the path changed.
- **Focused evidence:** the complete lab experiment unit-test directory passed:
  **30 passed**. Ruff check passed for that directory; format check passed for
  the moved file. The directory-level format check exposed an unrelated
  pre-existing formatting difference in `test_snapshot_archive.py`, which was
  not modified. Repository-layout tests passed: **4 passed**.

This is one lab-only test-ownership move; it does not establish scientific
evidence or campaign validity.

## Sixth bounded organization slice: private-modeling and communication tests

Two more root-level modules now belong to `tests/unit/modeling/`:
`test_private_modeling_contract.py` and `test_communication_telemetry.py`.
Both exercise `symbiont.modeling` APIs, with no test-module consumers or active
documentation references found for their old paths.

- **Compatibility surface:** production APIs and test contents are unchanged;
  paths only were relocated.
- **Focused evidence:** the full modeling test directory passed: **76 passed**.
  Ruff check passed for the directory, formatting passed for the two moved
  modules, and repository-layout tests passed: **4 passed**.

## Seventh bounded organization slice: host durable-I/O tests

`tests/unit/test_durable_io.py` covers only `symbiont.host.durable` contracts
and has no external test-module or documentation references. It now resides in
`tests/unit/host/`, the existing owner for host capabilities and state.

- **Compatibility surface:** test functions and assertions are unchanged; only
  the path changed.
- **Focused evidence:** all host unit tests passed: **259 passed**. Ruff check
  passed for the host directory, format check passed for the moved test, and
  repository-layout tests passed: **4 passed**.

Across these evidence-backed test moves, twelve root-level modules now have
explicit subsystem homes. Remaining tests are still mapped individually before
any further relocation.

## Eighth bounded apparatus extraction: monitor payload converters

The monitor's two telemetry conversion functions now live in
`src/symbiont_lab/app/physics3d/monitor/converters.py`. They translate a telemetry
record into the `MonitorSnapshot`-compatible mapping and the evaluator-safe
physical-state payload consumed by replay rendering. The monitor still imports
and re-exports both functions, preserving the application and legacy
`symbiont_lab.physics3d.monitor` import surfaces.

- **Owned responsibility:** pure conversion and fallback-field reconstruction
  for monitor/replay payloads. The extracted module has no UI, IPC, process, or
  rendering dependencies; it imports only the humanoid schema constants used to
  construct physical-state records.
- **Callers:** `_viewer_main` uses both helpers on the replay path. Focused
  conversion tests exercise complete and fallback records through the legacy
  facade. Repository search found no other production callers.
- **Compatibility surface:** function names, signatures, output keys, fallback
  values, and both existing import paths remain unchanged. The application
  module's exports are direct aliases of the extracted functions.
- **Preserved invariants:** AST comparison against the pre-extraction
  `origin/main` implementations was exact for both functions; no conversion
  logic, field ordering, fallback behavior, or state schema was changed.
- **Focused evidence:** monitor and desktop-app tests passed before extraction
  (**31 passed, 1 skipped**) and after extraction (**32 passed, 1 skipped**).
  Ruff check and formatting passed for the touched Python files. This does not
  establish a full application or repository-suite result.

The extraction separates a data-conversion seam only. `MonitorSnapshot`, replay
event assembly, multiprocessing, camera state and UI remain in the monitor
pending their own caller, compatibility and state-invariant mapping.

## Ninth bounded organization slice: Physics3D module families

Under accepted ADR-0055, the existing application-owned Physics3D modules now
reside under `src/symbiont_lab/app/physics3d/`; monitor presentation and
conversion code reside under its `monitor/` subpackage. The versioned
Physics3D telemetry modules and supporting reader/tool modules now reside under
`src/symbiont_lab/physics3d/telemetry/`. Their unit tests reside under
`tests/unit/lab/physics3d/telemetry/`.

- **Ownership mapping:** geometry stays pure in `app/physics3d/geometry.py`;
  run/session orchestration stays in sibling `runs.py` and `session.py`; the
  monitor viewer and payload conversion stay separate in `monitor/viewer.py`
  and `monitor/converters.py`. Telemetry format/version, binary encoding,
  schema, reader, structural, and tool responsibilities remain separate
  modules within `physics3d/telemetry/`.
- **File mapping:** `app/physics3d_geometry.py` → `app/physics3d/geometry.py`;
  `app/physics3d_monitor.py` → `app/physics3d/monitor/viewer.py`;
  `app/physics3d_monitor_converters.py` →
  `app/physics3d/monitor/converters.py`; `app/physics3d_runs.py` and
  `app/physics3d_session.py` → `app/physics3d/runs.py` and `session.py`.
  Telemetry files `telemetry.py`, `telemetry_binary.py`, `telemetry_cli.py`,
  `telemetry_compaction.py`, `telemetry_events.py`, `telemetry_numeric.py`,
  `telemetry_reader.py`, `telemetry_schema.py`, `telemetry_structural.py`,
  `telemetry_tools.py`, `telemetry_v4.py`, `telemetry_v41.py`, and
  `_async_telemetry.py` map to `telemetry/v3.py`, `binary.py`, `cli.py`,
  `compaction.py`, `events.py`, `numeric.py`, `reader.py`, `schema.py`,
  `structural.py`, `tools.py`, `v4.py`, `v41.py`, and `async_worker.py`.
  The nine `test_telemetry_*.py` modules moved unchanged into the telemetry
  test directory.
- **Callers and paths:** production imports, packaging entry points, active
  documentation references, governance path manifests, and test selectors
  were updated. Explicit compatibility facades preserve established flat
  module imports. Archived design records remain historical and are not
  rewritten.
- **Package markers:** explicit `__init__.py` files define the new app,
  monitor, telemetry, and test packages. Telemetry's package initializer
  exposes a curated versioned reader/writer API; it does not merge formats.
- **Preserved invariants:** this is file organization only. No telemetry schema,
  version policy, run/session behavior, numerical semantics, or scientific
  state is intentionally changed.
- **Focused evidence:** Physics3D unit tests, desktop-app tests, relevant
  observation/integrity tests, and the primitive-effects integration test
  passed: **309 passed, 1 skipped, 8 deselected**. Ruff check and format check
  passed for the touched Python files. Full-suite validation was not run.

## Tenth bounded organization slice: private experience pipeline test ownership

`tests/unit/test_private_experience_pipeline.py` exercises the private-modeling
experience pipeline through `PrivateModelOrganismRuntime`, `ExperienceRecord`,
`EpisodicProjection`, and training-corpus APIs. It now resides in
`tests/unit/modeling/`, alongside the existing deterministic modeling contract
tests.

- **Consumers:** repository search found no imports of the test module or active
  documentation references to its previous path.
- **Ownership:** the tested production APIs are owned by `symbiont.modeling`;
  the test uses `RuntimeTickResult` and `Actuation` as boundary fixtures but its
  questions concern privacy, epistemic status, experience retention and
  modeling/training projections.
- **Compatibility surface:** test names, assertions and production APIs are
  unchanged; only the test path changed.
- **Focused evidence:** the entire modeling unit-test directory, including the
  relocated module, passed: **88 passed**. Repository-layout and Markdown-link
  checks passed: **5 passed**. Ruff check and format check passed for the moved
  module. The full repository suite has not been run.
