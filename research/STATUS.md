# Estado de investigación

Corte de referencia publicado: `v0.80.16` (tag intacto). Estado de `main`:
trabajo posterior al corte; el tag histórico no se modifica. La auditoría final
v2 recomienda congelar el sustrato del organismo.

Biological Closure v1, Private SLM v1, Cultural Foundation v1, Cumulative
Culture v1 y Autonomous Cultural Agency v1 permanecen cerrados en sus
alcances declarados.

El trabajo posterior de `Longitudinal Population Ecology v1` es una campaña de
discovery y no modifica el corte ni reabre gates históricos.

Este registro clasifica el estado de la evidencia; no sustituye al roadmap ni
convierte un resultado exploratorio en una afirmación de capacidad.

## Adaptive Sensory System v1 — Sensory Plasticity v1 cerrada; Sensory Modalities v1 abierta

Esta línea es una extensión experimental posterior al freeze
`experimental-organism-v1`; no modifica el tag histórico ni reinterpreta sus
resultados. El cambio separa explícitamente fuente externa, identidad de señal,
sensor organismo-owned, percepto y entrada cognitiva.

Estado de implementación en `main`:

- `symbiont.sensory` introduce modalidades opacas heterogéneas, sensores con
  identidad estable, lineage, health/confidence/utility/redundancy/coste,
  transducción bounded, duplicación, adaptación paramétrica, pruning y
  exploración multisource;
- el runtime separa selección de fuentes de atención perceptiva y mantiene los
  aliases humanos fuera del camino cognitivo adaptativo;
- `SignalKnowledge` continúa describiendo señales externas; el fenotipo
  sensorial se mantiene como estado del organismo y se proyecta en
  `BodySchema`/Observatory sin crear un canal de control;
- checkpoint host v8 persiste el fenotipo sensorial y la genealogía de
  mutaciones, pero no valores crudos ni memoria temporal privada; los sensores
  temporales marcan explícitamente el primer output post-restore como
  `cold_start`;
- la capacidad sensorial cruza el nacimiento clonal, pero los sensores
  adquiridos no se heredan;
- el fingerprint constitucional pasa a schema v5 para incluir límites,
  modalidades y capacidad de plasticidad sin incluir trayectoria aprendida.

Los ocho protocolos originales `perception.*` ya fueron ejecutados y
registrados. Tras el resultado multisource negativo frente a frozen se añaden
cuatro protocolos preregistrados de selección autónoma, elevando la línea a 12
protocolos declarados.

**Primeros tres gates empíricos ejecutados el 2026-09-18: positivos en
las seeds 101/127/149.**

1. `perception.identity-equivalence`: equivalencia exacta en las tres seeds,
   con `max_absolute_error = 0.0` y un único identity sensor.
2. `perception.adaptive-delta-discovery`: el receptor `modality.alpha`
   reduce el MAE frente a identity de `3.6352 -> 0.0171`, `2.9957 -> 0.0151`
   y `1.7587 -> 0.0183`; `all_improved = true`.
3. `perception.temporal-scale-specialisation`: alpha ocupa consistentemente
   el nicho rápido y beta el lento. Los gains fast son
   `+0.4637/+0.4790/+0.4816` y los gains slow
   `+0.4370/+0.4557/+0.4587`; `all_niches_distinct = true`.

Interpretación acotada: estos resultados demuestran que el sustrato sensorial
puede conservar el camino legacy y expresar transformaciones perceptivas
funcionalmente distintas y útiles. **No demuestran todavía selección autónoma
de la transformación correcta**: las modalidades ya delimitan familias de
operadores distintas y la exploración inicial es determinista.

**Cinco gates restantes ejecutados el 2026-09-18:**

- `perception.modality-specialisation`: positivo como caracterización de
  sustratos; fast/slow/distributed aparecen en las tres seeds. Sin embargo,
  `gamma` obtiene MAE `0.0` porque su operador `MIX` coincide exactamente
  con el target evaluator-side `(x+y)/2`; por tanto el resultado distribuido
  no demuestra adaptación ni selección.
- `perception.sensory-duplication-divergence`: positivo en boundedness y
  divergencia estructural; dos variantes (`alpha/difference` y
  `beta/integrate`), lineage explícita y máximo de una mutación por ventana
  frente a budget 4 en las tres seeds.
- `perception.sensory-ablation`: positivo en causalidad dentro del protocolo.
  La ablación del receptor especializado incrementa fuertemente el MAE en las
  tres seeds y `all_support_causal_role = true`.
- `perception.multisource-specialisation`: **negativo frente al control
  frozen**. El adaptativo supera single-source, pero empata exactamente con el
  multisource frozen: MAE `0.0` vs `0.0`, `gain_vs_frozen = 0.0`,
  `all_beat_frozen = false`.
- `perception.same-world-phenotype-divergence`: resultado válido de
  **convergencia total**: `unique_phenotypes = 1` en las tres seeds,
  `converged_runs = 3`, `diverged_runs = 0`.

