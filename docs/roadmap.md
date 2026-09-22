# Symbiont organism roadmap

This roadmap prioritizes capabilities acquired by the organism. Laboratory work is introduced only when a new organism capability needs a new measurement instrument.

The sequence is directional rather than calendar-based.

The roadmap distinguishes two things that must not be conflated:

1. **developmental limitations** — capabilities the organism does not have yet but may acquire later;
2. **permanent invariants** — consent, boundedness, epistemic separation and anti-evasion constraints that remain in force even as capability grows.

## North star

Build a benevolent digital organism that can develop on a consenting host, regulate its own internal computational economy, maintain viability under finite resources, reproduce through explicit heredity mechanisms, and eventually participate in bounded digital ecologies where cooperation, competition, coexistence and specialization are observable outcomes rather than hard-coded goals.

The organizing research sequence is:

> **Development before intelligence. Physiology before ecology. Ecology before society.**

Symbiont is not intended to remain permanently solitary, read-only or non-reproductive merely because those are properties of the current release. New capabilities may be added when their semantics, consent model, resource model and experimental observability are designed first.

At the same time, increased capability must not weaken the permanent invariants: no covert persistence, no stealth or evasion, no privilege escalation, no exploitation, no hidden evaluator oracle, no learned bypass of kernel limits, and no uncontrolled propagation.

---

Full milestone history (A-H) and the per-patch tracking log are archived in
[`docs/history/roadmap-log.md`](history/roadmap-log.md).

## Permanent invariants

These constraints survive future increases in capability.

1. Real-host access remains explicit, revocable and capability-bounded.
2. Learned state cannot manufacture permissions, commands, executable code or new kernel capabilities.
3. Credentials and privilege-escalation mechanisms remain outside the organism's developmental substrate.
4. Residence and persistence remain transparent and owner-controlled.
5. No stealth, concealment or evasion is used to maintain residence or acquire resources.
6. No exploitation is used to acquire capabilities, compute, storage or access.
7. Hard CPU, memory, storage and communication ceilings remain outside learned control.
8. Reproduction never means covert or uncontrolled propagation.
9. Materializing a descendant requires an authorized habitat, carrying-capacity slot and explicit resource allocation.
10. A dead organism identity cannot be normally resumed as though continuity never closed.
11. Experimental ground truth remains outside organism cognition.
12. The laboratory may observe the organism without silently becoming its controller.
13. New write, network, action or reproduction capabilities cross an explicit design and consent gate before implementation.

These invariants do **not** imply that Symbiont must remain permanently read-only, non-communicating or non-reproductive.

---

## Birth, identity, dormancy and death

The physiology and reproduction milestones require explicit life-cycle semantics.

The project uses the following distinctions unless a later design document supersedes them:

- **birth** — creation of a new organism identity with a valid genome and authorized initial resource allocation;
- **germinal / developing / mature** — viable developmental phases of one organism identity;
- **active** — viable and executing its normal cognitive cycle;
- **stressed** — viable but physiologically constrained by resource or integrity pressure;
- **dormant** — viable but intentionally running a minimal maintenance cycle;
- **stopped** — process not running; this is not by itself death;
- **restarted** — the same organism identity resumes only if its durable viable state is valid;
- **dying** — continuity is still present but bounded recovery has failed and death finalization is pending;
- **dead / non-viable** — organism continuity is explicitly and irreversibly closed;
- **descendant** — a new organism identity created through a reproductive event, even when it has exactly the same genome as its parent.

Normal restore rejects a `DEAD` identity. Reconstructing or cloning from historical artifacts, if later allowed experimentally, creates a new identity and is not resurrection.

Organism lifecycle, cognitive topology health and reproductive readiness remain separate state dimensions. For example, an organism may simultaneously be `MATURE`, `ADAPTIVE` and `REPRODUCTIVELY_READY`.

This prevents process management concepts from silently standing in for biological ones.

---

## Merge policy

The project owner has explicitly instructed that GitHub Actions are not a merge gate.

A release can therefore merge after local/structural review even when hosted CI is unavailable.

The remaining gates are:

