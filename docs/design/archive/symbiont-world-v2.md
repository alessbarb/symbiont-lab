---
id: design.world.symbiont-world-v2
title: "Symbiont World V2"
document_type: design
domain: world
status: superseded
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Symbiont World v2

> **Implemented and closed**, except §7 (movement capacity gate: open door, concrete design not approved — deliberately remains without code). §3–§6 and §8 are implemented, tested, and W03 was run against real data: **rejects H0** (see `experiments/world/genesis-v1/audit-w03.md`). The actual implementation status is verified in `docs/roadmap.md` / `ORGANISM.md`, same as v1.

## 1. Scientific question

> Do 8 founders without mutation produce ecological differentiation (niches) purely ontogenetically/socially? (W03, v1 §8)

W03 is the next gate after W01/W02 (both H0). The formal barrier of v1 §8 remains in effect: W03 only means something because W01/W02 were actually executed, not because unproven adaptation is assumed.

## 2. What it inherits from v1 unchanged

Packages (§2 of v1): `symbiont_world` continues to import nothing; `symbiont_lab` remains the only adapter; `symbiont` continues without gaining any new method or type **except** as described in §7 (capacity gate, explicitly approved by the owner, not ambient). The epistemological invariants of v1 §3 (no ground truth to the organism, strict determinism, no Observatory→World channel, no imposed fitness, no global broadcast, no physiology duplication, tick atomicity) are inherited without modification and are extended in §4.

All v1 contracts (`WorldObservation`/`WorldAction`, `WorldConstitution`, `WorldEvent`, `WorldState`/`TickTransaction`, `HexTopology`/`OccupancyGrid`/`WorldBody`, `PeriodicFieldLaw`/`ResourceLaw`/`HazardLaw`, `SingleOrganismGenesisRuntime`) remain valid as is. v2 extends them **additively** — no v1 test can fail due to a v2 change (gate V02-08, §8).

## 3. Regional heterogeneity of `GroundTruth` (the most important finding of v1)

`WorldEnvironment` currently applies the **same** `ResourceLaw`/`HazardLaw` to every cell; only the pool value per cell varies, never the law. Without regional variation, no niche can emerge — every cell is functionally identical. This is corrected non-disruptively:

```
RegionId = str   # opaco, igual disciplina que FieldId/ResourceId/HazardId

GroundTruth {
    fields: Mapping[FieldId, PeriodicFieldLaw]         # sin cambios, global
    resources: Mapping[ResourceId, ResourceLaw]         # sin cambios: ley
                                                         # base/fallback
    hazards: Mapping[HazardId, HazardLaw]               # sin cambios: ley
                                                         # base/fallback
    region_of: Callable[[HexCoord], RegionId] | None = None
    regional_resources: Mapping[RegionId, Mapping[ResourceId, ResourceLaw]] = {}
    regional_hazards: Mapping[RegionId, Mapping[HazardId, HazardLaw]] = {}
}
```

`region_of`/`regional_resources`/`regional_hazards` are optional with default `None`/`{}`: a v1 `GroundTruth` without these fields behaves exactly the same as in v1 (total fallback to the base law). This is what makes the change additive, not disruptive — no W0–W3 test should require modification.

`WorldEnvironment.resource_pool(cell)`/`renew_resources(cell)`/`acquire(...)` change their internal law resolution:

```
law_for(cell, resource_id):
    region = ground_truth.region_of(cell) if ground_truth.region_of else None
    regional = ground_truth.regional_resources.get(region, {})
    return regional.get(resource_id, ground_truth.resources[resource_id])
```

Same opacity discipline as v1 §3 inv. 1: `RegionId` is an opaque hash: the real semantics of a region ("north, high ground, scarce resource") lives solely in apparatus metadata within `symbiont_lab`, just like `GENESIS_V1_METADATA` for fields/resources/hazards — never in `symbiont_world`.

Fields remain global (uniform time cycles) in v2; a spatial field gradient is out of scope, just like in v1 §13.

## 4. Multi-organism: founders and occupation at scale

### Deterministic founder placement