Conclusión provisional: el sustrato sensorial v1 está técnicamente validado,
bounded y causalmente funcional, pero **Sensory Plasticity v1 y Sensory
Modalities v1 no se cierran todavía como adaptación autónoma**. Los protocolos
actuales demuestran capacidad de representación y especialización funcional de
operadores diseñados, no que el organismo seleccione o descubra por sí mismo
una transformación mejor que controles estructuralmente equivalentes. El gate
multisource frozen falla explícitamente y se conserva como resultado negativo.

### Fase preregistrada: selección sensorial autónoma

Se implementa un selector organism-side bounded basado en relaciones predictivas
lag-1 entre perceptos. Cada receptor compite contra el mejor baseline trivial
local — media o persistencia — y solo el exceso predictivo estable puede
convertirse en `selection_credit`, utilidad y prioridad perceptiva. La evidencia
usa olvido exponencial bounded para poder cambiar tras un cambio de régimen y
no persiste valores crudos del tick anterior.

Antes de observar resultados se preregistran:

- `perception.autonomous-sensory-selection`;
- `perception.sensory-regime-reversal`;
- `perception.sensory-null-selection`;
- `perception.experience-conditioned-phenotype`.

DAGs arbitrarios y evolución heredable de modalidades continúan cerrados.

**Cierre científico acotado — Sensory Plasticity v1.**

Los protocolos 09–12 fueron ejecutados el 2026-09-18 sobre el código validado
técnicamente:

- `autonomous-sensory-selection`: el selector organism-side eligió
  `difference` en las tres seeds y coincidió con el mejor receptor
  evaluator-side en 3/3; superó random en 3/3. Frente al frozen ganó 2/3 y
  empató en seed 127 porque el frozen había quedado preregistrado precisamente
  en `difference`, el mejor receptor de esa seed;
- `sensory-regime-reversal`: 3/3 cambiaron de `difference` a `integrate`
  sin feedback evaluator-side, con delays 89, 75 y 108 ticks;
- `sensory-null-selection`: 3/3 rechazaron falsa especialización, con
  `max_selection_credit = 0.0`;
- `experience-conditioned-phenotype`: resultado de caracterización
  convergente; 18/18 organismos prefirieron `integrate` y no apareció
  divergencia ontogenética bajo el nivel de micro-ruido preregistrado.

Con los gates previos de equivalencia, causalidad, boundedness, replay,
Observatory pasivo y ausencia de semántica humana, **Sensory Plasticity v1 queda
cerrada en el alcance declarado**: un Symbiont puede evaluar receptores desde
evidencia local, seleccionar el funcionalmente útil dentro del conjunto
disponible, retirar crédito cuando deja de ser útil y cambiar de preferencia
cuando cambia el régimen, sin target del evaluador.

Este cierre **no cierra Sensory Modalities v1** ni demuestra sentidos
open-ended. `alpha/beta/gamma` siguen siendo familias estructurales diseñadas
sobre entradas escalares. La convergencia completa del protocolo 12 refuerza
que todavía no hay evidencia de ontogenias perceptivas alternativas bajo el
mismo sustrato.

La mutación estructural general de DAGs de transducción y la evolución heredable
de nuevas modalidades permanecen cerradas.

### Emergent Sensory Modalities v1 — diseño propuesto, no implementado

La siguiente frontera queda definida en [`../docs/design/emergent-sensory-modalities-v1.md`](../docs/design/emergent-sensory-modalities-v1.md). El diseño elimina `alpha/beta/gamma` como clases constitucionales de desarrollo: todos los receptores compartirán un kernel común de primitivas bounded y “modalidad” será una propiedad derivada evaluator-side del fenotipo receptor, nunca una respuesta suministrada al organismo.

La migración se abre por etapas: compatibilidad escalar, `ReceptorProgram`, retirada de restricciones por modalidad, mutación estructural bounded y solo después geometría vectorial. Event/sequence/field, ciclos, invención de primitivas e herencia de programas adquiridos permanecen cerrados.

No existe todavía implementación de `ReceptorProgram`, geometría vectorial ni
resultados M01–M08. Sin embargo, Observatory ya incorpora la infraestructura
visual de esta frontera: una perspectiva `Sensory Map` separa señales del
mundo, receptores organismo-owned y destino cognitivo, muestra las clases
`alpha/beta/gamma` únicamente como sustrato actual predeclarado y reserva las
modalidades derivadas para la futura evidencia M07. La proyección sigue siendo
pasiva y replay-safe.

Los gates M01–M08 quedan definidos antes de cualquier ejecución.

**Validación dirigida de Observatory/Sensory Map ejecutada el 2026-09-18:**

- `276 passed in 11.36s`;
- cubre sensory phenotype, snapshot/replay, state-flow, pasividad y nueva
  perspectiva `Sensory Map`;
- `git diff --check`: limpio.

La suite completa del repositorio sigue pendiente antes de considerar cerrada
esta ampliación visual.

**Validación técnica local previa a la fase de selección autónoma, ejecutada el 2026-09-18:**

- batería dirigida de regresiones reparadas:
  `59 passed in 3.61s`;
