# ADR-0060 — Responsibility and Naming of World and Environment Families

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** Constitution §1, ADR-0008, ADR-0009, `docs/design/world/world-responsibility-map-v1.md`, issue #280
- **Scope:** Vocabulary, role classification and placement rule for environment-side code. No runtime is moved, merged or removed.

## Context

"World" is used for three different things in the repository:

1. the **World kernel**, `src/symbiont_world/`, which Constitution §1 item 3 names
   as the owner of external laws, opportunities and dynamics;
2. the **World run kinds** of the Experience and World architecture
   (`RunKind.WORLD_CHALLENGE`, `RunKind.WORLD_OPEN`, `WorldConsequencePolicy`):
   a run regime in which consequences are complete and nothing rescues the Body.
   Those runs are hosted today by Physics3D, not by the World kernel;
3. loosely, any environment an organism is placed in: Physics3D surroundings,
   habitats, synthetic Bodies.

The World Responsibility Map inventories every environment family and its
consumers. It records that no organism runtime depends on the World kernel, that
resource and population surfaces live in the organism package, and that two
legacy environments are still consumed. It takes no decision.

The risk is not duplicated code. It is that behaviour specific to one apparatus
is read as a property of "the World", and that new environment-side code has no
rule for where it belongs.

## Decision

### 1. World is a category with one constitutional kernel, not a single interface

"World" stays a conceptual category: the external side of the organism boundary.
No canonical interface or authority spanning all environment families is
introduced. The families have different contracts (hex topology and opaque
signals; rigid-body physics; filesystem mailboxes; resource pools) and no current
consumer needs them unified.

`symbiont_world` remains the only constitutional World implementation. Its
programme status stays `maintenance-only`.

### 2. Vocabulary

| Term | Means | Never means |
| --- | --- | --- |
| **World kernel** | `src/symbiont_world/` | Physics3D, habitats, Bodies |
| **World adapter** | `src/symbiont_lab/world/`: the Lab layer that connects the World kernel to an organism | the kernel itself |
| **World run** | a run of kind `world.challenge` or `world.open`: complete consequences, no rescue | that the World kernel is involved |
| **Environment family** | any of the families in §3 | an interface |
| **Habitat** | a resource, population or mailbox boundary handed to a runtime by its launcher | the World kernel |
| **Body apparatus** | the Lab apparatus that provides a Body and its physical surroundings | a World implementation |

Unqualified "World" is used only for the category or, where the Constitution is
quoted, for the kernel. Documentation and identifiers name the kernel, the
adapter or the run kind explicitly. A result obtained in one family is reported
as a result in that family, not as a property of "the World".

### 3. Role of each environment family

| Family | Location | Role |
| --- | --- | --- |
| World kernel | `src/symbiont_world/` | World |
| World adapter | `src/symbiont_lab/world/` | Compatibility/connection layer between the World kernel and an organism |
| Legacy population path (`experimental_clean=False`) | `src/symbiont_lab/world/population.py` | Legacy |
| Physics3D, including its surroundings recipes | `src/symbiont_lab/physics3d/` | Body apparatus; hosts World runs |
| `CausalBody` | `src/symbiont_lab/studies/learning/agency_acquisition_body.py` | Study apparatus |
| Standard clean Body with `Individual` | `src/symbiont/core/embodiment/body.py` | Study apparatus |
| `SharedHabitat` | `src/symbiont/core/social/ecology.py` | Habitat |
| `SocialHabitat` | `src/symbiont/core/social/relations.py` | Habitat |
| `LocalHabitat` | `src/symbiont/core/host/local_habitat.py` | Habitat (host boundary) |
| Host providers | `src/symbiont/host/` | Host boundary |
| `IntegratedHabitatRuntime` | `src/symbiont_lab/integration/integrated_habitat.py` | Lab orchestration over a habitat |
| Synthetic host events | `src/symbiont/environment/` | Legacy |

### 4. Responsibilities that exist in more than one family

These are recorded, not merged:

| Responsibility | Where it exists |
| --- | --- |
| Finite resource stock and intake | World kernel `ResourceLaw` pools (through the adapter); `SharedHabitat` |
| Population membership and capacity | World kernel occupancy grid; `SocialHabitat`; `SharedHabitat` capacity |
| Namespaced seed derivation | `symbiont_world.rng`; `symbiont.environment.rng` (same scheme, deliberately not shared, because the kernel imports nothing) |
| Persistence of an environment with its organisms | `symbiont_lab.world.persistence`; the Physics3D bundle and Body checkpoint |
| Hazard and physiological consequence | World kernel `HazardLaw`; Physics3D contact and metabolism |

Unifying any of them is a separate decision with its own consumers and
experimental impact.

### 5. Placement rule for new code

1. External laws, topology, dynamics and opaque observation of a spatial world go
   in the World kernel, which imports nothing from `symbiont` or `symbiont_lab`.
2. Anything that gives environment quantities a meaning, connects an organism to
   an environment, simulates a Body or its surroundings, or orchestrates a
   population goes in the Lab.
3. No new environment-side class is added to the organism package
   (`src/symbiont/`). The existing ones — `SharedHabitat`, `SocialHabitat`,
   `HabitatSnapshot`, `LocalHabitat` and `symbiont.environment` — are a closed
   list, in tension with Constitution §1 item 1 and tolerated because they hold no
   organism knowledge and reach the runtime only as launcher-supplied handles.
4. A new apparatus is named for what it is (Body, habitat, surroundings), not
   "World".

`tests/experimental_integrity/test_environment_placement.py` enforces rule 3.

### 6. What is deferred

- Moving the habitat classes out of the organism package. Twenty-eight source
  modules import them and World is maintenance-only; this is revisited at the
  Individual Readiness Gate.
- Whether Physics3D surroundings should implement World kernel contracts.
- Retiring the legacy population path and `symbiont.environment`. Both still
  have consumers, listed in the responsibility map. Nothing is removed while a
  consumer remains.

## Consequences

- Every active environment family has exactly one role.
- A reader can tell whether "World" means the kernel, the adapter or a run kind.
- The organism package cannot silently gain more environment-side classes.
- No experiment, checkpoint or apparatus behaviour changes.

## Alternatives considered

- **Reserve "World" for the kernel only.** Rejected: the Experience and World
  architecture already uses "World" for a run regime hosted by Physics3D, and
  renaming accepted run kinds would touch recorded run provenance.
- **Introduce a canonical World interface implemented by every family.**
  Rejected for now: no consumer needs it, and it would have to be designed
  against four unrelated contracts while World is maintenance-only.
- **Move the habitat classes now.** Deferred, see §6.
