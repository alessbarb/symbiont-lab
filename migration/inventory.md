# Architectural inventory

One row per package unit, in the final layout. Sizes, dependencies and consumers
come from `migration/tools/depgraph.py` (static import graph, runtime imports
only; 548 modules, 3855 import edges). Classification is based on what the code
imports and does, not on its name.

Confidence: **high** = ownership follows from the import graph; **medium** =
ownership is clear but the unit is entangled; **low** = mixed responsibilities.

| Domain | Import package | Files | Lines |
|---|---|---|---|
| Symbiont | `symbiont` | 234 | 63062 |
| Environment | `environment` | 17 | 2031 |
| Modality | `modality` | 2 | 150 |
| Embodiment | `embodiment` | 13 | 4839 |
| Lab | `lab` | 263 | 64691 |

## Symbiont — `symbiont/src/symbiont`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Scientific impact | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `core.orchestration` | 8 / 4781 | `OrganismRuntime`, tick, checkpoint, governor, resident | actuation, host, core.embodiment, core.domains | lab.studies, lab.cli, `symbiont.api` | organism checkpoint (schema 11) | `tests/unit/core` | very high | SYMBIONT | high |
| `core.cognition` | 15 / 6200 | attention, memory, consolidation, bridge to the cognition graph | cognition, host, genetics | core.domains, lab.studies | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.domains` | 13 / 5513 | per-tick domains (action, perception, physiology, …) | actuation, host, agency, sensory | core.orchestration | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.embodiment` | 22 / 6281 | body, body schema, physiology, metabolism, embodiment session/episode, re-embodiment | actuation | lab.studies, embodiment | checkpoint (embodiment history) | `tests/unit/core` | very high | SYMBIONT + EMBODIMENT | low |
| `core.foundation` | 7 / 747 | fingerprint, limits, epistemic | cognition, genetics, host | everything in core | — | `tests/unit/core` | medium | SYMBIONT | high |
| `core.lineage` | 4 / 187 | germline, heritage, inheritance | genetics | lab.studies, `symbiont.api` | checkpoint lineage | `tests/unit/core` | high | SYMBIONT | high |
| `core.regulation`, `core.signals`, `core.social`, `core.host` | 24 / 3278 | innate reactivity, signal knowledge, social relations, advisories | core.foundation, host | core.orchestration, lab.studies | checkpoint | `tests/unit/core` | high | SYMBIONT | high |
| `cognition` | 36 / 5879 | cognition graph, learning, plasticity, generative | genetics | lab.studies, lab.observatory, core | cognition checkpoint | `tests/unit/cognition` | very high | SYMBIONT | high |
| `genetics` | 7 / 1830 | genome (schema 2), germline, expression | — | cognition, lab.evolution | genome | `tests/unit/genetics` | very high | SYMBIONT | high |
| `agency` | 13 / 2218 | intention, policy, prospective agency | actuation | core.domains, modeling | checkpoint | `tests/unit/agency` | high | SYMBIONT | high |
| `modeling` | 18 / 9426 | private models, episodic, culture, symbols | agency, cognition, core.orchestration | lab.studies, lab.modeling, lab.physics3d | private-model state | `tests/unit/modeling` | high | SYMBIONT | medium |
| `actuation` | 26 / 8500 | sensorimotor: binding, effects, surface, acquisition | host | core.domains, core.orchestration, agency | checkpoint | `tests/unit/actuation` | very high | SYMBIONT + EMBODIMENT | low |
| `sensory` | 11 / 1739 | organism-owned transduction, `SensoryModality` substrate families | host | core.domains, embodiment | checkpoint | `tests/unit/sensory` | high | SYMBIONT + MODALITY | low |
| `host` | 23 / 5704 | boundary with a consenting local host: readings, acclimation, drift, checkpoint file I/O, `providers/` | core.foundation | core.orchestration, lab.cli, embodiment | checkpoint file format | `tests/unit/host` | high | MODALITY (host) + persistence | low |
| `api` | 1 / 63 | public surface, re-exports only | core, host.checkpoint | none yet | — | architecture + independence tests | none | SYMBIONT | high |
| `capacity`, `provenance` | 2 / 285 | capacity accounting, causal provenance | — | actuation, agency, modeling | — | `tests/unit` | medium | SYMBIONT | high |