- suite completa:
  `1748 passed, 2 warnings in 224.11s`;
- `git diff --check`: limpio;
- GitHub Actions se mantiene fuera por billing.

La fase nueva de selección autónoma modifica `symbiont.sensory`, runtime,
fingerprint, Observatory y protocolos experimentales; por tanto requiere una
**nueva ejecución local de regresión y suite completa** antes de considerar
cerrado su gate técnico. Los resultados `1748 passed` anteriores no se
reutilizan como validación de este nuevo código.

**Regresión dirigida de la fase de selección autónoma ejecutada el 2026-09-18:**

- `369 passed in 16.00s`;
- incluye sensory selection/system, protocolos autónomos, fingerprint/runtime,
  frontera ground-truth y Observatory;
- `git diff --check`: limpio.

Este resultado cierra el gate dirigido.

**Suite completa de la fase de selección autónoma ejecutada el 2026-09-18:**

- `1762 passed, 2 warnings in 227.07s`;
- `git diff --check`: limpio;
- los warnings son los mismos dos no bloqueantes ya conocidos
  (`multiprocessing.popen_fork` y PyTorch nested tensors).

El gate técnico completo de esta fase queda cerrado. Los protocolos 09–12 se
ejecutaron a continuación sobre este código; su interpretación científica depende
exclusivamente de los artefactos reales generados en `.symbiont/runs/`.

Los dos warnings son no bloqueantes y preexistentes en áreas ajenas al nuevo
aparato sensorial: `multiprocessing.popen_fork` advierte sobre `fork()` en un
proceso multithread, y PyTorch avisa de la configuración de nested tensors en
`TransformerEncoder`. Ninguno produjo fallo de test.

## Final Adversarial Audit v2 — READY_FOR_FREEZE

La auditoría integral original identificó `P0-INT-001`: clase **C —
modularmente validada pero no integrada**. `IntegratedHabitatRuntime` intenta
resolver únicamente ese P0 mediante una ruta canónica que conserva las APIs y
políticas existentes. La reauditoría v2 confirma la resolución.

- La nueva ruta integrada es clase **A — INTEGRATED** en el sentido
  arquitectónico y de smoke técnico: el mismo habitat ejerce población,
  fisiología, aprendizaje, estado de Private SLM, cultura, grounding,
  comunicación y telemetría; el probe de lifecycle solo activa APIs existentes.
- La boundedness integrada pasa en 1.000 y 10.000 ticks dentro de los límites
  declarados; el run de 10.000 ticks es seed `101` y no se extrapola a todas las
  semillas.
- La QA interactiva real de Observatory con Chrome local es `PASS`, incluyendo
  vistas, filtros, estados legacy/truncados y viewport estrecho.
- No se encontraron P0 ni P1 materiales. Con la aprobación formal del owner,
  el contrato de freeze queda vigente en el corte etiquetado
  `experimental-organism-v1`.

El campo `audited_head` del readiness JSON identifica el último commit de
código auditado (`eafb85e`); la documentación posterior del freeze no cambia
ese alcance.

Evidencia y metodología originales: [`2026-09-final-experimental-organism-v1.md`](audits/current/experimental-organism-v1/initial.md).
La nueva evidencia está en [`2026-09-integrated-habitat-runtime-v1.md`](audits/current/integrated-habitat-runtime-v1.md)
y en `experiments/integration/integrated-habitat-runtime/results.json`.
La batería dirigida actual del runtime integrado y Observatory pasa (`15
passed`); la suite completa pasa con `1676 passed, 1 warning` y `git diff
--check` está limpio.
No se añadieron
capacidades cognitivas, culturales, sociales o lingüísticas: las correcciones
son de orquestación, determinismo de nacimiento/checkpoint y aislamiento del
lifecycle del descendiente.

## Integrated Habitat Runtime v1 — implementado y validado técnicamente

El entrypoint canónico `symbiont_lab.integration.IntegratedHabitatRuntime`
mantiene población bounded, identidad/genealogía, lifecycle, habitat social,
canales autorizados, ledgers privados por organismo, checkpoint de fin de tick
y telemetría outbound-only. El orden de tick y los límites están documentados
en [`../docs/design/integrated-habitat-runtime-v1.md`](../docs/design/integrated-habitat-runtime-v1.md).

El smoke `integration.integrated-habitat-runtime` cubre seeds `101, 127, 149`:
cada seed ejerció un nacimiento, una muerte, comunicación, grounding,
restauración, replay y comparación `telemetry ON/OFF`, todos `PASS`. La prueba
de boundedness ejecutada cubre 1.000 ticks y la prueba de duración extendida
cubre 10.000 ticks en seed `101`; no se extrapola ese último resultado a las
otras semillas. En 10.000 ticks el historial quedó en 256 entradas, la
telemetría en 2.048 eventos y el checkpoint en aproximadamente 1,87 MB.

El canal de secuencias usa una ventana de entregas por tick bounded; la
telemetría conserva su propio techo histórico. Esto resuelve un agotamiento
accidental del contador de transporte en runs largos sin hacer ilimitada la
comunicación. El resultado demuestra integración técnica, no reproducción
espontánea, ecología multigeneracional ni cierre del organismo.

