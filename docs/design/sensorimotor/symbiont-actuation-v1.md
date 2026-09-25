---
id: design.general.symbiont-actuation-v1
title: "Symbiont Actuation V1"
document_type: design
domain: sensorimotor
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Symbiont Actuation v1 — Motor Apparatus & Closed Body Loop

**Status:** end-to-end technical design and specification, revision 6 — **P0 CLOSED**. Revision 1: `draft / needs amendment`. Revision 2: `approvable with 4 hardenings`. Revision 3: `4 hardenings incorporated`. Revision 4 fixes two startup details of P0 and an explicit test requirement. Revision 5 fixes four gaps from a post-merge audit (§16): phase persistence of the motor schedule (P0.1), strict restore validation (P0.2), effect replication between windows (P0.3), hardening of field validation + invariants of `MotorSlot`/`ActuatorConstitution` (P0.4); it supersedes the reset rule from revision 3/4 that broke replay equivalence; and, following a second finding in the same audit, it also removes the export gate based on minimum samples — the checkpoint is now bit-exact from any tick, including tick 0 (§16.6). Revision 6 closes P0 with two final adjustments (§16.7): `restore_actuation_state` validates consistency between fields (`windows_with_effect <= windows_completed`, `tick_in_window < window_ticks`, an `active` candidate must actually satisfy its own promotion condition) instead of accepting internally impossible states that would only fail ticks later; and `effect_strength = |corr(activation, Δpercept)|` is declared as the exact metric of v1 (§6), aligning the letter of the spec with the already verified implementation — the point-biserial correlation over a balanced ON/OFF schedule already captures the substance of "ON/OFF difference" that previous revisions described with other notation. It does not reopen the general architecture.
**Scope:** `symbiont.actuation` (new), `symbiont.cognition.cognition_bridge` (extended), `symbiont.core.runtime` (extended), `symbiont_lab.world.adapter` (new bridge), `symbiont.cognition.checkpoint` (extended).
**Guiding principle:** the organism's input chain (World → Source → Sensor → Percept → Cognition) currently has a broken symmetry — there is no equivalent output chain. Cognition produces `readouts` that no one consumes except telemetry (`runtime.py:2249`); real movement in World v4 is decided by `policy_rng.choice` in `symbiont_lab/world/population.py:299-317`, completely outside the organism. This spec closes the body loop:

```text
                percepción
WORLD ──→ SOURCE ──→ SENSOR ──→ PERCEPT
                                  │
                                  ▼
                              COGNITION
                                  │
                                  ▼
                          motor readouts
                                  │
                                  ▼
                       MotorIntentSelector
                                  │
                                  ▼
                            MOTOR INTENTION
                                  │
                                  ▼
                            ACTUATOR SYSTEM
                                  │
                                  ▼
                              ACTUATION
                                  │
                                  ▼
WORLD ←── ActuationAdapter (Lab) ─┘
   │
   └──────────────► proprioceptive evidence ──► SENSOR (tick N+1)
```

**Central invariant of this spec:**

> **Lab can translate an `Actuation`, but it can never choose an actuation on behalf of the organism.**

This explicitly eliminates the current pattern where Lab filters `valid_dirs` by permeability/occupancy before the organism decides — that filtering gifts the organism knowledge of the world that it shouldn't have. After P2, the organism can try to activate an actuator whose effect in World is null (wall, occupant, degraded actuator) and must learn from that result, not be protected from it.

---

## 1. Package boundary

```text
symbiont/actuation/
├── types.py        # ActuatorId, MotorCandidate, MotorIntent, Actuation
├── constitution.py # ActuatorConstitution — cuerpo motor fijo, ver §3
├── candidate.py     # ActuatorCandidateState, effect-relation tracking
├── proposer.py      # exploración bounded del repertorio corporal potencial
├── system.py        # ActuatorSystem: resuelve MotorIntent → Actuation
└── health.py         # ActuatorState: health/reliability/cost
```

Strictly maintained:

```text
symbiont        ✗→ symbiont_world
symbiont        ✗→ symbiont_lab
symbiont_world  ✗→ symbiont (cognición)
```

`symbiont_lab` remains the sole translator between organism and world, exactly as it already is for perception.

---

## 2. Types: candidate, intent, execution — three different things

```text
MotorCandidate
    posibilidad corporal todavía no consolidada
    (el organismo no sabe aún si "existe" de forma útil)

MotorIntent
    lo que el organismo intenta hacer
    (activation deseada sobre un actuator_id, ya seleccionada — ver §8)

Actuation
    lo que el aparato corporal realmente consiguió ejecutar
    (requested vs delivered, tras aplicar health/cost/degradación)
```

```python
@dataclass(frozen=True)
class MotorIntent:
    actuator_id: ActuatorId
    activation: float  # [0.0, 1.0], deseado por cognición

@dataclass(frozen=True)
class Actuation:
    actuator_id: ActuatorId
    requested: float
    delivered: float   # tras health/cost — puede ser 0.0 si el actuador está degradado
    cost: float
    health_at_execution: float
```

**The effect in World is NOT part of `Actuation`.** `Actuation` is purely bodily — how much was actually delivered, not what happened outside. The physical consequence is the exclusive responsibility of World, mediated by `ActuationAdapter` in Lab (§9). This preserves the epistemological boundary: the body knows what it did, not what it caused.

Absence of `MotorIntent` for a tick = absence of actuation. There is no `"stay"` actuator nor an equivalent boolean `WorldAction.rest` inside `symbiont`; "not acting" is the absence of intent, not a named action.

---

## 3. `ActuatorConstitution` — who owns the motor body

**Revision 2 correction.** Revision 1 assumed a "potential repertoire bounded and fixed from genesis" without saying where it lives or who generates it. Without this, Lab could end up inventing the IDs when building the organism — and then it would be the apparatus defining part of the organism's body, exactly the inversion of responsibility that this spec exists to prevent.

`ActuatorConstitution` is a property of **`symbiont`**, not of World or Lab:

**Revision 4 correction — truly immutable representation.** `@dataclass(frozen=True)` does not freeze the `Mapping`/`dict` it contains: two "equal" instances could carry different mutable dictionaries inside, and a fingerprint/hash over that is not reliable. For a fingerprintable constitution (necessary for `ActuationBindingConstitution`, §10, and to compare constitutions across generations) it is represented as ordered tuples of slots, not as a dataclass-with-dict:

