# Symbiont Actuation v1 — Motor Apparatus & Closed Body Loop

**Estado:** diseño y especificación técnica end-to-end (arquitectura completa; implementación por fases).
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
├── types.py     # ActuatorId, MotorCandidate, MotorIntent, Actuation
├── candidate.py # ActuatorCandidateState, effect-relation tracking
├── proposer.py  # exploración bounded del repertorio corporal potencial
├── system.py    # ActuatorSystem: resuelve MotorIntent → Actuation
└── health.py    # ActuatorState: health/reliability/cost
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
    (activation deseada sobre un actuator_id)

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

**El efecto en World NO forma parte de `Actuation`.** `Actuation` es puramente corporal — cuánto se entregó realmente, no qué pasó fuera. La consecuencia física es responsabilidad exclusiva de World, mediada por `ActuationAdapter` en Lab (§7). Esto preserva la frontera epistemológica: el cuerpo sabe lo que hizo, no lo que provocó.

Ausencia de `MotorIntent` para un tick = ausencia de actuación. No existe un actuador `"stay"` ni un `WorldAction.rest` boolean equivalente dentro de `symbiont`; "no actuar" es la ausencia de intención, no una acción con nombre.

---

## 3. Descubrimiento: repertorio corporal potencial, no universo de IDs arbitrario

`proposer.py` **no** genera IDs opacos desde un espacio abstracto infinito. Eso permitiría que el organismo "acierte" candidatos que casualmente tienen cuerpo en World, lo cual es artificial y no corresponde a ningún mecanismo biológico real.

En su lugar:

```text
body constitution (bounded, fijo por organismo desde genesis)
      ↓
opaque potential actuators   ← conjunto finito, ya existe físicamente
      ↓
proposer                     ← decide CUÁLES explorar y en qué orden
      ↓
probing                      ← activación real, presupuestada
      ↓
active repertoire            ← selección bounded que entra en cognición rutinaria
```

El organismo descubre **su cuerpo** (cuáles de sus canales potenciales son útiles), no crea miembros por enumeración aleatoria. La generación *de novo* de nuevos efectores mediante plasticidad estructural queda fuera de v1 — es una capacidad biológica distinta y más profunda, a revisar en spec separada si se decide perseguirla.

`max_potential_actuators` es una propiedad de la constitución corporal (análoga a los sensores físicamente disponibles), no un parámetro de exploración.

---

## 4. Utilidad motora ≠ correlación

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

## 5. `ActuatorCandidateState`

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

Bounds globales, análogos a `AdaptiveSenseModel`:

```text
max_candidates = 64
active_limit = <constitution-dependent, e.g. 8>
max_effect_relations_per_candidate = 16
```

### Lifecycle: active / probing / dormant

Idéntico en estructura a sensores (`sampling_plan()`, `host/adaptive.py:593`), con una diferencia importante: **probar un sensor solo cuesta observar; probar un actuador cambia el mundo o el organismo.** Por tanto el presupuesto de exploración motora es mucho más conservador:

```text
sensory probe_limit = 4   (referencia existente)
motor probe_limit   = 1   (default v1)
```

---

## 6. Cognición: familias de readout separadas, no un solo bool

Hallazgo clave del código actual: `cognition_bridge.py` asume un único readout relevante (`_CORE_READOUT_ID = "readout_core"`, creado lazily por `needs_readout`). `_nodes_with_path_to_readout()` se reutiliza para `stranded_concepts`, recycling, y fitness. Si simplemente añadimos nodos `READOUT` motores al mismo conjunto sin distinguirlos, un concepto conectado únicamente a `readout_motor:X` aparecería como "routed" aunque no tenga camino a `readout_core` — corrompiendo silenciosamente topology health, recycling y telemetría existente.

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

No se crea un `readout_motor` por cada uno de los (hasta 64) candidatos — solo para los que están en `active_repertoire`. Si un actuador vuelve a `dormant` de forma permanente y hay presión estructural, su `readout_motor:*` es candidato a reciclaje bajo las mismas reglas de recycling ya existentes en el grafo, aplicadas a esta familia por separado.

