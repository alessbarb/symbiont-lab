# Symbiont World v1

> **Especificación normativa, no implementación.** Nada de lo descrito aquí
> existe en `src/`. Este documento fija el contrato, los invariantes y el
> modelo de tick que cualquier implementación futura de `symbiont_world` debe
> cumplir. El estado real de implementación se verifica únicamente en
> [`../roadmap.md`](../roadmap.md) y [`../../ORGANISM.md`](../../ORGANISM.md).
> El razonamiento, los antecedentes de ALife y la bibliografía que motivan
> este diseño están en
> [`symbiont-world-v1-rationale.md`](symbiont-world-v1-rationale.md).

## 1. Qué es

Symbiont World es un entorno digital espacial, persistente, causal, finito y
semánticamente opaco desde la perspectiva de sus habitantes, capaz de
sostener indefinidamente una ecología de Symbionts y de producir un registro
reproducible completo de su historia. No es un juego: sin misiones, sin
score, sin fitness explícito, sin recompensa. La única consecuencia de una
acción es su efecto físico sobre el organismo que la ejecuta.

Es una tercera pieza junto a `symbiont` y `symbiont_lab`, no un reemplazo de
`SharedHabitat` ni de `IntegratedHabitatRuntime`: los extiende con topología
espacial, campos y dinámica ambiental.

## 2. Frontera de paquetes

```
symbiont_world   →  (nada)
symbiont         →  (nada nuevo; sigue sin importar symbiont_lab)
symbiont_lab     →  symbiont_world, symbiont
```

`symbiont_world` no importa `symbiont` ni `symbiont_lab`. `symbiont` no
importa `symbiont_world`: el organismo sigue recibiendo únicamente lecturas
normalizadas a través de `source → sensor → percept`, igual que con el host
real. `WorldObservation` y `WorldAction` (§4) son propiedad de
`symbiont_world`; `symbiont_lab` es quien instancia un mundo, lo conecta a un
`ModeledOrganismRuntime` existente y traduce en ambas direcciones. Este
documento añade una regla a las pruebas de dependencia AST existentes
(`tests/experimental_integrity/test_ground_truth_boundary.py` y afines):
ninguna importación de `symbiont_world` aparece bajo `src/symbiont/`.

## 3. Invariantes epistemológicos

Cada uno debe ser verificable por un test automatizado antes de que el mundo
alimente a un organismo real:

1. **No ground truth al organismo.** Ningún campo `world.semantic.*`,
   `observer.*` ni `ground_truth.*` cruza hacia `Sensor`, `CognitiveGraph`,
   Private SLM, cultura o decisión. Los recursos y campos tienen identidad
   opaca (`resource.<hash>`, `field.<hash>`); su significado real vive
   exclusivamente en metadata de apparatus (`symbiont_lab`), nunca en el
   contrato que ve el organismo.
2. **Determinismo estricto.** `world_seed + eventos + estado RNG ⇒` futuro
   único. El RNG del mundo usa flujos namespaced con el mismo esquema de
   derivación que `symbiont.environment.rng.derive_seed` (sha256 de
   `prefix:seed:namespace`), reimplementado dentro de `symbiont_world` sin
   importar `symbiont` (§2), para no perturbar la reproducibilidad
   same-seed de los experimentos sintéticos existentes.
3. **Sin canal de retorno del Observatory.** `Observatory → World` no existe,
   ni siquiera deshabilitado. Observatory solo lee `WorldEvent` y snapshots.
4. **Sin fitness impuesto.** Ninguna función de utilidad evaluator-side se
   inyecta como señal al organismo. La selección emerge solo de recursos,
   coste, reproducción y muerte ya existentes en la fisiología.
5. **Sin broadcast global.** Toda comunicación y todo contacto son locales:
   dependen de `range`, `attenuation` y coste. No existe un canal que
   alcance a toda la población en un tick.
6. **No duplicar fisiología.** World nunca introduce una segunda contabilidad
   de energía/salud; solo produce entradas (`resource acquisition`) que se
   entregan al `MetabolicLedger` ya existente en `symbiont`.
7. **Fallo perceptivo se tolera; fallo de transición de estado no.** Se
   distinguen dos clases de fallo, con semántica opuesta:
   - **Observation failure** (p. ej. un `ObservableSource` puntual no
     produce lectura): el organismo continúa el tick con percept
     missing/unavailable, igual que un provider real puede fallar sin
     detener la cognición.
   - **World state transition failure** (p. ej. `field propagation` o
     `resolve resource competition` no completan de forma consistente): el
     tick mundial **no se confirma**. No existe avance parcial de
     causalidad — o el tick completo se aplica (commit), o se aborta y se
     reintenta desde el último estado confirmado (rollback). Un organismo
     nunca cogniciona ni actúa sobre un tick que no ocurrió físicamente.

## 4. Contrato `WorldObservation` / `WorldAction`

Dos tipos, y nada más cruza la frontera.

