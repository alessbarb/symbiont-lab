# Auditoría v0.15 — integridad experimental y rendimiento

## Veredicto

**Las mejoras metodológicas principales están implementadas y verificadas. No
constituyen todavía una mejora demostrada de la capacidad de detección.**
Quedan dos inconsistencias reproducidas en el diseño de experimentos: el
tratamiento de reporteros invertidos también cambia rasgos de los agentes,
y la ruta longitudinal pierde valores no definidos. El punto ciego stealth
persiste con y sin herencia.

## Versión y alcance

Versión solicitada: **v0.15**, commit `05dc68c` (merge de la corrección de
integridad experimental). Al comenzar, HEAD ya era v0.16 (`fccdaea`); no se auditó
esa versión ni su implementación de presupuestos de atención. Se utilizó una
exportación aislada de v0.15, con verificación de archivos contra Git y hashes
por fuente en cada salida. Los cambios concurrentes del repositorio no afectan
estas ejecuciones. No se modificó el motor ni se hizo commit/push.

85 simulaciones válidas de 100 hosts × 300 pasos: **2.550.000 observaciones**.
- 45 ejecuciones: nueve condiciones, cinco semillas (3,7,11,17,23).
- 30 ejecuciones: cinco linajes, tres generaciones, heredado/control.
- 10 ejecuciones adicionales: inversión de reportes con rasgos de agentes fijados.

Resultados exploratorios, con cinco unidades independientes por comparación.
No se han ajustado parámetros ni calculado probabilidades de éxito. No comparar
porcentajes directamente con v0.14: los RNG nuevos cambian los mundos asociados
a una misma semilla. La tabla compara condiciones dentro de v0.15.

## Mejoras verificadas respecto a la auditoría anterior

| Mejora | Evidencia y alcance |
|---|---|
| Atención y clasificación separadas | Conteos y tasas canónicos; suma por familia/fase/deriva coincide con global en todas las ejecuciones observadas. |
| Calibración consistente | ECE de diez intervalos y Brier usan `threat_probability`; un test independiente reconstruye ECE desde los intervalos serializados. |
| Mundo independiente de agentes | Hash completo idéntico en las cinco semillas al cambiar poisoning o heterogeneidad y en las ablaciones. |
| Ruta longitudinal única | Usa `_run_population`, no un bucle duplicado. Las 15 parejas heredado/control tienen el mismo hash completo del mundo. |
| Control sin herencia | La generación 1 produce resultados completos idénticos al control en los cinco linajes. |
| Valores no definidos | Preservados en métricas canónicas y estudios comparativos, pero no completamente en longitudinal. |

Cambiar magnitud de deriva conserva los hashes de etiquetas, pero cambia las
observaciones: eso es parte de la intervención, no un fallo de reproducibilidad.
Neutralizar colectivo y retirar curiosidad son parches temporales del experimento,
restaurados al salir; ninguna etiqueta del evaluador entra en las decisiones.

## Experimentos de una generación

Medias entre semillas; FPR es la proporción de benignos investigados.

| Condición | Recall atención | Precisión atención | FPR atención | Recall clasificación |
|---|---:|---:|---:|---:|
| baseline | 49.19% | 59.03% | 0.51% | 18.66% |
| no_poison | 49.09% | 60.48% | 0.48% | 20.74% |
| poison_30 | 52.11% | 55.20% | 0.63% | 21.74% |
| homogeneous | 46.36% | 66.33% | 0.35% | 15.59% |
| strong_drift | 50.03% | 47.63% | 0.82% | 19.45% |
| no_threats | N/A | 0.00% | 0.55% | N/A |
| no_curiosity | 41.99% | 69.72% | 0.28% | 20.06% |
| neutral_collective | 72.66% | 25.62% | 3.12% | 13.27% |
| fixed_trust | 51.96% | 58.93% | 0.54% | 18.75% |

### Eventos por familia, baseline

Conteos agrupados de las cinco semillas.

| Familia | Eventos | Investigados | Clasificados como amenaza |
|---|---:|---:|---:|
| benign:backup | 2201 | 88 | 1 |
| benign:build | 1767 | 440 | 45 |
| benign:normal | 140131 | 1 | 0 |
| benign:update | 3713 | 222 | 23 |
| pathogen:bot_sim | 700 | 450 | 134 |
| pathogen:ransom_sim | 885 | 626 | 274 |
| pathogen:stealth_sim | 603 | 0 | 0 |

El control sin amenazas tiene precisión de atención cero, correctamente definida:
hubo investigaciones, todas benignas. El recall es N/A porque no hubo amenazas.

**Hallazgos:** retirar curiosidad eleva precisión de atención, pero reduce su
recall. Neutralizar probabilidad y certeza colectivas eleva el recall a 72.66%,
pero FPR pasa de 0.51% a 3.12% y el recall de clasificación baja. Esa ablación
modifica incertidumbre y curiosidad además del término de sospecha colectivo;
no identifica un único mecanismo causal.

El indicador de adaptación explícita a deriva es cero en todas las condiciones
principales de una generación, incluida deriva fuerte. No significa que no
existan actualizaciones ordinarias del modelo; significa que esta tanda no
valida la rama explícita de adaptación.

La calibración ahora está **bien medida**, no necesariamente es buena: baseline
ECE = 0.11369 y Brier = 0.02393. El predictor trivial de probabilidad cero tendría
Brier = 0.01459 en esos mismos eventos, pero recall cero. Es un control útil que
muestra por qué no debe optimizarse Brier sin métricas por clase y coste.
`threat_probability` sigue siendo el score heurístico de sospecha, no una
probabilidad cuya calibración se haya aprendido y validado.

