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

| Old path (under `src/symbiont_lab/`) | New path | Domain |
|---|---|---|
| `physics3d/vision.py`: `PerceptualTopology`, `VisualApparatus`, array constants | `modality/src/modality/vision.py` | MODALITY |
| `physics3d/vision.py`: `VisionHumanoidPhysics`, receptor ids, body kind | `embodiment/src/embodiment/physics3d/vision.py` | EMBODIMENT |
| `physics3d/humanoid.py` | `embodiment/src/embodiment/physics3d/humanoid.py` | EMBODIMENT |
| `physics3d/articulated.py`, `alternative_bodies.py`, `bodies.py` | `embodiment/src/embodiment/physics3d/` | EMBODIMENT |
| `physics3d/apparatus.py` | `embodiment/src/embodiment/physics3d/apparatus.py` | EMBODIMENT |
| `physics3d/reembodiment.py`, `longitudinal.py` | `embodiment/src/embodiment/physics3d/` | EMBODIMENT |
| `world/adapter.py`, `world/deferred.py` | `embodiment/src/embodiment/world/` | EMBODIMENT |
| `physics3d/environments.py` | `environment/src/environment/physics3d/environments.py` | ENVIRONMENT |
| `world/terrain.py`, `genesis_v1.py`, `genesis_v2.py` | `environment/src/environment/` | ENVIRONMENT |
| `src/symbiont/environment/rng.py` | `lab/src/lab/studies/common/rng.py` | LAB |
| `RunCoordinator` in `workbench/runs.py` | `lab/src/lab/workbench/coordinator.py` | LAB |

All moved verbatim except `vision.py`, which was split in two. Every importer was
rewritten; nothing forwards the old path. Validation for all rows: full suite
and architecture gates.

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
| `symbiont.core.embodiment`, `symbiont.actuation` | EMBODIMENT (partly) | PENDING — `open-issues.md` OI-3 |
| `symbiont.sensory`, `symbiont.host` (incl. `host.providers`) | MODALITY (partly) | PENDING — OI-3 |
| `lab.physics3d.{engine, runtime, persistence}` | LAB composition | STAYS — it composes organism, body and environment; OI-4 lists the Lab edges that keep it there |
| `lab.physics3d.resource` | ENVIRONMENT | PENDING — imports `SurfaceMaterial` from the humanoid body, and environment must not depend on embodiment (OI-4) |
| `scripts/` benchmarks, `tests/` | LAB / per domain | PENDING — OI-7, OI-8 |