### `WorldObservation` (World → organismo, vía `ObservableSource`)

Campos permitidos, todos escalares o vectores acotados de escalares:

- `signals: Mapping[SignalId, float]` — lecturas locales de campos/recursos
  bajo identidad opaca (`SignalId` es un hash estable, no un nombre
  semántico).
- `contact: Sequence[ContactEvidence]` — evidencia de fuentes cercanas
  (intensidad, no identidad tipada: nunca `entity.type = symbiont`).
- `reception: Sequence[ReceivedEmission]` — emisiones recibidas con
  intensidad atenuada, mismo contrato que la comunicación estructurada
  existente.
- `internal: Mapping[str, float]` — proyección de estado fisiológico interno
  ya existente (reserva, integridad), no nueva.

Explícitamente excluido: `cell_id`, coordenadas absolutas, orientación
numerada con semántica, cualquier `field.NN =` con nombre real, distancia a
un objetivo con significado impuesto.

### `WorldAction` (organismo → World)

- `move: ActuatorId` — uno de un repertorio pequeño y fijo de canales
  direccionales opacos más "stay"; el mapeo actuador→dirección vive solo en
  metadata de apparatus.
- `sample: SignalId | None` — intención de muestreo de una fuente local.
- `acquire: SignalId | None` — intención de adquisición de un recurso local.
- `emit: OpaqueSequence | None` — reutiliza el canal de comunicación
  estructurada existente, con coste y rango espacial añadidos.
- `rest: bool`

Explícitamente excluido: `eat()`, `attack()`, `mate()`, `trade()` o
cualquier acción con semántica de alto nivel impuesta por el diseño. El
significado emergente de combinaciones de primitivas es un resultado a
observar, no una capacidad a implementar.

Ambos tipos son inmutables por tick y no exponen ningún handle a `World`,
`Cell`, `Resource`, `Hazard` ni a la verdad de terreno.

## 5. Modelo de tick

El orden es parte del contrato, no un detalle de implementación; ninguna
implementación puede depender de orden de iteración de diccionario o de
scheduling de hilos. La secuencia es única, pero el *ownership* de cada fase
está separado por diseño: `symbiont_world` (WORLD/RESOLUTION/COMMIT) nunca
ejecuta cognición, y `symbiont` (ORGANISM) nunca ve estado de mundo crudo —
`symbiont_lab` es el único orquestador que atraviesa la frontera en ambos
sentidos:

```
WORLD PHASE           (owner: symbiont_world.WorldKernel)
 1  world scheduled processes
 2  field propagation
 3  resource renewal/decay
 4  local observation surfaces per organism → WorldObservation

ORGANISM PHASE        (owner: symbiont_lab orchestrator, delegando en
                        symbiont.* ya existente; symbiont_world no participa)
 5  sensor sampling (existing Sensor contract)
 6  organism cognition
 7  organism decisions → WorldAction intents

RESOLUTION PHASE      (owner: symbiont_world.WorldKernel, consume
                        WorldAction, nunca estado interno del organismo)
 8  resolve movement
 9  resolve resource competition
10  resolve contacts
11  resolve communications
12  physiological consequences — traducido por symbiont_lab hacia el
    `MetabolicLedger` existente en `symbiont`; el kernel de World solo
    produce cantidades de recurso adquirido, no aplica fisiología
13  births (existing habitat-authorized path, invocado por symbiont_lab)
14  deaths (existing terminal physiology state, invocado por symbiont_lab)
15  cultural deliveries (existing entry points, invocado por symbiont_lab)

COMMIT PHASE          (owner: symbiont_world.WorldKernel)
16  telemetry
17  journal commit (append WorldEvent) — tick queda confirmado aquí; antes
    de este punto un fallo de WORLD/RESOLUTION phase aborta el tick entero
18  checkpoint if due
```

Las fases 12–15 son responsabilidad de `symbiont_lab` como adaptador: el
kernel de World nunca importa ni invoca directamente `MetabolicLedger`,
reproducción o cultura — solo emite las cantidades/eventos que el
orquestador traduce hacia las APIs ya existentes de `symbiont`. Esto es lo
que mantiene válida la frontera de paquetes de §2.

**Resolución de intents simultáneos.** Cuando dos o más organismos declaran
intención sobre el mismo recurso/celda en el mismo tick, la resolución nunca
depende del orden de ejecución de las intenciones (evita ventaja accidental
por orden). La regla de asignación (proporcional, lotería determinista con
RNG namespaced, o dependiente de coste) se declara explícitamente en la
configuración del mundo y debe ser reproducible byte a byte para el mismo
seed y el mismo conjunto de intents.

## 6. Esquema de eventos (`WorldEvent`)

World es event-sourced desde el día uno; los snapshots son una optimización
de rendimiento, no la fuente de verdad.

