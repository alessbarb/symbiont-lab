# Symbiont World — Persistent World & Scientific Observatory

**Estado:** diseño propuesto sobre la implementación actual.
**Ámbito:** `symbiont_world` + `symbiont_lab.world` + World Observatory.
**Principio rector:** el mundo debe poder existir, evolucionar, sobrevivir a reinicios y ser observado exhaustivamente sin que la observación modifique su causalidad.

---

# 1. Objetivo

La siguiente etapa de Symbiont World no consiste en añadir más mecánicas.

El objetivo es convertir el prototipo actual en un **mundo digital íntegro, durable, reconstruible y científicamente observable**.

Debe ser posible:

```text
crear Genesis
     ↓
introducir Symbionts
     ↓
ejecutar millones de ticks
     ↓
cerrar el proceso
     ↓
reiniciar máquina/proceso
     ↓
recuperar exactamente el mismo mundo
     ↓
seguir desde el siguiente tick
```

Mientras tanto, un humano debe poder observar:

```text
World Reality
    ↓
ecología
    ↓
organismos
    ↓
fisiología
    ↓
percepción
    ↓
cognición
    ↓
historia causal
```

sin disponer de ningún mecanismo capaz de modificar el experimento.

El resultado buscado es un **terrario científico digital permanente**.

---

# 2. Estado de partida

La implementación actual ya contiene una cantidad importante de infraestructura válida:

```text
symbiont_world
├── WorldConstitution
├── WorldObservation / WorldAction
├── HexTopology
├── OccupancyGrid
├── WorldBody
├── WorldState
├── TickTransaction
├── WorldEvent / EventJournal
├── fields
├── resources
├── hazards
├── regional GroundTruth
└── deterministic RNG

symbiont_lab.world
├── Genesis presets
├── SingleOrganismGenesisRuntime
├── PopulationGenesisRuntime
├── deferred damage
├── founder placement
├── W01/W02/W03 experiments
├── dashboard server
├── read-only API
└── SVG world view
```

También existe un servidor que ejecuta continuamente el mundo independientemente del navegador.

El problema ya no es “hacer que exista el mundo”.

El problema es garantizar que:

```text
lo que ocurre
=
lo que se guarda
=
lo que se reproduce
=
lo que Observatory representa
```

---

# 3. Principios constitucionales

Toda implementación posterior debe preservar cinco separaciones.

```text
WORLD
realidad causal

ORGANISM
experiencia y acción

LAB
orquestación experimental

JOURNAL
historia confirmada

OBSERVATORY
proyección pasiva
```

Las dependencias siguen siendo:

```text
symbiont_world
      ↑
symbiont_lab
      ↓
   symbiont
```

Nunca:

```text
symbiont → symbiont_world
```

y nunca:

```text
Observatory → World
```

Observatory puede conocer ground truth.

El organismo no.

---

# 4. Prioridad máxima: atomicidad real del tick

La atomicidad actual es incompleta.

`TickTransaction` protege principalmente:

```text
WorldState
├── occupancy
└── bodies
```

pero durante un tick pueden modificarse también:

```text
WorldEnvironment
resource pools
field state

SharedHabitat
resource allocations

ModeledOrganismRuntime
cognition
memory
physiology
homeostasis
metabolism

DeferredEffectQueue

pending journal events
```

Por tanto necesitamos sustituir el concepto actual por una transacción integrada.

## 4.1 IntegratedWorldTickTransaction

Conceptualmente:

```text
BEGIN TICK N
    │
    ├── snapshot WorldState
    ├── snapshot WorldEnvironment
    ├── snapshot every organism
    ├── snapshot SharedHabitat surfaces
    ├── snapshot deferred effects
    ├── stage events
    │
    ▼
execute tick
    │
    ├── success ──────────────► COMMIT
    │
    └── failure ──────────────► ROLLBACK
```

COMMIT significa:

```text
world state accepted
organism states accepted
resource states accepted
deferred queue accepted
events appended
tick += 1
```

ROLLBACK significa:

```text
no tick advance
no resource consumption
no physiology change
no cognition change
no damage
no deferred-effect removal
no journal event
```

La propiedad que debe probarse es:

```text
failed_tick(state_n) == state_n
```