1. base/head drift is checked before merge;
2. no unresolved requested changes are knowingly ignored;
3. new resource use is bounded by construction and covered with deterministic tests;
4. privacy, consent and safety invariants accompany functional behavior;
5. ground truth remains outside organism cognition;
6. the release documents the new organism capability;
7. lineage, death and reproduction changes are transactional and replay-testable;
8. ecological changes include aggregate carrying-capacity tests, not only per-organism limits;
9. dead-organism restore and population-over-capacity paths have explicit negative tests.

---

## Decision gates

Work pauses for an explicit architectural and safety decision before any merge that:

- requests new write, execute, elevated or remote permissions;
- expands perception into identifying metadata or user content;
- enables network exchange;
- introduces hidden or non-removable persistence;
- permits autonomous real-world action;
- materializes descendants outside an existing authorized habitat;
- changes reproductive authority or carrying-capacity ownership;
- creates unbounded CPU, memory, storage, population or network use;
- weakens the separation between organism and evaluator;
- allows learned state to alter immutable kernel limits or permissions;
- materially expands a human-facing security/operational advisory beyond the already approved consultative boundary.

Transparent owner-installed residence and bounded current read-only sensory development are already explicitly approved and do not reopen those decisions.

---

## Milestone I — Fisiología integrada (implementación parcial)

Milestone I cierra el acoplamiento entre intake, metabolismo, homeostasis,
reparación, dormancia, degradación, viabilidad, reproducción, muerte y hábitat.
El diseño normativo está en
[`design/fisiologia-y-reproduccion.md`](design/fisiologia-y-reproduccion.md).

La implementación ya cubre estado fisiológico, intake explícito, checkpoint,
liberación de hábitat y frontera post-muerte. Incluye un arnés determinista de
inanición/recuperación en `symbiont_lab.studies.physiology`. Quedan gates de
integración para reparación, dormancia y reproducción; el Observatory ya
publica estos estados de forma pasiva.

## Milestone J — Desarrollo predictivo autónomo (implementación parcial)

Milestone J convierte señales opacas y relaciones estadísticas en hipótesis
contrastables, con atención anti-captura, persistencia cuantizada con cero
exacto, conceptos `stranded` y predicción en shadow mode antes de promover
nodos `PREDICTOR`. Sus métricas son externas y no otorgan semántica privilegiada
al organismo. El diseño normativo está en
[`design/sociabilidad-y-desarrollo-predictivo.md`](design/sociabilidad-y-desarrollo-predictivo.md).

La implementación se divide en P0 (codec y atención), P1 (hipótesis y reparación
de rutas) y P2 (predicción e instrumentación). Existe además un gate longitudinal de shadow-promotion con candidatos positivos
y sin ganancia. La promoción runtime es opt-in, bounded y persiste su contrato
en checkpoints.

## Milestone K — Sociabilidad emergente (implementación parcial)

Milestone K proporciona capacidades celulares para percibir, intercambiar,
competir, asociarse, separarse y revisar interacciones sin imponer una sociedad
ni objetivos sociales. El diseño normativo está en
[`design/sociabilidad-y-desarrollo-predictivo.md`](design/sociabilidad-y-desarrollo-predictivo.md).

La base implementada es un ledger de relaciones agregadas, un `SocialHabitat`
autorizado y un motor de intercambio/competencia sobre recursos finitos. Existe
un arnés determinista de intercambio/competencia para evaluación externa.
El ledger conserva ahora reciprocidad, conflictos y frescura de la evidencia,
y el hábitat permite suspender/reanudar pares explícitamente, con checkpoints
backward-readable. La validación longitudinal básica ya cuenta con estudios de suspensión,
reactivación y diferenciación de nichos. v0.79.18 añade un baseline determinista
de emergencia para el laboratorio; v0.79.19 acopla la dormancia del runtime a
costes de actividad reducidos sin reposición gratuita; v0.79.20 integra presión
reproductiva y budding clonal autorizado con identidad y capacidad acotadas; v0.79.21 conserva la frontera estructural del paquete y
v0.79.22 cobra el coste metabólico de nacimientos exitosos; v0.79.23 materializa
el runtime germinal del descendiente sin copiar el fenotipo adquirido; v0.79.24
verifica el replay determinista de padre/descendiente; v0.79.25 verifica muerte
y liberación exactly-once en una población padre/hijo. Esto
no demuestra todavía emergencia autónoma en producción ni impone ninguna meta
social o semántica humana.