## Environment — `environment/src/environment`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|
| hex world (`topology`, `laws`, `state`, `genesis`, `observation`, `checkpoint`, `events`, …) | 12 / 1019 | world state, laws, ground truth, local observation | stdlib | lab.world, embodiment.world | world checkpoint | `tests/unit/world` | ENVIRONMENT | high |
| `terrain`, `genesis_v1`, `genesis_v2` | 3 / 773 | terrain generation and world genesis recipes | environment | lab.world, lab.studies | — | `tests/unit/lab/world` | ENVIRONMENT | high |
| `physics3d.environments` | 1 / 239 | Physics3D fixtures and their dynamics | `environment.rng` | lab.physics3d | — | `tests/unit/lab/physics3d` | ENVIRONMENT | high |

## Modality — `modality/src/modality`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|---|
| `vision` | 1 / 144 | square receptor array on a body link: bounded luminance per opaque receptor, receptor adjacency | — | embodiment.physics3d.vision | `tests/unit/lab/physics3d/test_vision_apparatus.py` | MODALITY | high |

## Embodiment — `embodiment/src/embodiment`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|---|
| `physics3d.humanoid`, `articulated`, `alternative_bodies`, `bodies` | 4 | Physics3D bodies and their receptor/effector contracts | modality (via `vision`) | lab.physics3d, lab.app, lab.studies | `tests/unit/lab/physics3d` | EMBODIMENT | high |
| `physics3d.vision` | 1 | vision body kind: binds the receptor array to the humanoid | modality | lab.physics3d | same | EMBODIMENT | high |
| `physics3d.apparatus` | 1 | adapters presenting a Physics3D body to the organism as discovery/reading providers and an actuator surface | symbiont (host, sensory, actuation, cognition.birth/limits) | lab.physics3d | same | EMBODIMENT | medium |
| `physics3d.reembodiment`, `longitudinal` | 2 | re-embodiment of a checkpoint into another body; epoch summaries | symbiont (host.checkpoint, core.embodiment, actuation) | lab.physics3d, lab.studies | `tests/unit/lab/physics3d/test_reembodiment.py` | EMBODIMENT | high |
| `world.adapter`, `world.deferred` | 2 | coupling between the hex world and an organism | environment, symbiont | lab.world | `tests/unit/lab/world` | EMBODIMENT | medium |

## Lab — `lab/`

| Unit | Files / LOC | Responsibility | Depends on | Domain | Confidence |
|---|---|---|---|---|---|
| `studies` | 133 / 28147 | study protocols and runners | symbiont, embodiment, lab.physics3d, lab.modeling | LAB | high |
| `experiments` | 11 / 2189 | registry, runner, manifest, execution fingerprint | lab.studies | LAB | high |
| `cli`, `server`, `workbench` | 18 / 3260 | entry points, local server, web workbench | everything | LAB | high |
| `app` | 8 / 4592 | Physics3D run store, session and viewer | embodiment, lab.physics3d | LAB | high |
| `evaluation`, `evolution`, `experience`, `integration`, `reproduction`, `kernel_characterization` | 23 / 3086 | analysis, baselines, composition | symbiont | LAB | high |
| `modeling` | 15 / 2610 | private-model training (torch) | symbiont.modeling | LAB | high |
| `observation`, `observatory` | 23 / 6188 | projection of runs for observation; adapter, journal, schemas | symbiont, each other | LAB / OBSERVABILITY | medium |
| `physics3d` | 25 / 11808 | PyBullet engine, runtime (composition of organism + body + environment), persistence, telemetry v4.1, `resource`, `observer_semantics` | embodiment, environment, symbiont, lab.app/modeling/observation | LAB (composition) with ENVIRONMENT residue | medium |
| `world` | 6 / 2808 | population runtime, transactions, persistence, CLI view | environment, embodiment, symbiont | LAB (composition) | medium |
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

## Units whose ownership is still mixed

`symbiont.core.embodiment`, `symbiont.actuation`, `symbiont.sensory` and
`symbiont.host` each combine organism state with coupling or channel code and
were left inside the organism. `open-issues.md` OI-3 gives the import edges that
block extraction.