## Implementado y validado

- Contratos y límites históricos de `symbiont` y Observatory cubiertos por sus
  suites de pruebas correspondientes al último corte ejecutado antes de abrir
  Private SLM.
- Estudios de aceptación de conocimiento de señales: límites del kernel,
  proyección acotada y separación organismo/evaluador verificadas en la partición
  sintética descrita en [`signal-knowledge-study.md`](studies/cognition/signal-knowledge/README.md).
- Auditorías históricas v0.13–v0.24 reproducibles desde sus commits congelados,
  con procedencia y restricciones documentadas individualmente.
- **Biological Closure v1**: cerrados los tres gates finales en el alcance
  predeclarado y reproducible:
  1. interocepción con reducción longitudinal de intervenciones en cohortes
     experimentada vs. naïve con la misma superficie interoceptiva;
  2. diferenciación ecológica replay-safe con múltiples firmas de adquisición
     tardías independientes de identidad en semillas 7, 11 y 19;
  3. diferencial adaptativo heredable condicionado por presión ambiental para
     el locus bounded `behavior_exploration`, conservado por descendencia clonal.
  Estos resultados no afirman generalidad universal; cierran la base biológica
  v1 necesaria para abrir la siguiente línea experimental.

- **Private SLM v1 — cerrado científicamente en el alcance declarado**.
  Sustrato implementado según
  [`../docs/design/futuro-cultural.md`](../docs/design/futuro-cultural.md):
  - ledger privado y bounded de experiencia abstracta por organismo;
  - captura automática de vida sin raw telemetry ni `runtime_events` del evaluador;
  - estados epistemológicos y procedencia explícita;
  - corpus temporal train/validation/test con deduplicación y aislamiento por organismo;
  - exclusión estructural de predicciones de modelo salvo confirmación independiente;
  - tokenizer nativo determinista, sin lenguaje ni embeddings preentrenados;
  - autoridad externa con ceilings de parámetros/contexto/ejemplos/epochs/steps/bytes;
  - GRU causal y Transformer causal aleatoriamente inicializados;
  - entrenamiento PyTorch opcional en `symbiont_lab`, nunca dentro del runtime;
  - artifact store atómico/content-addressed y manifests ligados a corpus/tokenizer;
  - evaluación held-out restringida a outcomes, no a la gramática fija del registro;
  - lifecycle `CANDIDATE -> SHADOW -> ACTIVE -> DEGRADED/RETIRED`;
  - activación solo tras autorización de promoción independiente;
  - inferencia tipada sin escritura directa de hechos ni acciones;
  - validación automática contra outcomes vividos;
  - checkpoint de ledger/registro sin pesos y cold-start del gateway al restaurar;
  - descendencia clonal conserva capacidad de modelado pero no corpus ni modelos adquiridos;
  - adaptación incremental separada de cold start con continuidad real de pesos,
    ownership/arquitectura/tokenizer/contexto/integridad validados y lineage completa;
  - el padre permanece activo hasta promoción independiente del successor;
  - Observatory expone solo estado, lineage y resumen pasivo, nunca pesos.

  **Validación técnica local ejecutada el 2026-09-17**:
  - suite completa: `1551 passed` fuera del sandbox restringido;
  - batería específica de adaptación: `5 passed`;
  - regresión posterior del guard de runtime: `12 passed`;
  - `git diff --check` limpio y workspace limpio.

  **Gate A — utilidad held-out: positivo** (`learning.private-model-utility`, seeds 101/127/149, 128 ticks):
  - GRU: ganancia media sobre mejor baseline trivial `+0.049437`, 2/3 promociones;
  - Transformer: ganancia media `+0.080261`, 2/3 promociones;
  - Transformer vs. GRU: ganancia media `+0.030824`;
  - no se reajustaron hiperparámetros tras observar el resultado.

  **Gate B — especificidad individual: positivo según criterio preregistrado, efecto débil/heterogéneo**:
  - margen medio `+0.002465` nats;
  - seed 101 `-0.064455`, seed 127 `+0.003251`, seed 149 `+0.068600`.

  **Gate C — remapeo opaco: positivo fuerte**:
  - disrupción stale media `+3.132914` nats;
  - gap medio tras reentrenamiento `-0.003140` nats respecto al rendimiento original.

  **Gate D-v1 — cambio de régimen asimétrico: negativo**:
  - degradación stale media `-0.004362` nats;
  - recuperación media `+0.031878` nats.
  Se conserva como resultado negativo/ambiguo por posible diferencia de dificultad entre regímenes.

  **Gate D-v2 — cambio de régimen simétrico: no supera el criterio completo** (`learning.private-model-regime-symmetric`):
  - `mean_stale_degradation = +0.0276356`;
  - `mean_recovery = -0.00118335`;
  - `mean_recovered_vs_pre_gap = +0.028819`.
  El modelo stale detecta el drift en promedio, pero un fresh model desde cero no recupera de forma consistente frente al stale. Este resultado no se reinterpreta como positivo.

  **Adaptación incremental — positiva en estudio nuevo preregistrado** (`learning.private-model-adaptation`, seeds 101/127/149):
  - `mean_stale_degradation = +0.0276356`;
  - `mean_fresh_recovery = -0.00118335`;
  - `mean_adapted_recovery = +0.0868168`;
  - `mean_adapted_vs_stale = +0.0868168`;
  - `mean_adapted_vs_fresh = +0.0880002`;
  - lineage válida `3/3`;
  - coste medio `44` pasos, dentro de ceilings.
  El successor adaptado mejora frente al stale en las tres semillas y supera al control fresh en este protocolo. Esto cierra la capacidad de adaptación incremental bounded en el alcance preregistrado, sin convertir D-v1 ni D-v2 en positivos.