```text
candidate
   │ evidence sufficient (effect_strength por encima de umbral, bounded ticks)
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

## 7. Integración en el tick (`core/runtime.py`)

```text
tick N:
  1792  sensory_system.transduce(...)        → percepts
  1969  cognitive_bridge.tick(...)           → cognition_result (.readouts, .prediction_errors)
  NEW   ActuatorSystem.resolve(
            cognition_result.readouts_for_family("motor")
        )                                     → Actuation(s)
        [antes de finalización de percept/journal del tick]

  Lab (fuera de symbiont):
        ActuationAdapter.translate(Actuation) → WorldAction
        World resuelve consecuencia física

tick N+1:
  1792  sensory_system.transduce(...) incluye evidencia propioceptiva de tick N
```

El lag de un tick (intent/actuation en N, percept propioceptivo en N+1) es exactamente el patrón ya existente para `delay_ticks=1` en `graph.py:159-162`. No se introduce ningún scheduler ni primitiva de delay nueva — mantiene causalidad, checkpoint semantics y cold-restart semantics alineados con el resto del `CognitiveGraph`.

### Propriocepción mínima desde P2 (no diferida)

Locomoción autónoma sin feedback corporal deja el bucle incompleto desde el primer paso — por eso la propriocepción mínima entra ya en P2, no se pospone a una fase posterior. Señales propioceptivas v1, deliberadamente sin interpretación de éxito/fracaso:

```text
motor.requested_activation.<id>
motor.delivered_activation.<id>
motor.load.<id>
motor.effect_observed.<id>    # opcional, solo si se puede definir sin semántica de "logré lo que quería"
```

**No** se emite `motor.success.<id> = 1/0`: "éxito" ya es una interpretación (requiere saber cuál era el objetivo). El organismo debe poder aprender por sí mismo, a partir de los hechos crudos (requested vs delivered vs load), si el resultado le fue favorable — esa inferencia vive en cognición (prediction error), no en el sensor propioceptivo.

---

## 8. `ActuationAdapter` (Lab) — traduce, no decide

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

El adapter **no** consulta geografía, ocupación ni recursos para decidir la mejor dirección — eso ya ocurrió (o no) en la selección de la cognición del organismo. Reemplaza por completo el bloque actual:

```python
# src/symbiont_lab/world/population.py:299-317 — A ELIMINAR en P2
valid_dirs = [d for d in range(6) if geography.can_traverse(...)]
movement_intents[organism_id] = rig.policy_rng.choice(valid_dirs)  # o None
```

**Consecuencia importante (invariante fuerte de esta spec):** hoy Lab filtra `valid_dirs` antes de ofrecer opciones — el organismo nunca puede "intentar" un movimiento imposible porque Lab ya se lo impidió. Tras P2 eso termina. El organismo puede activar `actuator.72c` aunque haya pared, ocupante, o el actuador esté degradado; World resuelve la consecuencia (incluido "no pasó nada"), y esa consecuencia —vía propriocepción y percept— es evidencia de aprendizaje. Filtrar de antemano regala al organismo conocimiento del mundo que no le corresponde tener.

---

## 9. Persistencia

**Sí se persiste** (agregados establecidos, nunca historial crudo — igual que `host/adaptive.py:661-734`):

```text
ActuatorCandidateState: agregados de effect_relations (no Δpercept crudo)
ActuatorState: health, reliability, cost
active_repertoire (IDs)
probe cursor / probing_state
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

## 10. Alcance explícitamente diferido dentro de esta misma spec

`acquire` y `emit` se mantienen en el alcance end-to-end de esta spec (arquitectura), pero **después** de validar el paradigma corporal con locomoción pura — no se implementan hasta P4/P5:

- **`acquire`** hoy es `resource_id` — contiene más semántica que un actuador opaco de movimiento (`actuator → resource concreta` filtraría conocimiento corporal/mundo). P4 estudia si hace falta un actuador por recurso o un único "interaction effector" que actúa sobre la superficie local, dejando que World interprete la consecuencia.
- **`emit`** es un canal expresivo distinto (contenido `OpaqueSequence`, rango, coste) — no se mezcla con locomoción en v1.

