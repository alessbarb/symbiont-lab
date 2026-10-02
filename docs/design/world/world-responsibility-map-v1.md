---
id: design.world.world-responsibility-map-v1
title: "World Responsibility Map v1"
document_type: reference
domain: world
status: proposed
canonical: false
implementation_status: implemented
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
source_audit: research/audits/current/2026-10-02-current-state-architecture-audit.md
language: en
---

# World Responsibility Map v1

## 1. Purpose

The
[current-state audit](../../../research/audits/current/2026-10-02-current-state-architecture-audit.md)
(F-09) found that "World" names a family of environments rather than one runtime
authority. This map records, from the code, every environment an organism can be
placed in: what it is responsible for, which layer owns it, who consumes it and
whether it is active, experimental or legacy.

It is an inventory. It removes nothing and changes no authority. Consumers were
traced by import at `main@3246a39d`; test consumers are counted, not listed.

## 2. What the Constitution calls World

Constitution §1, item 3: *"World is the world. `src/symbiont_world/` owns external laws,
opportunities, and dynamics, never cognition or internal organism knowledge."*
Symbiont must not import `symbiont_world`; World must not import `symbiont` or
`symbiont_lab`; the Lab is the only layer that connects them.
`tests/experimental_integrity/test_ground_truth_boundary.py` enforces both import
rules.

So there is exactly one constitutional World: the `symbiont_world` kernel. Every
other environment below is either Lab apparatus, a host boundary, or a resource
surface that predates the kernel.

"World" also names a run regime: the Experience and World architecture's
`world.challenge` and `world.open` run kinds, which are hosted by Physics3D and
do not involve the kernel. ADR-0060 fixes the vocabulary.

## 3. Inventory

| Environment | Location | Owning layer | Responsibility | Role | State |
| --- | --- | --- | --- | --- | --- |
| World kernel | `src/symbiont_world/` | World | Constitution, hex topology, movement, local observation, generic laws, events, RNG, checkpoint. Semantically opaque. | World | Active, maintenance-only |
| World adapter | `src/symbiont_lab/world/` | Lab | The only package that knows what a field, resource or hazard means: genesis ground truth, organism↔World adapter, population runtime, persistence, tick transaction, terrain | Lab connection of World and Symbiont | Active, maintenance-only |
| `PopulationGenesisRuntime(experimental_clean=False)` | `src/symbiont_lab/world/population.py` | Lab | Pre-decontamination population path | Legacy apparatus. The canonical live World refuses it. W03, the study it backed, is closed | Legacy; no study depends on it |
| Physics3D | `src/symbiont_lab/physics3d/` | Lab | PyBullet Body and physical environment recipes (`environments.py`), embodiment runtime, re-embodiment | Embodiment apparatus: Body plus its physical surroundings. Not the constitutional World. | Active |
| `CausalBody` | `src/symbiont_lab/studies/learning/agency_acquisition_body.py` | Lab | Deterministic opaque synthetic Body behind the host discovery/reading boundary | Experimental apparatus (a Body, not a World) | Active in the agency-acquisition studies |
| Standard clean Body | `src/symbiont/core/embodiment/body.py` (`create_standard_body`) with `Individual` | Organism package | Minimal Body for the reduced seed | Experimental apparatus of the clean-embodiment studies | Active in the embodiment falsification studies |
| `SharedHabitat` | `src/symbiont/core/social/ecology.py` | Organism package | Finite shared resource stock with capacity and membership | Resource surface handed to the runtime by the launcher | Active |
| `SocialHabitat` | `src/symbiont/core/social/relations.py` | Organism package | Authorized local population boundary that mediates interaction requests over a finite pool | Population mediator handed to the runtime by the launcher | Active |
| `IntegratedHabitatRuntime` | `src/symbiont_lab/integration/integrated_habitat.py` | Lab | Lifecycle ordering and population bookkeeping for modeled organisms over a `SocialHabitat` | Lab orchestration | Active, one study consumer |
| `LocalHabitat` | `src/symbiont/core/host/local_habitat.py` | Organism package (host boundary) | Filesystem capsule mailbox and embryo incubator for resident organisms | Host habitat of the live resident | Active |
| Host providers | `src/symbiont/host/` | Organism package (host boundary) | Discovery and reading of the real machine | The environment of the live resident | Active |
| Synthetic host events | `src/symbiont/environment/` | Organism package | `HostProfile`, simulated benign/pathogen events and regimes for the legacy `Agent` simulation | Legacy simulation apparatus | Legacy, still consumed |

