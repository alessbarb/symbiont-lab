# Mapping: old path → new path

Old paths are those of commit `593c2a02` (source repository, untouched). Import
names changed for every package except the organism, so that renaming the
organism later touches one package only.

## Packages

| Old path | Old import | New path | New import | Status |
|---|---|---|---|---|
| `src/symbiont/` | `symbiont` | `symbiont/src/symbiont/` | `symbiont` | MIGRATED, own distribution `symbiont` |
| `src/symbiont_world/` | `symbiont_world` | `environment/src/environment/` | `environment` | MIGRATED, own distribution `environment` |
| `src/symbiont_lab/` | `symbiont_lab` | `lab/src/lab/` | `lab` | MIGRATED, own distribution `lab` |
| `observatory/*.py`, `schemas/`, `world.html` | `observatory` | `lab/src/lab/observatory/` | `lab.observatory` | MIGRATED (back-end only) |
| `observatory/tests/` (back-end) | — | `lab/src/lab/observatory/tests/` | — | MIGRATED, 108 tests |
| `experiments/` | — | `lab/experiments/` | — | MIGRATED (byte-identical, minus removed legacy specs) |
| `research/` | — | `lab/research/` | — | MIGRATED (4 files had relative links repaired) |
| `examples/` | — | `lab/examples/` | — | MIGRATED (byte-identical) |

## Elements extracted into the new domains

| Old path | New path | Domain | Status |
|---|---|---|---|
| `src/symbiont_lab/physics3d/vision.py` (`PerceptualTopology`, `VisualApparatus`, array constants) | `modality/src/modality/vision.py` | MODALITY | MIGRATED — receptor-array channel, no body or organism dependency |
| `src/symbiont_lab/physics3d/vision.py` (`VisionHumanoidPhysics`, receptor ids, body kind) | `embodiment/src/embodiment/physics3d/vision.py` | EMBODIMENT | MIGRATED — binds the channel to the humanoid body |
| `src/symbiont_lab/physics3d/humanoid.py` | `embodiment/src/embodiment/physics3d/humanoid.py` | EMBODIMENT | MIGRATED verbatim |
| `src/symbiont/environment/rng.py` | `lab/src/lab/studies/common/rng.py` | LAB | MIGRATED (only surviving user is a lab study) |
| `RunCoordinator` in `src/symbiont_lab/workbench/runs.py` | `lab/src/lab/workbench/coordinator.py` | LAB | MIGRATED (rest of the module removed) |

New in the organism: `symbiont/src/symbiont/api.py` (public surface, re-exports only).

## Import aliases retired (importers rewritten, no shim left)

`migration/alias-map.json` holds the 65 pairs. Summary:

| Old import | New import |
|---|---|
| `symbiont.core.<name>` for 52 historical names (`runtime`, `governor`, `memory`, `physiology`, `body_schema`, `signal_knowledge`, `germline`, …) | `symbiont.core.<domain>.<name>` (`orchestration.runtime`, `embodiment.physiology`, `signals.knowledge`, `lineage.germline`, …) |
| `symbiont.core.canonical_birth` | `symbiont.core.orchestration.canonical_birth` |
| `symbiont_lab.physics3d.telemetry_<x>`, `_async_telemetry` | `lab.physics3d.telemetry.<x>`, `.async_worker` |
| `symbiont_lab.physics3d.monitor`, `symbiont_lab.app.physics3d_monitor[_converters]` | `lab.app.physics3d.monitor.viewer` / `.converters` |

## Removed (requested by the owner during the migration)

| Removed | What it was |
|---|---|
| `ORGANISM.md`, `deploy/` | deleted by the owner; not part of the new structure |
| `src/symbiont/simulation/`, `src/symbiont/environment/{world,regimes}.py` | legacy agent-population simulation and synthetic host world |
| `src/symbiont/core/cognition/{agent,beliefs,curiosity,metacognition,reasoning}.py`, `core/foundation/model.py`, `core/social/ledger.py` | legacy Agent stack |
| `src/symbiont_lab/studies/{attention,evidence,heritage,campaigns}/`, `studies/longitudinal_population_ecology.py` | studies that ran on the legacy simulation |
| `src/symbiont_lab/archive/`, `workbench/runs.py` (except `RunCoordinator`), `cli/{simulate,audit,archive}.py`, `study compare` / `study show` | experiment/study archive and launch on the legacy simulation; endpoints `/api/experiments/start`, `/api/studies/start` |
| 12 protocols (`simulate`, `attention.*`, `evidence.*`, `heritage.*`, `learning.longitudinal-population-ecology`) and 7 experiment specs under `lab/experiments` | legacy protocols |
| `src/symbiont_lab/observation/demo.py`, server/CLI `--demo` | synthetic UI telemetry |
| `observatory/` front-end: `index.html`, `app.js`, `styles.css`, `communication/`, `projection/`, `render/`, `state/`, `transport/`, `ui/` | legacy Observatory UI, including its demo state |
| `src/symbiont/core/lineage/heredity.py`, `core/canonical_birth.py`, telemetry and monitor facades, `tests/archive/` | removed-API stubs, forwarders, archived tests |

Everything removed remains in the source repository and in this repository's
history at `593c2a02`.

## Not migrated

| Path | Target | Status |
|---|---|---|
| `symbiont.core.embodiment`, `symbiont.actuation` | EMBODIMENT (partly) | PENDING — see `open-issues.md` OI-3 |
| `symbiont.sensory`, `symbiont.host` (incl. `host.providers`) | MODALITY (partly) | PENDING — OI-3 |
| `lab.physics3d` (bodies, apparatus, re-embodiment, engine, environments) | EMBODIMENT / ENVIRONMENT | PENDING — OI-4 |
| `lab.world` (adapter, terrain, genesis) | EMBODIMENT / ENVIRONMENT | PENDING — OI-4 |
| `scripts/` benchmarks, `tests/` | LAB / per domain | PENDING — OI-7, OI-8 |