```
event_id
world_id
tick
kind            # WORLD_FIELD_CHANGED | RESOURCE_RENEWED | ORGANISM_MOVED |
                # RESOURCE_ACQUIRED | ORGANISM_EMITTED | ORGANISM_CONTACT |
                # BIRTH | DEATH | GENOME_MUTATION | CULTURAL_TRANSMISSION
actor           # organism id, o null para eventos puramente ambientales
position        # cell id opaco
payload         # bounded, tipado por kind
causal_parent_ids       # event_id[] — causalidad mecánica conocida por el
                        # kernel, p.ej. RESOURCE_ACQUIRED →
                        # METABOLIC_RESERVE_CHANGED
contributing_event_ids  # event_id[] — antecedentes relevantes sin afirmar
                        # causalidad suficiente, p.ej. una secuencia de
                        # METABOLIC_RESERVE_CHANGED contribuyendo a
                        # REPRODUCTION_READY, donde el umbral depende de
                        # estado acumulado y no de un único evento previo
```

El log es append-only. `causal_parent_ids` se reserva para relaciones que el
kernel garantiza por construcción (una transición de estado que solo puede
producirse como efecto directo de otra, en el mismo tick o el inmediato
siguiente). Todo lo demás —relaciones que dependen de estado acumulado,
umbrales o múltiples antecedentes concurrentes— va en
`contributing_event_ids`. Observatory debe distinguir ambos al reconstruir
genealogías: presentar `contributing_event_ids` como causalidad estricta
sería afirmar más certeza de la que el kernel tiene.

## 7. Genesis v1 (configuración congelada)

```toml
[world]
schema = 1
width = 64
height = 64
topology = "hex"
seed = 101

[population]
founders = 8
capacity = 64

[time]
checkpoint_interval = 1024

[fields]
count = 4

[resources]
count = 4

[hazards]
count = 2

[communication]
local = true
attenuation = true
```

El significado real de cada `field.N`/`resource.N`/`hazard.N` (qué ciclo
sigue, qué efecto fisiológico produce, qué depende de qué) se documenta
únicamente en metadata de apparatus dentro de `symbiont_lab`, nunca en el
contrato del organismo ni en este archivo de configuración congelado.

Al menos un recurso debe tener beneficio inmediato con daño diferido (para
probar si el sistema predictivo existente evita preferirlo por reactividad
pura), y al menos un hazard debe depender de densidad poblacional (para
introducir retroalimentación organismo→mundo, no solo mundo→organismo).

### Ground truth congelada de Genesis

`world.toml` fija dimensiones y conteos; no basta para identificar un mundo
reproducible porque las dinámicas reales quedan sin especificar. Necesita un
segundo archivo, evaluator-side y jamás visible al organismo:

```
experiments/world/genesis-v1/world-ground-truth.toml
```

que congela, por cada `field.N`/`resource.N`/`hazard.N`:

```
field equations              # forma funcional exacta (p.ej. F(t)=a+b·sin(ωt+φ))
initial distributions
diffusion constants
resource renewal laws
resource physiological effects   # mapeo hacia efectos del MetabolicLedger
hazard equations
population-density coupling      # acoplamiento explícito para W06
delays                            # p.ej. el retardo del daño diferido
RNG namespaces                    # vía symbiont.environment.rng.derive_seed
boundary conditions
```

`Genesis seed = 101` sin este archivo no identifica un mundo: identifica solo
su geometría y conteos. La tupla reproducible completa es
`(world.toml, world-ground-truth.toml, seed)`.

### Colocación de founders

Los 8 founders comparten genoma y arquitectura germinal, pero **no** la
misma celda inicial: colocarlos juntos introduciría interacción social
intensa antes de que ninguno haya aprendido a percibir el mundo. La
colocación es una función determinista `seed → founder placement`, declarada
en `world-ground-truth.toml`, no aleatoria en tiempo de ejecución ni
elegida por el implementador ad hoc.

W02 es la excepción deliberada: para aislar divergencia por historia
estocástica pura, sus réplicas parten de la misma celda inicial, tal como ya
fija el gate.

### Embodiment espacial (`WorldBody`)

Pertenece a `symbiont_world`, no al `SelfModel` del organismo — es lo que el
mundo sabe sobre dónde está un cuerpo, no lo que el organismo cree sobre sí
mismo:

```
WorldBody {
    organism_id
    occupied_cell
    orientation_state
    interaction_radius
    emission_origin
}
```

Regla de ocupación para Genesis v1: **una celda admite como máximo un
organismo vivo.** Esto da significado físico claro a movimiento, contacto,
bloqueo territorial y densidad sin introducir resolución de colisiones
múltiples. Un intento de `move` hacia una celda ya ocupada falla como
cualquier otro intent perdedor en la resolución simultánea de §5.

### Frontera del mapa

`hard/reflecting boundary`, no toroidal. Una topología toroidal es barata
computacionalmente pero introduce una física artificial (salir por el este
reaparece al oeste) que el organismo no tiene forma honesta de descubrir
como regularidad. Con frontera reflectante/impermeable, un intento de
`move` que cruzaría el borde falla — el coste de la acción puede seguir
aplicándose — y el organismo puede aprender la regularidad empíricamente,
sin recibir el concepto "pared" ni "borde".