## 4. Consumers

Non-test source consumers and experiment directories. "Tests" is the number of
test modules that import the name.

| Environment | Source consumers | Experiments | Tests |
| --- | --- | --- | --- |
| `symbiont_world` | `symbiont_lab.world.*` (11 modules), `symbiont_lab.physics3d.environments` (RNG derivation only), `symbiont_lab.studies.embodiment.label_invariance`, `symbiont_lab.studies.world.genesis_viability` | `world/genesis-v1` | 30 |
| `symbiont_lab.world` | `symbiont_lab.cli.world` (`symbiont-world` entry point), `symbiont_lab.observation.bus`, `symbiont_lab.observation.physics3d`, `symbiont_lab.physics3d.runtime`, `symbiont_lab.studies.embodiment.integrity_gates`, `symbiont_lab.studies.embodiment.label_invariance`, `symbiont_lab.studies.world.genesis_viability` | `world/genesis-v1` (`run_w01_w02.py`, `run_w02_retry.py`, `run_w03.py`, `view_world.py`) | 18 |
| Physics3D | `symbiont_lab.app.*` (GUI), `symbiont_lab.cli.main`, `symbiont_lab.server.*`, `symbiont_lab.observation.physics3d`, `symbiont_lab.kernel_characterization.runner`, `symbiont_lab.studies.embodiment.reembodiment_cli`, 11 `symbiont_lab.studies.learning.*` modules, 3 `symbiont_lab.studies.physics3d.*` modules | — | 51 |
| `CausalBody` | `symbiont_lab.studies.learning.{agency_acquisition, binding_degradation, footprint_precision}` | 10 directories under `learning/agency-*` | 18 |
| `SharedHabitat` | `symbiont.core.orchestration.runtime` (constructor handle), `symbiont_lab.studies.shared_habitat_intake`, `symbiont_lab.world.adapter`, `symbiont_lab.world.persistence` | — | 3 |
| `SocialHabitat` | `symbiont.core.orchestration.runtime` (constructor handle), `symbiont_lab.integration.integrated_habitat`, 20 `symbiont_lab.studies.social*` modules | — | 3 |
| `IntegratedHabitatRuntime` | `symbiont_lab.studies.integrated_habitat_runtime` | — | 1 |
| `LocalHabitat` | `symbiont.core.orchestration.resident`, `symbiont_lab.cli.observed_resident` | — | 2 |
| `symbiont.environment` | `symbiont.simulation.engine`, `symbiont_lab.cli.audit`, 5 `symbiont_lab.studies.*` modules (attention, evidence, common), `symbiont_lab.physics3d.{runtime, cli}` (seed derivation) | — | 4 |

## 5. Responsibilities by layer

**World (`symbiont_world`).** External laws, topology, movement resolution, local
observation, opaque signal identifiers, event journal, world RNG and world
checkpoint. Nothing here knows what a quantity means to an organism.

**Lab.** Everything that gives World quantities a meaning or connects an
organism to an environment: genesis ground truth, adapters, population
orchestration, persistence of a populated world, physical simulation, synthetic
Bodies, evaluators.

**Body.** Physical and physiological state of one Body. In Physics3D the Body and
its surroundings live in the same apparatus; the surroundings are Lab fixtures
(`environments.py`), not the constitutional World.