Pure function, evaluator-side (`symbiont_lab.world`), never inside `symbiont_world`:

```
founder_placement(world_seed: int, topology: HexTopology, count: int) -> tuple[HexCoord, ...]
```

Deterministic for `(world_seed, topology, count)`; produces `count` distinct cells within the limits of `topology`, using `derive_world_rng(world_seed, "genesis.founder-placement")` (same derivation scheme as the rest of the kernel, v1 §2) to choose without collision. It does not guarantee minimum dispersion among founders in v2 — that is a refinement of v3 if it proves necessary after observing W03.

### 8-organism occupation (no resource contention yet)

`OccupancyGrid` was never exercised with more than one occupant — W3 only had one stationary organism. v2 does test this: 8 founders occupying 8 distinct cells simultaneously, with `state.occupancy.occupy()` failing correctly upon collision (V02-02).

**Honest correction on resource contention**, found during implementation: resource pools are per-cell (`dict[HexCoord, dict[ResourceId, float]]`, v1 §3), not per-region. Regional heterogeneity (§3) only means two cells in the same region share the same *law* — each still has its own independent pool. Therefore **there is no real resource contention among founders in v2**: each has its own pool in its own cell, shared law or not. A pool truly shared by region (or remote acquisition) is out of v2 — it is a candidate for v3, not a debt of v2.

The resolution of simultaneous intents (`resolve_movement`, v1 §5) remains unexercised with more than one organism in v2: without approved movement (§7), no organism attempts to occupy another's cell. Gate V02-04 (§10) is marked as not applicable in v2 for this reason, not omitted by oversight.

### `SingleOrganismGenesisRuntime` → multi-organism runtime

The W3 adapter is extended (not replaced) toward a runtime that sustains 8 instances of `ModeledOrganismRuntime`, each with its own `WorldReadingProvider`/`resource_habitats`, all sharing the same `WorldState`/`WorldEnvironment`. The tick order per organism follows the same rule from v1 §5 (never depends on dictionary iteration order; deterministic order by sorted `organism_id`).

## 5. W02 retry with real divergence mechanism

The v1 audit found that `organism_seed` alone has no causal path to the behavior of a solitary organism with `exploration=0.0`, no plasticity, no reproduction. v2 retries W02 by activating `sensory_plasticity=True`/`discover_senses=True` in the adapter — both already exist in `symbiont`, without core changes. The protocol:

```
replica_a, replica_b: mismo world_seed, mismo GroundTruth, misma celda,
distinto organism_seed, sensory_plasticity=True, discover_senses=True

métrica: distancia entre los conjuntos de sensores activos/seleccionados
         de cada réplica tras N ticks (ya expuesto por
         AdaptiveSenseModel/SensorySystem existente), más el
         composite_score de v1 (mean reserve + integrity)
```

Same discipline as v1: the result (diverges or not) is reported exactly as it turns out, without converting convergence into failure nor divergence into premature success. If it also doesn't diverge with active plasticity, that is also honestly documented — it would be another real methodological finding, not a failure to hide.

## 6. Deferred damage ("immediate benefit, deferred damage")

v1 §7 required at least one resource with this profile; `ResourceLaw` still does not model it (it only governs the pool, not the effect). It is implemented entirely in `symbiont_lab` (adapter), without a new API in `symbiont_world` or `symbiont`:

```
DeferredEffect {
    organism_id: str
    due_tick: int
    amount: float   # en (0, 0.25], mismo contrato que
                     # apply_environmental_damage
}
```

Upon acquiring from the resource marked as "deferred" (apparatus metadata, not kernel), the adapter enqueues a `DeferredEffect` with `due_tick = current_tick + delay` (fixed delay per resource, defined in `world-ground-truth.toml`-equivalent of `symbiont_lab.world`). On every tick, before resolving the organism's action, the adapter applies any `DeferredEffect` whose `due_tick` has already been reached, via the same `apply_environmental_damage` it already uses for hazards. The queue is bounded (fixed maximum size, e.g., 32 entries) — an organism cannot accumulate unlimited damage debt.

## 7. Capacity gate: spatial movement