## Milestone L8 — Prospective Agency (implementación en curso)

L8 conecta por primera vez el repertorio motor adquirido, el Private SLM ACTIVE
y el valor homeostático aprendido para permitir elección prospectiva de acciones
sin introducir semántica del laboratorio. La especificación normativa está en
[`design/prospective-agency-v1.md`](design/prospective-agency-v1.md).

El alcance v1 es deliberadamente one-step. Una acción sólo puede entrar en
deliberación si ya es una competencia sensorimotora y su `primitive_readout`
ha sido admitido por CognitiveGraph. El modelo privado puede predecir una
consecuencia opaca, pero esa predicción nunca se convierte por sí sola en
evidencia ni valor. `OutcomeValueLedger` aprende exclusivamente de outcomes
observados después de acciones reales y de su consecuencia fisiológica
posterior.

Estado de cierre:

- L8.0 readiness/candidate repertoire — implementado; validación empírica pendiente.
- L8.1 primitive causal tokens — implementado.
- L8.2 ACTIVE counterfactual inference no mutante — implementado.
- L8.3 endogenous OutcomeValueLedger — implementado.
- L8.4 prospective policy/runtime integration — implementado baseline.
- L8.5 delayed observed-outcome credit — implementado.
- L8.6 checkpoint/fail-closed semantics — implementado baseline.
- L8.7 Physics3D passive telemetry — implementado baseline.
- L8.8 decontamination boundary — implementado por tests AST.
- L8.9 controlled shuffled/no-counterfactual studies — pendiente.
- L8.10 Physics3D causal study — pendiente.
- L8.11 adversarial re-audit y full regression — pendiente.
- L8.12 closure — pendiente.

L8 no autoriza rollouts multistep, MCTS, reward externo, distancia al recurso ni
políticas de locomoción. Cualquier profundidad prospectiva >1 requiere una fase
separada después de superar los controles causales de v1.

---

## Cultural Foundation y Cumulative Culture v1 — cerradas en alcance experimental

Cultural Foundation v1 y Cumulative Culture v1 añaden claims sociales bounded,
genealogía de roots, composición cultural versionada y transporte local autorizado.
La composición puede integrar claims de varios organismos, conservar contributors y
roots, continuar tras la desaparición de los fundadores y degradarse mediante
retirada explícita. La validación actual es evaluator-side y no demuestra todavía
una política autónoma de cooperación, símbolos, selección cultural ni coevolución
con Private SLM. Pesos, adapters y corpus siguen siendo estrictamente privados.

## Autonomous Cultural Agency v1 — cerrada en alcance bounded

`CulturalPolicy` y `CulturalDecisionRecord` trasladan la selección de contenido
cultural al organismo: el arnés autónomo solo suministra topología local,
ventanas y presupuestos. El estudio preregistrado
`learning.autonomous-cultural-agency` cerró ACA1–ACA10 y replay en las semillas
101, 127 y 149. La política produjo decisiones no triviales y composiciones
multi-contributor útiles sin recibir IDs de claims/composites ni ground truth.
El transporte sigue siendo local, autorizado y en memoria; Observatory sigue
siendo pasivo. No se abren símbolos, lenguaje, selección cultural, reputación ni
transferencia de Private SLM.

## Emergent Symbol Grounding v1 — cerrada

La línea posterior a `v0.80.16` cerró la convención simbólica opaca,
organismo-side y aprendida por experiencia dentro de sus gates preregistrados.
No abrió lenguaje, gramática ni semántica humana.

## Structured Communication Characterization v1 — cerrada

Línea posterior a Emergent Structured Communication v1. No añade capacidades
lingüísticas: caracteriza el canal general ya cerrado mediante un sweep pequeño
de complejidad ambiental, vocabulario, longitud, memoria/coste y controles.
Observatory expone únicamente telemetría pasiva bounded; las métricas de
estructura son evaluator-side. Véase
[`design/structured-communication-characterization-v1.md`](design/structured-communication-characterization-v1.md).