**Organism package.** Holds the host boundary (`symbiont.host`, `LocalHabitat`)
and three environment-side classes that are not organism knowledge:
`SharedHabitat`, `SocialHabitat` and `symbiont.environment`. The runtime does not
construct the habitats; the launcher supplies them and the continuity register
classifies them as process handles (`_habitat`, `_resource_habitats`,
`_social_habitat`: `MUST_RESET`, re-supplied by the launcher).

## 6. Findings

1. **One constitutional World, several environments.** Only `symbiont_world` is
   World in the constitutional sense. Physics3D, `CausalBody` and the standard
   clean Body are embodiment apparatus; `LocalHabitat` and the host providers are
   the host boundary. Calling any of them "World" is a vocabulary error, not a
   second implementation of the same thing.
2. **`symbiont_world` has no exclusive runtime role.** No organism runtime depends
   on it. It is reached only through `symbiont_lab.world`, by the `symbiont-world`
   CLI, two studies and one experiment directory. Physics3D uses one helper from
   it (`derive_world_rng`).
3. **External resource surfaces live in the organism package.** `SharedHabitat`
   and `SocialHabitat` model resources and population boundaries outside the
   organism, yet are defined under `symbiont.core.social` and imported by
   `OrganismRuntime`. They hold no organism knowledge and reach the runtime only
   as launcher-supplied handles, so no ground truth leaks through them. Their
   location is nevertheless in tension with Constitution §1 item 1 ("`src/symbiont/`
   must contain only state, capabilities, and processes belonging to the
   organism") and item 3. The same holds for `symbiont.environment`.
4. **Two legacy environments are still consumed.** `symbiont.environment` backs
   the legacy `Agent` simulation and several studies. The contaminated population
   path no longer backs any study: W03 was closed by the owner on 2026-10-02 and
   its lock test retired (`research/studies/ecology/w03-closure.md`). What still
   constructs that path is test code and one viewer script: the World unit tests
   that build `PopulationGenesisRuntime` without `experimental_clean=True`
   (`test_population`, `test_persistence`, `test_cli_view`,
   `test_terrain_and_movement`, `test_actuation_end_to_end`,
   `test_transaction_integrity`, `tests/unit/observatory/test_world_integration`)
   and `experiments/world/genesis-v1/view_world.py`. Removing the path means
   migrating or retiring those, not a study.
5. **Stale specification paths.** World docstrings pointed at
   `docs/design/symbiont-world-v*.md`, which moved during the 2026-09-25
   documentation migration. They now point at
   `docs/design/archive/symbiont-world-v{1,2}.md` and
   `docs/design/world/symbiont-world-v{3,4}.md`.

## 7. Owner decisions

Decided by [ADR-0060](../../adr/ADR-0060-world-responsibility-and-naming.md)
(2026-10-02): World stays a category with one constitutional kernel; each family
below has one role; "World" is qualified as kernel, adapter or run kind; no new
environment-side class enters the organism package. Items 1 to 3 are deferred
there, item 4 is decided.

1. Whether `SharedHabitat` and `SocialHabitat` should move out of the organism
   package (to World or to the Lab). Twenty-eight source modules import them.
2. Whether Physics3D surroundings should become a World implementation behind the
   World contracts, or stay Lab fixtures.
3. Whether the legacy population path and `symbiont.environment` are retired, and
   with which studies.
4. Vocabulary: whether "World" is reserved for `symbiont_world` and the other
   families are named Body apparatus, habitat and host boundary in documentation.

Under the owner's sequencing of 2026-09-29, World is maintenance-only: bug fixes,
reproducibility and finishing open experiments. None of the decisions above is
authorized by this map.

## 8. Claims this map does not make

- that any environment should be removed or merged;
- that the location of the habitat classes changes organism behaviour;
- that Physics3D is, or should be, the canonical World.
