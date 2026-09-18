# Symbiont Experimental Organism v1 — Final Adversarial Audit

**Fecha:** 2026-09-18
**Rama auditada:** `main`
**HEAD:** `239858f1648a7997306dfe928bdeb0f24a959659`
**Referencia congelada:** `v0.80.16` = `7cf5cce277a1f157f17bb9114ac33663c69ed1ab`

## Executive summary

**VEREDICTO: NOT READY FOR FREEZE.**

El repositorio contiene un sustrato amplio, con fronteras epistemológicas,
provenance, replay, límites y observabilidad bien cubiertos en los protocolos
existentes. La auditoría, sin embargo, encuentra un blocker P0 de integración:
no existe un ciclo canónico donde población dinámica, reproducción, fisiología,
aprendizaje individual, Private SLM, cultura, política cultural autónoma,
grounding simbólico, comunicación estructurada y telemetría funcionen juntos.

La conclusión no es que las capacidades separadas sean inválidas. Es que el
estado actual es **C — MODULARLY VALIDATED BUT NOT INTEGRATED**. Bajo el criterio
definido para este audit, eso bloquea afirmar que ya existe un organismo
experimental integrado listo para congelar.

## Metodología y límites

Se revisaron código, imports, contratos, estudios, snapshots, tests,
preregistros, resultados y documentación. Se ejecutaron:

```text
pytest -q                                      1664 passed, 1 warning
pytest targeted                               61 passed
git diff --check                              limpio
longitudinal smoke: seed 101, 32 ticks, 2 hosts
```

El smoke longitudinal confirmó estado finito, contadores bounded y replay
determinista en el simulador fijo; el probe separado confirmó 8 generaciones,
lineage y checkpoint/replay. No se presentó esa combinación como integración.
La QA interactiva de navegador no se ejecutó; Chrome existe, pero no se
dispuso de un arnés de interacción local ya configurado. Por honestidad, esto
queda como P1 y no como evidencia positiva.

## Traza de arquitectura e integración

| Superficie | Evidencia real | Alcance |
| --- | --- | --- |
| `symbiont.simulation.engine.run_simulation` | `src/symbiont/simulation/engine.py:322-347` | Cohorte fija; snapshots y evaluación ecológica; sin births/deaths/reproduction ni SLM/cultura/comunicación del runtime modelado |
| Longitudinal ecology | `src/symbiont_lab/studies/longitudinal_population_ecology.py:1-8,104-158` | Long runs bounded y replay; declara explícitamente que canonical y social-runtime no son un organismo integrado |
| Social generations | `src/symbiont_lab/studies/social_runtime_generations.py:32-81` | Birth/death/lineage/social lifecycle separado; no integra SLM privado, claims/composites, grounding o population telemetry |
| `ModeledOrganismRuntime` | `src/symbiont/modeling/runtime.py` | Integra capacidades privadas/culturales/simbólicas en ese runtime, pero el simulador canónico no lo instancia |
| Observatory/telemetry | `src/symbiont/modeling/telemetry.py`, `observatory/` | Exportación factual y pasiva; no crea la integración ausente |

Los tests lo hacen explícito: `tests/integration/studies/test_longitudinal_population_ecology.py:17-20`
afirma `integrated_multigeneration_communication is False`.

### Clasificación crítica

**C — MODULARLY VALIDATED BUT NOT INTEGRATED.**

No se detectó incompatibilidad estructural D, pero tampoco una ruta A/B. La
resolución correcta es proponer un futuro `Integrated Habitat Runtime v1` de
orquestación de APIs existentes, no añadir capacidades durante esta auditoría.

## Hallazgos por severidad

### P0 — FREEZE BLOCKER

**P0-INT-001 — ausencia de ciclo canónico integrado.** La población fija del
simulador principal no reproduce el ciclo de vida dinámico. El estudio de
generaciones es otro protocolo y no ejerce Private SLM, cultura y comunicación
estructurada. Esto impide probar conjuntamente las invariantes que definirían
el sujeto congelado. No se corrigió mediante un planner ni una nueva capacidad.