byte-equivalent donde el contrato permita equivalencia binaria, o semantic-equivalent donde existan timestamps externos no causales.

---

# 5. Commit ordering

El modelo de tick debería evolucionar a cuatro grandes fases.

```text
WORLD PHASE
1 scheduled environment processes
2 field propagation
3 resource regeneration/decay
4 observation surfaces

ORGANISM PHASE
5 sensing
6 cognition
7 action intent generation

RESOLUTION PHASE
8 resolve simultaneous movement/intents
9 resolve resource acquisition
10 resolve contact
11 resolve communication
12 apply physiological consequences
13 lifecycle transitions
14 culture/social delivery

COMMIT PHASE
15 construct committed WorldEvents
16 journal append
17 advance tick
18 durable checkpoint when required
```

Nada debería llegar al journal antes de saberse que el tick completo va a confirmarse.

---

# 6. Persistencia completa del universo

El `WorldCheckpoint` actual es insuficiente para un mundo perenne.

Necesitamos un nuevo artefacto:

```text
PersistentWorldCheckpoint
```

que represente un universo completo recuperable.

## 6.1 Contenido

Conceptualmente:

```text
PersistentWorldCheckpoint
├── schema_version
├── world_id
├── world_fingerprint
├── world_seed
├── epoch
├── tick
│
├── topology
├── occupancy
├── WorldBody[]
│
├── environment
│   ├── field values
│   ├── resource pools
│   └── environmental state
│
├── organisms
│   ├── organism_id
│   ├── organism checkpoint
│   ├── resource habitats
│   └── adapter-owned state
│
├── deferred_effects
├── RNG stream states
├── last_event_id
└── journal integrity metadata
```

Debe incluir todo aquello cuyo estado pueda cambiar el futuro.

---

# 7. Regla de persistencia

El mundo no se considera verdaderamente persistente hasta superar esta prueba:

```text
Run A
tick 0 → tick 50,000
checkpoint
continue → tick 60,000

Run B
tick 0 → tick 50,000
checkpoint
kill process
restore
continue → tick 60,000
```

Y entonces:

```text
future(A) == future(B)
```

para:

```text
world
organisms
resources
hazards
actions
birth/death
events
RNG
```

Éste debe convertirse en un gate técnico obligatorio.

---

# 8. Persistencia física

El checkpoint no puede vivir únicamente en memoria.

Propuesta:

```text
~/.local/state/symbiont/worlds/<world_id>/
├── manifest.json
├── constitution.json
├── checkpoints/
│   ├── 000000001024.chk
│   ├── 000000002048.chk
│   └── ...
├── events/
│   ├── segment-000001.jsonl
│   └── ...
└── HEAD
```

`HEAD` apunta al último estado confirmado.

Escritura:

```text
write temporary checkpoint
fsync
validate checksum
atomic rename
update HEAD
```

Nunca sobrescribir directamente el último checkpoint bueno.

---

# 9. Event sourcing real

`EventJournal` debe dejar de ser sólo una estructura disponible y convertirse en la historia oficial del mundo.

El journal sólo contiene eventos **confirmados**.

Ejemplos:

```text
WORLD_FIELD_CHANGED
RESOURCE_RENEWED
RESOURCE_ACQUIRED
ORGANISM_MOVED
ORGANISM_CONTACT
ORGANISM_EMITTED
HAZARD_EXPOSURE
PHYSIOLOGICAL_DAMAGE
REPAIR
BIRTH
DEATH
GENOME_MUTATION
CULTURAL_TRANSMISSION
```

Cada uno mantiene:

```text
event_id
world_id
tick
kind
actor
position
payload
causal_parent_ids
contributing_event_ids
```

---

# 10. Causalidad

Se conserva estrictamente la distinción:

```text
causal_parent_ids
```

= transición mecánica conocida por construcción.

Ejemplo:

```text
RESOURCE_ACQUIRED
        ↓
METABOLIC_RESERVE_CHANGED
```

mientras:

```text
contributing_event_ids
```

= antecedentes relevantes pero no suficientes.

Ejemplo:

```text
resource history
damage history
age
reserve
       ↓
REPRODUCTION_READY
```

