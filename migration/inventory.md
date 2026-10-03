# Architectural inventory (Phase 1)

> Written before the packages took their domain names and before the legacy
> removals. `symbiont_lab` is now `lab`, `symbiont_world` is `environment`, and
> `symbiont.simulation`, `symbiont.environment`, `observatory` (front-end) and the
> legacy studies no longer exist. See `mapping.md` for the current paths.

One row per package unit. Sizes, dependencies and consumers come from
`migration/tools/depgraph.py` (static import graph, runtime imports only).
Classification is based on what the code imports and does, not on its name.

Confidence: **high** = ownership follows from the import graph; **medium** =
ownership is clear but the unit is entangled; **low** = mixed responsibilities.

## Organism — `symbiont/src/symbiont`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Scientific impact | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `core.orchestration` | 8 / 4789 | `OrganismRuntime`, tick, checkpoint, governor, resident | actuation, host, core.embodiment, core.domains | lab.studies, lab.cli, modeling | organism checkpoint v11 | `tests/unit/core` | very high | SYMBIONT | high |
| `core.cognition` | 20 / 6798 | agent, attention, memory, bridge to cognition graph | cognition, host, genetics | core.domains, lab.studies | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.domains` | 13 / 5513 | per-tick domains (action, perception, physiology…) | actuation, host, agency, sensory | core.orchestration | checkpoint | `tests/unit/core` | very high | SYMBIONT | high |
| `core.embodiment` | 22 / 6281 | body, body schema, physiology, metabolism, re-embodiment, embodiment session/episode | actuation | lab.studies, lab.physics3d | checkpoint (embodiment history) | `tests/unit/core` | very high | SYMBIONT + EMBODIMENT | low |
| `core.foundation` | 8 / 867 | host model, fingerprint, limits | cognition, genetics, host | everything in core | — | `tests/unit/core` | medium | SYMBIONT | high |
| `core.lineage` | 5 / 211 | germline, heritage, inheritance | genetics | lab.studies | checkpoint lineage | `tests/unit/core` | high | SYMBIONT | high |
| `core.regulation`, `core.signals`, `core.social`, `core.host` | 25 / 3397 | innate reactivity, signal knowledge, social ledger, advisories | core.foundation, host | core.orchestration, lab.studies | checkpoint | `tests/unit/core` | high | SYMBIONT | high |
| `cognition` | 36 / 5904 | cognition graph, learning, plasticity, generative | genetics | lab.studies, observatory, core | cognition checkpoint | `tests/unit/cognition` | very high | SYMBIONT | high |
| `genetics` | 8 / 2067 | genome, schema, germline, migration | — | cognition, lab.evolution | genome | `tests/unit/genetics` | very high | SYMBIONT | high |
| `agency` | 13 / 2218 | intention, policy, prospective agency | actuation | core.domains, modeling | checkpoint | `tests/unit/agency` | high | SYMBIONT | high |
| `modeling` | 18 / 9426 | private models, episodic, culture, symbols | agency, cognition, core.orchestration | lab.studies, lab.modeling, lab.physics3d | private-model state | `tests/unit/modeling` | high | SYMBIONT | medium |
| `actuation` | 26 / 8500 | sensorimotor v2: binding, effects, surface, acquisition | host | core.domains, core.orchestration, agency | checkpoint | `tests/unit/actuation` | very high | SYMBIONT + EMBODIMENT | low |
| `sensory` | 11 / 1739 | organism-owned transduction, `SensoryModality` substrate families | host | core.domains, lab.physics3d | checkpoint | `tests/unit/sensory` | high | SYMBIONT + MODALITY | low |
| `host` | 23 / 6025 | boundary with a consenting local host: readings, acclimation, drift, checkpoint file I/O, `providers/` | core.foundation | core.orchestration, lab.cli, lab.physics3d | checkpoint file format and migrations | `tests/unit/host` | high | MODALITY (host) + persistence | low |
| `environment` | 4 / 234 | legacy synthetic host events and RNG streams | core.foundation | simulation, lab.studies, lab.cli | — | `tests/unit/environment` | legacy studies | ENVIRONMENT (legacy) | high |
| `simulation` | 7 / 894 | legacy agent-population simulation engine | core.cognition, environment | lab.studies, lab.cli, lab.archive | run results | `tests/integration` | legacy studies | LAB (legacy) | high |
| `api` (new) | 1 / 66 | public surface, re-exports only | core, host.checkpoint | — | — | architecture test | none | SYMBIONT | high |

## Environment — `environment/src/symbiont_world`

| Unit | Files / LOC | Responsibility | Depends on | Main consumers | Persisted formats | Tests | Domain | Confidence |
|---|---|---|---|---|---|---|---|---|
| `symbiont_world` | 12 / 1019 | hex world: topology, laws, state, ground truth, local observation, checkpoint | stdlib only | lab.world, lab.studies, lab.physics3d | world checkpoint | `tests/unit/world` | ENVIRONMENT | high |

## Lab — `lab/src/symbiont_lab`, `lab/experiments`, `lab/research`, `lab/examples`

| Unit | Files / LOC | Responsibility | Depends on | Domain | Confidence |
|---|---|---|---|---|---|
| `studies` | 151 / 32900 | study protocols and runners | organism, lab.physics3d, lab.modeling | LAB | high |
| `experiments` | 11 / 2229 | registry, runner, manifest, execution fingerprint | lab.studies | LAB | high |
| `cli`, `app`, `server`, `workbench` | 39 / 9763 | entry points, UI, local server | everything | LAB | high |
| `archive`, `evaluation`, `evolution`, `experience`, `integration`, `reproduction`, `kernel_characterization` | 27 / 3353 | analysis, baselines, composition | organism | LAB | high |
| `modeling` | 15 / 2586 | private-model training (torch) | symbiont.modeling | LAB | high |
| `observation` | 13 / 3393 | projection of runs for observation | observatory, lab.physics3d | LAB / OBSERVABILITY | medium |
| `world` | 11 / 4486 | adapter between `symbiont_world` and the organism, population runtime, persistence | symbiont_world, organism internals | EMBODIMENT + ENVIRONMENT + LAB | low |
| `physics3d` | 50 / 17615 | PyBullet engine, humanoid and bodies, vision, apparatus, re-embodiment, telemetry | organism internals, lab.app, lab.modeling, lab.observation | ENVIRONMENT + EMBODIMENT + MODALITY | low |
| `lab/experiments` | 377 files | experiment specs, runners, results (some frozen) | — | LAB | high |
| `lab/research` | 91 files | evidence registry, audits, protocols | — | LAB | high |
| `lab/examples` | 3 files | example genome/graph, replay | — | LAB | high |

## Left in place

| Path | Classification | Reason |
|---|---|---|
| `observatory/` | OBSERVABILITY | §15: auxiliary system, not forced into the five domains |
| `scripts/agentctl.py`, `scripts/governance/`, `docs/governance/` | GOVERNANCE | §15 |
| `scripts/bench_*.py`, `characterize_kernel.py`, `aggregate_e8_*`, `run_e8_*`, `reprofile_performance.py` | LAB candidate | benchmarks and analysis; not moved, see `open-issues.md` OI-7 |
| `tests/` | SHARED-UNRESOLVED | spans every domain; split per domain is a later step (OI-8) |
| `docs/`, `assets/` | SHARED-UNRESOLVED | project-wide |

## Units not migrated because ownership is mixed

`core.embodiment`, `actuation`, `sensory`, `host`, `symbiont_lab.physics3d`
and `symbiont_lab.world` each combine more than one target domain. They were
relocated with the package that currently contains them and left internally
unchanged. `embodiment/README.md` and `modality/README.md` list the candidates
and the import edges that block extraction.