## 8. Gates de falsación (W01–W07)

Preregistrados antes de ejecutar, con criterio explícito de qué cuenta como
resultado negativo — no solo de éxito. Dado el historial de este repo
(`genesis: controls ineffective` en runs previos de ecología emergente,
`unique_phenotypes = 1` en un protocolo sensorial, y un resultado negativo de
presión reversible con p=1.0 en el sondeo evolutivo más reciente), el default
es esperar convergencia trivial y exigir evidencia positiva, no al revés.

| Gate | Pregunta | Rechaza H0 si | H0 (default) |
|------|----------|----------------|---------------|
| W01 | ¿Un único Symbiont mejora su trayectoria fisiológica por encima de una política de acción aleatoria bajo el mismo mundo? | mejora significativa vs. control aleatorio, mismo seed, múltiples réplicas | sin mejora medible |
| W02 | ¿Dos Symbionts idénticos (mismo genoma, misma celda inicial) divergen en sensores/conceptos/conducta bajo distinta historia estocástica? | divergencia fenotípica medible entre réplicas | convergencia completa (repite el patrón `unique_phenotypes = 1` ya observado) |
| W03 | ¿8 fundadores sin mutación producen diferenciación ecológica (nichos) puramente ontogenética/social? | clustering de nicho estadísticamente distinto de ruido | sin diferenciación |
| W04 | ¿Activar mutación cambia el resultado de W03 más allá de lo explicable por plasticidad sola? | efecto atribuible a variación heredable, con control de plasticidad aislado | mutación no añade separación sobre W03 |
| W05 | ¿Activar cultura permite que conocimiento aprendido por un individuo persista y beneficie a descendientes que nunca vivieron el descubrimiento original? | beneficio medible en linaje tras desaparición del descubridor, controlado contra transmisión nula | sin persistencia útil |
| W06 | ¿El hazard dependiente de densidad poblacional produce retroalimentación organismo→mundo→selección detectable? | correlación causal (no solo temporal) entre densidad y presión selectiva resultante | sin retroalimentación detectable |
| W07 | ¿Aparece alguna innovación clasificable según la ontología de novelty congelada abajo, no enumerada por el diseñador antes del run? | evento cruza las cuatro condiciones de la ontología de novelty | ausencia de novedad que las cruce |

Cada gate corre con matriz de controles: `learning ON/OFF`, `sensor
plasticity ON/OFF`, `culture ON/OFF`, `mutation ON/OFF`, `communication
ON/OFF`, `spatiality ON/shuffled`, `resource scarcity ON/OFF`. Un resultado
solo se reporta como observación (`OBSERVED` / `NEEDS_REPLICATION`), nunca
como claim confirmado, sin un segundo preregistro independiente — mismo
protocolo que `longitudinal-population-ecology-v1.md`.

### Ontología de novelty para W07

"No enumerada por el diseñador" es demasiado laxo por sí solo — se presta a
interpretación retrospectiva. Antes de correr W07 se congela, sin
excepciones posteriores:

```
descriptor spaces     behavioral | ecological | cognitive | cultural
distance_threshold     mínima distancia al fenotipo/conducta más cercano
                        ya observado en el descriptor space correspondiente
persistence_threshold  ticks mínimos que el rasgo debe mantenerse activo
adaptive_value         mejora causal medible (no solo correlacional) en
                        trayectoria fisiológica o descendencia
minimum_replication    número mínimo de instancias independientes antes de
                        reportar, no un evento aislado
```

```
novelty =
    distance(nuevo, previamente_observado) > distance_threshold
    AND persistence ≥ persistence_threshold
    AND adaptive_value demostrado (no solo "parece interesante")
    AND replicación ≥ minimum_replication
```

Sin las cuatro condiciones no se reporta como novedad — se reporta, cuando
mucho, como `OBSERVED` sin clasificar. Esto es obligatorio si el proyecto
quiere hablar seriamente de open-endedness (MODES exige exactamente esta
disciplina, no juicio ad hoc post-hoc).

### Barrera formal entre programas

W01–W07 no se ejecutan como un único sweep. Cada programa es un gate: si el
anterior no rechaza su H0, no tiene sentido interpretar el siguiente —
adaptación funcional (W01) es condición previa para que ecología, evolución,
cultura u open-endedness signifiquen algo distinto de ruido:

```
WORLD v1            W01, W02
────────── GATE ──────────
WORLD Ecology v1    W03, W06
────────── GATE ──────────
WORLD Evolution v1  W04
────────── GATE ──────────
WORLD Culture v1    W05
────────── GATE ──────────
Open-endedness      W07
```

W07 no se ejecuta solo porque sea técnicamente posible; se ejecuta solo tras
cruzar las barreras anteriores.

## 9. World Constitution y epochs

### `WorldConstitution`

