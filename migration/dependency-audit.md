# Dependency audit

Final layout. Source: `migration/tools/depgraph.py` over the five source roots:
550 modules, 3860 import edges. Counts are runtime imports (`top` = at import
time, `lazy` = inside a function); `TYPE_CHECKING` imports are excluded.

Reproduce:

```bash
python migration/tools/depgraph.py --root symbiont/src --root environment/src \
    --root modality/src --root embodiment/src --root lab/src --edges-from embodiment
```

## Domain-level graph

The four domain libraries are peers. None imports another, none imports the Lab.

| From → To | Edges | Class |
|---|---|---|
| symbiont → embodiment / modality / environment / lab | 0 | VALID (enforced) |
| embodiment → symbiont / modality / environment / lab | 0 | VALID (enforced) |
| modality → symbiont / embodiment / environment / lab | 0 | VALID (enforced) |
| environment → symbiont / embodiment / modality / lab | 0 | VALID (enforced) |
| any of the four → pybullet, torch, numpy, PIL | 0 | VALID (enforced) |
| lab → symbiont, embodiment, modality, environment | many | VALID: the Lab is the composition root |

Declared dependencies match: `symbiont` needs only `cryptography`; `embodiment`,
`modality` and `environment` declare none; `lab` declares the four.

## Pairs required by the instructions (§7)

| Pair | Finding | Class |
|---|---|---|
| Symbiont ↔ World | no edge either way | VALID |
| Symbiont ↔ Physics3D | no edge; no heavy library in the organism | VALID |
| Symbiont ↔ Lab | no edge from the organism | VALID |
| Symbiont ↔ Observatory | no edge from the organism | VALID |
| Symbiont ↔ Embodiment | no edge between the packages. Inside the organism, `core.orchestration` → `actuation` 46 and `core.domains` → `actuation` 48 still tie the core to coupling code that has not been separated | debt inside the organism (OI-3) |
| Embodiment ↔ Physics3D | bodies are in `embodiment`; the engine and runtime in `lab.physics3d` compose them | VALID |
| Modality ↔ Environment | no edge | VALID |

## Debt that remains

| # | Where | Evidence | Class |
|---|---|---|---|
| V1 | organism builds concrete host modality implementations | `core.orchestration.runtime` → `host.providers.{stdlib, stdlib_readings}` (top), `{interoception, linux_surfaces, portable_surfaces}` (lazy); `core.domains.perception` → `host.providers.interoception` (lazy) | ARCHITECTURAL VIOLATION inside the organism, pinned by ratchet (OI-3) |
| V2 | organism core ↔ host boundary is circular | `core.*` → `symbiont.host` 78; `symbiont.host` → `symbiont.core` 7 | ARCHITECTURAL VIOLATION inside the organism |
| V3 | Lab integration code uses organism internals | `lab.integration.physics3d.apparatus` and `lab.integration.world.adapter` → `symbiont.cognition.{birth, limits}`, `symbiont.host`, `symbiont.actuation`, …; `lab.physics3d.runtime` → `symbiont.cognition.{generative, limits, types}` | TRANSITIONAL: allowed for the Lab, but should go through `symbiont.api` (OI-5) |
| V4 | physics runtime ↔ other Lab units | `lab.physics3d` → `lab.app` 4, `lab.modeling` 9, `lab.observation` 3, `lab.experiments` 1 | internal to the Lab |
| V5 | observation ↔ observatory cycle | `lab.observation` ↔ `lab.observatory` 4 each way | internal to the Lab |
| V6 | organism submodules → top-level `symbiont` | for `__version__`; `symbiont/__init__.py` imports `symbiont.core` to hold a pre-existing import cycle in order (OI-6) | PRE-EXISTING |

## Resolved during the migration

- `symbiont.environment` and `symbiont.simulation` no longer exist.
- Physics3D bodies are an independent library; the vision receptor array is
  separated from the body that carries it, and the mount pose belongs to the
  body, not to the channel.
- Code that knew two domains was moved to `lab.integration`: the Physics3D
  apparatus adapters, re-embodiment, the composed vision body and body
  catalogue, and the hex-world adapter.

## Enforcement

Import Linter (`[tool.importlinter]` in `pyproject.toml`, run with
`lint-imports`; in CI, pre-commit and the test suite), three contracts:

1. the four domain libraries are mutually independent;
2. domain libraries do not depend on the Lab;
3. pybullet, torch, numpy and PIL are imported only by the Lab.

`tests/experimental_integrity/test_five_domain_architecture.py` repeats the
matrix as a hard gate, checks that the four `pyproject.toml` declare no
first-party dependency, that each source root holds exactly its package, and
keeps one ratchet (V1). Each library also has a test that runs with nothing
else installed (`symbiont/tests`, `embodiment/tests`, `modality/tests`,
`environment/tests`).
