# Mapping: old path → new path

Old paths are those of commit `593c2a02` (source repository, untouched). Import
names changed for every package except the organism, so that renaming the
organism later touches one package only.

## Packages

| Old path | Old import | New path | New import | Status | Validation |
|---|---|---|---|---|---|
| `src/symbiont/` | `symbiont` | `symbiont/src/symbiont/` | `symbiont` | MIGRATED, own distribution | full suite; independence test; identity check |
| `src/symbiont_world/` | `symbiont_world` | `environment/src/environment/` | `environment` | MIGRATED, own distribution | full suite; architecture gates |
| `src/symbiont_lab/` | `symbiont_lab` | `lab/src/lab/` | `lab` | MIGRATED, own distribution | full suite |
| `observatory/*.py`, `schemas/`, `world.html` | `observatory` | `lab/src/lab/observatory/` | `lab.observatory` | MIGRATED (back-end only) | its 108 tests |
| `experiments/` | — | `lab/experiments/` | — | MIGRATED, byte-identical minus 7 removed legacy specs | diff against `593c2a02` |
| `research/` | — | `lab/research/` | — | MIGRATED; 4 files had relative links repaired | link check |
| `examples/` | — | `lab/examples/` | — | MIGRATED, byte-identical | diff against `593c2a02` |

## Elements extracted into the domains

The four domain libraries are peers: none imports another. A module that knew
two domains went to `lab/src/lab/integration/`.

| Old path (under `src/symbiont_lab/`) | New path | Domain |
|---|---|---|
| `physics3d/vision.py`: `PerceptualTopology`, `VisualApparatus` | `modality/src/modality/vision.py` | MODALITY |
| `physics3d/vision.py`: body kind, receptor ids, head mount, `VisionHumanoidPhysics` (array now injected) | `embodiment/src/embodiment/physics3d/vision.py` | EMBODIMENT |
| `physics3d/humanoid.py`, `articulated.py`, `alternative_bodies.py` | `embodiment/src/embodiment/physics3d/` | EMBODIMENT |
| `physics3d/bodies.py`: descriptors, `BodyRegistry` | `embodiment/src/embodiment/physics3d/bodies.py` | EMBODIMENT |
| `physics3d/bodies.py`: `ANTHROPOMORPHIC_V6_VISION`, `DEFAULT_BODY_REGISTRY` | `lab/src/lab/integration/physics3d/bodies.py` | LAB (embodiment + modality) |
| `physics3d/apparatus.py` | `lab/src/lab/integration/physics3d/apparatus.py` | LAB (embodiment + symbiont) |
| `physics3d/reembodiment.py`, `physics3d/longitudinal.py` | `symbiont/src/symbiont/core/embodiment/{transition, longitudinal}.py` | SYMBIONT |
| `world/adapter.py`, `world/deferred.py` | `lab/src/lab/integration/world/` | LAB (environment + symbiont) |
| `physics3d/environments.py` | `environment/src/environment/physics3d/environments.py` | ENVIRONMENT |
| `world/terrain.py`, `genesis_v1.py`, `genesis_v2.py` | `environment/src/environment/` | ENVIRONMENT |
| `src/symbiont/environment/rng.py` | `lab/src/lab/studies/common/rng.py` | LAB |
| `RunCoordinator` in `workbench/runs.py` | `lab/src/lab/workbench/coordinator.py` | LAB |

Moved verbatim except `vision.py` and `bodies.py`, which were split by knowledge
boundary. One behaviour-neutral change: the head mount pose moved from the
receptor array class to the body and is passed in at composition. Every importer
was rewritten; nothing forwards an old path. Validation for all rows: full
suite, Import Linter contracts, architecture gates.

Extracted from the organism (old paths under `src/symbiont/`):

| Old path | New path | Domain |
|---|---|---|
| `host/providers/{stdlib, stdlib_readings, linux_surfaces, portable_surfaces}.py` | `modality/src/modality/host/` (own record types in `records.py`) | MODALITY |
| `host/providers/interoception.py`: tick latency, resident memory | `modality/src/modality/host/process_telemetry.py` | MODALITY |
| `host/providers/interoception.py`: the organism's own channels | `symbiont/src/symbiont/sensory/interoception.py` | SYMBIONT |
| `host/bootstrap.py` (`discover_local_host`, …) | `lab/src/lab/integration/organism/local_host.py` | LAB (modality + symbiont) |
| provider selection in `OrganismRuntime.__init__` | `lab/src/lab/integration/organism/canonical.py`; what is required is resolved in `symbiont/src/symbiont/core/orchestration/sense_requirements.py` | LAB / SYMBIONT |

