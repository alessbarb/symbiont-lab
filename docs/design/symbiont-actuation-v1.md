# Symbiont Actuation v1 — Motor Apparatus & Closed Body Loop

**Estado:** diseño y especificación técnica end-to-end, revisión 6 — **P0 CLOSED**. Revisión 1: `draft / needs amendment`. Revisión 2: `approvable with 4 hardenings`. Revisión 3: `4 hardenings incorporados`. Revisión 4 fija dos detalles de arranque de P0 y un requisito de test explícito. Revisión 5 corrige cuatro gaps de una auditoría post-merge (§16): persistencia de fase del calendario motor (P0.1), validación estricta de restore (P0.2), replicación de efecto entre ventanas (P0.3), endurecimiento de validación de campos + invariantes de `MotorSlot`/`ActuatorConstitution` (P0.4); supersede la regla de reset de revisión 3/4 que rompía la equivalencia de replay; y, tras un segundo hallazgo en la misma auditoría, elimina también el gate de exportación por mínimo de muestras — el checkpoint ahora es bit-exacto desde cualquier tick, incluido el tick 0 (§16.6). Revisión 6 cierra P0 con dos últimos ajustes (§16.7): `restore_actuation_state` valida consistencia entre campos (`windows_with_effect <= windows_completed`, `tick_in_window < window_ticks`, un candidato `active` debe satisfacer realmente su propia condición de promoción) en vez de aceptar estados internamente imposibles que solo fallarían ticks después; y se declara `effect_strength = |corr(activation, Δpercept)|` como la métrica exacta de v1 (§6), alineando la letra de la spec con la implementación ya verificada — la correlación point-biserial sobre un calendario ON/OFF balanceado ya captura la sustancia de "diferencia ON/OFF" que revisiones anteriores describían con otra notación. No reabre la arquitectura general.
**Ámbito:** `symbiont.actuation` (nuevo), `symbiont.cognition.cognition_bridge` (extendido), `symbiont.core.runtime` (extendido), `symbiont_lab.world.adapter` (nuevo puente), `symbiont.cognition.checkpoint` (extendido).
**Principio rector:** la cadena de entrada del organismo (World → Source → Sensor → Percept → Cognition) tiene hoy una simetría rota — no existe una cadena de salida equivalente. La cognición produce `readouts` que nadie consume salvo telemetría (`runtime.py:2249`); el movimiento real en World v4 lo decide `policy_rng.choice` en `symbiont_lab/world/population.py:299-317`, fuera del organismo por completo. Esta spec cierra el bucle corporal:

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

**Invariante central de esta spec:**

> **Lab puede traducir una `Actuation`, pero nunca puede elegir una actuación en nombre del organismo.**

Esto elimina explícitamente el patrón actual donde Lab filtra `valid_dirs` por permeabilidad/ocupación antes de que el organismo decida — ese filtrado le regala al organismo conocimiento del mundo que no debería tener. Tras P2, el organismo puede intentar activar un actuador cuyo efecto en World sea nulo (pared, ocupante, actuador degradado) y debe aprender de ese resultado, no ser protegido de él.

---

## 1. Frontera de paquetes

```text
symbiont/actuation/
├── types.py        # ActuatorId, MotorCandidate, MotorIntent, Actuation
├── constitution.py # ActuatorConstitution — cuerpo motor fijo, ver §3
├── candidate.py     # ActuatorCandidateState, effect-relation tracking
├── proposer.py      # exploración bounded del repertorio corporal potencial
├── system.py        # ActuatorSystem: resuelve MotorIntent → Actuation
└── health.py         # ActuatorState: health/reliability/cost
```

Se mantiene estrictamente:

```text
symbiont        ✗→ symbiont_world
symbiont        ✗→ symbiont_lab
symbiont_world  ✗→ symbiont (cognición)
```

`symbiont_lab` sigue siendo el único traductor entre organismo y mundo, exactamente como ya lo es para percepción.

---

## 2. Tipos: candidato, intención, ejecución — tres cosas distintas

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

**El efecto en World NO forma parte de `Actuation`.** `Actuation` es puramente corporal — cuánto se entregó realmente, no qué pasó fuera. La consecuencia física es responsabilidad exclusiva de World, mediada por `ActuationAdapter` en Lab (§9). Esto preserva la frontera epistemológica: el cuerpo sabe lo que hizo, no lo que provocó.

Ausencia de `MotorIntent` para un tick = ausencia de actuación. No existe un actuador `"stay"` ni un `WorldAction.rest` boolean equivalente dentro de `symbiont`; "no actuar" es la ausencia de intención, no una acción con nombre.

---

## 3. `ActuatorConstitution` — quién posee el cuerpo motor

**Corrección de revisión 2.** La revisión 1 asumía un "repertorio potencial bounded y fijo desde genesis" sin decir dónde vive ni quién lo genera. Sin esto, Lab podría terminar inventando los IDs al construir el organismo — y entonces sería el aparato quien define parte del cuerpo del organismo, exactamente la inversión de responsabilidad que esta spec existe para evitar.

`ActuatorConstitution` es una propiedad de **`symbiont`**, no de World ni de Lab:

**Corrección de revisión 4 — representación realmente inmutable.** `@dataclass(frozen=True)` no congela los `Mapping`/`dict` que contiene: dos instancias "iguales" podrían llevar diccionarios mutables distintos por dentro, y un fingerprint/hash sobre eso no es fiable. Para una constitución fingerprintable (necesaria para `ActuationBindingConstitution`, §10, y para comparar constituciones entre generaciones) se representa como tuplas ordenadas de slots, no como dataclass-con-dict:

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

Con `slots` como tupla de records inmutables (no `dict`), dos constituciones con el mismo contenido son estructuralmente iguales y hasheables sin normalización adicional — condición necesaria para que `ActuationBindingConstitution` (§10) sea un fingerprint fiable.