Equivalente, para el mundo, al fingerprint constitucional que ya identifica
al organismo. Un `world_seed` por sí solo no identifica un universo
reproducible entre implementaciones o versiones de código; el fingerprint sí:

```
WorldConstitution {
    constitution_schema_version   # versiona la serialización canónica en sí
                                   # misma, independiente de lifecycle/rng
    topology_schema
    world_dimensions
    field_laws_hash          # hash de world-ground-truth.toml, campos
    resource_laws_hash       # hash de world-ground-truth.toml, recursos
    hazard_laws_hash         # hash de world-ground-truth.toml, hazards
    interaction_rules_hash   # regla de resolución de intents simultáneos
    resolution_policy
    communication_physics
    lifecycle_contract_version
    rng_scheme_version
}

world_fingerprint = SHA256(canonical(WorldConstitution))
```

`constitution_schema_version` permite evolucionar la forma canónica en sí
misma (orden de campos, formato de hash) sin ambigüedad futura sobre si dos
fingerprints son comparables.

Una ejecución queda identificada, sin ambigüedad, por:

```
organism_constitutional_fingerprint + world_fingerprint + world_seed
+ founder_genomes
```

Dos organismos con el mismo `world_fingerprint` y `world_seed` vivieron el
mismo universo constitucional; esto es lo que hace comparables W02 (misma
celda, misma constitución, distinta historia estocástica) entre
implementaciones o revisiones de código.

### `WorldEpoch`

Un mundo puede vivir durante meses; `tick` como único identificador de
referencia deja de ser manejable en archivado y navegación. Un epoch es un
punto durable, evaluator-side, que **no reinicia el mundo**:

El registro durable de un epoch es identidad, no interpretación —
un evento semántico como "first reproduction" es una etiqueta humana que
Observatory muestra, nunca el identificador normativo del artefacto
científico:

```
world_id, epoch, start_tick, trigger_event_id
```

```
Genesis
 ├ epoch=0, start_tick=0,       trigger_event_id=null      (label: "foundation")
 ├ epoch=1, start_tick=184920,  trigger_event_id=<BIRTH #…> (label: "first reproduction")
 ├ epoch=2, start_tick=…,       trigger_event_id=<DEATH #…> (label: "first extinction")
 └ ...
```

Los criterios de qué constituye un nuevo epoch (primer nacimiento, primera
extinción, cambio de fase experimental) se declaran en la configuración de
`symbiont_lab`, no en `symbiont_world`: el kernel del mundo no sabe que
"epoch" existe, solo produce el `WorldEvent` que el orquestador usa para
marcarlo. La etiqueta humana ("first reproduction") vive junto al epoch en
metadata de apparatus, nunca reemplaza a `trigger_event_id` como referencia.

## 10. Alcance excluido de v1

3D, visión por píxeles, LLMs externos, física rígida, herramientas,
depredación/combate explícitos, evolución de las leyes físicas del mundo,
ecosistemas proceduralmente ilimitados, y cualquier fitness explícito o
quest. Fuera de alcance porque taparían la pregunta científica de v1, no
porque estén prohibidos para siempre.

## 11. Pregunta científica de v1

> ¿Puede un Symbiont situado en un entorno espacial persistente y no
> semantizado aprender regularidades ambientales y modificar autónomamente su
> percepción y comportamiento de forma que produzca mejores consecuencias
> fisiológicas, sin recibir objetivos, etiquetas ni señales de recompensa del
> evaluador?

W01–W02 la operacionalizan directamente; W03–W07 son las preguntas de
siguientes versiones (ecología de nichos, herencia sin fitness explícito,
persistencia cultural, innovación acumulativa) y no se abordan hasta que v1
tenga implementación y al menos un gate con resultado real, no solo el
contrato descrito aquí.

## 12. Incremento normativo W1 — movimiento y percepción local

W0 (implementado; ver `roadmap.md` / `ORGANISM.md` Parte XIII) entregó solo
el fundamento estructural: constitución, contratos, topología, RNG, eventos,
estado y checkpoint. Ningún organismo vive todavía dentro del mundo. Esta
sección congela el contrato normativo de W1 — el siguiente incremento, no
una revisión de los invariantes ya congelados en §1–§9.

### Alcance de W1

Exactamente dos capacidades sobre el kernel de W0, y nada más:

1. **Percepción local por organismo.** La fase 4 del tick (§5,
   `local observation surfaces per organism`) empieza a producir una
   `WorldObservation` real por organismo, poblada únicamente con `signals`
   derivados de la celda ocupada (`WorldBody.occupied_cell`, §7) y su
   vecindad inmediata (`interaction_radius`). Sin `fields` ni `resources`
   todavía: W1 puede sintetizar señales de marcador de posición (p. ej. una
   única señal opaca "ocupación local") solo para ejercer el pipeline
   `ObservableSource → WorldObservation` de punta a punta. Las leyes reales
   de campos/recursos siguen diferidas a W2 (Genesis ground truth, §7).