```python
@dataclass(frozen=True, slots=True)
class MotorSlot:
    slot_id: str            # "motor_slot.0", estable, ver más abajo
    actuator_id: ActuatorId  # f(constitution schema, slot_id) — ver más abajo
    basal_cost: float
    initial_health: float
    execution_threshold: float  # ver §9

@dataclass(frozen=True, slots=True)
class ActuatorConstitution:
    slots: tuple[MotorSlot, ...]   # orden canónico por slot_id, nunca por inserción
```

With `slots` as a tuple of immutable records (not `dict`), two constitutions with the same content are structurally equal and hashable without additional normalization — a necessary condition for `ActuationBindingConstitution` (§10) to be a reliable fingerprint.

- It is generated **deterministically from the genome** in `symbiont/cognition/birth.py` (the same module where `load_base_genome`/`load_base_cognition` lives today — not in `core/birth_authority.py`, which assigns `organism_id`/lineage/habitat slots and does not know physiology, nor in `core/canonical_birth.py`, which only wires already-derived cognition within a resident's restore flow; see P0 startup note below), it is not built by Lab or World.
- `actuator_ids` are stable during the organism's lifetime — they are not regenerated tick by tick.
- **Inheritance:** upon reproduction, the motor constitution is **constitutional and deterministic from the child's genome**, just like any other inherited trait in `birth.py` — it is not literally copied from the parent nor inherited separately as an opaque blob. This maintains a single inheritance mechanism instead of two.
- Lab/World only **consume** `actuator_ids` to build their own `ActuationAdapter` mapping (§9) — they never generate or alter them.

**Revision 3 correction — stability against non-motor mutations.** `actuator_id = hash(full genome)` is not derived: an irrelevant mutation (e.g. `learning_rate`) would rename all of the child's actuators, losing the inherited bodily identity for no reason. Instead:

```text
motor_slot.0, motor_slot.1, ..., motor_slot.N   ← slots heredables, identidad estable
actuator_id = f(motor constitution schema, slot identity)   ← no depende del genoma completo
```

(`MotorSlot`/`ActuatorConstitution` as immutable tuples — exact definition above.)

Genomic mutations can alter the **parameters** of a slot (cost, initial health, `execution_threshold`, even presence/absence of the slot) without renaming the other slots. This is what makes A04 tractable (permuting `actuator→direction` without changing IDs) and will be necessary as soon as the evolution of the motor constitution across generations is studied.

`proposer.py` (§4) explores within `actuator_ids` already given by the constitution; it does not invent them.

---

## 4. Discovery: potential bodily repertoire, not universe of arbitrary IDs

`proposer.py` does **not** generate opaque IDs from an infinite abstract space. That would allow the organism to "guess" candidates that coincidentally have a body in World, which is artificial and does not correspond to any real biological mechanism.

Instead:

```text
ActuatorConstitution.actuator_ids (§3, bounded, fijo por organismo desde genesis)
      ↓
opaque potential actuators   ← conjunto finito, ya existe físicamente
      ↓
proposer                     ← decide CUÁLES explorar y en qué orden
      ↓
probing                      ← activación real, presupuestada, con controles (§6)
      ↓
active repertoire            ← selección bounded que entra en cognición rutinaria
```

The organism discovers **its body** (which of its potential channels are useful), it does not create limbs by random enumeration. The *de novo* generation of new effectors through structural plasticity is out of scope for v1 — it is a distinct and deeper biological capability, to be reviewed in a separate spec if it is decided to pursue it.

`len(actuator_ids)` is a property of the bodily constitution (§3), not an exploration parameter.

---

## 5. Motor utility ≠ correlation

Error to avoid: `utility = abs(correlation(activation, Δpercept))` solely measures **"this has a reproducible effect"**, not **"it is in my interest to activate it"**. An actuator that always causes damage can have an extremely high correlation. Confusing the two would turn body discovery into an implicit survival policy — exactly what we want to avoid in this layer.

Two signals are explicitly separated:

```text
effect_strength / controllability   ← "activating this has measurable and reproducible consequences"
                                        (which DOES live in ActuatorCandidateState, via PairAccumulator)

adaptive_value                       ← "those consequences are favorable to me under these conditions"
                                        (subsequent learning, via Actuation → future percepts →
                                        future physiology → prediction error, in cognition, NOT in
                                        the ActuatorSystem)
```

`ActuatorCandidateState` only tracks the first one. The second belongs to the existing cognitive learning cycle (prediction error, already present in `cognition_bridge.py`), it is not reimplemented here.

---

## 6. `ActuatorCandidateState` — with contrast control, not just trial

A single `PairAccumulator` per candidate is insufficient — we do not know a priori which percept is affected. A bounded table of effect→percept relations is tracked:

```text
ActuatorCandidateState
├── actuator_id
├── activations                          # aggregated history, not raw
├── effect_relations: dict[PerceptId, PairAccumulator]   # bounded to the active-sensor ceiling
│    max_effect_relations_per_candidate = 256
├── cost_evidence
├── probing_state (active | probing | dormant)
└── last_seen_tick
```

Reuses `PairAccumulator`/`SensoryRelation` (`host/adaptive.py:137-256`) without reinventing statistics — same primitive, applied to `(activation, Δpercept)` instead of a single passive stream.

**Revision 2 correction — ON/OFF paired observations.** If during probing only ticks with `activation≈1` are registered, the `PairAccumulator` cannot distinguish "the actuator caused the change" from "the environment changed on its own in that same tick" — a background environmental cycle would produce the same `Δpercept` without the actuator being causal, and with almost constant `activation` the correlation is useless or spurious. The probing budget therefore requires a **deterministic contrast schedule**, independent of the observed percept.

**Revision 3 correction — the schedule cannot be even/odd.** A strict `even→OFF, odd→ON` alternation perfectly aligns with any environmental regularity of period 2 (or 4, 8...), potentially "discovering" motor causality that is actually a cycle of the world coinciding in phase. Instead, each probing window uses a **balanced sequence generated by the organism's namespaced RNG**, not by tick index:

```text
seed = derive_rng(organism_id, actuator_id, probing_window_index)
sequence = balanced_shuffle(seed, length=window_ticks)   # equal number of ON and OFF, non-periodic order
```

and **more than one window with distinct sequences** is required before a candidate can transition to `active` — a single window, however balanced it may be, remains vulnerable to a coincidental isolated environmental event.

**Revision 6 correction — exact definition of `effect_strength` (code and spec already coincided in substance, not in letter).** Previous revisions described `effect_strength` as "the difference `Δpercept(ON) − Δpercept(OFF)` aggregated across windows". The actual implementation (`ActuatorCandidateState.effect_strength`, `PairAccumulator.correlation`) uses instead:

```text
effect_strength = max( |corr(activation, Δpercept)| )  over effect_relations, accumulated all-time
```

This is declared **explicitly as the v1 metric**, not a provisional approximation, for the following reasons:

- With a balanced `activation ∈ {0, 1}` schedule, the Pearson correlation between a binary and a continuous variable **is** the point-biserial correlation — a monotonic normalization of the ON vs OFF difference of means (`Δpercept(ON) − Δpercept(OFF)`), not a distinct statistic. The substance of "ON/OFF difference" is already captured; it differs only in normalization.
- `effect_threshold ∈ [0.0, 1.0]` (spec §9) only makes natural sense over an already normalized statistic — a raw difference of means does not have that range.
- `PairAccumulator` is the primitive already reused from `host/adaptive.py`, bounded and numerically stable — introducing a second parallel ON/OFF statistic solely to fulfill the literal letter of a sentence in the spec would mean duplicating infrastructure with no real gain.
- The true replication requirement no longer depends solely on `effect_strength`: `windows_with_effect` (revision 5, below) demands that the effect be detected **independently across multiple separate windows**, evaluating `effect_strength` over the transient accumulator of each window separately (`complete_window()`), not just over the historical accumulation. This reinforces A03 (§13) exactly as the original wording intended, through a different but equally rigorous route.

No new statistics are introduced. This is a documentation change so the spec faithfully describes the already implemented and verified code (matrix of 648 configurations, `tests/unit/actuation/test_continuity_gate.py` and `test_proposer.py`), not a behavior change.

Global bounds, analogous to `AdaptiveSenseModel`:

```text
max_candidates = len(ActuatorConstitution.actuator_ids)   # see §3, no longer an independent cap
max_effect_relations_per_candidate = 256
```

### Lifecycle: active / probing / dormant

Identical in structure to sensors (`sampling_plan()`, `host/adaptive.py:593`), with one important difference: **probing a sensor only costs observation; probing an actuator changes the world or the organism.** Therefore, the motor exploration budget is much more conservative:

```text
sensory probe_limit = 4   (existing reference)
motor probe_limit   = 1   (default v1, already distributes the ON/OFF schedule described above)
```

**Explicit test requirement (revision 4, not a design change — the architecture already requires it via the one-tick lag of §9).** Every test for `effect_relations`/`PairAccumulator` must verify that it compares `activation(t)` with `Δpercept = percept(t+1) − percept(t)`, never `percept(t) − percept(t)` from the same tick. It is an implementation requirement for P0 (construction of the `PairAccumulator`) and verification in P3 (actual motor learning), not a new architectural rule — the N→N+1 causality is already fixed in §9.

---

## 7. Cognition: separate readout families, not a single bool

Key finding from current code: `cognition_bridge.py` assumes a single relevant readout (`_CORE_READOUT_ID = "readout_core"`, created lazily in `_propose_new_concept_mutations` when `needs_readout = not readouts`, lines 367-403). `_nodes_with_path_to_readout()` (line 406) is reused for `stranded_concepts`, recycling (`_propose_concept_recycling_mutations`, line 436+), and fitness. If we simply add motor `READOUT` nodes to the same set without distinguishing them, a concept connected only to `readout_motor:X` would appear as "routed" even if it has no path to `readout_core` — silently corrupting topology health, recycling, and existing telemetry.

`_nodes_with_path_to_readout(target=None)` with `None = all` **is not done**. Explicit topological semantics for two families are introduced:

```text
readout_core                    ← invariant, unchanged; historical general cognitive output
                                   continues feeding exclusively:
                                   - _nodes_with_path_to_core_readout()  (renamed from the current one)
                                   - unrouted tracking / recycling / topology health
                                   - existing telemetry (runtime.py:2249) — consumer intact

readout_motor:<opaque actuator_id>   ← new family, independent sink per actuator
                                   - _nodes_with_path_to_motor_readout(actuator_id)
                                   - DOES NOT participate in the calculation of stranded/recycling for readout_core
```

### Lazy materialization, only for active candidates

A `readout_motor` is not created for each of the potential candidates in the constitution — only for those that are in `active_repertoire`. If an actuator permanently returns to `dormant` and there is structural pressure, its `readout_motor:*` is a candidate for recycling under the same existing recycling rules in the graph, applied to this family separately.

```text
candidate
   │ evidence sufficient (effect_strength above threshold, bounded ticks, with ON/OFF control)
   ▼
ACTIVE
   │
   ▼
readout_motor:<id> materializes lazily (same pattern as needs_readout today)
   │
   ▼ (if it permanently returns to dormant + structural pressure)
recycled
```

This keeps motor plasticity consuming real cognitive budget, instead of reserving a slot in advance for each potential candidate.

---

## 8. Motor edge learning — how connections to `readout_motor` are born

**Blocking piece identified in revision 2.** §7 correctly defines that `readout_motor:X` is born isolated from `readout_core`, but a motor readout with no incoming edges is useless: the organism would have discovered it possesses the effector, without being able to learn *when* to use it. This must be resolved before P2, not after.

The current code already has the mechanism to reuse. When a new concept is created from coactivated `SENSE` sources, `_propose_new_concept_mutations` (`cognition_bridge.py:374-403`) emits exactly this sequence of `Mutation`:

```python
mutations = [
    Mutation(kind="add_node", payload={"node_id": concept_id, "kind": NodeKind.CONCEPT, ...}),
    Mutation(kind="add_node", payload={"node_id": readout_id, "kind": NodeKind.READOUT}),  # if needed
    Mutation(kind="add_edge", payload={
        "source_id": concept_id, "target_id": readout_id,
        "kind": EdgeKind.EXCITATORY, "weight": _TENTATIVE_WEIGHT,
        "plasticity": 0.5, "delay_ticks": 1,
    }),
]
```

and `self._structural_plasticity.observe_coactivation(...)` (line 1124) already exists tracking coactivation to propose these connections.

**Revision 3 correction — do not reuse `observe_coactivation()` with the literal signature.** `observe_coactivation(source_id, target_id, source_active, target_active, tick, ...)` (`structure.py:49-59`) observes activity between **`CognitiveGraph` nodes that already exist and are already activating**. Before an edge exists, the newly materialized `readout_motor:X` is isolated — it has no real activation to report. Calling it with `target_active = actuator_is_active` would falsify a node's activation, disguising an external bodily signal (evidence of actuator controllability) as genuine cognitive activation. That could make it appear as if motor connections are being learned when in reality they are induced by a signal foreign to the graph.

Instead, an explicit method is added, with its own semantic boundary, reusing the internal statistical/structural mechanism (accumulator, thresholds, cooldown, `Mutation(kind="add_edge", ...)`) **without lying about node activation**:

```python
def observe_motor_association_evidence(
    self,
    *,
    source_id: str,          # concept/state node, truly active in the graph
    motor_readout_id: str,   # "readout_motor:<actuator_id>", might be isolated
    source_active: bool,
    actuator_has_effect_evidence: bool,   # NOT "target_active" — it's bodily evidence, not node activation
    tick: int,
) -> None:
    ...
```

Internally it shares accumulator/cooldown/`Mutation` with `observe_coactivation`, but the parameter is named and documented for what it is: evidence that an actuator with sufficient `effect_strength` coincided with an active concept, not an activation of `readout_motor:X` that cannot yet activate on its own.

```text
concept/state active in tick N (real source_active, via this same graph)
        │
        │  AND in the SAME window, actuator_id X becomes ACTIVE (§7) with sufficient effect_strength
        ▼
observe_motor_association_evidence(...)
        ▼
tentative edge proposal:  concept_id → readout_motor:X
        kind = EXCITATORY, weight = _TENTATIVE_WEIGHT, plasticity = 0.5, delay_ticks = 1
        (same apply_mutations, same minimum_support genome threshold
         that already governs concept creation)
```

- The signal is **purely internal** (active concept + actuator with its own effect evidence), never World semantics.
- The edge is born **tentative** (same `_TENTATIVE_WEIGHT`/`plasticity` used by core today) and remains subject to the same reinforcement/pruning rules as any tentative edge in the graph — it is not privileged.
- `_nodes_with_path_to_motor_readout(actuator_id)` (§7) is the function that validates, for tests, that these edges actually connect something reachable — separate from the `readout_core` metric.

P1→P2 Gate: at least one integration test that, with an active actuator and a deterministically coactivated concept, verifies that the tentative edge is born and that `readout_motor:X` is no longer isolated — without this changing a single bit of `stranded_concepts`/`recycling` for `readout_core`.

---

## 9. Intent selection and tick (`core/runtime.py`)

**Revision 2 correction.** Revision 1 had `ActuatorSystem.resolve(cognition_result.readouts_for_family("motor")) → Actuation(s)` — that skips the `MotorIntent` boundary that the types (§2) already declared. It is made explicit:

```text
tick N:
  1792  sensory_system.transduce(...)          → percepts
  1969  cognitive_bridge.tick(...)             → cognition_result (.readouts, .prediction_errors)
  NEW   motor_readouts = cognition_result.readouts_for_family("motor")
  NEW   MotorIntentSelector.select(motor_readouts) → MotorIntent | None
  NEW   ActuatorSystem.execute(MotorIntent)     → Actuation | None
        [antes de finalización de percept/journal del tick]

  Lab (fuera de symbiont):
        ActuationAdapter.translate(Actuation)   → WorldAction
        World resuelve consecuencia física

tick N+1:
  1792  sensory_system.transduce(...) incluye evidencia propioceptiva de tick N
```

### `MotorIntentSelector` — current deterministic rule

The selector is no longer winner-takes-all for cognitive control. It preserves, in descending order of activation and tie-breaking by `actuator_id`, up to four channels above `selection_threshold`.

The singular view `select()` is preserved solely for compatibility; the canonical runtime uses `select_many()`.

Sensorimotor babbling and temporal primitives do not receive RNG from the Lab. All exploration is internal to the organism and reproducible from its identity and persisted state.

**Revision 3 correction — two thresholds, two distinct owners.** `selection_threshold` does not yet have a clear owner compared to `execution_threshold` (§3). They are explicitly separated:

```text
selection_threshold
    = umbral COGNITIVO — cuánta activación de readout_motor:X hace falta para que
      MotorIntentSelector lo considere candidato
    = configuración de MotorIntentSelector, eventualmente adaptable/aprendible
    = NO vive en ActuatorConstitution

execution_threshold
    = umbral CORPORAL/físico — cuánto delivered hace falta para que el actuador
      efectivamente intente moverse (§9, más abajo)
    = vive en ActuatorConstitution (§3), fijo por organismo, deriva del slot motor
```

Confusing them would mix "how much I want to activate this" (cognitive decision) with "how much my body can deliver" (physical limit) into a single number — exactly the mixture that this spec avoids in all other points.

### Execution threshold: from continuous `activation` to discrete one-cell movement

**Revision 2 correction.** We had to freeze what `Actuation.delivered ∈ [0,1]` means for `WorldAction.move`, which today is a discrete direction. v1 rule:

```text
delivered < execution_threshold   → ActuationAdapter no emite intención de movimiento
delivered >= execution_threshold  → ActuationAdapter emite un intento de movimiento (una celda)
```

`execution_threshold` is part of `ActuatorConstitution` (§3) — it belongs to the body/actuator, not to World. `cost` can indeed continue to be a continuous function of `requested`/`delivered`. `activation` is deliberately **not** converted into a probability of movement — that would unnecessarily introduce RNG into the body, and mix bodily non-determinism with decision non-determinism, two things that this spec keeps separate.

### Minimal proprioception starting from P2 (not deferred)

Autonomous locomotion without bodily feedback leaves the loop incomplete from the first step — that is why minimal proprioception enters already in P2, it is not postponed to a later phase. Proprioceptive signals v1, deliberately without success/failure interpretation:

```text
motor.requested_activation.<id>
motor.delivered_activation.<id>
motor.load.<id>
```

**Revision 3 correction — `motor.load` is internal cost, not world resistance.** `motor.load.<id>` reports the **metabolic cost/effort actually paid by the body** when executing the `Actuation` (function of `cost`/`health_at_execution` in `ActuatorConstitution`, §3) — never information about whether the world opposed resistance. If a wall blocks movement, the body does not magically receive that information through this channel; that would be a mechanical resistance sensor which does not exist in v1. The only legitimate way for "there was a wall" to reach the organism is the normal percept of tick N+1 (or its absence — nothing changed in the perceived position), never a proprioceptive shortcut.

**Revision 2 correction — `motor.effect_observed.<id>` is removed from P2.** Although it was marked optional in revision 1, it adds nothing that cannot be derived by comparing consecutive percepts, and is dangerously close to telling the organism "your action had an effect" — an interpretation, not a bodily fact. The external effect must arrive exclusively through normal sensors (percept of the world at N+1), never from a proprioceptive channel dedicated to "this worked". Nor is `motor.success.<id> = 1/0` emitted for the same reason: "success" requires knowing what the goal was, and that inference lives in cognition (prediction error), not in the proprioceptive sensor.

---

## 10. `ActuationAdapter` (Lab) — translates, does not decide

```text
Actuation(actuator_id=actuator.72c, delivered=0.8)
          │
          ▼
    ActuationAdapter          (symbiont_lab/world/adapter.py)
          │  mapping fijo, declarado por World/Lab en genesis
          │  actuator.72c → hex direction 3   (ejemplo)
          ▼
    WorldAction(move=<hex direction 3>)
```

The adapter does **not** consult geography, occupancy, or resources to decide the best direction — that already happened (or not) in `MotorIntentSelector` (§9). It completely replaces the current block:

```python
# src/symbiont_lab/world/population.py:299-317 — A ELIMINAR en P2
valid_dirs = [d for d in range(6) if geography.can_traverse(...)]
movement_intents[organism_id] = rig.policy_rng.choice(valid_dirs)  # o None
```

**Important consequence (strong invariant of this spec):** today Lab filters `valid_dirs` before offering options — the organism can never "attempt" an impossible movement because Lab already prevented it. After P2 that ends. The organism can activate `actuator.72c` even if there is a wall, an occupant, or the actuator is degraded; World resolves the consequence (including "nothing happened"), and that consequence —via proprioception and percept— is evidence for learning. Filtering beforehand gifts the organism knowledge of the world that it is not supposed to have.

**Revision 2 correction — reproducible identity of the mapping.** The `actuator_id → hex direction` mapping is itself an experimental condition, not an implementation detail: two runs with the same `world_seed` and organism but different mapping **are not the same condition**. `ActuationBindingConstitution` is defined: a fingerprint (deterministic hash of the complete mapping) that is part of the experimental manifest of each run, alongside `world_seed` and genome. Any experiment that depends on permuting the mapping (e.g. A04, §13) must explicitly register both fingerprints in its manifest.

---

## 11. Persistence — minimal per phase, complete in P6

**Revision 2 correction.** Revision 1 left the entire checkpoint for P6, but an already persistent World (v4 already is) cannot afford for a restart to erase the motor repertoire as soon as P2 starts using `ActuatorSystem` — that state becomes part of the organism's causal future from the first tick it exists.

- **P0** must already define `export()`/`restore()` for `ActuatorCandidateState`/`ActuatorState`/`ActuatorConstitution`, even if they are not yet used within World.
- **P2** cannot enter a persistent World without that `export()`/`restore()` being wired to the organism's checkpoint — a restart has to reproduce the same active repertoire, not restart motor discovery from scratch.
- **P6** remains the great gate of *cold restart + full replay equivalence*, verifying the entire system (including `readout_motor:*` already naturally persisted within the CognitiveGraph), not the first time anything is persisted.

**Is persisted** (established aggregates, never raw history — just like `host/adaptive.py:661-734`):

```text
ActuatorConstitution: actuator_ids, basal_cost, initial_health, execution_threshold (inmutable, deriva del genoma)
ActuatorCandidateState: agregados de effect_relations (no Δpercept crudo)
ActuatorState: health, reliability, cost
active_repertoire (IDs)
probe cursor / probing_state / calendario ON-OFF en curso
```

**Is not persisted**:

```text
last raw activation
last raw Δpercept
MotorIntent transitorio
Actuation transitoria
```

The `readout_motor:*` nodes of the CognitiveGraph **are not duplicated** in the actuation checkpoint — they are already naturally persisted as part of the existing cognitive graph checkpoint (`cognition/checkpoint.py`).

---

## 12. Explicitly deferred scope within this same spec

`acquire` and `emit` are kept in the end-to-end scope of this spec (architecture), but **after** validating the bodily paradigm with pure locomotion — they are not implemented until P4/P5:

- **`acquire`** today is `resource_id` — it contains more semantics than an opaque movement actuator (`actuator → concrete resource` would leak bodily/world knowledge). P4 studies whether one actuator per resource is needed or a single "interaction effector" that acts upon the local surface, letting World interpret the consequence.
- **`emit`** is a different expressive channel (`OpaqueSequence` content, range, cost) — it is not mixed with locomotion in v1.

---

## 13. Scientific gates (in addition to software tests)

```text
A01  ¿Activa canales sin recibir semántica platform-side?
A02  ¿Distingue un actuador causal de un actuador sham (sin efecto)?
A03  ¿Descubre actuator→percept contingencies por encima de correlación ambiental de fondo,
     usando el contraste ON/OFF de §6 — no correlación bruta de una sola serie?
A04  ¿Puede reaprender si permutamos actuator→dirección física sin cambiar los IDs?
A05  ¿Detecta degradación de un actuador (health decreciente)?
A06  ¿Diferencia "quise actuar" (MotorIntent) de "mi cuerpo actuó" (Actuation)
     de "el mundo cambió" (consecuencia en World, fuera de symbiont)?
A07  ¿La locomoción autónoma mejora respecto a activación aleatoria de actuadores?
     El EVALUADOR puede usar posición ground-truth para MEDIR esto (desplazamiento, rutas,
     supervivencia, consecuencias fisiológicas) — lo prohibido es que ese oracle de posición
     entre en la policy o vuelva al organismo como percept, no que el aparato científico lo mida.
```

**A04 is the most important gate of this spec.** Protocol example: `actuator.A → hex direction 0` in one phase, `actuator.A → hex direction 4` in another, without communicating the change to the organism. Each phase registers its own `ActuationBindingConstitution` fingerprint (§10) in the experimental manifest — they are distinct conditions, not the same condition with different noise. If the behavior readjusts through experience (not through state reset), we have real evidence of motor learning and not of memorizing a fixed mapping.

## 14. Implementation phases

```text
P0 — Motor substrate
     ActuatorId (derived from stable motor_slot.N, §3), MotorCandidate, MotorIntent, Actuation,
     ActuatorConstitution (deterministically generated in birth.py), ActuatorCandidateState with
     PairAccumulator + balanced non-periodic ON/OFF control calendar, RNG-namespaced,
     multi-window (§6), proposer bounded on actuator_ids of the constitution.
     export()/restore() of constitution/candidate/state already defined (§11), although not wired
     yet to the World checkpoint.
     NO cognition. NO World.
     Gate: opaque channels can be explored and classified as active/probing/dormant in a
           deterministic and bounded way, distinguishing causal from sham via sustained ON/OFF contrast
           across multiple calendars, in isolation, with their own tests.

P1 — Cognitive output roles + motor edge learning
     Cognitive refactor in cognition_bridge.py:
     readout_core remains invariant; readout_motor family introduced (§7);
     motor edge learning (§8) via new observe_motor_association_evidence in
     StructuralPlasticity — reuses accumulator/cooldown/Mutation from observe_coactivation
     WITHOUT spoofing activation of isolated readout_motor:X — to propose tentative edges
     concept→readout_motor:X;
     core reachability unchanged; legacy recycling unchanged;
     telemetry consumer (runtime.py:2249) unchanged; checkpoint roundtrip unchanged.
     NOTHING executes an actuator yet. Most audited step — explicit regression tests on
     stranded_concepts/recycling/topology health of readout_core BEFORE touching anything else,
     plus the integration test from §8 (tentative edge is born, readout_motor ceases to be isolated,
     without any node reporting activation it didn't have).

P2 — Closed locomotor loop (with minimal proprioception included)
     motor readouts → MotorIntentSelector (§9, deterministic, bounded concurrency) →
     MotorIntent(s) → ActuatorSystem.execute → Actuation(s) → execution threshold (§9) →
     Lab ActuationAdapter (with ActuationBindingConstitution fingerprint, §10) →
     World movement intent → consequence → minimal proprioception (requested/delivered/load)
     in tick N+1.
     P0 export()/restore() wired to the World checkpoint — a restart reproduces the same
     active repertoire (§11), does not restart motor discovery from scratch.
     Removes policy_rng.choice(valid_dirs) from population.py.
     Removes prior filtering of valid_dirs (invariant §10).

P3 — Motor learning
     Actuation → Δpercept → effect relations → controllability →
     adaptation of the active repertoire. Health/cost/reliability with real effect.

P4 — Interaction/acquisition
     Only after resolving its correct body semantics (§12).

P5 — Emission
     Local, opaque expressive channel, separate from locomotion.

P6 — Persistence & continuity (full gate)
     Cold restart + replay equivalence of the entire system (constitution + candidate state +
     active repertoire + readout_motor topology within the CognitiveGraph), not the first time
     anything is persisted — that already happened incrementally in P0/P2.
```

---

## 15. Invariants inherited from CLAUDE.md that this spec respects

- `symbiont` never imports `symbiont_world` nor `symbiont_lab` (actuation included).
- Providers/World never expose identity semantics to cognition — the same applies in reverse: the organism never exports semantics to World, only opaque `actuator_id`/`activation`.
- Raw telemetry is not persisted; only bounded descriptive/learned state (§11).
- The failure of a component does not halt the organism, but **physiological degradation and state corruption are not the same** (revision 2 correction):

  ```text
  actuator unavailable/degraded (low health due to use/normal physiology)
      → delivered = 0.0
      → tick continues without aborting

  corrupt internal/checkpoint state (data invariant violated)
      → explicit validation failure
      → restore/recovery fails safely (does not continue with invented state)
  ```

  Silencing a state corruption as if it were `health=0` would hide real bugs and could produce irreproducible trajectories — CLAUDE.md demands that a provider's failure does not halt the organism, not that corrupt data masquerades as physiology.
- No real action on the host (`symbiont.host`) is affected by this spec — the scope of real actuation outside World/simulation is explicitly left out and would require an explicit decision from the owner, just like any new class of real action already contemplated in CLAUDE.md.

---

## 16. Revision 5 — P0 hardening after post-merge audit

P0 was implemented and merged to `main` in revision 4. An independent audit of the resulting `main` (not of the plan, but of the already integrated code) found four continuity/robustness gaps that revision 4 did not close. This section documents them and adjusts the spec so that the code remains its faithful implementation.

### 16.1 P0.1 — Persistence of the motor calendar phase

`ActuatorProposer` kept `tick_in_window` as transient state **outside** of `ActuatorCandidateState`, explicitly not persisted ("transient scheduling phase, not established evidence"). A restart mid-window would reset to `tick_in_window=0`, producing a different ON/OFF sequence than what would have occurred without interruption — `continuous run ≠ checkpoint → restore → continue`, even before connecting World.

**Correction:** `tick_in_window` becomes a field of `ActuatorCandidateState` (persisted in `to_payload`/`from_payload`), and `ActuatorProposer` delegates to it instead of keeping its own dictionary. A restore resumes the window exactly where it was left, it does not restart it.

### 16.2 P0.2 — Strict validation of `restore_actuation_state`

Three hardenings:

1. **Set equality, not subset.** `set(payload["candidates"].keys())` must be exactly `set(constitution.actuator_ids)` — no more, no less. `export_actuation_state` always exports one candidate per actuator (including the `dormant` ones), so a payload with missing candidates is a truncated checkpoint, not "this organism never explored some of its actuators".
2. **Key↔field match.** The internal `actuator_id` of each `ActuatorCandidateState` must match the dictionary key under which it is saved — prevents candidate B's state from slipping under key A when both are known IDs.
3. **Strictly typed `probe_cursor`.** It is validated with the same `_require_nonneg_int` used in the rest of the package (rejects `bool`, `float`, numeric strings, and negatives) instead of `int(...)`, which would accept them silently.

### 16.3 P0.3 — Effect replication across independent windows (replaces the "reset" of revision 3/4)

Revision 3/4 demanded that the effect be sustained "across multiple distinct ON/OFF calendars", but the promotion only checked `windows_completed >= min_probing_windows` on a **globally accumulated** correlation — a single window with a very strong signal could by itself sustain a high accumulated correlation during several windows of pure noise, without the effect actually replicating.

**Correction:** `ActuatorCandidateState` adds `windows_with_effect: int` and a transient accumulator `_current_window_relations` (same `PairAccumulator`, with a single-window scope). `complete_window(effect_threshold)` evaluates **only** the evidence of the window that just closed and, if that window by itself exceeds `effect_threshold`, increments `windows_with_effect`; then it resets the transient accumulator. Promotion now requires three conditions:

```text
windows_completed   >= min_probing_windows   (enough windows have passed)
windows_with_effect >= min_probing_windows   (the effect replicated in that many independent windows)
effect_strength     >= effect_threshold      (the total accumulated correlation also confirms it)
```

This makes tractable the scenario that revision 3/4 only stated: an isolated noisy window with a high correlation by chance is no longer enough, because `windows_with_effect` requires actual repetition.

**`windows_with_effect` and `_current_window_relations` are persisted just like `tick_in_window` (§16.1)** — without this second field, a mid-window checkpoint would lose the partial evidence of that window and the replication count would diverge between a continuous run and one with checkpoint/restore (found empirically by the continuity gate, §16.5, before reaching `main`).

**Consequence — the "reset together" from I4 (revision 3/4) is removed.** The previous rule — resetting `windows_completed`/`windows_with_effect`/`tick_in_window` to 0 when the exported `effect_relations` was empty — was introduced to prevent a candidate from promoting with a single post-restore window without real evidence behind it. That rule directly conflicts with P0.1: it resets a real window phase not "earned by anyone", and desynchronizes the `window_index` (used to recompute `probing_calendar`) from the index under which the evidence was genuinely registered, breaking replay equivalence. With `windows_with_effect` as an independent guard — a counter that already reflects real replication of past windows, whatever the export state of `effect_relations` — the original hazard of I4 is closed without needing the reset: a restored candidate cannot satisfy `windows_with_effect >= min_probing_windows` from a single post-restore window; it can only be at or above that threshold because replication already actually occurred in previous windows. See `test_promotion_requires_re_earned_effect_strength_after_restore` (verifies the property that I4 protected, not the reset mechanism).

### 16.4 P0.4 — Additional validation hardening

- `ActuatorCandidateState.from_payload` validates `activations`/`last_seen_tick`/`windows_completed`/`windows_with_effect`/`tick_in_window` with `_require_nonneg_int` (rejects `bool`, floats, negatives) and `cost_evidence` with `_require_nonneg_finite`, instead of `int(...)`/`float(...)` without guards.
- `MotorSlot.__post_init__` validates that `slot_id`/`actuator_id` are non-empty and that `basal_cost`/`initial_health`/`execution_threshold` are in `[0.0, 1.0]`, defending its own invariants even if constructed directly without going through `GenomeCodec`.
- `ActuatorConstitution.__post_init__` validates that all `actuator_id` of its slots are unique.

### 16.5 Continuity gate (new, `tests/unit/actuation/test_continuity_gate.py`)

New gate required by revision 5, following exactly the protocol requested in the audit:

```text
run A: test N+M ticks without interruption
run B: test N ticks → export_actuation_state → restore_actuation_state → test M more ticks
assert: same active_repertoire, same state of each candidate
        (probing_state, windows_completed, windows_with_effect, tick_in_window),
        same effect_relations bit for bit (PairAccumulator is comparable by
        field equality; to_payload/from_payload does not lose precision)
```

The split is deliberately chosen **mid-window** (non-null `tick_in_window` at the cut point) so that the test is meaningful — a split at a window boundary would not have detected the loss of `_current_window_relations` that this very gate found during the development of revision 5. This is the gate that strongly closes P0: the motor substrate upon which cognition will be grafted in P1 is reproducible against interruption/restart.

### 16.6 Exact replay equivalence contract — checkpoint ≠ externally observable state

During the development of §16.3/§16.5 it was discovered, through a verification matrix (multiple seeds × split points × `slot_count`/`probe_limit` configurations), that the export gate of `effect_relations` itself (inherited from `SensoryRelation.to_payload(min_samples=...)` in `host/adaptive.py`, which retains relations with few samples so as not to expose an immature correlation as established knowledge to an external observer) is in itself a source of **permanent** loss against a checkpoint: a Welford accumulator is a running aggregate, not a reproducible log. If a sample is not persisted, there is no way to "recover" it later — the restored accumulator follows a different statistical trajectory than the continuous one **forever**, not just during the tick in which the sample was missing.

**First attempt at correction (lowering the threshold to 2) proved insufficient.** An early test in this section claimed that a run with a checkpoint diverges only in the tick where a relation had fewer than 2 samples, and that afterwards it "converges". That is mathematically false: if sample A is discarded in the checkpoint, the restored run never again contains A in its accumulator — `mean_x`, `mean_y`, `m2_x`, `m2_y`, `c_xy` remain different from those of the continuous run indefinitely, no matter how many new samples arrive later. The original test didn't detect this either because it didn't actually restore the exported payload; it kept feeding the same `proposer` object in memory (false positive fixed in `tests/unit/actuation/test_continuity_gate.py`).

**Final decision (revision 5): the checkpoint is not a filtered projection — it is the entire internal state of the organism.** `ActuatorCandidateState.to_payload()`/`from_payload()` export `effect_relations` and `current_window_relations` **without any sample threshold**, including relations with `count == 1`. `_MIN_RELATION_SAMPLES_FOR_EXPORT` is completely removed. Reason:

- The privacy argument of `SensoryRelation` ("with one sample, the mean is literally the raw data") is real, but it applies to **exposing** a reading to an external observer. A checkpoint is not that — it is the organism itself persisting its own internal state to continue being itself after a restart, exactly as `checkpoint()`/`restore()` already do for the `CognitiveGraph` in `symbiont.cognition.checkpoint`.
- `PairAccumulator.correlation` (host/adaptive.py) already returns `None` below `count < 3` — an immature relation can never influence `effect_strength` nor promotion, whether it is exported or not. There is no risk of a single-sample correlation "appearing to be established": the statistical primitive itself prevents it, regardless of the checkpoint.
- If in the future an externally observable projection is built (e.g., an Observatory that shows "what has this organism learned about its body"), that consolidation gate belongs to **that** layer, new and yet to be built — never to the checkpoint mechanism itself, which must remain 100% faithful to the real internal state.

**Resulting contract, now indeed exact and without exceptions:**

```text
continuous run (N+M ticks)
==
run with checkpoint at any tick k (0 <= k <= N+M) → export → restore → continue

for all k, including k=0 (before the first sample)
```

Verified by `tests/unit/actuation/test_continuity_gate.py` with splits parameterized from `0` (before any sample) up to several window boundaries, in single and multiple actuator configurations, and by the matrix of 624 configurations (3 body shapes × 6 seeds × up to 48 split points) referenced in the commit — 0 unexpected divergences.

### 16.7 Revision 6 — cross-validation between fields in `restore_actuation_state`

`ActuatorCandidateState.from_payload` (§16.4/P0.4) validates each field individually (type, non-negativity) but not the relationships between them. A payload could pass `from_payload` with internally impossible fields:

```text
windows_with_effect = 5, windows_completed = 2       # replication credited in windows that never occurred
tick_in_window >= window_ticks                        # calendar position out of range
probing_state = "active" without evidence to back it up
```

The second case is the most dangerous: it does not fail in `restore_actuation_state`, but several ticks later, inside `probing_calendar`, as an out-of-range index — far from its real cause and from the moment the corrupt checkpoint entered the system.

**Correction:** `restore_actuation_state` (which already knows `window_ticks`/`min_probing_windows`/`effect_threshold`, unlike `ActuatorCandidateState.from_payload`, which does not have that configuration) validates, for each reconstructed candidate, before installing it:

```text
windows_with_effect <= windows_completed
tick_in_window < window_ticks
if probing_state == "active":
    windows_completed   >= min_probing_windows
    windows_with_effect >= min_probing_windows
    effect_strength     >= effect_threshold
```

Any violation raises `ValueError` immediately during the restore — consistent with the rest of this section: a corrupt checkpoint must fail at the moment of corruption, never several ticks later as an indirect symptom.

## Concurrent cognitive actuation amendment

The original P0 selector used winner-takes-all semantics and produced one
`MotorIntent` per tick. That contract is now superseded for cognitive control.

The canonical runtime supports a bounded tuple of simultaneous intents and
actuations while retaining the singular fields as compatibility projections.

Rules:

1. cognitive motor readouts above threshold may execute concurrently;
2. concurrency is bounded to four channels per canonical tick;
3. ordering is deterministic by descending activation then actuator id;
4. each actuation is resolved independently through its own `ActuatorState`;
5. metabolic maintenance cost is additive across delivered commands;
6. proprioceptive requested/delivered/load feedback is emitted for each command;
7. spontaneous/structured actuator-discovery probing remains isolated to one
   actuator so causal promotion evidence is not confounded;
8. adapters capable of concurrent embodiment must consume `last_actuations`,
   not the legacy singular `last_actuation`.

The compatibility `last_actuation` value is the strongest selected command
only and must never be interpreted as the full motor state.


## Developmental sensorimotor amendment

Direct actuator readouts are no longer the only learned motor abstraction.

A canonical organism may instantiate a resident semantic-free
`SensorimotorLearner` when its constitutional motor-development mode is
`babbling`.

### Constitutional availability vs learned control

An actuator channel belongs to the body from birth and may therefore receive
developmental babbling before cognition has learned what it controls.

This distinction is fundamental:

- **constitutional availability** means the physical effector exists;
- **learned controllability** means the organism has accumulated evidence about
  reproducible consequences;
- **cognitive motor association** means learned concepts have acquired a route
  to an action readout.

The old design conflated these stages by making discovery effectively gate
whether a channel could be explored.

### Developmental exploration

Babbling is bounded, deterministic for one organism identity, multi-channel and
temporally correlated. It supplies no gait, sequence, anatomy or utility.

#### Mutually-exclusive opaque motor groups

An embodiment may declare groups of actuator IDs that are physically
mutually-exclusive directions of one motor unit. The declaration contains only
opaque IDs. It carries no joint name, anatomical side, preferred direction,
utility or task semantics.

The invariant applies to **all** concurrent motor sources, not only babbling.
If cognition and developmental exploration request multiple members of one
group in the same tick, the strongest requested activation survives; ties are
resolved by opaque ID. Only surviving requests are executed, charged, credited
and admitted as sensorimotor evidence.

Physics3D uses 31 two-channel groups over its 62 directional actuator slots.


Every constitutional actuator remains available, but coordination cardinality is
sampled with a logarithmic low-dimensional prior rather than uniformly over
`1..N`. Small combinations are therefore common, while broad and whole-body
coordination remains possible. Channel sets persist over a short epoch while
amplitude evolves smoothly. Coverage bias favors under-exercised constitutional
channels, preventing one easy actuator from monopolizing development.

### Sensorimotor dynamics

The learner records bounded sufficient statistics relating:

```text
opaque body state(t) + delivered motor vector(t)
    -> opaque body-state change(t+h)
```

for independent horizons `h ∈ {1, 4, 16, 64}`.

Horizon statistics remain separate.

The body-state snapshot includes the complete finite set of currently perceived,
non-command-echo signals. It is not truncated by lexicographic opaque ID.

Effect magnitude is computed from the strongest bounded non-zero consequences
(top 8), rather than averaging over every available signal. This prevents a
body-wide action from receiving higher controllability merely because it changes
more channels and prevents a strong local consequence from being diluted by
unchanged channels.

Primitive recurrence is support-aware. Sequence distance combines quantized
activation discrepancy with active-channel support discrepancy. Dense patterns
therefore cannot make added/removed channels disappear merely by increasing the
denominator.


### Motor primitives

A four-tick temporal sequence of actually delivered motor vectors may become an
opaque `MotorPrimitive` candidate. The sequence can contain a different
multi-channel vector at every tick. Primitive identity is derived from the
learned sequence; it has no semantic label.

A single episode is only a hypothesis. Endogenous replay must reproduce a
directionally consistent body-state transformation before the primitive becomes
cognitively available. Contradictory replication lowers controllability and can
remove the primitive entirely.

Replay selection is active rather than lottery-based. The organism retains one
unresolved opaque motor hypothesis and gives it bounded independent probes
until it becomes a competence, is falsified, or exhausts its verification
budget. Candidate priority is computed only from organism-owned residual
controllability, directional repeatability and remaining uncertainty budget.
No world coordinate, locomotion score, resource direction, anatomy label or
evaluator reward is visible to this selector.

A primitive becomes cognitively addressable only after repeated evidence and a
bounded variance/controllability gate. Eligible primitives receive a separate
`readout_primitive:` family inside the CognitiveGraph.

Primitive readouts:

- are not core readouts;
- are not direct actuator readouts;
- can acquire concept-to-readout structural associations through genuine
  plastic evidence;
- execute only their previously learned temporal actuator sequence;
- do not contain a target, direction or reward.

Thus motor hierarchy is acquired rather than authored:

```text
physical actuators -> learned synergies -> cognitive primitive actions
```

The complete sensorimotor state is part of organism persistence. Current
sensorimotor checkpoint schema is **v10**. It persists the opaque exclusive motor
groups, the body-owned actuator `contract_fingerprint`, babbling phase, sufficient
statistics and learned primitives. Each primitive is scoped to that opaque
embodiment fingerprint and cannot execute on a different surface. v9 checkpoints
are admitted only as a one-time migration onto an already validated current body;
pre-v9 learned sensorimotor state fails closed: its evidence was
collected under different motor-concurrency and statistical rules and cannot be
silently reinterpreted.