- Se genera de forma **determinística a partir del genoma** en `symbiont/cognition/birth.py` (mismo módulo donde hoy vive `load_base_genome`/`load_base_cognition` — no en `core/birth_authority.py`, que asigna `organism_id`/lineage/slots de hábitat y no conoce fisiología, ni en `core/canonical_birth.py`, que solo cablea cognición ya derivada dentro del flujo de restore de un resident; ver nota de arranque de P0 más abajo), no la construye Lab ni World.
- `actuator_ids` son estables durante la vida del organismo — no se regeneran tick a tick.
- **Herencia:** al reproducirse, la constitución motora es **constitucional y determinística desde el genoma del hijo**, igual que cualquier otro rasgo heredado en `birth.py` — no se copia literalmente del progenitor ni se hereda por separado como un blob opaco. Esto mantiene un único mecanismo de herencia en vez de dos.
- Lab/World solo **consumen** `actuator_ids` para construir su propio `ActuationAdapter` mapping (§9) — nunca los generan ni los alteran.

**Corrección de revisión 3 — estabilidad frente a mutaciones no motoras.** No se deriva `actuator_id = hash(genoma completo)`: una mutación irrelevante (p. ej. `learning_rate`) renombraría todos los actuadores del hijo, perdiendo la identidad corporal heredada sin motivo. En su lugar:

```text
motor_slot.0, motor_slot.1, ..., motor_slot.N   ← slots heredables, identidad estable
actuator_id = f(motor constitution schema, slot identity)   ← no depende del genoma completo
```

(`MotorSlot`/`ActuatorConstitution` como tuplas inmutables — definición exacta arriba.)

Las mutaciones genómicas pueden alterar los **parámetros** de un slot (coste, health inicial, `execution_threshold`, incluso presencia/ausencia del slot) sin renombrar los demás slots. Esto es lo que hace tratable A04 (permutar `actuator→dirección` sin cambiar IDs) y será necesario en cuanto se estudie evolución de la constitución motora entre generaciones.

`proposer.py` (§4) explora dentro de `actuator_ids` ya dados por la constitución; no los inventa.

---

## 4. Descubrimiento: repertorio corporal potencial, no universo de IDs arbitrario

`proposer.py` **no** genera IDs opacos desde un espacio abstracto infinito. Eso permitiría que el organismo "acierte" candidatos que casualmente tienen cuerpo en World, lo cual es artificial y no corresponde a ningún mecanismo biológico real.

En su lugar:

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

El organismo descubre **su cuerpo** (cuáles de sus canales potenciales son útiles), no crea miembros por enumeración aleatoria. La generación *de novo* de nuevos efectores mediante plasticidad estructural queda fuera de v1 — es una capacidad biológica distinta y más profunda, a revisar en spec separada si se decide perseguirla.

`len(actuator_ids)` es una propiedad de la constitución corporal (§3), no un parámetro de exploración.

---

## 5. Utilidad motora ≠ correlación

Error a evitar: `utility = abs(correlation(activation, Δpercept))` mide únicamente **"esto tiene efecto reproducible"**, no **"me conviene activarlo"**. Un actuador que siempre causa daño puede tener correlación altísima. Confundir ambas cosas convertiría el descubrimiento corporal en una policy de supervivencia implícita — exactamente lo que queremos evitar en esta capa.

Se separan explícitamente dos señales:

```text
effect_strength / controllability   ← "activar esto tiene consecuencias medibles y reproducibles"
                                        (lo que SÍ vive en ActuatorCandidateState, vía PairAccumulator)

adaptive_value                       ← "esas consecuencias me son favorables bajo estas condiciones"
                                        (aprendizaje posterior, vía Actuation → future percepts →
                                        future physiology → prediction error, en cognición, NO en
                                        el ActuatorSystem)
```

`ActuatorCandidateState` solo trackea la primera. La segunda pertenece al ciclo de aprendizaje cognitivo existente (prediction error, ya presente en `cognition_bridge.py`), no se reimplementa aquí.

---

## 6. `ActuatorCandidateState` — con control de contraste, no solo ensayo

Un `PairAccumulator` único por candidato es insuficiente — no sabemos a priori qué percept se ve afectado. Se trackea una tabla bounded de relaciones efecto→percept:

```text
ActuatorCandidateState
├── actuator_id
├── activations                          # historial agregado, no raw
├── effect_relations: dict[PerceptId, PairAccumulator]   # bounded
│    max_effect_relations_per_candidate = 32
├── cost_evidence
├── probing_state (active | probing | dormant)
└── last_seen_tick
```

Reutiliza `PairAccumulator`/`SensoryRelation` (`host/adaptive.py:137-256`) sin reinventar estadística — misma primitiva, aplicada a `(activation, Δpercept)` en vez de a un stream pasivo único.

**Corrección de revisión 2 — observaciones emparejadas ON/OFF.** Si durante el probing solo se registran ticks con `activation≈1`, el `PairAccumulator` no puede distinguir "el actuador causó el cambio" de "el entorno cambió por sí solo en ese mismo tick" — un ciclo ambiental de fondo produciría `Δpercept` igual sin que el actuador sea causal, y con `activation` casi constante la correlación es inútil o espuria. El presupuesto de probing exige por tanto un **calendario determinista de contraste**, independiente del percepto observado.

**Corrección de revisión 3 — el calendario no puede ser par/impar.** Una alternancia estricta `par→OFF, impar→ON` se alía perfectamente con cualquier regularidad ambiental de periodo 2 (o 4, 8...), pudiendo "descubrir" causalidad motora que en realidad es un ciclo del mundo coincidiendo en fase. En su lugar, cada ventana de probing usa una **secuencia balanceada generada por RNG namespaced del organismo**, no por índice de tick:

```text
seed = derive_rng(organism_id, actuator_id, probing_window_index)
sequence = balanced_shuffle(seed, length=window_ticks)   # igual nº de ON y OFF, orden no periódico
```

y se exige **más de una ventana con secuencias distintas** antes de que un candidato pueda pasar a `active` — una sola ventana, por balanceada que esté, sigue siendo vulnerable a un evento ambiental puntual coincidente.

**Corrección de revisión 6 — definición exacta de `effect_strength` (código y spec ya coincidían en sustancia, no en la letra).** Revisiones anteriores describían `effect_strength` como "la diferencia `Δpercept(ON) − Δpercept(OFF)` agregada entre ventanas". La implementación real (`ActuatorCandidateState.effect_strength`, `PairAccumulator.correlation`) usa en su lugar:

```text
effect_strength = max( |corr(activation, Δpercept)| )  sobre effect_relations, acumulado all-time
```

Se declara esto **explícitamente la métrica de v1**, no una aproximación provisional, por las siguientes razones:

- Con un calendario `activation ∈ {0, 1}` balanceado, la correlación de Pearson entre una variable binaria y una continua **es** la correlación point-biserial — una normalización monótona de la diferencia de medias ON vs OFF (`Δpercept(ON) − Δpercept(OFF)`), no una estadística distinta. La sustancia de "diferencia ON/OFF" ya está capturada; difiere solo en normalización.
- `effect_threshold ∈ [0.0, 1.0]` (spec §9) solo tiene sentido natural sobre una estadística ya normalizada — una diferencia de medias cruda no tiene ese rango.
- `PairAccumulator` es la primitiva ya reutilizada de `host/adaptive.py`, bounded y numéricamente estable — introducir una segunda estadística ON/OFF paralela solo para cumplir la letra literal de una frase de la spec sería duplicar infraestructura sin ganancia real.
- El requisito de replicación real ya no depende únicamente de `effect_strength`: `windows_with_effect` (revisión 5, más abajo) exige que el efecto se detecte **independientemente en múltiples ventanas separadas**, evaluando `effect_strength` sobre el acumulador transitorio de cada ventana por separado (`complete_window()`), no solo sobre el acumulado histórico. Esto refuerza A03 (§13) exactamente como pretendía la redacción original, por una vía distinta pero igual de rigurosa.

No se introduce ninguna estadística nueva. Esto es un cambio de documentación para que la spec describa fielmente el código ya implementado y verificado (matriz de 648 configuraciones, `tests/unit/actuation/test_continuity_gate.py` y `test_proposer.py`), no un cambio de comportamiento.

Bounds globales, análogos a `AdaptiveSenseModel`:

```text
max_candidates = len(ActuatorConstitution.actuator_ids)   # ver §3, ya no es un tope independiente
max_effect_relations_per_candidate = 32
```

### Lifecycle: active / probing / dormant

Idéntico en estructura a sensores (`sampling_plan()`, `host/adaptive.py:593`), con una diferencia importante: **probar un sensor solo cuesta observar; probar un actuador cambia el mundo o el organismo.** Por tanto el presupuesto de exploración motora es mucho más conservador:

```text
sensory probe_limit = 4   (referencia existente)
motor probe_limit   = 1   (default v1, ya reparte el calendario ON/OFF descrito arriba)
```

**Requisito de test explícito (revisión 4, no es cambio de diseño — la arquitectura ya lo exige vía el lag de un tick de §9).** Todo test de `effect_relations`/`PairAccumulator` debe verificar que compara `activation(t)` con `Δpercept = percept(t+1) − percept(t)`, nunca `percept(t) − percept(t)` del mismo tick. Es un requisito de implementación de P0 (construcción del `PairAccumulator`) y de verificación en P3 (motor learning real), no una nueva regla arquitectónica — la causalidad N→N+1 ya está fijada en §9.

---

## 7. Cognición: familias de readout separadas, no un solo bool

Hallazgo clave del código actual: `cognition_bridge.py` asume un único readout relevante (`_CORE_READOUT_ID = "readout_core"`, creado lazily en `_propose_new_concept_mutations` cuando `needs_readout = not readouts`, líneas 367-403). `_nodes_with_path_to_readout()` (línea 406) se reutiliza para `stranded_concepts`, recycling (`_propose_concept_recycling_mutations`, línea 436+), y fitness. Si simplemente añadimos nodos `READOUT` motores al mismo conjunto sin distinguirlos, un concepto conectado únicamente a `readout_motor:X` aparecería como "routed" aunque no tenga camino a `readout_core` — corrompiendo silenciosamente topology health, recycling y telemetría existente.

**No se hace** `_nodes_with_path_to_readout(target=None)` con `None = todos`. Se introduce semántica topológica explícita de dos familias:

```text
readout_core                    ← invariante, sin cambios; salida cognitiva general histórica
                                   sigue alimentando exclusivamente:
                                   - _nodes_with_path_to_core_readout()  (renombrado desde el actual)
                                   - unrouted tracking / recycling / topology health
                                   - telemetría existente (runtime.py:2249) — consumidor intacto

readout_motor:<opaque actuator_id>   ← nueva familia, sink independiente por actuador
                                   - _nodes_with_path_to_motor_readout(actuator_id)
                                   - NO participa en el cálculo de stranded/recycling de readout_core
```

### Materialización lazy, solo para candidatos activos

No se crea un `readout_motor` por cada uno de los candidatos potenciales de la constitución — solo para los que están en `active_repertoire`. Si un actuador vuelve a `dormant` de forma permanente y hay presión estructural, su `readout_motor:*` es candidato a reciclaje bajo las mismas reglas de recycling ya existentes en el grafo, aplicadas a esta familia por separado.

```text
candidate
   │ evidence sufficient (effect_strength por encima de umbral, bounded ticks, con control ON/OFF)
   ▼
ACTIVE
   │
   ▼
readout_motor:<id> materializa lazily (mismo patrón que needs_readout hoy)
   │
   ▼ (si vuelve a dormant permanentemente + presión estructural)
recycled
```

Esto mantiene la plasticidad motora consumiendo presupuesto cognitivo real, en vez de reservar de antemano un slot por cada candidato potencial.

---

## 8. Motor edge learning — cómo nacen las conexiones hacia `readout_motor`

**Pieza bloqueante identificada en revisión 2.** §7 define correctamente que `readout_motor:X` nace aislado de `readout_core`, pero un readout motor sin aristas entrantes es inútil: el organismo habría descubierto que posee el efector, sin poder aprender *cuándo* usarlo. Esto tiene que resolverse antes de P2, no después.

El código actual ya tiene el mecanismo a reutilizar. Cuando se crea un concepto nuevo desde fuentes `SENSE` coactivadas, `_propose_new_concept_mutations` (`cognition_bridge.py:374-403`) emite exactamente esta secuencia de `Mutation`:

```python
mutations = [
    Mutation(kind="add_node", payload={"node_id": concept_id, "kind": NodeKind.CONCEPT, ...}),
    Mutation(kind="add_node", payload={"node_id": readout_id, "kind": NodeKind.READOUT}),  # si hace falta
    Mutation(kind="add_edge", payload={
        "source_id": concept_id, "target_id": readout_id,
        "kind": EdgeKind.EXCITATORY, "weight": _TENTATIVE_WEIGHT,
        "plasticity": 0.5, "delay_ticks": 1,
    }),
]
```

y ya existe `self._structural_plasticity.observe_coactivation(...)` (línea 1124) trackeando coactivación para proponer estas conexiones.

**Corrección de revisión 3 — no reutilizar `observe_coactivation()` con la firma literal.** `observe_coactivation(source_id, target_id, source_active, target_active, tick, ...)` (`structure.py:49-59`) observa actividad entre **nodos del `CognitiveGraph` que ya existen y ya se activan**. Antes de que exista una arista, `readout_motor:X` recién materializado está aislado — no tiene ninguna activación real que reportar. Llamarlo con `target_active = actuator_is_active` sería falsificar la activación de un nodo, disfrazando una señal corporal externa (evidencia de controllability del actuador) de activación cognitiva genuina. Eso podría hacer parecer que se aprenden conexiones motoras cuando en realidad se inducen mediante una señal ajena al grafo.

En su lugar, se añade un método explícito, con su propia frontera semántica, que reutiliza el mecanismo estadístico/estructural interno (acumulador, thresholds, cooldown, `Mutation(kind="add_edge", ...)`) **sin mentir sobre activación de nodo**:

```python
def observe_motor_association_evidence(
    self,
    *,
    source_id: str,          # concept/state node, activo de verdad en el grafo
    motor_readout_id: str,   # "readout_motor:<actuator_id>", puede estar aislado
    source_active: bool,
    actuator_has_effect_evidence: bool,   # NO "target_active" — es evidencia corporal, no activación de nodo
    tick: int,
) -> None:
    ...
```

Internamente comparte acumulador/cooldown/`Mutation` con `observe_coactivation`, pero el parámetro se llama y se documenta por lo que es: evidencia de que un actuador con `effect_strength` suficiente coincidió con un concepto activo, no una activación de `readout_motor:X` que todavía no puede activarse por sí solo.

```text
concept/state activo en tick N (source_active real, vía este mismo grafo)
        │
        │  Y en la MISMA ventana, actuator_id X pasa a ACTIVE (§7) con effect_strength suficiente
        ▼
observe_motor_association_evidence(...)
        ▼
propuesta tentativa de edge:  concept_id → readout_motor:X
        kind = EXCITATORY, weight = _TENTATIVE_WEIGHT, plasticity = 0.5, delay_ticks = 1
        (mismo apply_mutations, mismo umbral minimum_support del genoma
         que ya gobierna la creación de conceptos)
```

- La señal es **puramente interna** (concepto activo + actuador con evidencia de efecto propia), nunca semántica de World.
- La arista nace **tentativa** (mismo `_TENTATIVE_WEIGHT`/`plasticity` que usa hoy el core) y queda sujeta a las mismas reglas de refuerzo/poda que cualquier arista tentativa del grafo — no se privilegia.
- `_nodes_with_path_to_motor_readout(actuator_id)` (§7) es la función que valida, para tests, que estas aristas efectivamente conectan algo alcanzable — separada de la métrica de `readout_core`.

Gate de P1→P2: al menos un test de integración que, con un actuador activo y un concepto coactivado deterministamente, verifique que nace la arista tentativa y que `readout_motor:X` deja de estar aislado — sin que esto mueva ni un bit de `stranded_concepts`/`recycling` de `readout_core`.

---

## 9. Selección de intención y tick (`core/runtime.py`)

**Corrección de revisión 2.** La revisión 1 tenía `ActuatorSystem.resolve(cognition_result.readouts_for_family("motor")) → Actuation(s)` — eso salta la frontera `MotorIntent` que los tipos (§2) ya declaraban. Se hace explícito:

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

### `MotorIntentSelector` — regla determinista vigente

El selector ya no es winner-takes-all para control cognitivo. Conserva, por
orden de activación descendente y desempate por `actuator_id`, hasta cuatro
canales por encima de `selection_threshold`.

La vista singular `select()` se conserva únicamente como compatibilidad; el
runtime canónico usa `select_many()`.

El babbling sensorimotor y las primitivas temporales no reciben RNG del Lab.
Toda exploración es interna al organismo y reproducible desde su identidad y
estado persistido.

**Corrección de revisión 3 — dos umbrales, dos dueños distintos.** `selection_threshold` no tiene todavía propietario claro frente a `execution_threshold` (§3). Se separan explícitamente:

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

Confundirlos mezclaría "cuánto quiero activar esto" (decisión cognitiva) con "cuánto puede entregar mi cuerpo" (límite físico) en un único número — exactamente la mezcla que esta spec evita en todos los demás puntos.

### Umbral de ejecución: de `activation` continua a movimiento discreto de una celda

**Corrección de revisión 2.** Había que congelar qué significa `Actuation.delivered ∈ [0,1]` para `WorldAction.move`, que hoy es una dirección discreta. Regla v1:

```text
delivered < execution_threshold   → ActuationAdapter no emite intención de movimiento
delivered >= execution_threshold  → ActuationAdapter emite un intento de movimiento (una celda)
```

`execution_threshold` es parte de `ActuatorConstitution` (§3) — pertenece al cuerpo/actuador, no a World. `cost` sí puede seguir siendo función continua de `requested`/`delivered`. Deliberadamente **no** se convierte `activation` en una probabilidad de movimiento — eso introduciría RNG en el cuerpo sin necesidad, y mezclaría indeterminismo corporal con indeterminismo de decisión, dos cosas que esta spec mantiene separadas.

### Propriocepción mínima desde P2 (no diferida)

Locomoción autónoma sin feedback corporal deja el bucle incompleto desde el primer paso — por eso la propriocepción mínima entra ya en P2, no se pospone a una fase posterior. Señales propioceptivas v1, deliberadamente sin interpretación de éxito/fracaso:

```text
motor.requested_activation.<id>
motor.delivered_activation.<id>
motor.load.<id>
```

**Corrección de revisión 3 — `motor.load` es coste interno, no resistencia del mundo.** `motor.load.<id>` reporta el **coste metabólico/esfuerzo realmente pagado por el cuerpo** al ejecutar la `Actuation` (función de `cost`/`health_at_execution` en `ActuatorConstitution`, §3) — nunca información sobre si el mundo opuso resistencia. Si una pared bloquea el movimiento, el cuerpo no recibe mágicamente esa información por este canal; eso sería un sensor mecánico de resistencia que no existe en v1. La única vía legítima para que "hubo una pared" llegue al organismo es el percept normal del tick N+1 (o su ausencia — nada cambió en la posición percibida), nunca un atajo propioceptivo.

**Corrección de revisión 2 — se elimina `motor.effect_observed.<id>` de P2.** Aunque estaba marcado opcional en revisión 1, no aporta nada que no se pueda derivar comparando perceptos consecutivos, y está peligrosamente cerca de decirle al organismo "tu acción tuvo efecto" — una interpretación, no un hecho corporal. El efecto externo debe llegar exclusivamente a través de sensores normales (percept del mundo en N+1), nunca de un canal propioceptivo dedicado a "esto funcionó". Tampoco se emite `motor.success.<id> = 1/0` por el mismo motivo: "éxito" requiere saber cuál era el objetivo, y esa inferencia vive en cognición (prediction error), no en el sensor propioceptivo.

---

## 10. `ActuationAdapter` (Lab) — traduce, no decide

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

El adapter **no** consulta geografía, ocupación ni recursos para decidir la mejor dirección — eso ya ocurrió (o no) en `MotorIntentSelector` (§9). Reemplaza por completo el bloque actual:

```python
# src/symbiont_lab/world/population.py:299-317 — A ELIMINAR en P2
valid_dirs = [d for d in range(6) if geography.can_traverse(...)]
movement_intents[organism_id] = rig.policy_rng.choice(valid_dirs)  # o None
```

**Consecuencia importante (invariante fuerte de esta spec):** hoy Lab filtra `valid_dirs` antes de ofrecer opciones — el organismo nunca puede "intentar" un movimiento imposible porque Lab ya se lo impidió. Tras P2 eso termina. El organismo puede activar `actuator.72c` aunque haya pared, ocupante, o el actuador esté degradado; World resuelve la consecuencia (incluido "no pasó nada"), y esa consecuencia —vía propriocepción y percept— es evidencia de aprendizaje. Filtrar de antemano regala al organismo conocimiento del mundo que no le corresponde tener.

**Corrección de revisión 2 — identidad reproducible del mapping.** El mapping `actuator_id → hex direction` es en sí mismo una condición experimental, no un detalle de implementación: dos runs con el mismo `world_seed` y organismo pero distinto mapping **no son la misma condición**. Se define `ActuationBindingConstitution`: un fingerprint (hash determinista del mapping completo) que forma parte del manifiesto experimental de cada run, junto a `world_seed` y genoma. Cualquier experimento que dependa de permutar el mapping (p. ej. A04, §13) debe registrar explícitamente ambos fingerprints en su manifiesto.

---

## 11. Persistencia — mínima por fase, completa en P6

**Corrección de revisión 2.** La revisión 1 dejaba todo el checkpoint para P6, pero un World ya persistente (v4 ya lo es) no puede permitirse que un restart borre el repertorio motor en cuanto P2 empieza a usar `ActuatorSystem` — ese estado pasa a formar parte del futuro causal del organismo desde el primer tick en que existe.

- **P0** ya debe definir `export()`/`restore()` de `ActuatorCandidateState`/`ActuatorState`/`ActuatorConstitution`, aunque todavía no se usen dentro de World.
- **P2** no puede entrar en un World persistente sin que ese `export()`/`restore()` esté cableado al checkpoint del organismo — un restart tiene que reproducir el mismo repertorio activo, no reiniciar el descubrimiento motor desde cero.
- **P6** sigue siendo el gran gate de *cold restart + replay equivalence completo*, verificando el sistema entero (incluyendo `readout_motor:*` ya persistido naturalmente dentro del `CognitiveGraph`), no la primera vez que se persiste nada.

**Sí se persiste** (agregados establecidos, nunca historial crudo — igual que `host/adaptive.py:661-734`):

```text
ActuatorConstitution: actuator_ids, basal_cost, initial_health, execution_threshold (inmutable, deriva del genoma)
ActuatorCandidateState: agregados de effect_relations (no Δpercept crudo)
ActuatorState: health, reliability, cost
active_repertoire (IDs)
probe cursor / probing_state / calendario ON-OFF en curso
```

**No se persiste**:

```text
last raw activation
last raw Δpercept
MotorIntent transitorio
Actuation transitoria
```

Los nodos `readout_motor:*` del `CognitiveGraph` **no se duplican** en el checkpoint de actuation — ya quedan persistidos naturalmente como parte del checkpoint existente del grafo cognitivo (`cognition/checkpoint.py`).

---

## 12. Alcance explícitamente diferido dentro de esta misma spec

`acquire` y `emit` se mantienen en el alcance end-to-end de esta spec (arquitectura), pero **después** de validar el paradigma corporal con locomoción pura — no se implementan hasta P4/P5:

- **`acquire`** hoy es `resource_id` — contiene más semántica que un actuador opaco de movimiento (`actuator → resource concreta` filtraría conocimiento corporal/mundo). P4 estudia si hace falta un actuador por recurso o un único "interaction effector" que actúa sobre la superficie local, dejando que World interprete la consecuencia.
- **`emit`** es un canal expresivo distinto (contenido `OpaqueSequence`, rango, coste) — no se mezcla con locomoción en v1.

---

## 13. Gates científicos (además de tests de software)

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

