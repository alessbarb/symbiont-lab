# Symbiont World v2

> **Implementado y cerrado**, salvo §7 (gate de capacidad de movimiento:
> puerta abierta, diseño concreto no aprobado — permanece sin código a
> propósito). §3–§6 y §8 están implementados, testeados y W03 se ejecutó
> contra datos reales: **rechaza H0** (ver
> `experiments/world/genesis-v1/audit-w03.md`). El estado real de
> implementación se verifica en `docs/roadmap.md` / `ORGANISM.md`, igual
> que v1.

## 1. Pregunta científica

> ¿8 founders sin mutación producen diferenciación ecológica (nichos)
> puramente ontogenética/social? (W03, v1 §8)

W03 es el siguiente gate tras W01/W02 (ambos H0). La barrera formal de v1
§8 sigue vigente: W03 solo significa algo porque W01/W02 se ejecutaron de
verdad, no porque se asuma adaptación no demostrada.

## 2. Qué hereda de v1 sin cambios

Paquetes (§2 de v1): `symbiont_world` sigue sin importar nada;
`symbiont_lab` sigue siendo el único adaptador; `symbiont` sigue sin ganar
ningún método o tipo nuevo **excepto** lo descrito en §7 (gate de
capacidad, aprobado explícitamente por el owner, no ambient). Los
invariantes epistemológicos de v1 §3 (no ground truth al organismo,
determinismo estricto, sin canal Observatory→World, sin fitness impuesto,
sin broadcast global, no duplicar fisiología, atomicidad de tick) se
heredan sin modificación y se extienden en §4.

Todos los contratos de v1 (`WorldObservation`/`WorldAction`,
`WorldConstitution`, `WorldEvent`, `WorldState`/`TickTransaction`,
`HexTopology`/`OccupancyGrid`/`WorldBody`, `PeriodicFieldLaw`/
`ResourceLaw`/`HazardLaw`, `SingleOrganismGenesisRuntime`) siguen siendo
válidos tal cual. v2 los extiende de forma **aditiva** — ningún test de v1
puede dejar de pasar por un cambio de v2 (gate V02-08, §8).

## 3. Heterogeneidad regional de `GroundTruth` (el hallazgo más importante de v1)

`WorldEnvironment` aplica hoy la **misma** `ResourceLaw`/`HazardLaw` a
toda celda; solo el valor del pool por celda varía, nunca la ley. Sin
variación regional no puede emerger ningún nicho — toda celda es
funcionalmente idéntica. Esto se corrige de forma no disruptiva:

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

`region_of`/`regional_resources`/`regional_hazards` son opcionales con
default `None`/`{}`: un `GroundTruth` de v1 sin estos campos se comporta
exactamente igual que en v1 (fallback total a la ley base). Esto es lo que
hace el cambio aditivo, no disruptivo — ningún test de W0–W3 debe requerir
modificación.

`WorldEnvironment.resource_pool(cell)`/`renew_resources(cell)`/
`acquire(...)` cambian su resolución de ley internamente:

```
law_for(cell, resource_id):
    region = ground_truth.region_of(cell) if ground_truth.region_of else None
    regional = ground_truth.regional_resources.get(region, {})
    return regional.get(resource_id, ground_truth.resources[resource_id])
```

