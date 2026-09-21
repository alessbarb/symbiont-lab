# L5.5.1 v1 — per-structure damage: scoped-out debt

`BodyStructureState` / `LivingBodyState.structure_states` (this change) gives the
organism a real per-structure integrity/wear substrate instead of one scalar, with
`structural_integrity` kept as the aggregate (mean) for backward compatibility. What
it deliberately does **not** do yet:

## 1. World/physics3d contact → structure targeting (L5.5.2)

`apply_wear(amount)` still applies `amount` uniformly to every structure (equivalent
to the old scalar decrement when structures start uniform). No caller anywhere —
`symbiont_lab.world.population`, `symbiont_lab.physics3d.apparatus`,
`symbiont_lab.world.runtime` — can yet say "this specific hazard/contact hit
structure X." That requires a real contact→structure_id mapping in physics3d
(geometry-aware: which link/joint took the impulse) and an equivalent concept in the
non-3D `symbiont_lab.world` hazard model. Until that lands, per-structure state has no
live differentiation source — every structure decays together, so it is currently
observable (checkpointed, inspectable) but not yet exploitable as "this organism is
lame in one limb but fine elsewhere."

## 2. Structure population strategy

`structure_states` is populated 1:1 from `ActuatorConstitution.slots` at construction
time, only when `actuation_enabled`. Organisms without actuation (most synthetic-
ecology `core.body.Body` subjects, most existing tests) keep `structure_states == {}`
forever and behave exactly as before (scalar-only). Open questions for later:

- Should sensors also get structure entries (a damaged receptor is a different kind of
  degradation than a damaged effector)?
- Should `core.body.Body` (the older receptor/effector substrate, still used by some
  Lab studies) get structures too, or is that substrate frozen/legacy?

## 3. `functional_capacity` / `repair_progress` are inert placeholders

`BodyStructureState.functional_capacity` and `.repair_progress` are stored and
checkpointed but nothing reads or writes `functional_capacity` to actually degrade an
actuator's output, and nothing advances `repair_progress` as a process distinct from
`integrity` recovering directly. A later phase should decide: does a partially-damaged
actuator lose motor authority proportionally to `functional_capacity`, and is repair a
two-stage process (progress accumulates, then integrity jumps) or the same thing under
two names? Right now they're scaffolding for that decision, not yet load-bearing.

## 4. Direct-field-write fragility

`structural_integrity` stays a plain dataclass field (not a property) specifically so
every existing `LivingBodyState(structural_integrity=...)` constructor call and the ~19
existing read sites across `symbiont_lab` keep working untouched. Only
`LivingBodyState.apply_wear` and `HomeostaticController.integrity`'s setter are
structure-aware (they update `structure_states` then recompute the scalar mean). Any
*new* code that assigns `.structural_integrity = X` directly, bypassing both of those,
will desync the scalar from `structure_states` until the next `apply_wear`/repair call
silently overwrites it back to the recomputed mean. `symbiont_lab.world.persistence`
already does one direct restore-time assignment (`...structural_integrity = float(...)`)
— that's fine (checkpoint restore, not a physics mutation) but is the one existing
example of the pattern to watch for.

## 5. Checkpoint compatibility

`LivingBodyState.checkpoint()` schema bumped 2→3 (`structure_states` added,
default `{}` on restore of a v2 payload — honest: no v2 checkpoint ever had structures,
since this field didn't exist before). No outer `CHECKPOINT_SCHEMA_VERSION` bump was
needed (mirrors how `SensorimotorLearner`'s own schema bump 3→4 didn't require one
either) since this is backward-compatible, not a fail-closed physiological-truth gate
like Living Body L5 itself was.
