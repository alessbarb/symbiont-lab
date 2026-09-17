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

## Private SLM v1 — implementación validada; cierre científico en curso

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

- **Validación técnica local ejecutada el 2026-09-17**:
  - suite completa: `1534 passed`;
  - batería Private SLM específica: `28 passed`;
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
