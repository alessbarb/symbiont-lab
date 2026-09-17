# Estado de investigación

Corte: post-`v0.80.15`, Biological Closure v1 + Private SLM v1 validation.

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

## Private SLM v1 — adaptación incremental implementada y validada; cierre científico positivo en el alcance declarado

- Sustrato implementado según
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
  - comparación contra uniform/frecuencia/persistencia y referencia GRU;
  - lifecycle `CANDIDATE -> SHADOW -> ACTIVE -> DEGRADED/RETIRED`;
  - activación solo tras autorización de promoción independiente;
  - inferencia tipada de predicciones, sin escritura directa de hechos ni acciones;
  - validación automática de predicciones activas contra outcomes vividos, con el
    resultado oculto al input del modelo;
  - checkpoint de ledger/registro sin pesos y cold-start del gateway al restaurar;
  - coste metabólico bounded para solicitar/adoptar modelos;
  - descendencia clonal conserva capacidad de modelado pero no corpus ni modelos adquiridos.
  - adaptación incremental separada de cold start: carga pesos parentales reales,
    valida ownership/arquitectura/tokenizer/contexto/integridad, registra lineage
    completa y mantiene el padre activo hasta promoción independiente;
  - límites de adaptación y coste observado quedan ligados al manifest; Observatory
    expone solo estado, lineage y resumen pasivo, nunca pesos.

- **Validación técnica local ejecutada el 2026-09-17**:
  - suite completa: `1551 passed` (ejecutada fuera del sandbox restringido,
    porque los tests históricos de Observatory requieren sockets y estado local);
  - batería nueva de adaptación: `5 passed`; regresiones de modelado y runtime
    incluidas en la suite completa;
  - regresión posterior de protocolo por semilla: `7 passed`;
  - controles B-D de protocolo: `12 passed` antes del run experimental.

- **Gate A — utilidad held-out preregistrada: positivo en el alcance declarado**.
  Experimento `learning.private-model-utility`, semillas 101/127/149, 128 ticks:
  - GRU: ganancia media sobre mejor baseline trivial `+0.049437`, 2/3 promociones;
  - Transformer: ganancia media `+0.080261`, 2/3 promociones;
  - Transformer vs. GRU: ganancia media `+0.030824`;
  - seed 101: GRU no promociona; Transformer sí;
  - seed 127: GRU promociona; Transformer no promociona por no superar la referencia recurrente;
  - seed 149: promocionan ambos.
  El preregistro exigía ganancia media positiva de al menos una familia, no 3/3
  promociones. No se reajustan hiperparámetros tras observar el resultado.

- **Gate B — especificidad individual: positivo según criterio preregistrado, efecto débil/heterogéneo**.
  `learning.private-model-controls`, semillas 101/127/149, 128 ticks:
  - margen medio `+0.002465` nats;
  - seed 101 `-0.064455`, seed 127 `+0.003251`, seed 149 `+0.068600`.
  Cumple el criterio medio `> 0`; no se interpreta como universalidad por semilla.

- **Gate C — invariancia estructural bajo remapeo opaco: positivo fuerte**.
  En el mismo protocolo:
  - disrupción stale media `+3.132914` nats tras permutar identidades opacas;
  - gap medio tras reentrenamiento `-0.003140` nats respecto al rendimiento original.
  El modelo stale depende de la codificación aprendida, pero la misma estructura
  puede reaprenderse tras una renominación arbitraria de símbolos.

- **Gate D-v1 — cambio de régimen asimétrico: criterio preregistrado no superado**.
  En `learning.private-model-controls`:
  - degradación stale media `-0.004362` nats (criterio requería `> 0`);
  - recuperación media `+0.031878` nats.
  El resultado se conserva como negativo. La comparación `post_stale - pre` mezcla
  cambio de contingencia con posible diferencia de dificultad/entropía entre las
  dos reglas de outcomes. No se reinterpreta ni se reemplaza retroactivamente.

## Implementado; validación científica pendiente de ejecución

- **Gate D-v2 — cambio de régimen simétrico** mediante
  `learning.private-model-regime-symmetric`:
  - mismo contexto, acciones, longitud de secuencia y multiconjunto de frecuencias
    de outcomes antes/después;
  - el régimen post-shift aplica una permutación biyectiva fija a identidades de outcome;
  - criterio preregistrado: degradación stale media `> 0`, recuperación media `> 0`
    y modelo reentrenado dentro de `0.15` nats del loss pre-shift en promedio.
  Este follow-up existe para eliminar el confusor de dificultad entre regímenes de
  D-v1, no para borrar su resultado negativo. No se ajustarán hiperparámetros tras
  observar D-v2.

- **Capacidad de adaptación incremental — positiva en el estudio nuevo preregistrado**.
  El estudio `learning.private-model-adaptation`, creado después de confirmar que
  el antiguo entrenamiento ignoraba los pesos del padre, compara stale, fresh y
  successor inicializado desde el padre bajo exactamente el cambio simétrico de
  D-v2, con semillas 101/127/149:
  - `mean_adapted_vs_stale = +0.0868168` nats;
  - `mean_adapted_vs_fresh = +0.0880002` nats;
  - lineage válida en las tres semillas;
  - coste medio de adaptación: 44 pasos, dentro de los ceilings autorizados;
  - el control fresh conserva `mean_fresh_recovery = -0.00118335`, consistente
    con el resultado D-v2 y sin reescribirlo.
  Cumple el criterio preregistrado de mejora media sobre stale, no inferioridad
  material frente a fresh (`>= -0.15`), lineage completa y presupuesto bounded.
  El resultado demuestra una capacidad de successor adaptativo en este protocolo;
  no afirma generalización a todos los shifts ni convierte D-v1/D-v2 en positivos.

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

## Diseñado pero no implementado

- **Cultura social post-L**: transmisión inter-organismo de claims/modelos/corpus,
  genealogía cultural, dependencia de fuentes y símbolos compartidos. Sigue
  deliberadamente fuera de Private SLM v1.
- Nuevas capacidades de comunicación real o acciones sobre el host.

## Diferido o requiere nuevo consentimiento

- Escrituras del host, remediación, ejecución de comandos, inspección de procesos,
  credenciales, escaneo de red, propagación y auto-instanciación.
- Toda ampliación del residente que cambie de observación pasiva a control activo.
- Transferencia cultural de modelos, corpus, adapters o conocimiento aprendido
  entre organismos; requiere diseño separado después del gate de utilidad Private SLM.

## Regla de cierre

Una tarea de investigación solo se puede mover a **implementado y validado** si
conserva procedencia, separa evaluación de cognición, declara su matriz y tiene
una validación reproducible. Una suite verde aislada no basta para cerrar un
estudio.