## Population Communication Telemetry v1 — cerrada

Trabajo posterior al corte congelado `v0.80.16`; añade únicamente telemetría
factual bounded y vistas Observatory read-only; no modifica la política ni el
canal cognitivo de comunicación.

## Longitudinal Population Ecology v1 — cerrada como discovery

Línea de discovery posterior al corte congelado `v0.80.16`. Ejecutó stages
progresivamente largos sobre el simulador existente y reporta por separado el
sondeo multigeneracional del runtime social existente. No añade capacidades al
organismo ni convierte patrones descubiertos en claims confirmados. Véase
[`design/longitudinal-population-ecology-v1.md`](design/longitudinal-population-ecology-v1.md).

## Integrated Habitat Runtime v1 — P0 de integración resuelto

`symbiont_lab.integration.IntegratedHabitatRuntime` es ahora el entrypoint
canónico y bounded para ejercer en un mismo habitat las capacidades existentes
de población, fisiología, aprendizaje, model registry privado, cultura,
grounding, comunicación y telemetría. El habitat solo orquesta ciclo, identidad,
contactos autorizados, checkpoint y contabilidad; no elige claims, mensajes,
receptores, significados ni composites.

El smoke técnico preregistrado cubre births/deaths, comunicación, grounding,
restore y replay en seeds `101, 127, 149`. La prueba larga ejecutada cubre
`1,000` ticks para esos invariantes en seed `101` y `10,000` ticks en seed
`101`; sus límites de historial, telemetría y transporte son explícitos. La
clasificación de integración pasa de C a **A — INTEGRATED** en sentido
arquitectónico y de smoke técnico. Esto demuestra coexistencia técnica, no
fenómenos poblacionales emergentes. La auditoría adversaria posterior y la
aprobación del owner congelan ahora el sustrato en `1.0.0`.

## Symbiont Experimental Organism v1 — frozen in 1.0.0

La auditoría adversaria final v2 no encontró P0 ni P1 materiales: integración
**A**, replay integrado, equivalencia con telemetría activada/desactivada,
boundedness y QA interactiva de Observatory pasan. Véase
[`../research/audits/current/experimental-organism-v1/final-v2.md`](../research/audits/current/experimental-organism-v1/final-v2.md).
El corte publicado usa el tag anotado `experimental-organism-v1` y la versión
de paquete `1.0.0`; el tag histórico `v0.80.16` no se modifica. La publicación
del tag y del release se completa como operación administrativa separada.

```text
CAPABILITY DEVELOPMENT: FROZEN BY DEFAULT
EXPERIMENTAL RESEARCH: ACTIVE
```

Después del freeze, el organismo core solo cambia por bugs, seguridad,
boundedness o reproducibilidad demostrados. New phenomena should primarily be
investigated through habitats and experiments, not by continuously adding
organism capabilities.

## Symbiont World v1 — W0 (package boundary y kernel foundation) implementado

Nuevo paquete `symbiont_world`, un hábitat espacial persistente y opaco para
el organismo ya congelado en `1.0.0` — exactamente el tipo de trabajo que el
freeze permite explícitamente ("new habitats and experiments"). Especificación
normativa en
[`design/symbiont-world-v1.md`](design/symbiont-world-v1.md); razonamiento y
bibliografía de ALife en
[`design/symbiont-world-v1-rationale.md`](design/symbiont-world-v1-rationale.md).