---

## 11. Fases de implementación

```text
P0 — Motor substrate
     ActuatorId, MotorCandidate, MotorIntent, Actuation, ActuatorCandidateState,
     PairAccumulator effect evidence, proposer bounded sobre repertorio corporal fijo.
     NO cognition. NO World.
     Gate: canales opacos pueden explorarse y clasificarse active/probing/dormant
           de forma determinista y bounded, en aislamiento, con tests propios.

P1 — Cognitive output roles
     Refactor exclusivamente cognitivo en cognition_bridge.py:
     readout_core permanece invariante; familia readout_motor introducida;
     core reachability sin cambios; recycling legacy sin cambios;
     consumidor de telemetría (runtime.py:2249) sin cambios;
     checkpoint roundtrip sin cambios.
     NADA ejecuta un actuador todavía. Paso más auditado — tests de regresión
     explícitos sobre stranded_concepts/recycling/topology health ANTES de
     tocar nada más.

P2 — Closed locomotor loop (con propriocepción mínima incluida)
     CognitiveBridge → MotorIntent → ActuatorSystem → Actuation →
     Lab ActuationAdapter → World movement intent → consequence →
     propriocepción mínima en tick N+1.
     Elimina policy_rng.choice(valid_dirs) de population.py.
     Elimina filtrado previo de valid_dirs (invariante §8).

P3 — Motor learning
     Actuation → Δpercept → effect relations → controllability →
     adaptación del repertorio activo. Health/cost/reliability con efecto real.

P4 — Interaction/acquisition
     Solo tras resolver su semántica corporal correcta (§10).

P5 — Emission
     Canal expresivo local, opaco, separado de locomoción.

P6 — Persistence & continuity
     Checkpoint completo de ActuatorCandidateState/ActuatorState,
     cold restart, replay equivalence.
```

---

## 12. Gates científicos (además de tests de software)

```text
A01  ¿Activa canales sin recibir semántica platform-side?
A02  ¿Distingue un actuador causal de un actuador sham (sin efecto)?
A03  ¿Descubre actuator→percept contingencies por encima de correlación ambiental de fondo?
A04  ¿Puede reaprender si permutamos actuator→dirección física sin cambiar los IDs?
A05  ¿Detecta degradación de un actuador (health decreciente)?
A06  ¿Diferencia "quise actuar" (MotorIntent) de "mi cuerpo actuó" (Actuation)
     de "el mundo cambió" (consecuencia en World, fuera de symbiont)?
A07  ¿La locomoción autónoma mejora respecto a activación aleatoria de actuadores,
     sin usar un oracle de posición para medirlo?
```

**A04 es el gate más importante de esta spec.** Ejemplo de protocolo: `actuator.A → hex direction 0` en una fase, `actuator.A → hex direction 4` en otra, sin comunicar el cambio al organismo. Si el comportamiento se reajusta por experiencia (no por reinicio de estado), tenemos evidencia real de aprendizaje motor y no de memorización de un mapeo fijo.

---

## 13. Invariantes heredadas de CLAUDE.md que esta spec respeta

- `symbiont` nunca importa `symbiont_world` ni `symbiont_lab` (actuation incluida).
- Providers/World nunca exponen semántica de identidad a cognición — igual aplica en sentido inverso: el organismo nunca exporta semántica a World, solo `actuator_id`/`activation` opacos.
- Raw telemetry no se persiste; solo estado descriptivo/aprendido bounded (§9).
- El fallo de un componente no detiene al organismo: un `ActuatorCandidateState` corrupto o un actuador degradado a `health=0` no debe abortar el tick, solo producir `delivered=0.0`.
- Ninguna acción real sobre el host (`symbiont.host`) se ve afectada por esta spec — el alcance de actuación real fuera de World/simulación queda explícitamente fuera y requeriría decisión explícita del owner, igual que cualquier nueva clase de acción real ya contemplada en CLAUDE.md.
