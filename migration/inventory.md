# Architectural inventory

One row per package unit, in the final layout. Sizes, dependencies and consumers
come from `migration/tools/depgraph.py` (static import graph, runtime imports
only; 550 modules, 3860 import edges). Classification is based on what the code
imports and does, not on its name.

Confidence: **high** = ownership follows from the import graph; **medium** =
ownership is clear but the unit is entangled; **low** = mixed responsibilities.

| Domain | Import package | Files | Lines |
|---|---|---|---|
| Symbiont | `symbiont` | 234 | 63062 |
| Environment | `environment` | 17 | 2031 |
| Modality | `modality` | 2 | 151 |
| Embodiment | `embodiment` | 8 | 2806 |
| Lab | `lab` | 270 | 66792 |

## Symbiont — `symbiont/src/symbiont`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Scientific impact | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `core.orchestration` | 8 / 4781 | `OrganismRuntime`, tick, checkpoint, governor, resident | actuation, host, core.embodiment, core.domains | lab.studies, lab.cli, `symbiont.api` | organism checkpoint (schema 11) | `tests/unit/core` | very high | SYMBIONT | high |
| `core.cognition` | 15 / 6200 | attention, memory, consolidation, bridge to the cognition graph | cognition, host, genetics | core.domains, lab.studies | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.domains` | 13 / 5513 | per-tick domains (action, perception, physiology, …) | actuation, host, agency, sensory | core.orchestration | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.embodiment` | 22 / 6281 | body, body schema, physiology, metabolism, embodiment session/episode, re-embodiment | actuation | lab.studies, lab.integration | checkpoint (embodiment history) | `tests/unit/core` | very high | SYMBIONT + EMBODIMENT | low |
| `core.foundation` | 7 / 747 | fingerprint, limits, epistemic | cognition, genetics, host | everything in core | — | `tests/unit/core` | medium | SYMBIONT | high |
| `core.lineage` | 4 / 187 | germline, heritage, inheritance | genetics | lab.studies, `symbiont.api` | checkpoint lineage | `tests/unit/core` | high | SYMBIONT | high |
| `core.regulation`, `core.signals`, `core.social`, `core.host` | 24 / 3278 | innate reactivity, signal knowledge, social relations, advisories | core.foundation, host | core.orchestration, lab.studies | checkpoint | `tests/unit/core` | high | SYMBIONT | high |
| `cognition` | 36 / 5879 | cognition graph, learning, plasticity, generative | genetics | lab.studies, lab.observatory, core | cognition checkpoint | `tests/unit/cognition` | very high | SYMBIONT | high |
| `genetics` | 7 / 1830 | genome (schema 2), germline, expression | — | cognition, lab.evolution | genome | `tests/unit/genetics` | very high | SYMBIONT | high |
| `agency` | 13 / 2218 | intention, policy, prospective agency | actuation | core.domains, modeling | checkpoint | `tests/unit/agency` | high | SYMBIONT | high |
| `modeling` | 18 / 9426 | private models, episodic, culture, symbols | agency, cognition, core.orchestration | lab.studies, lab.modeling, lab.physics3d | private-model state | `tests/unit/modeling` | high | SYMBIONT | medium |
| `actuation` | 26 / 8500 | sensorimotor: binding, effects, surface, acquisition | host | core.domains, core.orchestration, agency | checkpoint | `tests/unit/actuation` | very high | SYMBIONT + EMBODIMENT | low |
| `sensory` | 11 / 1739 | organism-owned transduction, `SensoryModality` substrate families | host | core.domains, lab.integration | checkpoint | `tests/unit/sensory` | high | SYMBIONT + MODALITY | low |
| `host` | generic boundary with a host: contracts, discovery, sampling, readings, acclimation, drift, rhythms, checkpoint file I/O. No concrete channel | core.foundation | core.orchestration, lab.cli, lab.integration | checkpoint file format | `symbiont/tests/unit/host` | high | SYMBIONT (signal machinery) + persistence | medium |
| `api` | 1 / 63 | public surface, re-exports only | core, host.checkpoint | none yet | — | architecture + independence tests | none | SYMBIONT | high |
| `capacity`, `provenance` | 2 / 285 | capacity accounting, causal provenance | — | actuation, agency, modeling | — | `tests/unit` | medium | SYMBIONT | high |