**A04 es el gate más importante de esta spec.** Ejemplo de protocolo: `actuator.A → hex direction 0` en una fase, `actuator.A → hex direction 4` en otra, sin comunicar el cambio al organismo. Cada fase registra su propio `ActuationBindingConstitution` fingerprint (§10) en el manifiesto experimental — son condiciones distintas, no la misma condición con distinto ruido. Si el comportamiento se reajusta por experiencia (no por reinicio de estado), tenemos evidencia real de aprendizaje motor y no de memorización de un mapeo fijo.

---

## 14. Fases de implementación

```text
P0 — Motor substrate
     ActuatorId (derivado de motor_slot.N estable, §3), MotorCandidate, MotorIntent, Actuation,
     ActuatorConstitution (generada determinísticamente en birth.py), ActuatorCandidateState con
     PairAccumulator + calendario de control ON/OFF balanceado no periódico, RNG-namespaced,
     multi-ventana (§6), proposer bounded sobre actuator_ids de la constitución.
     export()/restore() de constitution/candidate/state definidos ya (§11), aunque sin cablear
     todavía al checkpoint de World.
     NO cognition. NO World.
     Gate: canales opacos pueden explorarse y clasificarse active/probing/dormant de forma
           determinista y bounded, distinguiendo causal de sham vía contraste ON/OFF sostenido
           a través de múltiples calendarios, en aislamiento, con tests propios.

P1 — Cognitive output roles + motor edge learning
     Refactor cognitivo en cognition_bridge.py:
     readout_core permanece invariante; familia readout_motor introducida (§7);
     motor edge learning (§8) vía nuevo observe_motor_association_evidence en
     StructuralPlasticity — reutiliza acumulador/cooldown/Mutation de observe_coactivation
     SIN falsificar activación de readout_motor:X aislado — para proponer aristas tentativas
     concept→readout_motor:X;
     core reachability sin cambios; recycling legacy sin cambios;
     consumidor de telemetría (runtime.py:2249) sin cambios; checkpoint roundtrip sin cambios.
     NADA ejecuta un actuador todavía. Paso más auditado — tests de regresión explícitos sobre
     stranded_concepts/recycling/topology health de readout_core ANTES de tocar nada más,
     más el test de integración de §8 (arista tentativa nace, readout_motor deja de estar aislado,
     sin que ningún nodo reporte activación que no tuvo).

P2 — Closed locomotor loop (con propriocepción mínima incluida)
     motor readouts → MotorIntentSelector (§9, determinista, concurrencia bounded) →
     MotorIntent(s) → ActuatorSystem.execute → Actuation(s) → umbral de ejecución (§9) →
     Lab ActuationAdapter (con ActuationBindingConstitution fingerprint, §10) →
     World movement intent → consequence → propriocepción mínima (requested/delivered/load)
     en tick N+1.
     export()/restore() de P0 cableado al checkpoint de World — un restart reproduce el mismo
     repertorio activo (§11), no reinicia descubrimiento motor desde cero.
     Elimina policy_rng.choice(valid_dirs) de population.py.
     Elimina filtrado previo de valid_dirs (invariante §10).

P3 — Motor learning
     Actuation → Δpercept → effect relations → controllability →
     adaptación del repertorio activo. Health/cost/reliability con efecto real.

P4 — Interaction/acquisition
     Solo tras resolver su semántica corporal correcta (§12).

P5 — Emission
     Canal expresivo local, opaco, separado de locomoción.

P6 — Persistence & continuity (gate completo)
     Cold restart + replay equivalence del sistema entero (constitution + candidate state +
     active repertoire + readout_motor topology dentro del CognitiveGraph), no la primera vez
     que se persiste nada — eso ya ocurrió incrementalmente en P0/P2.
```

---

## 15. Invariantes heredadas de CLAUDE.md que esta spec respeta

- `symbiont` nunca importa `symbiont_world` ni `symbiont_lab` (actuation incluida).
- Providers/World nunca exponen semántica de identidad a cognición — igual aplica en sentido inverso: el organismo nunca exporta semántica a World, solo `actuator_id`/`activation` opacos.
- Raw telemetry no se persiste; solo estado descriptivo/aprendido bounded (§11).
- El fallo de un componente no detiene al organismo, pero **degradación fisiológica y corrupción de estado no son lo mismo** (corrección de revisión 2):

  ```text
  actuator unavailable/degraded (health baja por uso/fisiología normal)
      → delivered = 0.0
      → tick continúa sin abortar

  corrupt internal/checkpoint state (invariante de datos violado)
      → validation failure explícito
      → restore/recovery falla de forma segura (no continúa con estado inventado)
  ```

  Silenciar una corrupción de estado como si fuera `health=0` escondería bugs reales y podría producir trayectorias irreproducibles — CLAUDE.md exige que el fallo de un proveedor no detenga al organismo, no que un dato corrupto se disfrace de fisiología.
- Ninguna acción real sobre el host (`symbiont.host`) se ve afectada por esta spec — el alcance de actuación real fuera de World/simulación queda explícitamente fuera y requeriría decisión explícita del owner, igual que cualquier nueva clase de acción real ya contemplada en CLAUDE.md.

---

## 16. Revisión 5 — Hardening de P0 tras auditoría post-merge

P0 fue implementado y mergeado a `main` en la revisión 4. Una auditoría independiente del `main` resultante (no del plan, sino del código ya integrado) encontró cuatro gaps de continuidad/robustez que la revisión 4 no cerraba. Esta sección los documenta y ajusta la spec para que el código siga siendo su implementación fiel.

### 16.1 P0.1 — Persistencia de la fase del calendario motor

`ActuatorProposer` mantenía `tick_in_window` como estado transitorio **fuera** de `ActuatorCandidateState`, explícitamente no persistido ("transient scheduling phase, not established evidence"). Un restart a mitad de ventana volvía a `tick_in_window=0`, produciendo una secuencia ON/OFF distinta a la que habría ocurrido sin interrupción — `run continuo ≠ checkpoint → restore → continue`, incluso antes de conectar World.

**Corrección:** `tick_in_window` pasa a ser un campo de `ActuatorCandidateState` (persistido en `to_payload`/`from_payload`), y `ActuatorProposer` delega en él en vez de mantener su propio diccionario. Un restore reanuda la ventana exactamente donde se dejó, no la reinicia.

### 16.2 P0.2 — Validación estricta de `restore_actuation_state`

