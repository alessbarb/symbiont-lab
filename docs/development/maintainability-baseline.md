# A9 Maintainability Baseline

**Captured:** 2026-10-01  
**Repository commit:** `6190039520bda6de418687925158120631ea4da3`  
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
| `src/symbiont` | 251 | 64,038 |
| `src/symbiont_lab` (excluding Observatory) | 285 | 73,006 |
| `src/symbiont_world` | 12 | 1,019 |
| **In-scope source total** | **548** | **138,063** |
| **In-scope tests** | **521** | **67,286** |

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
| 3,589 | `src/symbiont_lab/app/physics3d_monitor.py` |
| 3,319 | `src/symbiont/core/orchestration/runtime.py` |
| 2,954 | `src/symbiont/core/domains/action.py` |
| 2,556 | `src/symbiont_lab/physics3d/runtime.py` |
| 1,967 | `src/symbiont/actuation/sensorimotor.py` |
| 1,859 | `src/symbiont/modeling/runtime.py` |
| 1,658 | `src/symbiont_lab/physics3d/telemetry_v41.py` |
| 1,590 | `src/symbiont/core/embodiment/body_schema.py` |
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
`src/symbiont_lab/physics3d/telemetry_v4.py` and `telemetry_v41.py`. Their
`_run`, `append`, `flush`, `close`, and worker-error handling were duplicated;
the V4.1 snapshot policy is distinct and remains in its versioned adapter.

- **Owned responsibility:** bounded queue, worker thread lifecycle, persistence
  delegation and worker-error propagation. The new private
  `physics3d/_async_telemetry.py` helper owns no telemetry format or tick policy.
- **Callers:** the Physics3D engine constructs the V4.1 adapter; V4/V4.1 async
  behavior is exercised in `tests/unit/lab/physics3d/test_telemetry_v4.py` and
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
`src/symbiont_lab/app/physics3d_geometry.py`; the monitor imports them and keeps
its historical names available through the `symbiont_lab.physics3d.monitor`
compatibility facade.

- **Owned responsibility:** convex hull and ray-casting containment over 2D
  points. The module has no UI, IPC, PyBullet, or organism dependencies.
- **Callers:** the monitor's support-polygon rendering path is the only source
  caller; `tests/unit/lab/physics3d/test_monitor.py` exercises both algorithms
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