## Environment — `environment/src/environment`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|
| hex world (`topology`, `laws`, `state`, `genesis`, `observation`, `checkpoint`, `events`, …) | 12 / 1019 | world state, laws, ground truth, local observation | stdlib | lab.world, lab.integration.world | world checkpoint | `tests/unit/world` | ENVIRONMENT | high |
| `terrain`, `genesis_v1`, `genesis_v2` | 3 / 773 | terrain generation and world genesis recipes | environment | lab.world, lab.studies | — | `tests/unit/lab/world` | ENVIRONMENT | high |
| `physics3d.environments` | 1 / 239 | Physics3D fixtures and their dynamics | `environment.rng` | lab.physics3d | — | `tests/unit/lab/physics3d` | ENVIRONMENT | high |

## Modality — `modality/src/modality`

| Unit | Responsibility | First-party dependencies | Composed by | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|
| `vision` | square receptor array: bounded luminance per opaque receptor, receptor adjacency. Carrying link, mount pose and receptor ids are supplied by the caller | none | `lab.integration.physics3d.bodies` | `modality/tests`, `lab/tests/unit/lab/physics3d/test_vision_apparatus.py` | MODALITY | high |
| `host` | read-only aggregate channels of the machine: standard-library, Linux and portable surfaces, process telemetry; own record types | none | `lab.integration.organism` | `modality/tests/host` | MODALITY | high |

## Embodiment — `embodiment/src/embodiment`

| Unit | Responsibility | First-party dependencies | Composed by | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|
| `physics3d.humanoid`, `articulated`, `alternative_bodies` | Physics3D bodies and their receptor/effector contracts | none | `lab.physics3d`, `lab.integration` | `embodiment/tests`, `tests/unit/lab/physics3d` | EMBODIMENT | high |
| `physics3d.bodies` | body descriptors, registry class, `vision_body_descriptor(factory)` | none | `lab.integration.physics3d.bodies` | same | EMBODIMENT | high |
| `physics3d.vision` | vision body kind: head mount (link, pose, receptor slots and ids); the receptor array is injected | none | `lab.integration.physics3d.bodies` | same | EMBODIMENT | high |

## Lab — `lab/`

| Unit | Files / LOC | Responsibility | Depends on | Domain | Confidence |
|---|---|---|---|---|---|
| `studies` | 133 / 28147 | study protocols and runners | symbiont, embodiment, lab.physics3d, lab.modeling | LAB | high |
| `experiments` | 11 / 2189 | registry, runner, manifest, execution fingerprint | lab.studies | LAB | high |
| `cli`, `server`, `workbench` | 18 / 3260 | entry points, local server, web workbench | everything | LAB | high |
| `app` | 8 / 4592 | Physics3D run store, session and viewer | embodiment, lab.physics3d | LAB | high |
| `evaluation`, `evolution`, `experience`, `reproduction`, `kernel_characterization` | 21 / 2645 | analysis, baselines | symbiont | LAB | high |
| `integration` | 9 / 2542 | adapters that know more than one domain: Physics3D apparatus (body → organism providers and actuator surface), composed vision body and body catalogue, re-embodiment, hex-world adapter, integrated habitat | symbiont, embodiment, modality, environment | LAB (integration) | high |
| `modeling` | 15 / 2610 | private-model training (torch) | symbiont.modeling | LAB | high |
| `observation`, `observatory` | 23 / 6188 | projection of runs for observation; adapter, journal, schemas | symbiont, each other | LAB / OBSERVABILITY | medium |
| `physics3d` | 25 / 11808 | PyBullet engine, runtime (composition of organism + body + environment), persistence, telemetry v4.1, `resource`, `observer_semantics` | embodiment, environment, symbiont, lab.app/modeling/observation | LAB (composition) with ENVIRONMENT residue | medium |
| `world` | 6 / 2808 | population runtime, transactions, persistence, CLI view | environment, symbiont, lab.integration | LAB (composition) | medium |
| `lab/experiments` | 362 files | experiment specs, runners, results | — | LAB | high |
| `lab/research` | 91 files | evidence registry, audits, protocols | — | LAB | high |
| `lab/examples` | 3 files | example genome, graph, replay | — | LAB | high |

## Left at the repository root

| Path | Classification | Reason |
|---|---|---|
| `scripts/agentctl.py`, `scripts/governance/`, `docs/governance/` | GOVERNANCE | §15: auxiliary system |
| `scripts/bench_*.py`, `characterize_kernel.py`, `aggregate_e8_*`, `run_e8_*`, `reprofile_performance.py` | LAB candidate | OI-7 |
| `tests/` | SHARED-UNRESOLVED | spans every domain (OI-8) |
| `docs/`, `assets/` | SHARED-UNRESOLVED | project-wide |

## Units kept in the organism by decision

`symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory` and
`symbiont.host` hold intrinsic organism state and generic signal machinery.
Concrete external coupling has left them: bodies to `embodiment`, the vision
array and host channels to `modality`, composition to `lab.integration`.