Tres endurecimientos:

1. **Igualdad de conjuntos, no subconjunto.** `set(payload["candidates"].keys())` debe ser exactamente `set(constitution.actuator_ids)` — ni de más ni de menos. `export_actuation_state` siempre exporta un candidato por actuador (incluidos los `dormant`), así que un payload con candidatos faltantes es un checkpoint truncado, no "este organismo nunca exploró algunos de sus actuadores".
2. **Coincidencia clave↔campo.** El `actuator_id` interno de cada `ActuatorCandidateState` debe coincidir con la clave del diccionario bajo la que está guardado — evita que el estado del candidato B se cuele bajo la clave A cuando ambos son IDs conocidos.
3. **`probe_cursor` estrictamente tipado.** Se valida con el mismo `_require_nonneg_int` usado en el resto del paquete (rechaza `bool`, `float`, strings numéricos y negativos) en vez de `int(...)`, que los aceptaría silenciosamente.

### 16.3 P0.3 — Replicación de efecto entre ventanas independientes (sustituye el "reset" de revisión 3/4)

La revisión 3/4 exigía que el efecto se sostuviera "a través de múltiples calendarios ON/OFF distintos", pero la promoción solo comprobaba `windows_completed >= min_probing_windows` sobre una correlación **acumulada globalmente** — una única ventana con señal muy fuerte podía sostener por sí sola una correlación acumulada alta durante varias ventanas de puro ruido, sin que el efecto se replicara realmente.

**Corrección:** `ActuatorCandidateState` añade `windows_with_effect: int` y un acumulador transitorio `_current_window_relations` (mismo `PairAccumulator`, con alcance de una sola ventana). `complete_window(effect_threshold)` evalúa **solo** la evidencia de la ventana que acaba de cerrar y, si esa ventana por sí sola supera `effect_threshold`, incrementa `windows_with_effect`; luego reinicia el acumulador transitorio. La promoción ahora exige tres condiciones:

```text
windows_completed   >= min_probing_windows   (han pasado suficientes ventanas)
windows_with_effect >= min_probing_windows   (el efecto se replicó en tantas ventanas independientes)
effect_strength     >= effect_threshold      (la correlación acumulada total también lo confirma)
```

Esto hace tratable el escenario que la revisión 3/4 solo enunciaba: una ventana ruidosa aislada con correlación alta por azar ya no basta, porque `windows_with_effect` exige repetición real.

**`windows_with_effect` y `_current_window_relations` se persisten igual que `tick_in_window` (§16.1)** — sin este segundo campo, un checkpoint a mitad de ventana perdería la evidencia parcial de esa ventana y el conteo de replicación divergería entre un run continuo y uno con checkpoint/restore (encontrado empíricamente por el gate de continuidad, §16.5, antes de llegar a `main`).

**Consecuencia — se elimina el "reset together" de I4 (revisión 3/4).** La regla anterior — resetear `windows_completed`/`windows_with_effect`/`tick_in_window` a 0 cuando `effect_relations` exportado quedaba vacío — se introdujo para evitar que un candidato promocionara con un solo post-restore window sin evidencia real detrás. Esa regla entra en conflicto directo con P0.1: resetea una fase de ventana real y no "ganada por nadie", y desincroniza el `window_index` (usado para recomputar `probing_calendar`) del índice bajo el que la evidencia fue genuinamente registrada, rompiendo la equivalencia de replay. Con `windows_with_effect` como guardia independiente — un contador que ya refleja replicación real de ventanas pasadas, sea cual sea el estado de exportación de `effect_relations` — el hazard original de I4 queda cerrado sin necesidad del reset: un candidato restaurado no puede satisfacer `windows_with_effect >= min_probing_windows` a partir de una sola ventana post-restore; solo puede estar en o por encima de ese umbral porque la replicación ya ocurrió realmente en ventanas anteriores. Ver `test_promotion_requires_re_earned_effect_strength_after_restore` (verifica la propiedad que I4 protegía, no el mecanismo de reset).

### 16.4 P0.4 — Endurecimiento adicional de validación

- `ActuatorCandidateState.from_payload` valida `activations`/`last_seen_tick`/`windows_completed`/`windows_with_effect`/`tick_in_window` con `_require_nonneg_int` (rechaza `bool`, floats, negativos) y `cost_evidence` con `_require_nonneg_finite`, en vez de `int(...)`/`float(...)` sin guardas.
- `MotorSlot.__post_init__` valida que `slot_id`/`actuator_id` sean no vacíos y que `basal_cost`/`initial_health`/`execution_threshold` estén en `[0.0, 1.0]`, defendiendo sus propios invariantes aunque se construya directamente sin pasar por `GenomeCodec`.
- `ActuatorConstitution.__post_init__` valida que todos los `actuator_id` de sus slots sean únicos.

### 16.5 Gate de continuidad (nuevo, `tests/unit/actuation/test_continuity_gate.py`)

Nuevo gate exigido por revisión 5, siguiendo exactamente el protocolo pedido en la auditoría:

```text
run A: probar N+M ticks sin interrupción
run B: probar N ticks → export_actuation_state → restore_actuation_state → probar M ticks más
assert: mismo active_repertoire, mismo estado de cada candidato
        (probing_state, windows_completed, windows_with_effect, tick_in_window),
        mismas effect_relations bit a bit (PairAccumulator es comparable por
        igualdad de campos; to_payload/from_payload no pierde precisión)
```

El split se elige deliberadamente **a mitad de ventana** (`tick_in_window` no nulo en el punto de corte) para que el test sea significativo — un split en un límite de ventana no habría detectado la pérdida de `_current_window_relations` que este mismo gate encontró durante el desarrollo de la revisión 5. Éste es el gate que cierra P0 de forma fuerte: el sustrato motor sobre el que se injertará cognición en P1 es reproducible frente a interrupción/restart.

### 16.6 Contrato exacto de equivalencia de replay — checkpoint ≠ estado externamente observable