W0 entrega solo el fundamento estructural, sin fields, resources, hazards ni
organismos viviendo dentro: `WorldConstitution` (fingerprint versionado),
contratos `WorldObservation`/`WorldAction` inmutables y sin ground truth,
topología hexagonal con frontera reflectante y `OccupancyGrid` (una celda, un
organismo), RNG namespaced sin importar `symbiont`, `WorldEvent` con
`causal_parent_ids`/`contributing_event_ids` separados sobre un journal
append-only, y commit/rollback atómico de tick vía `TickTransaction`
(`symbiont_world/state.py`). 43 tests unitarios en `tests/unit/world/`
cubren estos invariantes; dos tests AST nuevos en
`tests/experimental_integrity/test_ground_truth_boundary.py` fijan la
frontera de paquetes en ambas direcciones (`symbiont` no importa
`symbiont_world`; `symbiont_world` no importa `symbiont` ni `symbiont_lab`).
Suite completa: 1817 passed (los 3 fallos restantes son deriva preexistente
de Observatory, no relacionada).

Siguiente paso declarado por la spec: W1 añade movimiento y observación
local por organismo sobre este kernel; W2 incorpora las leyes de Genesis
(`world-ground-truth.toml`). No se ejecuta ningún gate de falsación (W01–W07)
hasta que exista implementación real de fields/resources y al menos un
organismo viviendo en el mundo.

## Symbiont World v1 — W1, W2, W2.1 y preset Genesis v1 implementados

Sobre el kernel de W0: `symbiont_world/observation.py` (percepción local,
señal opaca de densidad de ocupación) y `symbiont_world/movement.py`
(resolución de movimiento determinista con desempate RNG-namespaced) cierran
W1 (§12 de la spec). Un bug real se encontró y corrigió durante el TDD:
`WorldState` solo hacía rollback de `occupancy`, no del registro
`WorldBody`; un tick abortado dejaba posiciones mutadas a medias. Se movió
`bodies` a `WorldState` para que ambas mutaciones compartan la misma
transacción atómica.

W2 (§13) añade `symbiont_world/laws.py`
(`PeriodicFieldLaw`/`ResourceLaw`, parámetros genéricos sin nombre de
dominio) y `symbiont_world/genesis.py` (`GroundTruth` + `WorldEnvironment`:
propagación de fields, renovación/decaimiento de recursos por celda con
inicialización perezosa, adquisición que nunca deja el pool negativo).
W2.1 (§14) añade `HazardLaw`, sin estado propio, función de exposición
acoplada a la densidad local que ya calculaba W1 — cierra el conteo
congelado de Genesis v1 (4 fields, 4 resources, 2 hazards) del lado del
kernel. `observation.py` extiende sus signals con fields/resources/hazards
reales cuando se le pasa un `WorldEnvironment`, sin romper el
comportamiento W1 cuando no se le pasa ninguno.

Un nuevo paquete `symbiont_lab.world` (único autorizado a conocer semántica
real, según §2/§13) instancia el primer mundo reproducible completo:
`genesis_v1.py` construye el `GroundTruth` congelado de Genesis v1 con
parámetros numéricos reales y su `WorldConstitution` correspondiente
(fingerprint determinista), manteniendo las etiquetas humanas
(`GENESIS_V1_METADATA`) fuera de `symbiont_world` en todo momento.

92 tests nuevos en `tests/unit/world/` y `tests/unit/lab/world/`. Suite
completa: 1866 passed (mismos 3 fallos preexistentes de Observatory sin
relación).

### Lo que falta para ejecutar W01/W02 (aún no iniciado)

Esto es deliberadamente honesto: todavía no existe ningún organismo viviendo
en el mundo. El preset Genesis v1 y el kernel completo de campos/recursos/
hazards no equivalen a un experimento ejecutable. Falta:

1. El adaptador real `symbiont_lab` que traduzca `WorldObservation` hacia el
   pipeline `ObservableSource → Sensor → Percept` existente de un
   `ModeledOrganismRuntime`, y sus decisiones de vuelta hacia `WorldAction`
   — esto es una integración de tamaño comparable a
   `IntegratedHabitatRuntime`, no una extensión menor.
2. El mapeo de efecto fisiológico real: `acquire`/hazard exposure aún no
   tocan `MetabolicLedger`; el "beneficio inmediato con daño diferido" que
   §7 exige de al menos un recurso de Genesis sigue sin implementación —
   `ResourceLaw` solo gobierna el pool, no el efecto sobre el organismo.
3. Colocación determinista de founders (`seed → founder placement`, §7) —
   sin implementar; los 8 founders de Genesis v1 no tienen todavía una
   regla de colocación inicial.