## Implementado con validación parcial histórica

- Capacidades de fisiología, herencia y ecología de `v0.60–v0.76`: el contrato y
  las pruebas del repositorio están implementados; la evidencia científica no
  equivale a una caracterización exhaustiva de todos los regímenes.
- Milestones I–K: sus contratos y gates de Biological Closure v1 están cubiertos
  en los alcances documentados. Permanecen abiertas preguntas de generalización
  más amplia, pero ya no bloquean la siguiente etapa experimental.
- Observatory: la suite histórica de contratos e integración pasa, pero no
  constituye QA visual exhaustivo ni medición de RSS en producción.
- Intercambio ecológico: transporte local en memoria validado; sockets, red y
  descubrimiento de pares siguen fuera de alcance.

## Cultural Foundation v1 — cerrada en el alcance de transporte local autorizado

La implementación nueva está descrita en
[`../docs/design/futuro-cultural.md`](../docs/design/futuro-cultural.md).
Mantiene el Private SLM privado y no transfiere pesos, adapters, corpus ni
telemetría. El runtime conserva claims en un `SocialEvidenceLedger` separado;
`SocialChannel` es únicamente transporte en memoria permitido por el
laboratorio, sin sockets ni descubrimiento de peers.

**Validación técnica local:** la validación cultural final del corte anterior
registró `1561 passed, 1 warning`; la batería posterior registró `26 passed` y
`git diff --check` limpio. El warning es el conocido de PyTorch sobre nested
tensors en `TransformerEncoder`.

**Estudio preregistrado:** `learning.cultural-foundation`, seeds `101, 127,
149`, 64 ticks. Resultado por seed: C1 faithful transmission, C2 anti-copy
inflation, C3 independent corroboration, C4 contradiction, C5 social utility,
C6 rumor control y C7 tradition pasan en las tres semillas; replay determinista
`3/3`. La fan-out produjo `10` holders y `10` copies con exactamente `1`
independent root. La comparación de utilidad del protocolo tuvo `4` ticks y
coste `3` con claim social frente a `12` ticks y coste `12` en el protocolo
solitario.

Este cierre es **operacional y acotado al mecanismo de claims y al transporte
autorizado**. C5 no demuestra todavía que una política autónoma de compartir
haya emergido: el laboratorio controla la entrega y la selección de claims no
está hardcodeada como cooperación. Tampoco demuestra cultura acumulativa,
lenguaje, consenso o transferencia de modelos. Esas preguntas quedan fuera de
esta fase y Cumulative Culture v1 se cerró posteriormente en su propio alcance
preregistrado; este resultado histórico no se reinterpreta.

## Registro histórico de la siguiente frontera — cultura acumulativa

En el corte en que se redactó esta sección, el siguiente programa podía
diseñarse sobre la secuencia:

`conocimiento individual validado -> transmisión social con procedencia -> persistencia entre individuos -> tradición -> cultura acumulativa`.

Debe conservar como invariantes:

- una copia de una claim no cuenta como nueva evidencia independiente;
- procedencia y genealogía cultural explícitas;
- separación entre observación propia, inferencia propia y conocimiento recibido;
- posibilidad de contradicción, olvido, mutación y retirada de claims transmitidas;
- ninguna transferencia directa de pesos/modelos/corpus en la primera fase cultural;
- ausencia de pretrained human knowledge en la línea científica base;
- Observatory permanece pasivo.

## Cumulative Culture v1 — cerrada en el alcance preregistrado

La implementación está descrita en
[`../docs/design/futuro-cultural.md`](../docs/design/futuro-cultural.md)
y añade composites culturales versionados sobre el DAG social existente. El
composite conserva claims componentes, padres, contributors, roots, generación,
reemplazo y retirada. No crea evidencia, no transfiere pesos/modelos/corpus y
la descendencia empieza con un ledger cultural vacío.

**Estudio preregistrado:** `learning.cumulative-culture`, seeds `101, 127, 149`,
128 ticks. CC1–CC8 y replay pasaron en las tres semillas. La secuencia fue
`X -> X+Y -> X+Y+Z`, con generaciones `0, 1, 2`, tres contributors, tres
independent roots, cobertura inicial máxima de un componente por fundador y
cuatro componentes después de la extensión del recién nacido. El error de un
componente permaneció en la genealogía y fue reemplazado en una versión nueva;
la retirada dejó el estado actual sin composite activo.