Observatory debe representar ambos de manera visualmente diferente.

---

# 11. WorldEpoch

Se mantiene `WorldEpoch` como concepto evaluator-side.

Un epoch no cambia el mundo.

Sólo proporciona navegación durable:

```text
Genesis
├── epoch 0
├── epoch 1
├── epoch 2
└── ...
```

Su representación interna:

```text
epoch
start_tick
trigger_event_id
label
```

Los labels:

```text
first birth
first extinction
```

son humanos.

La identidad durable sigue siendo:

```text
epoch=3
start_tick=182731
trigger_event_id=evt...
```

---

# 12. Genesis canónico vs mundos de prueba

Debe corregirse la ambigüedad actual.

Si `WorldConstitution` dice:

```text
64 × 64
```

un run:

```text
8 × 8
```

no es el mismo universo constitucional.

Propongo distinguir formalmente:

```text
Genesis-v1
64×64
mundo canónico

Genesis-Smoke-v1
8×8
pruebas rápidas

Genesis-Experimental-*
variantes científicas
```

Cada uno recibe su propio:

```text
WorldConstitution
world_fingerprint
```

Nunca reutilizar el fingerprint de Genesis para una geometría diferente.

---

# 13. Estado de W03

Los resultados actuales no se eliminan.

Se reclasifican.

W03 debe quedar como:

```text
EXPLORATORY
OBSERVED
NEEDS_REPLICATION
```

porque W01 no rechazó H0 y la barrera original exigía adaptación individual antes de interpretar ecología emergente.

Además:

```text
primer mecanismo causal propuesto
        ↓
hazard density coupling
        ↓
FALSIFICADO por control
```

y actualmente queda como candidato:

```text
different occupancy percept
→ different percept stream
→ different deterministic trajectory
```

Antes de convertir W03 en un resultado confirmado habrá que realizar:

```text
occupancy-percept ablation
+
multiple seeds
+
larger population
+
replication
```

---

# 14. Observatory: objetivo

Observatory no debe ser un videojuego.

Debe permitir que un humano entienda rápidamente:

```text
qué existe
qué está cambiando
qué individuo está deteriorándose
qué recurso se está agotando
qué evento acaba de ocurrir
qué percibe el organismo
qué cree el organismo
```

sin tocar el mundo.

---

# 15. Arquitectura de Observatory

```text
World Runtime
      │
      ├── current committed state
      └── EventJournal
             │
             ▼
      Projection Layer
             │
             ▼
       Read-only API
             │
             ▼
        Observatory UI
```

El navegador nunca habla con:

```text
WorldAction
WorldKernel
PopulationRuntime.run_tick()
```

No existen endpoints:

```text
POST
PUT
PATCH
DELETE
```

sobre el mundo.

---

# 16. Modelo visual del mapa

Cada hexágono debe existir permanentemente en el DOM.

El mapa visual se divide en:

```text
BASE
region / terrain

OVERLAY
resources / hazards / fields

FOREGROUND
organisms / recent events
```

---

# 17. Geografía

Actualmente las celdas vacías parecen idénticas.

Eso debe desaparecer.

Toda celda debe representar:

```text
CellView
├── q,r
├── region_id
├── resources
├── hazards
├── fields
├── occupant
└── recent event markers
```

La región determina el fondo base.

Los nombres tipo:

```text
north
south
rich biome
```

son metadata evaluator-side.

Nunca llegan al organismo.

---

# 18. Overlays

El usuario puede seleccionar una capa visual, sin cambiar el mundo.

```text
REGION
RESOURCE
HAZARD
FIELD
POPULATION
```

## Resource overlay

Puede representar:

```text
quantity / capacity
```

como intensidad/opacidad.

## Hazard overlay

Debe mostrar **exposición real**, no:

```python
local_density=0.0
```

como ocurre actualmente.

Debe calcularse con la misma densidad local utilizada por el runtime.

## Field overlay

Permite visualizar:

```text
field.01
field.02
...
```

usando las etiquetas humanas sólo en Observatory.

---

# 19. Organismo visual

El organismo no debe ser el hexágono.

Debe ser un glyph independiente colocado encima del terreno.

```text
terrain hex
     +
 organism
```

Esto permite posteriormente:

```text
movement interpolation
health rings
action pulses
selection
death markers
```

sin confundir lugar y habitante.

---

# 20. Vitalidad

El organismo muestra datos factuales.

No comenzar con categorías interpretativas como:

```text
hungry
happy
sick
```

sino:

```text
vital_state
integrity
metabolic reserve
metabolic pressure
age
generation
```

Visualmente:

```text
outer ring      integrity
inner fill      reserve
opacity         alive/dead
border pattern  vital state
```

---

# 21. Acciones y eventos recientes

Los efectos visuales son interpretación de Observatory sobre hechos objetivos.

Ejemplo:

```text
resource acquired
→ acquisition pulse

repair amount > 0
→ repair pulse

damage > 0
→ damage ring

death event
→ death marker
```

No se transmite al frontend una etiqueta como:

```text
organism_is_suffering
```

sino cantidades y eventos reales.

---

# 22. Muerte

Al morir:

```text
organism
→ removed from live occupancy
```

Observatory puede mantener temporalmente:

```text
recent_death_marker
```

pero esto es una anotación histórica.

No constituye un cadáver físico salvo que en una versión futura el mundo modele explícitamente materia residual.

---

# 23. Inspector

Click sobre una celda u organismo abre un panel lateral.

## Organismo

```text
IDENTITY
organism_id
generation
age

PHYSIOLOGY
vital_state
integrity
metabolic reserve
pressure

BEHAVIOR
last action
recent action history

WORLD EFFECTS
recent acquisition
damage
repair
hazard exposures

PERCEPTION
signals actually received

COGNITION
concept count
prediction data
confidence
self model
```

---

# 24. Cuatro perspectivas epistemológicas

El inspector debe separar explícitamente:

```text
WORLD
PHENOTYPE
PERCEPTION
SELF
```

## World

Lo que realmente existe.

## Phenotype

Lo que el organismo realmente es y hace.

## Perception

Lo que efectivamente recibe a través de sus sensores.

## Self

Lo que internamente representa sobre sí mismo o su entorno.

Nunca deben mezclarse.

---

# 25. Reality / Perception / Self

El elemento visual más importante puede ser un toggle:

```text
[ Reality ] [ Perception ] [ Self ]
```

Ejemplo:

```text
REALITY

resource.71 = 8.2
hazard.03 = .41


PERCEPTION

signal.a81 = .63
signal.d91 = .17


SELF

concept.18
expected consequence = favorable
confidence = .44
```

Eso permite observar el nacimiento de comprensión.

---

# 26. Inspector de celda

Debe mostrar:

```text
CELL q=12,r=7

region
occupant

resources
current quantity
capacity
renewal law summary

hazards
actual local exposure

fields
current values

recent events
```

Toda esta información pertenece al aparato científico.

---

# 27. Timeline

La simulación necesita una dimensión histórica visible.

Mantendremos buffers evaluator-side bounded:

```text
population_history
mean_integrity_history
mean_reserve_history
resource_acquisition_history
hazard_hits_history
birth_history
death_history
```

Por ejemplo:

```text
2048 samples
```

con downsampling cuando sea necesario.

---

# 28. Gráficas iniciales

Las primeras cuatro:

```text
alive organisms
mean integrity
mean metabolic reserve
resource acquisition rate
```

Luego:

```text
births
deaths
hazard hits
behavior distribution
```

Canvas nativo es suficiente.

No necesitamos dependencia gráfica.

---

# 29. Feed causal

Una vez conectado `EventJournal`, Observatory muestra eventos confirmados:

```text
tick 19342
RESOURCE_ACQUIRED

tick 19342
METABOLIC_RESERVE_CHANGED
caused by evt.9123

tick 19343
HAZARD_EXPOSURE

tick 19343
PHYSIOLOGICAL_DAMAGE
caused by evt.9131
```

La UI debe diferenciar:

```text
mechanical cause
```

de:

```text
contributing antecedent
```

mediante iconografía o líneas diferentes.

Nunca inferir eventos a partir de diferencias observadas.

---

# 30. Render sin flicker

Eliminar:

```javascript
svg.innerHTML = ''
```

El SVG debe construirse una vez.

Mantener:

```javascript
cellNodes = Map
organismNodes = Map
```

Por cada actualización:

```text
update attributes
update classes
update transforms
update labels
```

No reconstruir DOM.

---

# 31. Animación

Con nodos persistentes:

```css
transition:
    fill .45s,
    opacity .45s,
    stroke .2s,
    transform .45s;
```

Cuando exista movimiento:

```text
cell A → cell B
```

el glyph del organismo puede desplazarse suavemente.

---

# 32. Tecnología frontend

No introducir React/Vue todavía.

La pila actual puede mantenerse:

```text
stdlib HTTP
vanilla JavaScript
SVG map
Canvas charts
CSS transitions
```

Pero `dashboard_page.py` no debería seguir acumulando toda la aplicación en una cadena HTML.

Separar conceptualmente:

```text
dashboard/
├── page.py
├── world.js
├── renderer.js
├── inspector.js
├── timeline.js
├── api.js
└── styles.css
```

---

# 33. API

El payload actual debe evolucionar a una estructura explícita.

```json
{
  "world": {},
  "fields": {},
  "cells": {},
  "organisms": {},
  "history": {},
  "events": []
}
```

Ejemplo de organismo:

```json
{
  "id": "founder-3",
  "q": 12,
  "r": 7,
  "alive": true,
  "vital_state": "active",
  "integrity": 0.81,
  "metabolic_reserve": 0.54,
  "last_action": "intake:...",
  "recent_damage": 0.05
}
```

Los datos evaluator-side más interpretativos deben mantenerse separados.

---

# 34. Eventos incrementales

Se puede mantener polling.

No necesitamos WebSocket aún.

Por ejemplo:

```text
GET /api/state
GET /api/events?after=<event_id>
```

Así polling cada segundo no pierde eventos aunque el mundo avance varios ticks.

---

# 35. Zoom semántico

La navegación debe seguir:

```text
WORLD
 ↓
REGION
 ↓
CELL
 ↓
ORGANISM
 ↓
MIND
```

No es sólo zoom geométrico.

Cada escala cambia qué información se presenta.

World:

```text
ecología
```

Region:

```text
presiones locales
```

Cell:

```text
ground truth
```

Organism:

```text
fisiología y comportamiento
```

Mind:

```text
percepción, conceptos y predicción
```

---

# 36. Historia natural y ciencia experimental

Los mundos persistentes y los experimentos deben seguir separados.

```text
CANONICAL WORLD
vive continuamente

EXPERIMENTAL CLONE
parte de un checkpoint
```

Por ejemplo:

```text
Genesis
tick 2,184,993
```

puede clonarse en:

```text
Experiment A
original

Experiment B
communication disabled

Experiment C
resource X removed
```

sin alterar Genesis.

---

# 37. Recovery semantics

Al reiniciar el servidor:

```text
load HEAD
validate constitution fingerprint
validate journal/checkpoint continuity
restore world
restore population
resume at N+1
```

Si el último checkpoint está corrupto:

```text
fallback previous checkpoint
+
replay committed events
```

Nunca inventar estado.

---

# 38. Dashboard y persistencia son el mismo proyecto

No deben evolucionar por separado.

El dashboard consume únicamente:

```text
committed world state
+
committed journal
```

Por tanto:

```text
UI nunca ve estado provisional
```

Esto es importante.

Si un tick falla, el navegador no debe llegar a observar un universo que posteriormente desaparezca por rollback.

---

# 39. Plan de implementación

## Phase P0 — World Integrity

Resolver:

```text
IntegratedWorldTickTransaction
WorldEnvironment rollback
organism rollback
SharedHabitat rollback
DeferredEffectQueue rollback
pending-event staging
```

Gate:

```text
forced failure at every phase
→ exact state restoration
```

---

## Phase P1 — Durable World

Implementar:

```text
PersistentWorldCheckpoint
disk storage
atomic checkpoint writes
HEAD
startup restore
checkpoint/replay equivalence
```

Gate principal:

```text
continuous run
==
kill + restore + continue
```

---

## Phase P2 — Journal Integration

Conectar eventos reales:

```text
resource
damage
repair
death
birth
movement
communication
```

Los eventos se publican únicamente tras COMMIT.