Misma disciplina de opacidad que v1 §3 inv. 1: `RegionId` es un hash
opaco: la semántica real de una región ("norte, campo alto, recurso
escaso") vive únicamente en metadata de apparatus dentro de
`symbiont_lab`, igual que `GENESIS_V1_METADATA` para fields/resources/
hazards — nunca en `symbiont_world`.

Fields permanecen globales (ciclos temporales uniformes) en v2; un
gradiente espacial de field queda fuera de alcance, igual que en v1 §13.

## 4. Multi-organismo: founders y ocupación a escala

### Colocación determinista de founders

Función pura, evaluator-side (`symbiont_lab.world`), nunca dentro de
`symbiont_world`:

```
founder_placement(world_seed: int, topology: HexTopology, count: int) -> tuple[HexCoord, ...]
```

Determinista para `(world_seed, topology, count)`; produce `count` celdas
distintas dentro de los límites de `topology`, usando
`derive_world_rng(world_seed, "genesis.founder-placement")` (mismo esquema
de derivación que el resto del kernel, §2 de v1) para elegir sin colisión.
No garantiza dispersión mínima entre founders en v2 — eso es un refinamiento
de v3 si resulta necesario tras observar W03.

### Ocupación a 8 organismos (sin contención de recurso todavía)

`OccupancyGrid` nunca se ejercitó con más de un ocupante — W3 solo tuvo un
organismo estacionario. v2 sí prueba eso: 8 founders ocupando 8 celdas
distintas simultáneamente, con `state.occupancy.occupy()` fallando
correctamente ante colisión (V02-02).

**Corrección honesta sobre contención de recursos**, encontrada al
implementar: los pools de recurso son por-celda
(`dict[HexCoord, dict[ResourceId, float]]`, §3 de v1), no por-región. La
heterogeneidad regional (§3) solo hace que dos celdas de la misma región
compartan la misma *ley* — cada una sigue teniendo su propio pool
independiente. Por tanto **no existe contención real de recursos entre
founders en v2**: cada uno tiene su propio pool en su propia celda, ley
compartida o no. Un pool verdaderamente compartido por región (o
adquisición a distancia) queda fuera de v2 — es un candidato de v3, no
una deuda de v2.

La resolución de intents simultáneos (`resolve_movement`, v1 §5) sigue
sin ejercitarse con más de un organismo en v2: sin movimiento aprobado
(§7), ningún organismo intenta ocupar la celda de otro. El gate V02-04
(§10) queda marcado como no aplicable en v2 por esta razón, no omitido
por descuido.

### `SingleOrganismGenesisRuntime` → runtime multi-organismo

Se extiende (no se reemplaza) el adaptador de W3 hacia un runtime que
sostiene 8 instancias de `ModeledOrganismRuntime`, cada una con su propio
`WorldReadingProvider`/`resource_habitats`, todas compartiendo el mismo
`WorldState`/`WorldEnvironment`. El orden de tick por organismo sigue la
misma regla de v1 §5 (nunca depende de orden de iteración de diccionario;
orden determinista por `organism_id` ordenado).

## 5. Retry de W02 con mecanismo real de divergencia

El audit de v1 encontró que `organism_seed` solo no tiene camino causal
hacia la conducta de un organismo solitario con `exploration=0.0`, sin
plasticidad, sin reproducción. v2 reintenta W02 activando
`sensory_plasticity=True`/`discover_senses=True` en el adaptador — ambos
ya existen en `symbiont`, sin cambio de core. El protocolo:

```
replica_a, replica_b: mismo world_seed, mismo GroundTruth, misma celda,
distinto organism_seed, sensory_plasticity=True, discover_senses=True

métrica: distancia entre los conjuntos de sensores activos/seleccionados
         de cada réplica tras N ticks (ya expuesto por
         AdaptiveSenseModel/SensorySystem existente), más el
         composite_score de v1 (mean reserve + integrity)
```

Igual disciplina que v1: el resultado (diverge o no) se reporta tal cual
sale, sin convertir convergencia en fracaso ni divergencia en éxito
prematuro. Si tampoco diverge con plasticidad activa, eso también se
documenta honestamente — sería otro hallazgo metodológico real, no un
fallo a esconder.

## 6. Daño diferido ("beneficio inmediato, daño diferido")

v1 §7 exigía al menos un recurso con este perfil; `ResourceLaw` sigue sin
modelarlo (solo gobierna el pool, no el efecto). Se implementa
enteramente en `symbiont_lab` (adaptador), sin nueva API en
`symbiont_world` ni `symbiont`:

```
DeferredEffect {
    organism_id: str
    due_tick: int
    amount: float   # en (0, 0.25], mismo contrato que
                     # apply_environmental_damage
}
```

Al adquirir del recurso marcado como "deferred" (metadata de apparatus,
no del kernel), el adaptador encola un `DeferredEffect` con
`due_tick = current_tick + delay` (delay fijo por recurso, definido en
`world-ground-truth.toml`-equivalente de `symbiont_lab.world`). En cada
tick, antes de resolver la acción del organismo, el adaptador aplica
cualquier `DeferredEffect` cuyo `due_tick` ya se cumplió, vía la misma
`apply_environmental_damage` que ya usa para hazards. La cola está acotada
(tamaño máximo fijo, ej. 32 entradas) — un organismo no puede acumular
deuda de daño ilimitada.

## 7. Gate de capacidad: movimiento espacial

**Estado: puerta abierta, diseño concreto aún sin aprobar.**

v1 evitó esto descubriendo que W01/W02 no lo necesitan. W03 tampoco lo
necesita estrictamente (8 founders estacionarios ya pueden mostrar
diferenciación ecológica solo por heterogeneidad regional, §3). El default
de v2 sigue siendo **sin movimiento**, salvo que el diseño concreto de
abajo se apruebe por separado.

Decisión ya registrada (tomada durante el scoping de v2, con el owner):

- Rechazado: no tener movimiento indefinidamente — se quiere, no solo se
  tolera.
- Rechazado: mapear movimiento sobre la ejecución de `INVESTIGATE` — se
  consideró epistemológicamente arriesgado (cambiaría en silencio el
  significado de una acción ya auditada).
- Aceptado: un `ActionKind` nuevo (`MOVE`, tentativo) en
  `symbiont/core/behavior.py`, siguiendo el mismo patrón auditado que
  `INTAKE`/`REPAIR` — un cambio de capacidad real al organismo congelado,
  por lo que el contrato de freeze de `roadmap.md` exige que sea una
  puerta de revisión explícita y separada, no parte ambiental de v2.

Pendiente de decisión (necesita su propio pase de diseño antes de
implementar una sola línea):

1. Qué `ActionOpportunity`/`ExpectedOutcome` expone una oportunidad `MOVE`
   (coste, dimensiones de viabilidad/integridad/información) — determina
   si la cognición puede llegar a elegirla racionalmente frente a
   `INTAKE`/`REST`, relevante dado que W01 encontró que el modelo de
   acción actual ya falla en conectar consecuencias reales (daño de
   hazard) con la selección de oportunidad.
2. Si `MOVE` toma una dirección opaca (coincide exactamente con el
   `ActuatorId` que ya usa `WorldAction.move`, sin plomería nueva del lado
   de World — `HexTopology.resolve_move`/`OccupancyGrid.move` de W1 ya
   implementan la física) o un concepto de celda destino.
3. Impacto en checkpoint/replay: un `ActionKind` nuevo entra en
   `ActionExecutionResult`/historial de estado de comportamiento — exige
   la misma disciplina de replay que el resto del core congelado.

Esta sección es el artefacto que satisface la instrucción de CLAUDE.md de
"stop for an explicit owner decision before adding a new permission
class... or any new real-world action boundary": la decisión de abrir la
puerta queda registrada; el diseño concreto de `ActionKind` todavía
necesita su propia revisión antes de tocar una sola línea de
`symbiont`.

## 8. Observatory: capa de visualización para el operador humano

v1 no tenía nada que mirar — `WorldTickRecord`/`WorldEvent` solo existían
como estructuras que un script imprimía. Con 8 founders y heterogeneidad
regional, hace falta una vista pasiva, misma regla arquitectónica que
cualquier otra superficie de Observatory (CLAUDE.md: "the display does not
control cognition"; v1 §29: `Observatory → World` no existe, ni
deshabilitado).

**Dentro de alcance:**

- Render hexagonal de celdas ocupadas (`OccupancyGrid.snapshot()`),
  posiciones de founders, tick/epoch actual.
- Valores de field/resource/hazard por celda, etiquetados con su nombre
  semántico real desde `GENESIS_V1_METADATA` — Observatory es
  evaluator-side y ya tiene permitido conocer el significado (el
  invariante de opacidad de v1 §7 solo ata lo que llega al *organismo*,
  nunca lo que puede ver un operador humano). Esto es exactamente para lo
  que se construyó `GENESIS_V1_METADATA` en v1 y ha estado sin usar desde
  entonces.
- Feed de eventos desde `EventJournal.replay()`: nacimientos/muertes/
  adquisiciones/hazard hits, mostrando `causal_parent_ids` vs
  `contributing_event_ids` visualmente distintos (v1 §6 — que la UI no
  implique más certeza de la que tiene el kernel).
- Solo lectura. Ninguna superficie de control, ningún botón que llame
  `WorldAction` o avance un tick por su cuenta. Si se quiere un control de
  "avanzar un tick", solo puede llamar el mismo `run_tick()` que llamaría
  un script — nunca influir en *qué* decide el organismo.

**Fuera de alcance de v2**, diferido a un pase de diseño de Observatory
dedicado: actualizaciones en vivo/streaming durante una corrida larga,
scrubbing de replay, el Observatory de seis escalas (World/Region/
Population/Lineage/Individual/Mind) del documento de rationale §27 — v2
solo tiene 8 organismos estacionarios en potencialmente varias regiones;
la mayoría de esas escalas todavía no existen como datos que mostrar.

### Decisión de modo: CLI (grid ASCII en terminal)

> Nota histórica: esta fue la decisión correcta para v2. Desde septiembre de
> 2026, World ya no posee UI propia: la vista científica vive en Observatory y
> existe además un cliente Pygame opcional, pasivo y fuera de proceso, que consume
> exclusivamente el endpoint local de solo lectura `/world/state`. La decisión
> siguiente se conserva como rationale histórico de v2.

Tres modos considerados: CLI, web (integrado al Observatory JS existente
en `observatory/`), pygame. Se elige **CLI** para v2:

- Cero dependencias nuevas — el resto del kernel/adaptador tampoco las
  tiene (`pyproject.toml` solo depende de `cryptography`+`torch` opcional).
- Corre headless, igual que el resto de la suite de tests — se puede
  invocar desde script o pytest sin infraestructura extra.
- El Observatory web existente (`observatory/render/*.js`) es un sistema
  propio con su propio contrato (fenotipo, cognición) — integrar World ahí
  es un trabajo de diseño de Observatory separado (explícitamente diferido
  arriba), no algo a improvisar dentro de v2.
- pygame añade una dependencia gráfica no usada en ningún otro punto del
  repo, sin beneficio claro sobre ASCII para 8 organismos en un grid
  pequeño.

Contrato: `symbiont_lab.world.cli_view.render_world(state, environment,
ground_truth, metadata) -> str` — función pura, devuelve texto, nunca
imprime ni lee stdin directamente (así es testeable sin capturar stdout).
Un `if __name__ == "__main__"` delgado en un script separado la imprime.
No expone ningún control — no hay comando "step" ni "act" en la CLI que
toque `WorldAction`; solo lee.

### Extensión: servidor persistente

El operador esperaba conectarse a un mundo que corre solo, no lanzar un
script que corre N ticks y termina. Se extiende §8 con un servidor real,
mismo invariante de solo-lectura:

`symbiont_lab.world.dashboard_state.WorldDashboardState` corre el mundo en
un hilo daemon en background, indefinidamente, desde el momento en que se
llama `.start()` — independiente de si hay algún viewer conectado o no
(mismo principio que ya rige Observatory: el mundo no depende de quién lo
mira). `symbiont_lab.world.dashboard_server` expone esto vía
`http.server.ThreadingHTTPServer` (stdlib, mismo patrón que
`symbiont_lab.dashboard` ya usa para el organismo, sin dependencias
nuevas): `GET /` sirve una página que hace polling de `GET /api/state`
cada segundo y pisa un `<pre>` con la salida de `render_world()`.

**El handler HTTP no define ningún verbo POST/PUT/DELETE/PATCH** — un
test lo verifica explícitamente. No hay manera de que un cliente remoto
llame `WorldAction` ni de otro modo dirija el tick; la única forma de
"controlar" el mundo es lanzar o matar el proceso del servidor.

Lanzamiento: `symbiont-world-dashboard --port 8766 --tick-delay 0.5`
(entry point en `pyproject.toml`). `--seed`/`--founders`/`--width`/
`--height` configuran el mundo; `--tick-delay` es el único parámetro que
controla cadencia, nunca contenido.

## 9. Explícitamente fuera de v2

Cultura, comunicación, reproducción (W04/W05 — llegan después de que W03
tenga resultado, según la barrera formal de v1 §8). Movimiento real queda
fuera salvo aprobación separada del diseño concreto de §7.

## 10. Gates técnicos (V02, no falsación científica)

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

W03 (el gate de falsación real) se preregistra solo después de que estos
gates técnicos pasen, misma disciplina que v1.

## 11. Pregunta científica de v2 (para preregistro posterior)

> Con 8 founders idénticos, sin mutación, colocados deterministamente en
> un mundo con heterogeneidad regional de recursos/hazards: ¿emerge
> diferenciación ecológica medible (especialización por región, patrones
> de adquisición distintos) atribuible únicamente a desarrollo
> ontogenético/social, sin ninguna variación genética entre founders?

Esto opera W03 directamente. No se aborda ninguna pregunta de W04+
(cultura, evolución) hasta que W03 tenga un resultado real, igual que v1
no abordó W03+ hasta cerrar W01/W02.