### P1 — debe resolverse o aceptarse explícitamente antes del freeze

**P1-BOUND-001 — caracterización incompleta del sistema integrado.** Los
ledgers principales tienen límites explícitos (`deque`, caps de asociaciones,
telemetría de 2048 eventos y diarios acotados), y el longitudinal actual valida
finitud/replay. Aun así, no existe evidencia de boundedness/RSS/checkpoint
growth para un ciclo integrado; las etapas 50k/100k están diferidas.

**P1-OBS-001 — falta QA interactiva real.** Las suites existentes cubren
schemas, rendering y servidor, pero no se ejecutó navegación de navegador con
filtros, timeline, datos legacy y truncation. No se declara `visual QA passed`.

**P1-OBS-002 — observer equivalence no es un gate ejecutado.** Hay aislamiento
arquitectónico y tests de pasividad, pero no una comparación explícita del
mismo estado con `telemetry ON` y `telemetry OFF` para demostrar equivalencia
del comportamiento final.

### P2 — limitaciones aceptadas, no blockers científicos por sí mismas

- transporte social local, sin red real ni peer discovery;
- ausencia deliberada de lenguaje abierto, selección cultural y coevolución SLM;
- stages longitudinales 50k/100k no ejecutados por coste, sin ocultar el hecho;
- warning conocido de PyTorch sobre `enable_nested_tensor`/`norm_first`.

### P3 — investigación futura

- `Integrated Habitat Runtime v1` como integración, no expansión cognitiva;
- replicación independiente de fenómenos longitudinales candidatos;
- habitats mayores y estudios de divergencia cultural;
- experimentos posteriores de coevolución, solo tras revisar el freeze.

## Auditoría de fronteras y epistemología

### Organismo frente a laboratorio

La inspección de imports mantiene `symbiont` sin dependencia de
`symbiont_lab`. `truth_label`/`ground_truth` aparecen en superficies del
simulador y evaluator, pero no se pasan a las decisiones cognitivas; el camino
aprobado es `Event.truth_label` hacia `Evaluator.record`. Los módulos de
cultura, símbolos, secuencias y telemetría no reciben etiquetas evaluator-side.

Se buscaron usos de `ground_truth`, `latent`, `target`, `oracle`, `meaning`,
`label`, `utility` y equivalentes. Los usos relevantes quedaron clasificados
como evaluación, entrenamiento ML con targets permitidos o metadatos; no se
encontró una ruta que convierta verdad evaluator-side en decisión cultural o
simbólica.

### Private SLM y adaptación

La arquitectura conserva proposals frente a hechos, registry por organismo,
ownership, hashes, lineage, compatibilidad y adaptación bounded. No se detectó
transferencia de pesos/corpus a descendencia ni autoridad de acción directa.

### Cultura y comunicación

Social claims, roots, anti-copy inflation, contradicción, composites,
reemplazo, retiro, grounding y telemetría mantienen superficies separadas.
La política autónoma recibe estado local y el harness no selecciona IDs de
contenido en los tests de aceptación revisados. No reaparecen slots, roles,
gramática o mapping semántico en el sustrato de comunicación; las secuencias
son variables y opacas.

### Observatory

Observatory consume snapshots/streams y renderiza hechos exportados. No importa
la cognición del organismo ni ofrece una mutación de vuelta. Las vistas de
telemetría distinguen estado de organismo, eventos poblacionales y análisis
evaluator-side; no se encontró que una correlación se presente como meaning
organism-side. La falta de QA de navegador sigue siendo P1 operativo.

## Matriz de herencia

| Estado | ¿Se hereda? | Evidencia/semántica |
| --- | ---: | --- |
| genome/capacidad fisiológica | Sí, con mutación bounded | reproducción y `GenomeCodec` |
| experiencia aprendida | No | estado privado por runtime |
| Private SLM/adapters | No | clone crea registry/corpus nuevos |
| corpus privado | No | ownership y aislamiento |
| social claims/composites | No | transmisión solo por canal cultural |
| symbol/sequence grounding | No | newborn empieza sin ledger aprendido |
| decision history | No | estado adquirido, no genético |
| communication telemetry | No como conocimiento | observación externa; no cognition |

