# Estado de investigación

Corte: `v0.80.16`, con Biological Closure v1, Private SLM v1, Cultural
Foundation v1, Cumulative Culture v1 y Autonomous Cultural Agency v1 cerrados
en sus alcances declarados.

Este registro clasifica el estado de la evidencia; no sustituye al roadmap ni
convierte un resultado exploratorio en una afirmación de capacidad.

## Implementado y validado

- Contratos y límites históricos de `symbiont` y Observatory cubiertos por sus
  suites de pruebas correspondientes al último corte ejecutado antes de abrir
  Private SLM.
- Estudios de aceptación de conocimiento de señales: límites del kernel,
  proyección acotada y separación organismo/evaluador verificadas en la partición
  sintética descrita en [`signal-knowledge-study.md`](signal-knowledge-study.md).
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
  [`../docs/design/private-slm-and-cultural-foundation.md`](../docs/design/private-slm-and-cultural-foundation.md):
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
[`../docs/design/cultural-foundation-v1.md`](../docs/design/cultural-foundation-v1.md).
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
[`../docs/design/cumulative-culture-v1.md`](../docs/design/cumulative-culture-v1.md)
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