**Cierre científico acotado:** existe evidencia reproducible de composición
causal multi-contributor, utilidad operacional super-individual en el control
de transmisión atómica, persistencia intergeneracional, degradación,
corrección trazable y replay determinista. La selección de claims, composición
y transporte fue controlada por el arnés para aislar el mecanismo; esto no
demuestra todavía cooperación autónoma, símbolos, lenguaje, selección cultural
ni coevolución con Private SLM.

## Validación local del corte actual

La batería específica de Cumulative Culture registró `7 passed`; la batería
combinada de Cumulative Culture, Cultural Foundation y Observatory registró
`34 passed`. La batería específica de agencia, junto con las regresiones
culturales y Observatory, registró `30 passed`. La suite local completa,
excluyendo el worktree auxiliar `.claude/worktrees` para evitar colisiones de
módulos de pytest, registró `1574 passed, 1 warning` en 4:22; el warning es el
conocido de PyTorch sobre nested tensors en `TransformerEncoder`. La ejecución
literal `pytest -q` no pudo recolectar por esos módulos duplicados del worktree
auxiliar; no es un fallo funcional del código principal. `git diff --check`
queda limpio en la validación final.
GitHub Actions queda fuera por la incidencia de billing.

## Autonomous Cultural Agency v1 — cerrada en el alcance preregistrado

La implementación está descrita en
[`../docs/design/autonomous-cultural-agency-v1.md`](../docs/design/autonomous-cultural-agency-v1.md).
`CulturalPolicy` vive en `symbiont.modeling`, selecciona acciones sobre estado
local bounded y registra `CulturalDecisionRecord`; el tratamiento autónomo
recibe únicamente vecinos/topología, ticks y presupuestos. No recibe IDs de
claims/composites, labels de utilidad, ground truth ni un receptor impuesto.
La política no introduce loci culturales hereditarios en v1: los descendientes
conservan capacidad de decisión pero no ledger ni historial adquirido.

**Preregistro:** `learning.autonomous-cultural-agency`, seeds `101, 127, 149`,
24 ticks y 8 rondas de contacto. Se comparan no-culture, el benchmark histórico
dirigido y la política autónoma; el benchmark dirigido no se modifica.

**Resultado científico:** ACA1–ACA10 y replay pasan en las tres semillas. La
política produjo silencio, transmisión, validación, retención, descarte y
composición; las oportunidades superaron las transmisiones, aparecieron
composites multi-contributor y la condición autónoma resolvió la tarea
operacional mientras no-culture no la resolvió. Los costes permanecieron bajo
los ceilings preregistrados.

**Caveat de autonomía:** la política es un baseline explícito y la topología,
las ventanas y las superficies de experiencia siguen siendo del laboratorio.
El resultado elimina la selección evaluator-side de contenido del tratamiento;
no demuestra cooperación general ni abre lenguaje, símbolos, prestigio,
selección cultural o coevolución con Private SLM.

## Emergent Symbol Grounding v1 — cerrada en alcance preregistrado

Esta línea comienza después del corte congelado `v0.80.16` y no modifica ese
tag. Se añadió un espacio bounded de identificadores opacos, emisión local
organismo-side, `SymbolGroundingLedger`, transporte en memoria autorizado,
costes, límites, checkpoint/replay y aislamiento de descendencia. Observatory
expone únicamente IDs, contadores y fuerza local; no traduce símbolos a
significados humanos.

El preregistro `learning.emergent-symbol-grounding` fija las semillas `101,
127, 149` y compara `none`, `random`, `autonomous` y `permuted`. La auditoría
estática prohíbe tablas de significado, selección evaluator-side y truth oracle.
La batería preregistrada pasó ESG1–ESG10 y replay en `101, 127, 149`. La señal
autónoma emitió 42–43 veces y usó dos símbolos opacos por semilla; el receptor
registró dos asociaciones, con `prediction_gain` de `0.125`, `0.3125` y
`0.4375`, siempre por encima de `random_signal_gain` (`-0.1875`, `0.0`,
`-0.1875`) y de no-signal. La condición permutada conservó utilidad, la
retransmisión permitió adquisición newborn en 1–2 ticks y replay fue idéntico.
Los resultados completos están en `experiments/learning/emergent-symbol-grounding/results.json`.

**Interpretación acotada:** existe evidencia reproducible de una convención
simbólica opaca con grounding funcional y transmisión cultural en este protocolo.
No demuestra lenguaje, gramática, semántica humana ni negociación general. La
política emisora sigue siendo un baseline determinista local seeded; la
topología y las ventanas siguen siendo del laboratorio.

## Emergent Structured Communication v1 — cerrada en alcance funcional

El diseño prescriptivo de Proto-language v1 fue auditado y sustituido antes de
la ejecución final. Se conserva solo un canal genérico de símbolos opacos y
secuencias variables bounded, con grounding local exacto, costes, límites,
olvido, replay y aislamiento de descendencia. No hay slots, roles, gramática,
mapping semántico, holdout objetivo ni recompensa por composicionalidad.