---

## Phase P3 — Observatory 0.2

Implementar:

```text
persistent SVG DOM
region map
organism glyphs
vitality
actual hazard exposure
cell selection
organism selection
inspector
last action
damage markers
```

---

## Phase P4 — Observatory 0.3

Añadir:

```text
resource overlays
hazard heatmap
field overlays
transitions
legend
semantic zoom
```

---

## Phase P5 — Observatory 0.4

Una vez exista journal:

```text
event feed
causal provenance
population timeline
resource timeline
birth/death timeline
historical annotations
```

---

## Phase P6 — Observatory 0.5

Finalmente:

```text
Reality
Perception
Self

sensor inspector
concept inspector
prediction inspector
self-model inspector
```

---

# 40. Qué NO añadir todavía

Hasta cerrar P0–P2 no abriría nuevas capacidades sustanciales:

```text
MOVE como nueva capacidad cognitiva
reproducción espacial
culture-in-world
communication range
evolutionary expansion
complex niche construction
```

No porque sean malas ideas.

Porque aumentarían el espacio causal antes de que podamos garantizar:

```text
rollback
recovery
history
replay
```

---

# 41. Qué hacemos con los experimentos actuales

No borrar nada.

Reclasificar:

```text
W01
valid null result

W02
valid methodological null result

W03
exploratory observation
needs replication
not formal ecological gate
```

Los runs ya realizados son evidencia útil de desarrollo.

Pero el próximo programa científico debe partir de un mundo cuya identidad, persistencia y causalidad estén cerradas.

---

# 42. Condición para llamar al mundo “perenne”

No basta con que el proceso lleve varios días encendido.

La definición debería ser:

> Un Symbiont World es perenne cuando su continuidad causal no depende de la continuidad del proceso que lo ejecuta.

Es decir:

```text
process lifetime
≠
world lifetime
```

Ésa es la frontera importante.

---

# 43. Estado objetivo final

Queremos poder hacer esto:

```text
$ symbiont-world serve Genesis
```

y obtener:

```text
Loading Genesis...

world_id        genesis
fingerprint     91ab...
epoch           27
tick            18,392,188
population      43
last checkpoint 18,391,808
journal         valid

Resuming world.
Observatory:
http://127.0.0.1:8766
```

Mientras el navegador muestra:

```text
WORLD
──────────────
map
regions
resources
hazards
population

TIMELINE
──────────────
population
integrity
resources

EVENTS
──────────────
birth
damage
acquisition
death

INSPECTOR
──────────────
Reality
Phenotype
Perception
Self
```

El usuario puede cerrar el navegador.

Nada cambia.

Puede matar el servidor.

El mundo queda guardado.

Puede arrancarlo una semana después.

Continúa desde el último estado confirmado.

---

# 44. Criterio de éxito

Esta etapa estará terminada cuando podamos afirmar simultáneamente:

```text
1. El mundo no pierde causalidad ante un fallo de tick.

2. El mundo sobrevive a un reinicio del proceso.

3. Su futuro es reproducible desde checkpoint + journal.

4. Observatory sólo muestra estados confirmados.

5. Observatory no tiene ningún canal de control.

6. Un humano puede entender visualmente la ecología.

7. Puede distinguir World / Phenotype / Perception / Self.

8. La historia del mundo puede reconstruirse causalmente.

9. Genesis canónico tiene identidad constitucional inequívoca.

10. Podemos dejar a los Symbionts viviendo sin depender de que haya
    un humano mirando.
```

---

# 45. Resultado conceptual

Hasta ahora hemos pasado por:

```text
Symbiont
“tenemos un organismo”

        ↓

Symbiont World
“tenemos un entorno donde colocarlo”

        ↓

Persistent Symbiont World
“tenemos un lugar donde puede vivir”

        ↓

Scientific Observatory
“podemos observar qué ocurre sin intervenir”
```

Ésta debería ser la prioridad antes de ampliar todavía más la biología digital.

El siguiente gran salto del proyecto no consiste en dar a los Symbionts una capacidad nueva.

Consiste en conseguir que **la vida que ya pueden desarrollar tenga un mundo continuo, una historia real y un instrumento científico capaz de hacérnosla visible**.
