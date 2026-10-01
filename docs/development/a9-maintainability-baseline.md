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
