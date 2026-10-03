# Dependency audit (Phase 2)

> Written before the packages took their domain names and before the legacy
> removals. `symbiont_lab` is now `lab`, `symbiont_world` is `environment`, and
> `symbiont.simulation`, `symbiont.environment`, `observatory` (front-end) and the
> legacy studies no longer exist. See `mapping.md` for the current paths.

Source: `migration/tools/depgraph.py` over `symbiont/src`, `environment/src`,
`lab/src` and `.` (observatory): 636 modules, 4292 import edges. Counts are
runtime imports (`top` = at import time, `lazy` = inside a function);
`TYPE_CHECKING` imports are excluded.

Reproduce:

```bash
python migration/tools/depgraph.py --root symbiont/src --root environment/src \
    --root lab/src --root . --edges-from symbiont
```

## Required pairs (§7)

| Pair | Finding | Class |
|---|---|---|
| Symbiont → World (`symbiont_world`) | 0 edges | VALID |
| World → Symbiont | 0 edges; `symbiont_world` imports only the standard library | VALID |
| Symbiont → Physics3D | 0 edges; no `pybullet`, `torch`, `numpy` or `PIL` import anywhere in `symbiont` | VALID |
| Symbiont → Lab | 0 edges | VALID |
| Symbiont → Observatory | 0 edges | VALID |
| Lab → Symbiont | 863 edges into organism internals, not through an API | TRANSITIONAL (OI-5) |
| Observatory → Symbiont | 48 edges into `symbiont.cognition`, `symbiont.core`, `symbiont.host`, `symbiont.genetics` | TRANSITIONAL (OI-5) |
| Observatory ↔ Lab | observatory → `symbiont_lab.observation`/`server` (6); lab → observatory (26) | UNCERTAIN: mutual dependency between two auxiliary systems |
| Symbiont ↔ Embodiment | not separable today: `core.orchestration` → `actuation` 46, `core.domains` → `actuation` 48, `core.embodiment` → `actuation` 6 | ARCHITECTURAL VIOLATION of the target (OI-3) |
| Embodiment ↔ Physics3D | `symbiont_lab.physics3d` → `symbiont.core.embodiment` 15, → `symbiont.actuation` 7, → `symbiont.sensory` 2 | TRANSITIONAL |
| Modality ↔ Environment | `symbiont.sensory` → `symbiont.host` 7; `physics3d.vision` lives inside the physics package | UNCERTAIN |

## Violations of the target architecture

| # | Edge | Evidence | Class |
|---|---|---|---|
| V1 | organism core → concrete host modality implementations | `core.orchestration.runtime` → `host.providers.{stdlib, stdlib_readings}` (top), `{interoception, linux_surfaces, portable_surfaces}` (lazy); `core.domains.perception` → `host.providers.interoception` (lazy) | ARCHITECTURAL VIOLATION, pinned by ratchet |
| V2 | organism core ↔ host boundary is circular | `core.*` → `symbiont.host` 78 edges; `symbiont.host` → `core.foundation` 7, → `core.cognition` 1 (lazy) | ARCHITECTURAL VIOLATION |
| V3 | physics apparatus → cognition internals | `physics3d.apparatus` → `cognition.{birth, limits}`; `physics3d.runtime` → `cognition.{generative, limits, types}` | ARCHITECTURAL VIOLATION, pinned by ratchet |
| V4 | physics (environment/embodiment candidate) → lab | `physics3d` → `symbiont_lab.{app 5, experiments 1, observation 3, modeling 9}` | ARCHITECTURAL VIOLATION: blocks moving physics3d out of Lab |
| V5 | world adapter → organism internals | `symbiont_lab.world.adapter` → 21 organism modules (`actuation`, `cognition`, `core.embodiment`, `core.orchestration`, `host`, `genetics`, `modeling`) | TRANSITIONAL |
| V6 | legacy synthetic environment inside the organism namespace | `symbiont.environment`, `symbiont.simulation`; `symbiont/__init__.py` re-exports `symbiont.simulation` | TRANSITIONAL, pinned by guard (OI-2) |
| V7 | organism submodules → top-level `symbiont` | `core.orchestration.canonical_birth` (top), `core.orchestration.runtime` and `core.foundation.fingerprint` (lazy), for `__version__` | VALID but it makes the legacy simulation load with every organism import |

## Edges that are valid

- `symbiont.genetics` and `symbiont_world` have no first-party dependencies.
- `symbiont.cognition` depends only on `genetics`, `core.foundation`, `capacity`.
- Lab depends on everything; nothing in `symbiont` or `symbiont_world` depends on Lab.

## Enforcement

`tests/experimental_integrity/test_five_domain_architecture.py` (19 tests):

- hard rules: `symbiont` ✗→ `symbiont_lab`, `symbiont_world`, `observatory`,
  pybullet, torch, numpy, PIL; `symbiont_world` ✗→ `symbiont`, `symbiont_lab`,
  `observatory`, and the same heavy libraries;
- ratchets for V1, V3 and V6: the exact current edge set is asserted, so the
  debt cannot grow, and a reduction forces the baseline to be tightened;
- each source root holds exactly its domain package.

Not yet enforced: `symbiont` ✗→ embodiment and `embodiment`/`modality` ✗→
cognition internals as package-level rules, because those domains are not
separate packages yet (OI-3).