New in the organism: `symbiont/src/symbiont/api.py` (public surface, re-exports only).

## Import aliases retired

`migration/alias-map.json` holds the 65 pairs.

| Old import | New import |
|---|---|
| `symbiont.core.<name>` for 52 historical names (`runtime`, `governor`, `memory`, `physiology`, `body_schema`, `signal_knowledge`, `germline`, …) | `symbiont.core.<domain>.<name>` (`orchestration.runtime`, `embodiment.physiology`, `signals.knowledge`, `lineage.germline`, …) |
| `symbiont.core.canonical_birth` | `symbiont.core.orchestration.canonical_birth` |
| `symbiont_lab.physics3d.telemetry_<x>`, `_async_telemetry` | `lab.physics3d.telemetry.<x>`, `.async_worker` |
| `symbiont_lab.physics3d.monitor`, `symbiont_lab.app.physics3d_monitor[_converters]` | `lab.app.physics3d.monitor.viewer` / `.converters` |

## Removed at the owner's request

| Removed | What it was |
|---|---|
| `ORGANISM.md`, `deploy/` | deleted by the owner; not part of the new structure |
| `src/symbiont/simulation/`, `src/symbiont/environment/{world,regimes}.py` | legacy agent-population simulation and synthetic host world |
| `src/symbiont/core/cognition/{agent,beliefs,curiosity,metacognition,reasoning}.py`, `core/foundation/model.py`, `core/social/ledger.py` | legacy Agent stack |
| `studies/{attention,evidence,heritage,campaigns}/`, `studies/longitudinal_population_ecology.py` | studies that ran on the legacy simulation |
| `archive/`, `workbench/runs.py` (except `RunCoordinator`), `cli/{simulate,audit,archive}.py`, `study compare` / `study show`, `/api/experiments/start`, `/api/studies/start`, web view `views/lab*` | experiment/study archive and launch on the legacy simulation |
| 12 protocols (`simulate`, `attention.*`, `evidence.*`, `heritage.*`, `learning.longitudinal-population-ecology`) and 7 experiment specs | legacy protocols |
| `observation/demo.py`, server/CLI `--demo` | synthetic UI telemetry |
| `observatory/` front-end: `index.html`, `app.js`, `styles.css`, `communication/`, `projection/`, `render/`, `state/`, `transport/`, `ui/` | legacy Observatory UI, including its demo state |
| `app/{main,main_window,discovery,models,run_controller}.py`, `app` command, `symbiont-lab-gui` | desktop workbench |
| checkpoint migrations `_migrate_v1_to_v2` … `_migrate_v10_to_v11`, `tests/compatibility/` | loading of checkpoint schemas 1–10 |
| `genetics/migration.py`, `cognition/defaults/base-genome.json` | genome schema 1 and the `HeritableGenome` payload |
| `physics3d/telemetry/{v3,v4}.py`, `physics3d/telemetry.py`, `convert_run`, `symbiont-telemetry-convert` | telemetry v3 and v4 |
| `core/lineage/heredity.py`, `core/canonical_birth.py`, telemetry and monitor facades, `tests/archive/` | removed-API stubs, forwarders, archived tests |

Everything removed remains in the source repository and in this repository's
history at `593c2a02`.

## Not migrated

| Path | Target | Status |
|---|---|---|
| `symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory`, generic `symbiont.host` | SYMBIONT | STAYS by decision: intrinsic organism state and generic signal machinery |
| `lab.physics3d.{engine, runtime, persistence}` | LAB composition | STAYS — it composes organism, body and environment; OI-4 lists the Lab edges that keep it there |
| `lab.physics3d.resource` | ENVIRONMENT | PENDING — imports `SurfaceMaterial` from the humanoid body, and environment must not depend on embodiment (OI-4) |
| `scripts/` benchmarks, `tests/` | LAB / per domain | PENDING — OI-7, OI-8 |