2. **Resolución de movimiento.** La fase 8 del tick
   (`resolve movement`) consume `WorldAction.move` de cada organismo,
   invoca `HexTopology.resolve_move` (ya implementado en W0) y
   `OccupancyGrid.move`/`occupy` (ya implementado en W0) para actualizar
   `WorldBody.occupied_cell`. La resolución de intents simultáneos sobre la
   misma celda destino sigue la regla de §5 (determinista, RNG namespaced,
   nunca dependiente de orden de iteración).

Explícitamente fuera de W1: cualquier `field`/`resource`/`hazard` real,
`acquire`/`sample` con efecto fisiológico, comunicación (`emit`/`reception`),
contacto (`ContactEvidence`) más allá de la ocupación bruta, y cualquier de
los gates W01–W07 (requieren, como mínimo, W2).

### Ownership sin cambios

W1 no modifica la tabla de ownership de §5: `symbiont_world.WorldKernel`
sigue produciendo `WorldObservation` y consumiendo `WorldAction` sin conocer
`symbiont`; `symbiont_lab` sigue siendo el único orquestador que invoca
sensor sampling, cognición y decisión del organismo entre ambas fases.

### Gates técnicos de W1 (implementación, no falsación científica)

Igual que W0 tuvo gates técnicos (package boundary, atomicidad, etc., ver
`ORGANISM.md` Parte XIII), W1 se acepta solo si demuestra:

```
observation pipeline end-to-end   # WorldBody → signals → WorldObservation,
                                    # sin fields/resources reales todavía
movement resolution correctness    # HexTopology + OccupancyGrid ya
                                    # correctos en W0, ahora conectados a
                                    # WorldAction.move por tick
simultaneous move determinism      # dos organismos intentando la misma
                                    # celda destino: resultado reproducible
                                    # byte a byte para mismo seed
tick atomicity preserved            # una resolución de movimiento
                                    # inconsistente sigue abortando el tick
                                    # completo (§3, inv. 7), no solo el
                                    # movimiento del organismo afectado
no ground-truth leakage in signals  # el marcador de posición sintético de
                                    # W1 es tan opaco como cualquier field
                                    # real de W2 (SignalId, no nombre)
```

Ningún gate de falsación (W01–W07, §8) corre en W1: siguen requiriendo al
menos un `field`/`resource` real (W2) para que "mejorar la trayectoria
fisiológica" (W01) tenga contenido que medir.

## 13. Incremento normativo W2 — leyes de Genesis (fields y resources)

W1 (implementado) solo ejercitó el pipeline con una señal sintética de
ocupación. W2 introduce las primeras leyes reales de Genesis (§7), todavía
sin tocar hazards, fisiología ni `symbiont_lab`.

### Por qué el kernel puede conocer las leyes sin romper §2

`symbiont_world` sigue sin importar nada. La resolución al aparente conflicto
entre "el kernel ejecuta `field propagation`" (fase 2 del tick, ownership
`symbiont_world.WorldKernel`, §5) y "el significado real vive en metadata de
apparatus dentro de `symbiont_lab`" (§3 inv. 1, §7) es esta separación:

```
FieldLaw / ResourceLaw    →  parámetros numéricos genéricos, sin nombre de
                              dominio (amplitud, sesgo, frecuencia angular,
                              fase; capacidad, tasa de renovación, tasa de
                              decaimiento) — vive en symbiont_world.laws,
                              parte del kernel puro
GroundTruth                →  mapa FieldId/ResourceId opaco -> Law,
                              construido e inyectado por symbiont_lab desde
                              world-ground-truth.toml; symbiont_world nunca
                              lee TOML ni conoce la ruta del archivo
etiqueta semántica          →  ("esto modela humedad") vive únicamente en
("esto modela humedad")        metadata de apparatus separada dentro de
                              symbiont_lab, nunca llega ni siquiera a
                              GroundTruth
```

El kernel calcula dinámicas reales con parámetros reales; solo el nombre de
dominio permanece fuera de su alcance. Esto preserva §3 inv. 1: incluso si
alguien inspeccionase el estado interno del kernel, no encontraría
`"humidity"` — encontraría `field.<hash>` con una `PeriodicFieldLaw`
genérica.

### Alcance de W2

1. **Fields.** `PeriodicFieldLaw(amplitude, bias, angular_frequency, phase)`
   evaluada en `value_at(tick)`, espacialmente uniforme (sin gradiente
   todavía — un gradiente espacial real queda diferido a un incremento
   posterior). La fase 2 del tick (`field propagation`) recalcula el valor
   de cada field una vez por tick.
2. **Resources.** `ResourceLaw(capacity, renewal_rate, decay_rate,
   initial_quantity)` por celda: cada celda con un pool de recurso propio,
   inicializado perezosamente. La fase 3 del tick (`resource
   renewal/decay`) mueve cada pool hacia `capacity` a `renewal_rate` y le
   resta `decay_rate`, sin negativos.