## Herencia longitudinal

Se excluye generación 1 del efecto: promedio de generaciones 2–3 por linaje y
luego promedio de cinco linajes. Cambios en puntos porcentuales:

| Métrica | Heredado − control | Linajes que mejoran |
|---|---:|---:|
| Recall atención | −0.201 | 2/5 |
| Precisión atención | +0.261 | 5/5 |
| FPR atención | −0.0074 | 4/5 |
| Recall clasificación | +0.577 | 4/5 |
| Precisión clasificación | +0.187 | 4/5 |

El cambio de recall de clasificación varía entre −1.463 y +2.005 puntos por
linaje. Son efectos pequeños y variables, no una mejora concluyente.
Los linajes exportan finalmente 3,6,6,8,9 patrones. En generaciones 2–3 hay
**1.284 eventos stealth por condición: cero investigados y cero clasificados
como amenaza**, tanto con herencia como en el control. La utilidad marginal
observada no resuelve ese punto ciego.

## Problemas pendientes, reproducidos

### P1 — Confusión residual en el tratamiento de poisoning

`rng.py` separa mundo y agentes, pero `_make_agents` usa un mismo stream de
agentes para seleccionar reporteros invertidos y generar rasgos. Cambiar la
fracción altera `risk_scale`, `curiosity_scale` e `investigation_bias`.
`diagnostics.json` prueba hashes de rasgos diferentes en las cinco semillas.

Seguimiento: conservar exactamente los rasgos de baseline (8% invertidos),
cambiando únicamente la asignación de reportes invertidos. Se conserva el mismo
hash del mundo en las diez ejecuciones adicionales.

- Sin inversión, la comparación nativa da recall de clasificación **20.74%**;
  con rasgos fijados da **17.43%**. Baseline: **18.66%**. Cambia el signo de la
  diferencia media: no se puede atribuir la comparación original solo a poisoning.
- Con 30% invertidos y rasgos fijados, recall de atención **51.52%**, precisión
  **56.97%** y FPR **0.581%**. FPR aumenta y precisión baja frente a baseline en
  las cinco semillas. Investigar más no demuestra resistencia al poisoning.

**Corrección propuesta:** stream separado para selección de reporteros, o generar
rasgos antes de seleccionar invertidos; añadir invariancia de rasgos como test.
No se ha aplicado esta corrección al motor.

### P1 — Longitudinal convierte N/A en cero

`longitudinal.py:_value` convierte `None` a `0.0` para recall/precisión de
clasificación. Reproducción con `threat_rate=0`: `run_simulation` devuelve recall
`None`, pero `GenerationComparison.control_classification_recall` devuelve cero.
Esto afecta casos sin denominador, no la comparación principal con amenazas.

**Corrección propuesta:** tipos opcionales, pares válidos explícitos y propagación
de N/A como en `study.py`; no representar ausencia de amenazas como recall malo.

### P2 — La media longitudinal sigue incluyendo generación 1

Los `mean_*_delta` nativos promedian también la generación sin herencia. En este
diseño, diluyen el efecto post-herencia por un factor 2/3. No es un error aritmético,
pero responde a una pregunta distinta. Exponer ambos resúmenes y sus denominadores.

### P2 — Consenso repetido sigue inflando reputación

Sin nuevos reportes, 50 recalibraciones elevan confianza mayoritaria de 0.75 a
0.949 y reducen la del disidente a 0.203. El diagnóstico anterior sigue siendo
reproducible en v0.15. Reputación por coincidencia no prueba exactitud, ni evidencia
nueva. Evitar reutilización ilimitada y estudiar disidencia correcta/colusión
antes de presentar separación de confianza como robustez.

## Próximo paso recomendado

1. Cerrar las dos inconsistencias P1 con pruebas de invariancia y de N/A.
2. Mantener métricas por familia como criterio de aceptación: el recall stealth
   no debe desaparecer detrás del promedio global.
3. Auditar por separado los presupuestos de atención que ya existen en v0.16;
   no se evalúan aquí ni se asume que estén correctamente implementados.
4. Después, probar investigación con medición sintética adicional y ruidosa,
   nunca verdad del evaluador, a coste equiparado con selección aleatoria y
   por riesgo. Con el mecanismo actual investigar solo registra/reporta una
   creencia; el número de investigaciones no demuestra adquisición de evidencia.
5. Para herencia, añadir mundos que cambien entre generaciones y priors incorrectos,
   más linajes reservados y ventanas tempranas desde el inicio de amenazas.

## Validación y artefactos

- `core-tests.txt`: **49 tests pasan** sobre v0.15 aislada.
- `observer-tests.txt`: **3 tests pasan**; observador no altera resultado,
  reconstrucción de ECE y N/A sin amenazas.
- `single.jsonl`, `longitudinal-complete.jsonl`, `controlled-poison.jsonl`:
  resultados crudos con hashes. `summary.json`: agregados descriptivos.
- Primer intento longitudinal falló en el runner por reenviar dos veces
  `on_event`; se corrigió y añadió una prueba. `longitudinal.jsonl` contiene
  solo metadatos, **ningún resultado**, y está excluido del análisis.
- El hash del runner de la primera tanda corresponde a su versión anterior a
  esa corrección del callback. No cambió la lógica de la simulación.
- No se ejecutaron pruebas funcionales del dashboard ni se auditó v0.16.