4. Solo entonces W01/W02 (§8) pueden preregistrarse y ejecutarse contra
   datos reales, no contra el contrato descrito en la spec.

Este es un punto de control natural: el siguiente incremento (el
adaptador) es una pieza de integración grande y merece su propio
diseño/plan dedicado, no continuación ad hoc.

## Symbiont World v1 — W3 (adaptador real) y W01/W02 ejecutados: v1 cerrado

`symbiont_lab.world.adapter.SingleOrganismGenesisRuntime` (§15) conecta un
`ModeledOrganismRuntime` real al kernel sin modificar `symbiont` en
absoluto: percepción vía `DiscoveryProvider`/`ReadingProvider`
(`symbiont/host/contracts.py`, `symbiont/host/readings.py`, ya diseñados
para exactamente esto), adquisición vía `resource_habitats` +
`SharedHabitat.set_environment_resources` (ya pública, decisión de
adquirir sigue siendo de la cognición vía `autonomous_action_step()`), y
daño de hazard vía `apply_environmental_damage` (ya existente, acotado a
`(0, 0.25]`). No se añadió ningún `ActionKind`; `grep` de
`symbiont/core/behavior.py` no cambia — verificado por test.

Descubrimiento clave que redujo el alcance: releyendo §8, **W01 y W02 no
necesitan movimiento ni founders múltiples** — ambos usan un organismo
estacionario. Eso hizo tratable el adaptador (una celda, sin comunicación
ni reproducción) en vez de requerir la pieza completa de colocación de
founders/movimiento real que el punto de control anterior asumía
necesaria.

**W01/W02 se ejecutaron de verdad** contra datos reales (no simulados ni
inventados): `experiments/world/genesis-v1/run_w01_w02.py`, resultados en
`results.json`, análisis honesto en `audit.md`. Resultado:

```
W01: H0 se mantiene (no rechazada). cognitive_wins = 0/3 seeds.
     Mecanismo observado (no confirmado): la política cognitiva satura
     INTAKE y nunca elige REPAIR en ninguna semilla; el control aleatorio
     sí repara por muestreo uniforme y termina con mayor integridad.
     El daño de hazard no está causalmente conectado a ningún
     ExpectedOutcome de REPAIR en el modelo de acción actual.

W02: H0 se mantiene (no rechazada), más un hallazgo metodológico real:
     con exploration=0.0, discover_senses=False y sin reproducción,
     organism_seed no tiene ningún camino causal hacia la selección de
     acción de un organismo solitario — dos réplicas con distinto
     organism_seed producen una trayectoria bit-a-bit idéntica. No es un
     resultado fabricado de "convergencia"; es una limitación real de esta
     build para poner a prueba divergencia por historia estocástica.
```

Ninguno de los dos gates rechaza su H0. Por diseño (§11, §15): **esto es
lo que cierra v1**, no un resultado positivo fabricado. `docs/design/
symbiont-world-v1.md` §11 lo dice explícitamente: "W01–W02 operacionalizan
[la pregunta científica]... su resultado — sea cual sea, incluida
convergencia trivial como H0 — es lo que cierra v1". Con ambos gates en
H0, no hay base para avanzar a W03+ (ecología de nichos, evolución,
cultura, open-endedness, §8 barrera formal entre programas) interpretando
adaptación que los datos no muestran.

166 tests nuevos/actualizados en `tests/unit/lab/world/` y
`tests/unit/world/`; suite completa: 1878 passed (mismos 3 fallos
preexistentes de Observatory, verificados independientes de este trabajo
vía `git stash`).

### Qué queda fuera de v1, explícitamente

Movimiento real, founders múltiples/colocación determinista, comunicación,
reproducción, el efecto de "beneficio inmediato con daño diferido" de un
recurso (`ResourceLaw` sigue sin modelar ese daño retardado), y cualquier
mecanismo de divergencia estocástica genuina para un organismo solitario
(el hallazgo de W02 arriba). Todo eso es material legítimo para W03+, no
una deuda de v1.

## Symbiont World v2 — implementado; W03 ejecutado y rechaza H0