3. **Adquisición.** La fase 9 (`resolve resource competition`) resuelve
   `WorldAction.acquire` sobre el pool de la celda ocupada por cada
   organismo. Múltiples organismos en conflicto por el mismo recurso en la
   misma celda no son posibles todavía porque Genesis v1 ya impone una
   ocupación por celda (§7); el conflicto simultáneo real de adquisición
   solo aparece si se permite co-ocupación en una versión futura. Por eso
   W2 implementa adquisición como agotamiento simple del pool local,
   dejando la maquinaria de resolución proporcional/lotería (§5) lista pero
   sin caso de prueba forzado hasta que exista co-ocupación o adquisición a
   distancia.
4. **Percepción real.** `WorldObservation.signals` de W1 (solo densidad de
   ocupación) se extiende con un `SignalId` opaco por field activo y por
   recurso presente en la celda local, calculado desde `GroundTruth` +
   estado de entorno, nunca desde nombres de dominio.

Explícitamente fuera de W2: hazards (quedan para un incremento posterior,
igual que el acoplamiento por densidad poblacional de W06 §8), cualquier
efecto fisiológico real (`MetabolicLedger` sigue sin existir en este lado de
la frontera — eso es trabajo de `symbiont_lab`), gradientes espaciales de
field, y comunicación. Los gates de falsación W01–W02 siguen sin poder
correr: requieren un organismo real, que sigue sin existir hasta que
`symbiont_lab` construya el adaptador (§2).

### Gates técnicos de W2

```
field value determinism        # mismo seed/tick -> mismo valor de field,
                                # sin depender de orden de evaluación
resource renewal/decay bounds  # el pool nunca excede capacity ni baja de 0
resource acquisition depletes  # adquirir resta del pool local; adquirir
  pool without going negative    más de lo disponible nunca deja el pool
                                  negativo
lazy per-cell initialization   # una celda no visitada no consume memoria
  is deterministic               antes de su primer acceso, y su valor
                                  inicial es siempre initial_quantity
no domain semantics in state   # GroundTruth y WorldEnvironment solo
                                  contienen FieldId/ResourceId opacos y
                                  parámetros numéricos, nunca un nombre de
                                  dominio
signals extend, don't replace  # la señal de ocupación de W1 se sigue
  W1's occupancy signal          produciendo sin cambios
```

## 14. Incremento normativo W2.1 — hazards acoplados a densidad

W2 diefirió hazards explícitamente. Este incremento los cierra, completando
por fin el conteo de Genesis v1 (§7: 4 fields, 4 resources, 2 hazards) del
lado del kernel.

### Alcance

`HazardLaw(base_probability, density_coupling)` es sin estado propio: a
diferencia de un recurso, un hazard no tiene pool que agotar — es una
función de exposición evaluada sobre la densidad local ya calculada por
`local_observation` (§12.1) para la señal de ocupación de W1:

```
exposure(local_density) = clamp(
    base_probability * (1 + density_coupling * local_density), 0, 1
)
```

Esto es exactamente el acoplamiento organismo→mundo→selección que W06 (§8)
necesita medir más adelante: más densidad local produce más exposición,
sin que el kernel llame a esto "contaminación" ni ningún otro nombre de
dominio. La exposición se expone como un `SignalId` opaco más en
`WorldObservation.signals`; no aplica ningún efecto fisiológico — eso
requiere el adaptador `symbiont_lab` (§2) y queda fuera de este incremento,
igual que la adquisición de recursos quedó fuera del efecto sobre
`MetabolicLedger` en W2.

### Gates técnicos

```
exposure is bounded in [0, 1]        # para cualquier density y parámetros
                                        válidos de la ley
exposure increases monotonically      # a mayor densidad local, mayor o
  with local density                    igual exposición, nunca menor
zero density yields base_probability  # sin vecinos ocupados, la exposición
                                        es exactamente base_probability
hazard has no persistent pool         # a diferencia de un recurso, dos
                                        llamadas consecutivas con la misma
                                        densidad producen el mismo resultado
                                        sin efectos de acumulación
no domain semantics in hazard state   # HazardLaw y GroundTruth.hazards
                                        solo contienen HazardId opaco y
                                        parámetros numéricos
```

## 15. Incremento normativo W3 — adaptador `symbiont_lab` y alcance real de v1

Este incremento conecta el kernel (W0–W2.1) a un `ModeledOrganismRuntime`
real. Es el más grande hasta ahora porque decide cómo cruzar §2 sin tocar
`symbiont` — el organismo está congelado en `1.0.0`
(`docs/roadmap.md`: "CAPABILITY DEVELOPMENT: FROZEN BY DEFAULT") y añadirle
un `ActionKind` nuevo (mover, muestrear-mundo) sería exactamente el tipo de
nueva capacidad que el freeze prohíbe sin una puerta de revisión explícita
del owner. Este incremento no abre esa puerta: la resuelve reutilizando
superficies ya existentes sin modificarlas.

### Descubrimiento: v1 no necesita movimiento ni founders múltiples

