# Dependency audit

Final layout. Source: `migration/tools/depgraph.py` over the five source roots:
548 modules, 3855 import edges. Counts are runtime imports (`top` = at import
time, `lazy` = inside a function); `TYPE_CHECKING` imports are excluded.

Reproduce:

```bash
python migration/tools/depgraph.py --root symbiont/src --root environment/src \
    --root modality/src --root embodiment/src --root lab/src --edges-from embodiment
```

## Domain-level graph

| From → To | Edges | Class |
|---|---|---|
| symbiont → environment / modality / embodiment / lab | 0 | VALID (enforced) |
| symbiont → pybullet, torch, numpy, PIL | 0 | VALID (enforced) |
| environment → anything first-party | 0 | VALID (enforced) |
| modality → anything first-party | 0 | VALID (enforced) |
| embodiment → modality | 2 | VALID |
| embodiment → environment | 12 | VALID (world adapter) |
| embodiment → symbiont | 50 | TRANSITIONAL: into organism internals, not `symbiont.api` |
| embodiment → lab | 0 | VALID (enforced) |
| lab → symbiont | 793 | TRANSITIONAL: into organism internals (OI-5) |
| lab → embodiment | 66 | VALID |
| lab → environment | 62 | VALID |
| lab → pybullet, torch, numpy, PIL | 20 | VALID: heavy libraries live only in the Lab |

## Pairs required by the instructions (§7)

| Pair | Finding | Class |
|---|---|---|
| Symbiont ↔ World | no edge either way | VALID |
| Symbiont ↔ Physics3D | no edge from the organism; no heavy library in it | VALID |
| Symbiont ↔ Lab | no edge from the organism | VALID |
| Symbiont ↔ Observatory | no edge from the organism; `lab.observatory` → `symbiont` 48 | TRANSITIONAL |
| Symbiont ↔ Embodiment | the `embodiment` package depends on the organism (50). Inside the organism, `core.orchestration` → `actuation` 46 and `core.domains` → `actuation` 48 still tie the core to coupling code | ARCHITECTURAL VIOLATION of the target, inside the organism (OI-3) |
| Embodiment ↔ Physics3D | bodies and apparatus are in `embodiment`; the engine and runtime in `lab.physics3d` compose them | VALID |
| Modality ↔ Environment | no edge | VALID |

## Violations of the target architecture

| # | Edge | Evidence | Class |
|---|---|---|---|
| V1 | organism core → concrete host modality implementations | `core.orchestration.runtime` → `host.providers.{stdlib, stdlib_readings}` (top), `{interoception, linux_surfaces, portable_surfaces}` (lazy); `core.domains.perception` → `host.providers.interoception` (lazy) | ARCHITECTURAL VIOLATION, pinned by ratchet |
| V2 | organism core ↔ host boundary is circular | `core.*` → `symbiont.host` 78; `symbiont.host` → `symbiont.core` 7 | ARCHITECTURAL VIOLATION |
| V3 | embodiment and physics runtime → cognition internals | `embodiment.physics3d.apparatus` and `embodiment.world.adapter` → `symbiont.cognition.{birth, limits}`; `lab.physics3d.runtime` → `symbiont.cognition.{generative, limits, types}` | ARCHITECTURAL VIOLATION, pinned by ratchet |
| V4 | physics runtime → other Lab units | `lab.physics3d` → `lab.app` 4, `lab.modeling` 9, `lab.observation` 3, `lab.experiments` 1 | TRANSITIONAL: keeps engine, runtime and persistence in the Lab |
| V5 | embodiment → organism internals | `apparatus` → host, sensory, actuation, core.embodiment; `world.adapter` → 21 organism modules including `core.orchestration` and `modeling.runtime` | TRANSITIONAL (OI-5) |
| V6 | observation ↔ observatory cycle | `lab.observation` → `lab.observatory` 4; `lab.observatory` → `lab.observation` 4, → `lab.server` 2 | UNCERTAIN |
| V7 | organism submodules → top-level `symbiont` | for `__version__`; and `symbiont/__init__.py` imports `symbiont.core` to hold a pre-existing import cycle in order (OI-6) | PRE-EXISTING |

## Resolved during the migration

- `symbiont.environment` and `symbiont.simulation` (legacy synthetic environment
  and simulation inside the organism namespace) no longer exist.
- Physics3D bodies, apparatus, re-embodiment and the world adapter no longer
  live in the Lab, so the Lab is no longer the only place a body can be defined.
- The vision receptor array is separated from the body that carries it.

## Enforcement

`tests/experimental_integrity/test_five_domain_architecture.py` (25 tests):

- hard rules for every 0-edge row above;
- each source root holds exactly its domain package;
- ratchets on V1 and V3: the exact current edge set is asserted, so the debt
  cannot grow, and a reduction forces the baseline to be tightened;
- `symbiont.api` resolves and carries no modality-specific types.

Not enforced: "embodiment / modality / environment use only `symbiont.api`".
Today embodiment needs organism internals that the API does not expose (OI-5).