**Status: open door, concrete design not yet approved.**

v1 avoided this by discovering that W01/W02 do not need it. W03 does not strictly need it either (8 stationary founders can already show ecological differentiation solely through regional heterogeneity, §3). The default for v2 remains **without movement**, unless the concrete design below is approved separately.

Decision already recorded (taken during v2 scoping, with the owner):

- Rejected: not having movement indefinitely — it is wanted, not just tolerated.
- Rejected: mapping movement onto the execution of `INVESTIGATE` — it was considered epistemologically risky (it would silently change the meaning of an already audited action).
- Accepted: a new `ActionKind` (`MOVE`, tentative) in `symbiont/core/behavior.py`, following the same audited pattern as `INTAKE`/`REPAIR` — a real capacity change to the frozen organism, so the freeze contract of `roadmap.md` requires it to be an explicit and separate review gate, not an environmental part of v2.

Pending decision (needs its own design pass before implementing a single line):

1. What `ActionOpportunity`/`ExpectedOutcome` exposes a `MOVE` opportunity (cost, viability/integrity/information dimensions) — determines if cognition can manage to choose it rationally over `INTAKE`/`REST`, relevant given that W01 found that the current action model already fails to connect real consequences (hazard damage) with opportunity selection.
2. Whether `MOVE` takes an opaque direction (matches exactly the `ActuatorId` already used by `WorldAction.move`, without new plumbing on the World side — `HexTopology.resolve_move`/`OccupancyGrid.move` from W1 already implement the physics) or a target cell concept.
3. Impact on checkpoint/replay: a new `ActionKind` enters `ActionExecutionResult`/behavioral state history — it requires the same replay discipline as the rest of the frozen core.

This section is the artifact satisfying the CLAUDE.md instruction to "stop for an explicit owner decision before adding a new permission class... or any new real-world action boundary": the decision to open the door is recorded; the concrete design of `ActionKind` still needs its own review before touching a single line of `symbiont`.

## 8. Observatory: visualization layer for the human operator

v1 had nothing to look at — `WorldTickRecord`/`WorldEvent` only existed as structures printed by a script. With 8 founders and regional heterogeneity, a passive view is needed, same architectural rule as any other Observatory surface (CLAUDE.md: "the display does not control cognition"; v1 §29: `Observatory → World` does not exist, not even disabled).

**In scope:**

- Hexagonal render of occupied cells (`OccupancyGrid.snapshot()`), founder positions, current tick/epoch.
- Field/resource/hazard values per cell, labeled with their real semantic name from `GENESIS_V1_METADATA` — Observatory is evaluator-side and is already allowed to know the meaning (the opacity invariant of v1 §7 only binds what reaches the *organism*, never what a human operator can see). This is exactly what `GENESIS_V1_METADATA` was built for in v1 and has been unused since.
- Event feed from `EventJournal.replay()`: births/deaths/acquisitions/hazard hits, showing `causal_parent_ids` vs `contributing_event_ids` visually distinct (v1 §6 — that the UI does not imply more certainty than the kernel has).
- Read-only. No control surface, no button that calls `WorldAction` or advances a tick on its own. If an "advance one tick" control is desired, it can only call the same `run_tick()` a script would call — never influence *what* the organism decides.

**Out of scope of v2**, deferred to a dedicated Observatory design pass: live/streaming updates during a long run, replay scrubbing, the six-scale Observatory (World/Region/Population/Lineage/Individual/Mind) from rationale document §27 — v2 only has 8 stationary organisms in potentially several regions; most of those scales do not yet exist as data to show.

### Mode decision: CLI (ASCII grid in terminal)

> Historical note: this was the right decision for v2. Since September 2026, World no longer possesses its own UI: the scientific view lives in Observatory and the old Pygame client was retired; Observatory is the only World UI. The following decision is preserved as historical rationale for v2.

Three modes considered: CLI, web (integrated into existing JS Observatory in `observatory/`), retired Pygame viewer. **CLI** is chosen for v2:

- Zero new dependencies — the rest of the kernel/adapter doesn't have them either (`pyproject.toml` only depends on `cryptography`+optional `torch`).
- Runs headless, just like the rest of the test suite — can be invoked from a script or pytest without extra infrastructure.
- The existing web Observatory (`observatory/render/*.js`) is its own system with its own contract (phenotype, cognition) — integrating World there is a separate Observatory design job (explicitly deferred above), not something to improvise within v2.
- retired Pygame viewer adds a graphical dependency unused anywhere else in the repo, with no clear benefit over ASCII for 8 organisms on a small grid.

Contract: `symbiont_lab.world.cli_view.render_world(state, environment, ground_truth, metadata) -> str` — pure function, returns text, never prints or reads stdin directly (thus it's testable without capturing stdout). A thin `if __name__ == "__main__"` in a separate script prints it. It exposes no controls — there is no "step" or "act" command in the CLI that touches `WorldAction`; it only reads.

### Extension: persistent server

The operator expected to connect to a world that runs on its own, not launch a script that runs N ticks and terminates. §8 is extended with a real server, same read-only invariant:

`symbiont_lab.world.dashboard_state.WorldDashboardState` runs the world in a daemon background thread, indefinitely, from the moment `.start()` is called — regardless of whether there is any viewer connected or not (same principle that already governs Observatory: the world does not depend on who is looking at it). `symbiont_lab.world.dashboard_server` exposes this via `http.server.ThreadingHTTPServer` (stdlib, same pattern `symbiont_lab.dashboard` already uses for the organism, no new dependencies): `GET /` serves a page that polls `GET /api/state` every second and overwrites a `<pre>` with the output of `render_world()`.

**The HTTP handler defines no POST/PUT/DELETE/PATCH verbs** — a test explicitly verifies this. There is no way for a remote client to call `WorldAction` or otherwise direct the tick; the only way to "control" the world is to launch or kill the server process.

Launch: `symbiont-world-dashboard --port 8766 --tick-delay 0.5` (entry point in `pyproject.toml`). `--seed`/`--founders`/`--width`/`--height` configure the world; `--tick-delay` is the only parameter that controls cadence, never content.

## 9. Explicitly out of v2

Culture, communication, reproduction (W04/W05 — they come after W03 has a result, according to the formal barrier of v1 §8). Real movement remains out unless the concrete design of §7 is separately approved.

## 10. Technical gates (V02, not scientific falsification)

```
V02-01  colocación de founders determinista para un world_seed dado
V02-02  8 founders ocupan 8 celdas distintas, sin colisión
V02-03  asignación regional de leyes es opaca (ningún nombre de dominio
        llega a la forma pública de GroundTruth, igual que en v1)
V02-04  N/A EN v2: la resolución de intents simultáneos no se ejercita
        con más de un organismo porque v2 no tiene movimiento aprobado
        (§7) — sin movimiento, ningún organismo intenta la celda de
        otro. Se reactiva cuando §7 se apruebe e implemente.
V02-05  retry de W02 con plasticidad: reproducible para la misma seed,
        reporta divergencia honestamente en cualquier sentido
V02-06  el daño diferido dispara exactamente una vez por adquisición
        cualificada, dentro del rango (0, 0.25] ya exigido por
        apply_environmental_damage
V02-07  la vista World de Observatory no tiene ningún camino de código
        que llame WorldAction o mute WorldState — solo lectura, igual
        que toda superficie de Observatory existente
V02-08  ningún test existente de W0–W3 (tests/unit/world/,
        tests/unit/lab/world/) deja de pasar por un cambio de v2 —
        GroundTruth regional es aditivo, no disruptivo
```

W03 (the real falsification gate) is preregistered only after these technical gates pass, same discipline as v1.

## 11. Scientific question of v2 (for later preregistration)

> With 8 identical founders, without mutation, placed deterministically in a world with regional resource/hazard heterogeneity: does a measurable ecological differentiation emerge (specialization by region, distinct acquisition patterns) attributable solely to ontogenetic/social development, without any genetic variation among founders?

This operates W03 directly. No W04+ questions (culture, evolution) are addressed until W03 has a real result, just as v1 did not address W03+ until closing W01/W02.