El preregistro `learning.emergent-structured-communication` fija seeds `101,
127, 149` y compara no-signal, random-signal y canal autónomo. La estructura
comunicativa y cualquier productividad se analizarán evaluator-side después
del run; no se declarará lenguaje por la mera existencia de secuencias.

**Validación científica local ejecutada el 2026-09-17:** el canal autónomo
emitió `35/27/30` mensajes y mantuvo `13/21/18` silencios en las semillas
`101/127/149`; usó cuatro secuencias distintas por semilla y obtuvo ganancias
de predicción `0.6667/0.6667/0.6250`, superiores a random (`-0.0725/-0.0290/
0.1065`) y a no-signal en el protocolo preregistrado. La permutación, la
transmisión cultural, la adquisición newborn, la procedencia y el replay fueron
positivos en las tres semillas. La auditoría no encontró planner de contenido,
roles, slots, mapping semántico ni truth oracle.

El cierre es únicamente **functional emergent structured communication** en
este alcance. El clasificador evaluator-side no demuestra productividad
composicional ni proto-language; esas preguntas quedan abiertas para una fase
posterior con nuevo preregistro.

## Structured Communication Characterization v1 — caracterizada sin nueva capacidad lingüística

Esta línea no rediseña el canal. Audita y utiliza el sustrato genérico ya
cerrado bajo el principio literal: **Give Symbionts capabilities and
constraints, not linguistic answers.** La matriz preregistrada
`learning.structured-communication-characterization` compara no-signal,
random-signal, canal autónomo y presiones de complejidad, vocabulario, longitud
y coste con seeds `101, 127, 149`. No se proporcionan slots, roles, gramática,
composición, mappings semánticos ni rewards lingüísticos.

El resultado completo está en
`experiments/learning/structured-communication-characterization/results.json`:
27 filas por seed/condición. El canal autónomo produjo decisiones de silencio y
emisión no triviales, reutilización de mensajes opacos y ganancias de
predicción positivas en este protocolo; replay fue determinista en todas las
filas. La clasificación conservadora fue `no_functional_code` para los tres
controles no-signal y una fila random, y `functional_partially_structured_code`
para las restantes. Esto es caracterización descriptiva, no una nueva prueba
de composicionalidad, productividad, lenguaje o gramática.

La auditoría adversaria
`research/audits/2026-09-structured-communication-characterization-v1.md`
no encontró scaffolding lingüístico ni leakage en la ruta del estudio. La
vista pasiva `Communication Live` expone contadores, decisiones, IDs opacos,
grounding local y coste; no inventa un grafo poblacional ni mezcla métricas
evaluator-side con el estado del organismo. La suite específica pasó antes de
la validación completa; el resultado técnico final debe conservar la
distinción entre implementación, validación local y evidencia científica.

## Population Communication Telemetry v1 — implementada y validada técnicamente

Esta fase añade únicamente una fuente factual, bounded y outbound-only de
telemetría poblacional. `CommunicationEvent` y `GroundingEvent` se exportan
desde operaciones reales del canal y se mantienen separados del estado
epistemológico del organismo y de los análisis evaluator-side. Observatory
agrega eventos sin inventar aristas, conserva metadatos de truncamiento y
expone Communication Live, grafo poblacional, Convention Explorer y una línea
temporal derivada de los eventos disponibles.

El estudio técnico `observability.population-communication` reconstruye el
camino controlado `A → B → C → D`, además de retransmisión, grounding, restore
y truncamiento. No es evidencia de una capacidad cognitiva nueva. La batería
específica pasa (`24 passed`), la suite completa pasa (`1637 passed, 1 warning`)
y `git diff --check` está limpio. La superficie estática local respondió por
HTTP y cargó el panel, el renderer y el stylesheet; no se ejecutó una sesión
interactiva de navegador, por lo que la QA visual completa queda como límite
de validación, no como evidencia científica.

## Longitudinal Population Ecology v1 — discovery técnico ejecutado

La campaña `learning.longitudinal-population-ecology` ejecuta stages bounded de
larga duración sobre el simulador canónico y usa, en un bloque separado, el
protocolo social-runtime existente para comprobar ciclos multigeneracionales.
No añade capacidades cognitivas, culturales, sociales o lingüísticas; tampoco
presenta como integración única los subsistemas que el repositorio mantiene
separados. Los fenómenos candidatos se registran en
`research/longitudinal/candidate-phenomena.json` con estados explícitos y no se
confirman con el mismo dataset de discovery. El run actual cubrió seis
combinaciones stage/seed (`1,000` y `10,000` ticks; seeds `101, 127, 149`):
finitud, ceilings y replay pasaron en todas, sin anomalías. El probe separado
de lifecycle cubrió ocho generaciones con lineage y replay válidos. No se
declara un fenómeno científico confirmado y los stages de `50,000` y `100,000`
siguen diferidos por el resource envelope preregistrado.

## Independent-Seed Symbol Grounding v1 — discovery, resultado negativo

