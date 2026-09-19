# Symbiont Actuation v1 — Motor Apparatus & Closed Body Loop

**Estado:** diseño y especificación técnica end-to-end, revisión 4 — **READY FOR P0** (arquitectura completa; implementación por fases). Revisión 1: `draft / needs amendment`. Revisión 2: `approvable with 4 hardenings`. Revisión 3: `4 hardenings incorporados` (calendario de probing no periódico, `observe_motor_association_evidence` sin falsificar activación de nodo, slots motores heredables estables, separación `selection_threshold`/`execution_threshold` y `motor.load` como coste interno). Revisión 4 fija dos detalles de arranque de P0 (ubicación exacta de la derivación de constitución, representación inmutable) y un requisito de test explícito; no reabre la arquitectura — todas las secciones quedan `CLOSED`.
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
│    max_effect_relations_per_candidate = 16
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

y se exige **más de una ventana con secuencias distintas** antes de que un candidato pueda pasar a `active` — una sola ventana, por balanceada que esté, sigue siendo vulnerable a un evento ambiental puntual coincidente. `effect_strength` se calcula sobre la diferencia `Δpercept(ON) − Δpercept(OFF)` agregada across ventanas, no sobre la correlación bruta de una sola serie. Esto refuerza directamente **A03** (§13): un actuador solo se considera causal si esa diferencia se sostiene a través de múltiples calendarios distintos, no si coincide con un único patrón fijo.

Bounds globales, análogos a `AdaptiveSenseModel`:

```text
max_candidates = len(ActuatorConstitution.actuator_ids)   # ver §3, ya no es un tope independiente
max_effect_relations_per_candidate = 16
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

### `MotorIntentSelector` — regla determinista v1

Para locomoción, **como máximo un `MotorIntent` locomotor por tick**:

```text
candidatos = { actuator_id: activation for readout_motor:actuator_id en motor_readouts si activation >= selection_threshold }
si candidatos vacío:
    MotorIntent = None   (ausencia de actuación, no "stay")
si no:
    winner = argmax(candidatos, desempate por actuator_id ascendente)  # determinista, sin RNG de Lab
    MotorIntent(actuator_id=winner, activation=candidatos[winner])
```

Sin RNG de Lab en ningún punto de esta selección — si hace falta romper empates estocásticamente en el futuro, ese RNG vive en `symbiont` (namespaced, como el resto de RNG del organismo), nunca en `policy_rng` de Lab.

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
     motor readouts → MotorIntentSelector (§9, determinista, un intent locomotor por tick) →
     MotorIntent → ActuatorSystem.execute → Actuation → umbral de ejecución (§9) →
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