Releyendo el gate table de §8, **W01 y W02 — los únicos gates que
operacionalizan la pregunta científica de v1 (§11) — no requieren
movimiento ni ocupación múltiple**:

- W01 usa un único Symbiont estacionario; la pregunta es si mejora su
  trayectoria fisiológica frente a una política aleatoria, no si se
  desplaza.
- W02 usa réplicas independientes que parten de la misma celda; la
  divergencia que mide es de historia estocástica interna, no espacial.

Movimiento (W1) y colocación de founders múltiples (§7) siguen siendo
correctos y ya implementados en el kernel, pero **quedan fuera del alcance
de v1**: pertenecen a W03+ (ecología con 8 founders, §8). Esto reduce el
adaptador a algo mucho más tratable: un organismo, una celda, sin
comunicación ni reproducción.

### Cómo cruza la frontera sin tocar `symbiont`

Tres superficies ya existentes en `symbiont`, sin modificar ninguna:

1. **Percepción.** `DiscoveryProvider`/`ReadingProvider`
   (`symbiont/host/contracts.py`, `symbiont/host/readings.py`) son
   protocolos de inyección por constructor, ya diseñados para que
   plataformas externas aporten `Capability`/`SensorReading` sin que
   cognición conozca su origen. El adaptador implementa ambos para
   exponer los `SignalId` opacos de `WorldObservation` como si fueran
   sensores de host — misma opacidad, misma frontera, distinto origen
   físico.
2. **Adquisición de recursos.** `OrganismRuntime` ya acepta
   `resource_habitats: dict[str, SharedHabitat]` (`symbiont/core/runtime.py`)
   y genera una oportunidad `INTAKE` por cada una, decidida por la propia
   cognición vía `autonomous_action_step()` — no por el orquestador. El
   adaptador sincroniza el `_resources` de un `SharedHabitat` por recurso
   con el pool real de `WorldEnvironment` en cada tick
   (`SharedHabitat.set_environment_resources`, ya pública) y, tras la
   decisión del organismo, debita el pool real de `WorldEnvironment` por
   la cantidad efectivamente consumida (`WorldEnvironment.acquire`). La
   decisión de adquirir sigue siendo enteramente del organismo.
3. **Exposición a hazard.** `OrganismRuntime.apply_environmental_damage(amount)`
   (`symbiont/core/runtime.py`) ya existe exactamente para esto: "a bounded
   physical perturbation from the supplied habitat", `amount` acotado en
   `(0, 0.25]`. El adaptador tira una moneda RNG-namespaced por hazard y
   tick usando `hazard_exposures()` como probabilidad; si acierta, aplica
   un quantum fijo de daño. No hay imposición de objetivo ni fitness — es
   la misma consecuencia física que ya existía para el host real,
   reutilizada para el mundo.

`symbiont` no gana ningún método, tipo ni parámetro nuevo. El adaptador
vive enteramente en `symbiont_lab.world.adapter`.

### Alcance de W3

Un único organismo, estacionario, sin comunicación ni reproducción:

```
SingleOrganismGenesisRuntime(
    organism_id, world_seed, ground_truth, topology, start_cell
)
```

Cada tick: propaga fields, renueva recursos de la celda ocupada, sincroniza
los `SharedHabitat` desde `WorldEnvironment`, construye la
`WorldObservation` local, se la entrega al organismo vía los providers,
llama `runtime.tick()` y `runtime.autonomous_action_step()`, liquida la
adquisición real contra `WorldEnvironment`, y resuelve exposición a hazard.

Explícitamente fuera de W3: movimiento real (el organismo nunca emite
`WorldAction.move`), founders múltiples, comunicación, reproducción,
colocación determinista de founders (§7 — no aplica con un solo
organismo), y cualquier mapeo del "beneficio inmediato con daño diferido"
de un recurso (`ResourceLaw` sigue sin modelar ese efecto retardado; el
daño de hazard es la única vía de daño fisiológico real en v1).

### Gates técnicos de W3

```
provider protocols unmodified          # DiscoveryProvider/ReadingProvider
                                          se implementan, nunca se editan
no new ActionKind                      # grep de symbiont/core/behavior.py
                                          no cambia
resource sync round-trips              # lo que el hábitat consume se
                                          debita del pool real de
                                          WorldEnvironment, sin duplicar ni
                                          perder cantidad
hazard damage stays within contract    # todo apply_environmental_damage
                                          cae en (0, 0.25], nunca fuera
organism death stops the run cleanly   # un organismo muerto no produce
                                          ticks mundiales fantasma
full tick sequence runs without        # smoke: N ticks sin excepción no
  raising for a live organism            modelada, con un organismo real
```

### Lo que sigue siendo v1, no v2

Con W3, W01 y W02 (§8) pueden por fin preregistrarse y ejecutarse contra
datos reales. Su resultado — sea cual sea, incluida convergencia trivial
como H0 — es lo que cierra v1, no la existencia del adaptador por sí sola.