Especificación en [`design/symbiont-world-v2.md`](design/symbiont-world-v2.md).
Todo aditivo sobre v1: ningún test de W0–W3 dejó de pasar (gate V02-08
verificado por la suite completa).

**Heterogeneidad regional** (`GroundTruth.region_of`/`regional_resources`/
`regional_hazards`, `symbiont_world/genesis.py`): opcional, default `None`/
`{}` reproduce exactamente el comportamiento de v1. Corrección honesta
encontrada al implementar: los pools de recurso son por-celda, no
por-región — la región solo comparte la *ley*, nunca el pool; no hay
contención real de recursos entre founders en v2 (documentado en el spec,
§4). `hazard_exposures()` se mantiene sin cambios por compatibilidad;
`hazard_exposures_at(cell, density)` es la versión consciente de región.

**Multi-organismo** (`symbiont_lab.world.population`): `founder_placement()`
determinista, `PopulationGenesisRuntime` sostiene 8 `ModeledOrganismRuntime`
sobre un mismo `WorldState`/`WorldEnvironment`, orden de tick por
`organism_id` ordenado. `resolve_movement`/intents simultáneos siguen sin
ejercitarse con más de un organismo (V02-04 marcado N/A: v2 no tiene
movimiento aprobado, §7).

**Retry de W02 con plasticidad real** (`sensory_plasticity=True`,
`discover_senses=True`): **H0 se mantiene otra vez**, pero con diagnóstico
más preciso que v1 — dos réplicas observan una trayectoria de mundo
idéntica (mismo `world_seed`), así que no hay nada de lo que plasticidad
pueda divergir; `organism_seed` solo llega a `mutation_seed`, que solo
importa si hay reproducción. Ver
`experiments/world/genesis-v1/audit-w02-retry.md`.

**Daño diferido** (`symbiont_lab.world.deferred.DeferredEffectQueue`,
acotada a 32 entradas): verificado end-to-end disparando exactamente una
vez por adquisición cualificada, dentro del rango `(0, 0.25]` ya exigido
por `apply_environmental_damage`.

**Observatory CLI** (`symbiont_lab.world.cli_view.render_world`, función
pura, solo lectura): render de organismos/campos/recursos/hazards con
etiquetas reales de `GENESIS_V1_METADATA`; confirma honestamente que
ningún `EventJournal` está todavía conectado a los runtimes (gap real, no
fabricado). Launcher delgado en `experiments/world/genesis-v1/view_world.py`.

**Gate de capacidad de movimiento (§7): sin implementar, a propósito.**
Decisión de abrir la puerta registrada con el owner; diseño concreto de
`ActionKind.MOVE` explícitamente pendiente de su propia revisión antes de
tocar `symbiont/core/behavior.py`.

### W03 ejecutado de verdad: **rechaza H0**, con hallazgo honesto sobre el mecanismo

`experiments/world/genesis-v1/run_w03.py` (Genesis v2:
`symbiont_lab.world.genesis_v2`, dos regiones con `ResourceLaw` distinta
para 2 de 4 recursos). Dos founders comparten región (misma ley) y
**difieren en su recurso dominante de adquisición** — diferenciación
ecológica real sin variación genética. `reject_h0 = True`.

Hipótesis inicial (`hazard-density-coupled` genera presión posicional) —
**descartada por su propio control**: con `density_coupling=0` para ambos
hazards, el mismo patrón de desacuerdo aparece idéntico
(`mechanism_supported = False`). El mecanismo real sigue abierto —
candidato: el percept crudo de densidad de ocupación local ya difiere por
posición independientemente del hazard, y dado que v2 confirmó que la
cognición es una función determinista de su flujo de percepts, un flujo
distinto basta para producir trayectorias distintas. Se registra como
`OBSERVED, NEEDS_REPLICATION` — ver `experiments/world/genesis-v1/
audit-w03.md` — no como fenómeno confirmado.

54 tests nuevos en `tests/unit/lab/world/`, `tests/unit/world/`. Suite
completa: 1920 passed (mismos 3 fallos preexistentes de Observatory).