Durante el desarrollo de §16.3/§16.5 se descubrió, mediante una matriz de verificación (múltiples seeds × puntos de split × configuraciones de `slot_count`/`probe_limit`), que el propio gate de exportación de `effect_relations` (heredado de `SensoryRelation.to_payload(min_samples=...)` en `host/adaptive.py`, que retiene relaciones con pocas muestras para no exponer una correlación inmadura como conocimiento establecido a un observador externo) es en sí mismo una fuente de pérdida **permanente** frente a un checkpoint: un acumulador Welford es un agregado en marcha, no un log reproducible. Si una muestra no se persiste, no hay forma de "recuperarla" después — el acumulador restaurado sigue una trayectoria estadística distinta al continuo **para siempre**, no solo durante el tick en que la muestra faltaba.

**Primer intento de corrección (bajar el umbral a 2) resultó insuficiente.** Un primer test de esta sección afirmaba que un run con checkpoint diverge solo en el tick donde una relación tenía menos de 2 muestras, y que después "converge". Eso es matemáticamente falso: si la muestra A se descarta en el checkpoint, el run restaurado nunca vuelve a contener A en su acumulador — `mean_x`, `mean_y`, `m2_x`, `m2_y`, `c_xy` permanecen distintos de los del run continuo indefinidamente, por muchas muestras nuevas que lleguen después. El test original tampoco detectó esto porque no restauraba realmente el payload exportado; seguía alimentando el mismo objeto `proposer` en memoria (falso positivo corregido en `tests/unit/actuation/test_continuity_gate.py`).

**Decisión final (revisión 5): el checkpoint no es una proyección filtrada — es el estado interno completo del organismo.** `ActuatorCandidateState.to_payload()`/`from_payload()` exportan `effect_relations` y `current_window_relations` **sin ningún umbral de muestras**, incluyendo relaciones con `count == 1`. Se elimina por completo `_MIN_RELATION_SAMPLES_FOR_EXPORT`. Razón:

- El argumento de privacidad de `SensoryRelation` ("con una muestra, la media es literalmente el dato crudo") es real, pero se aplica a **exponer** una lectura a un observador externo. Un checkpoint no es eso — es el propio organismo persistiendo su propio estado interno para continuar siendo él mismo tras un restart, exactamente como ya hacen `checkpoint()`/`restore()` para el `CognitiveGraph` en `symbiont.cognition.checkpoint`.
- `PairAccumulator.correlation` (host/adaptive.py) ya devuelve `None` por debajo de `count < 3` — una relación inmadura nunca puede influir en `effect_strength` ni en la promoción, se exporte o no. No hay ningún riesgo de que una correlación de una sola muestra "aparente estar establecida": el propio primitivo estadístico lo impide, independientemente del checkpoint.
- Si en el futuro se construye una proyección observable externamente (p. ej. un Observatory que muestre "qué ha aprendido este organismo sobre su cuerpo"), ese gate de consolidación pertenece a **esa** capa, nueva y todavía no construida — nunca al mecanismo de checkpoint en sí, que debe seguir siendo fiel al 100 % del estado interno real.

**Contrato resultante, ahora sí exacto y sin excepciones:**

```text
run continuo (N+M ticks)
==
run con checkpoint en cualquier tick k (0 <= k <= N+M) → export → restore → continuar

para todo k, incluido k=0 (antes de la primera muestra)
```

Verificado por `tests/unit/actuation/test_continuity_gate.py` con splits parametrizados desde `0` (antes de cualquier muestra) hasta varios límites de ventana, en configuraciones de uno y varios actuadores, y por la matriz de 624 configuraciones (3 formas de cuerpo × 6 seeds × hasta 48 puntos de split) referenciada en el commit — 0 divergencias inesperadas.

### 16.7 Revisión 6 — validación cruzada entre campos en `restore_actuation_state`

`ActuatorCandidateState.from_payload` (§16.4/P0.4) valida cada campo individualmente (tipo, no negatividad) pero no las relaciones entre ellos. Un payload podía pasar `from_payload` con campos internamente imposibles:

```text
windows_with_effect = 5, windows_completed = 2       # replicación acreditada en ventanas que nunca ocurrieron
tick_in_window >= window_ticks                        # posición de calendario fuera de rango
probing_state = "active" sin evidencia que lo respalde
```

El segundo caso es el más peligroso: no falla en `restore_actuation_state`, sino varios ticks después, dentro de `probing_calendar`, como un índice fuera de rango — lejos de su causa real y del momento en que el checkpoint corrupto entró al sistema.

**Corrección:** `restore_actuation_state` (que ya conoce `window_ticks`/`min_probing_windows`/`effect_threshold`, a diferencia de `ActuatorCandidateState.from_payload`, que no tiene esa configuración) valida, para cada candidato reconstruido, antes de instalarlo:

```text
windows_with_effect <= windows_completed
tick_in_window < window_ticks
si probing_state == "active":
    windows_completed   >= min_probing_windows
    windows_with_effect >= min_probing_windows
    effect_strength     >= effect_threshold
```

Cualquier violación levanta `ValueError` inmediatamente durante el restore — consistente con el resto de esta sección: un checkpoint corrupto debe fallar en el momento de la corrupción, nunca varios ticks después como un síntoma indirecto.


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

Up to four channels can participate concurrently. Channel sets persist over a
short epoch while amplitude evolves smoothly. Coverage bias favors
under-exercised constitutional channels, preventing one easy actuator from
monopolizing development.

### Sensorimotor dynamics

The learner records bounded sufficient statistics relating:

```text
opaque body state(t) + delivered motor vector(t)
    -> opaque body-state change(t+h)
```

for independent horizons `h ∈ {1, 4, 16, 64}`.

Horizon statistics remain separate.

### Motor primitives

A four-tick temporal sequence of actually delivered motor vectors may become an
opaque `MotorPrimitive` candidate. The sequence can contain a different
multi-channel vector at every tick. Primitive identity is derived from the
learned sequence; it has no semantic label.

A single episode is only a hypothesis. Endogenous replay must reproduce a
directionally consistent body-state transformation before the primitive becomes
cognitively available. Contradictory replication lowers controllability and can
remove the primitive entirely.

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

The complete sensorimotor state is part of organism persistence. Checkpoint
restore must preserve babbling phase, sufficient statistics, learned primitives
and verification state.