No se encontró un leak severo de `deepcopy`/checkpoint hacia descendencia. Sí
queda pendiente comprobar esta matriz dentro del runtime integrado que hoy no
existe.

## Replay, RNG, tiempo y estabilidad numérica

El longitudinal fijo compara una segunda ejecución con el mismo seed y valida
snapshots/resultados; el probe social comprueba checkpoint/replay de su ledger.
Los contratos de checkpoints conservan los estados RNG de las superficies que
los usan y las pruebas dirigidas pasan. No existe aún replay end-to-end de la
combinación completa porque la combinación no está implementada.

Los checks actuales detectan no-finitud, contadores negativos/excesivos y ticks
no monotónicos. No se observaron anomalías en los runs ejecutados. Esto no
sustituye un stress test integrado.

## Boundedness inventory

| Estructura | Límite observado | Resultado |
| --- | --- | --- |
| ExperienceLedger | `deque(maxlen=...)` | bounded |
| Social/Cultural ledgers | caps y deques | bounded en tests |
| symbol/sequence grounding | `MAX_HISTORY`, `MAX_SEQUENCES` | bounded |
| communication telemetry | 2048 eventos, bytes/age/per-tick | bounded |
| narrative journal | truncado a 50 | bounded |
| modeled sequence decisions | corregido a `deque(maxlen=MAX_HISTORY)` | regression añadida |
| canonical longitudinal snapshots | lista por stage, cap de ticks | bounded por protocolo, no caracterizado en integración |
| integrated population state | inexistente | P0 de integración |

La corrección aplicada en auditoría es exclusivamente de boundedness: el
historial de decisiones de secuencia del runtime modelado ya no crece
indefinidamente y el restore rechaza payloads sobre el límite. No cambia la
política ni el contenido de comunicación.

## Calidad de tests y resultados

La suite actual cubre unit, integración, estudios, replay, schemas,
integridad experimental, telemetría y Observatory. La nueva regresión cubre el
límite y restore del historial de decisiones de secuencia. La suite pasó:

```text
1665 passed, 1 warning in 262.72s
66 passed in final targeted integration/boundary/telemetry battery
git diff --check: clean
```

No se trataron los resultados exploratorios como confirmación científica. Los
negativos/ambiguos históricos de Private SLM y la ausencia de fenómenos
longitudinales confirmados permanecen intactos.

## Correcciones aplicadas

1. `ModeledOrganismRuntime._sequence_decisions` pasó de lista ilimitada a
   `deque(maxlen=MAX_HISTORY)`; restore valida el tamaño.
2. Test de regresión para overflow lógico y checkpoint/restauración.
3. Estado y artefactos de auditoría añadidos; no se modificó `v0.80.16`.

Las modificaciones documentales locales no relacionadas en `docs/` se
preservaron y no forman parte de esta auditoría.

## Pregunta final obligatoria

> If we stop adding organism capabilities today, do we already have a coherent experimental organism worth studying as a stable subject?

**NO**, en el sentido requerido para un freeze integrado. Existe un conjunto
coherente de capacidades modularmente validadas y merece seguir siendo
estudiado, pero aún no existe el runtime canónico que las haga coexistir en un
mismo ciclo vital poblacional. El blocker no se resuelve añadiendo capacidades
lingüísticas o culturales; requiere decidir e implementar posteriormente una
integración de las capacidades ya existentes, con sus propios tests y estudio.

## Recomendación

Mantener `NOT READY FOR FREEZE`. El siguiente trabajo debe limitarse al diseño
y, tras revisión, implementación de `Integrated Habitat Runtime v1` como capa
de orquestación de capacidades existentes. Después repetir esta auditoría,
incluyendo boundedness, replay end-to-end, observer equivalence y QA de
navegador. No crear todavía tag de `Experimental Organism v1`.