La campaña `learning.independent-symbol-grounding` responde a la crítica de
que `emergent_symbol_grounding.py` daba el mismo `symbol_policy_seed` a los
dos emisores, por lo que la convergencia observada allí venía de la función
hash compartida, no de interacción. Este estudio da a cada emisor un seed
independiente sobre el mismo espacio de 32 símbolos (chance ≈ 1/32 por
sondeo), mide `agreement` antes y después de rondas de interacción con
refuerzo tipo naming-game, y corre gemelos de control `isolated`/`shuffled`
sin vínculo causal posible. Preregistro en `experiment.toml`, sin ajuste
posterior. Resultado: `isg1`/`isg4` **fallaron** en las 3 seeds (101/127/149)
— el agreement post-interacción se quedó en o cerca de chance; los controles
`isg2`/`isg3` se mantuvieron en chance como se esperaba, y `replay` fue
determinista. Se reporta como hallazgo negativo, evidencia a favor de H0 para
este mecanismo de symbol grounding, sin reajustar el mecanismo tras ver el
resultado. Detalle en
[`audits/current/2026-09-refutation-response-protocol-v1.md`](audits/current/2026-09-refutation-response-protocol-v1.md).

## Predictive Structure Discovery v1 — discovery, resultado positivo

La campaña `learning.predictive-discovery` responde a la crítica de que
`predictive_utility.py` precablea el nodo `PREDICTOR`, `predicts_node_id` y el
signo de la edge, sin dejar estructura por descubrir. Este estudio expone
varias señales candidatas de escala equivalente (una genuinamente predictiva,
tres señuelos: independiente, autocorrelacionada sin relación, antifase) sin
`PREDICTOR` ni `predicts_node_id` preexistente, usa la maquinaria ya presente
pero no ejercida por otros estudios (`ShadowPrediction` /
`promote_shadow_prediction` vía `auto_promote_predictors`) para que el
organismo descubra y promueva su propio predictor, y evalúa la ganancia sobre
seeds de evaluación nunca usados en la fase de desarrollo. Preregistro en
`experiment.toml`. Resultado: todos los gates (`pd1`-`pd5`, `replay`) pasaron
en los 3 pares de seeds desarrollo/evaluación — la fuente verdadera se
promovió siempre, ningún señuelo alcanzó promoción, y la ganancia se sostuvo
en holdout. El spike previo (`B.0`) encontró que `promote_shadow_prediction`
no cablea automáticamente una edge de entrada al nodo promovido — se
documenta como límite arquitectónico real, no se parchea. Detalle en
[`audits/current/2026-09-refutation-response-protocol-v1.md`](audits/current/2026-09-refutation-response-protocol-v1.md).

## Reversible-Pressure Selection v1 — discovery, resultado negativo

La campaña `autonomous-life.reversible-selection` responde al punto #3 de la
misma crítica: cada estudio Genesis previo funda su población con un único
genoma idéntico, así que ninguna evidencia previa prueba selección sobre
variación permanente — solo que un parámetro fijo cambia resultados. Este
estudio funda una población con alelos `behavior_exploration` genuinamente
mixtos (mitad `0.0`, mitad `0.1`, declarados como locus heredable real), la
corre bajo `regimes=("scarcity", "abundance", "scarcity")` — presión aplica,
se revierte, y se revierte otra vez a la original —, y mide la media
poblacional del alelo en cada frontera de régimen. Ejecución paralela por
seed nueva en el repositorio (`ProcessPoolExecutor`, ninguna infraestructura
de este tipo existía antes de esta campaña). Preregistro en `experiment.toml`
con 200 seeds, sin ajuste posterior. Resultado: `rs1` **falló**
(`mixed_reversals=44/200`, p=1.0, lejos de `p<0.01`); `rs2` se mantuvo
correctamente (`control_reversals=40/200`, p=1.0); `replay` pasó. Se reporta
como hallazgo negativo: no hay señal de selección que siga la reversión de
presión bajo este diseño. Una observación secundaria: tanto la condición
mixta como el control sin variación muestran la misma caída monótona de la
media del alelo a través de los tres segmentos — patrón más consistente con
un artefacto de recorte en el límite inferior de la mutación (`clamp` a 0.0)
que con selección ecológica real, reforzando el mismo tipo de artefacto ya
documentado en `genesis-multigenerational-followup.md`. Detalle en
[`audits/current/2026-09-refutation-response-protocol-v1.md`](audits/current/2026-09-refutation-response-protocol-v1.md).

## Diferido o requiere nuevo consentimiento

- Escrituras del host, remediación, ejecución de comandos, inspección de procesos,
  credenciales, escaneo de red, propagación y auto-instanciación.
- Toda ampliación del residente que cambie de observación pasiva a control activo.
- Transferencia directa de modelos, corpus, adapters o pesos entre organismos; requiere
  una fase cultural posterior y un diseño separado.

## Regla de cierre

Una tarea de investigación solo se puede mover a **implementado y validado** si
conserva procedencia, separa evaluación de cognición, declara su matriz y tiene
una validación reproducible. Una suite verde aislada no basta para cerrar un
estudio.
