# Auditoría actualizada — Symbiont Lab v0.19

**Fecha:** 2026-09-12. **Commit:** `eff5a0f30b26e72573df0a95333229c2f380985d`.

## Dictamen

**Mejor capacidad de estudiar el sistema; todavía no hay evidencia de una mejora general del agente.** v0.16–v0.19 añaden presupuesto comparable, segunda observación sintética, replicación y estrés de herencia. Son avances metodológicos reales, pero no corrigen el motor: los archivos existentes bajo `src/symbiont/` son idénticos a v0.15; se añaden ocho módulos.

Suite congelada: **66 tests pasan**. Matriz principal: **40 simulaciones, 1.200.000 eventos procesados, cinco semillas independientes**. Se reutilizan mundos entre tratamientos. Resultados exploratorios, no significación estadística ni validación de sistemas reales. Véanse `PROTOCOL.md`, `results.jsonl` y `summary.json`.

## 1. Atención con presupuesto comparable

Medias de cinco semillas; exactamente el mismo número de selecciones por estrategia dentro de cada semilla (379, 350, 396, 374, 328).

| Selector | Recall de atención | Precisión | FPR benigno | Recall stealth |
|---|---:|---:|---:|---:|
| Política actual | 49.19% | 59.03% | 0.508% | 0.000% |
| Riesgo | 52.03% | 62.53% | 0.466% | 0.172% |
| Novedad | 46.07% | 55.28% | 0.554% | 0.000% |
| Riesgo + novedad | 51.20% | 61.48% | 0.478% | 0.000% |
| Aleatorio | 0.87% | 1.04% | 1.223% | 0.604% |

Riesgo supera el recall de la política en **5/5 semillas**, con +2.84 puntos porcentuales de media. Pero `budget.py::_ranked_selection` ordena retrospectivamente todos los eventos; la política decide durante la simulación. Igual coste no implica igual disponibilidad temporal de información. No demuestra que sustituir la política por ese ranking mejore un agente online.

El punto ciego persiste: política selecciona **0 stealth**, riesgo 1 y aleatorio 4, en las cinco ejecuciones. La prioridad no debería ser aumentar complejidad sin probar primero una pequeña cuota de exploración y selección causal bajo el mismo presupuesto.

## 2. Segunda observación: beneficio condicionado al sensor y al objetivo

300 selecciones por mundo. `brier_gain` positivo significa mejora, medido **solo sobre seleccionados**. Correcciones netas = errores corregidos menos introducidos, media por ejecución.

| Selector | Ganancia Brier, ruido .18 | Correcciones netas .18 | Ganancia Brier, ruido .50 | Correcciones netas .50 |
|---|---:|---:|---:|---:|
| Riesgo | +0.06289 | +34.0 | +0.01216 | +6.6 |
| Novedad | +0.04721 | +36.2 | −0.01101 | +6.4 |
| Riesgo + novedad | +0.05744 | +33.0 | +0.00412 | +7.0 |
| Curiosidad shadow | +0.04556 | +42.6 | −0.01056 | +18.0 |
| Aleatorio | +0.00946 | 0.0 | −0.00637 | −3.2 |

Con ruido .18, curiosidad corrige más errores netos en promedio, pero riesgo mejora más Brier. **No existe un ganador independiente del objetivo.** Con ruido .50, curiosidad conserva correcciones netas positivas en 5/5 semillas, pero empeora Brier en 4/5: clasificar mejor al umbral y estimar probabilidades mejor son objetivos distintos.

Las cuatro estrategias dirigidas seleccionan **cero stealth** a este presupuesto. Aleatorio selecciona cuatro en total y corrige uno con ruido .18. Tener un sensor informativo no ayuda a eventos que nunca se investigan.

Límites importantes:

- Es un estudio **shadow**, sin actualización del agente vivo. El prior es otro score heurístico, no la probabilidad registrada por el agente.
- El sensor recibe una media sintética según la familia verdadera, exclusivamente dentro del simulador: no es por sí mismo una fuga de etiquetas hacia decisiones, pero su calidad es un supuesto experimental fuerte.
- `_posterior_probability` mantiene peso fijo .70 aunque cambie el ruido. Este experimento muestra que el beneficio no es robusto a toda calidad de sensor.
- Los Brier absolutos de diferentes subconjuntos no son directamente comparables como calidad poblacional. Con presupuesto idéntico y la misma base shadow, la ganancia sobre el flujo completo es la ganancia seleccionada × 0.01: riesgo +0.000629 y curiosidad +0.000456 con ruido .18. Es una derivación contrafactual, no una mejora medida del motor.

## 3. Herencia bajo estrés: corrección parcial, utilidad no consolidada

Cinco parejas fuente/destino. **Digest idéntico entre las cuatro condiciones en cada pareja**, comprobado por la implementación y por el agregador.

| Herencia | Recall clasificación | Precisión clasificación | FPR atención | Brier | Ganancia de alineación |
|---|---:|---:|---:|---:|---:|
| Sin herencia | 22.03% | 87.88% | 0.523% | 0.024307 | N/A |
| Aprendida | 22.21% | 87.78% | 0.512% | 0.024332 | +0.01382 |
| Invertida | 24.48% | 83.19% | 0.633% | 0.024669 | +0.28550 |
| Desalineada | 22.31% | 87.77% | 0.516% | 0.024335 | +0.01849 |

La herencia aprendida aporta **+0.174 pp** de recall clasificatorio medio frente a no heredar, pero solo mejora 3/5 parejas; rango **−3.795 a +3.548 pp**. Brier empeora en 4/5. No hay base para afirmar beneficio general consistente.

La herencia invertida aumenta recall en 5/5, a costa de precisión y Brier. Aunque el MAE de patrones baja de 0.6434 a 0.3579, sigue peor que 0.2651 con herencia aprendida. **Acercarse a la verdad desde un prior muy malo no equivale a superar el control sin herencia.**

Este protocolo estresa priors corruptos; no introduce un cambio ecológico explícito entre fuente y destino ni sigue su recuperación durante varias generaciones. El MAE es retrospectivo y pondera por igual fingerprints observados, no eventos. `live_mae` excluye patrones sin evidencia viva y puede usar otro subconjunto que `prior_mae`; no interpretar su diferencia sin comprobar cobertura.

## 4. Hallazgos y pendientes priorizados

### P1 — Integridad causal y semántica

1. **Poisoning sigue cambiando rasgos de agentes.** `diagnostics.json` reproduce hashes de rasgos distintos para fracciones 0, .08 y .30 en las cinco semillas. Separar RNG de asignación de reporteros y RNG de rasgos antes de atribuir efectos exclusivamente a poisoning.
2. **N/A longitudinal sigue convertido a cero.** Sin amenazas, recall canónico `null`, control longitudinal `0.0`. Preservar `None` y contar réplicas definidas. La afirmación general del README sobre denominadores cero necesita acotarse hasta corregirlo.
3. **Confianza se refuerza sin nuevos reportes.** Tras 50 recalibraciones de los mismos votos, mayoría .75→.94897 y minoría .75→.20284. Evitar reutilizar repetidamente la misma evidencia; consenso no es verdad.
4. **`corrected_reexports` cuenta cambios de lado de .5, no correcciones frente a verdad** (`heritage_stress.py:216–222`). README sí describe cambios de dirección, pero el nombre del campo induce a una interpretación más fuerte. Renombrar a `direction_flips` o añadir ganancia de error contra frecuencia empírica. Observación real, fuente 7/destino 1016: `M-M-M-M-L`, probabilidad .187576→0, frecuencia .035294, mejora MAE .116988, pero no cuenta como corregida. Otro patrón empeora sin cruzar el umbral. La regla también permitiría contar como corrección un cruce en dirección equivocada; esto último es una posibilidad del código, no un caso observado aquí. Evidencia: `semantics.json`.

### P2 — Validez del estudio

5. **Comparación retrospectiva versus online.** Añadir selector causal por ventanas o presupuesto secuencial antes de trasladar resultados de `budget`/`evidence` al agente.
6. **Semillas repetidas aceptadas como réplicas.** `run_replicated_evidence_study(seeds=(7,7))` devuelve dos runs y dos pares con desviación cero. Rechazar duplicados o declarar réplicas únicas; la matriz principal de esta auditoría no tiene duplicados.
7. **No confundir observabilidad con aprendizaje nuevo.** La memoria episódica no alimenta `Agent.assess`; la investigación viva no obtiene la nueva medición shadow. La herencia colectiva sí puede modificar decisiones. No describir todo el sistema como inerte ni el segundo sensor como integrado.
8. **Agregación longitudinal anterior sin cambios:** incluye generación 1, que no tiene intervención de herencia. Separarla de los efectos heredados; no se repitió aquí la campaña longitudinal completa de v0.15.

## 5. Próxima tranche recomendada

1. Corregir primero RNG, N/A, reciclado de votos y nombres/denominadores; añadir tests de regresión. No rediseñar el motor todavía.
2. Probar riesgo, curiosidad y mezcla con exploración bajo un presupuesto **causal** común. Informar recall stealth, precisión, Brier poblacional y correcciones netas; fijar el objetivo antes de elegir ganador.
3. Mantener el segundo sensor en shadow; barrer ruido y señal nula/sesgada, ajustando la confianza a calidad del sensor. Solo considerar integración acotada si el beneficio persiste.
4. Replicar herencia con cambio ecológico fuente→destino y horizonte multigeneracional; medir daño, cobertura, recuperación temporal y mejora de reexportaciones frente a verdad, con controles emparejados.

**Estado de entrega:** análisis y evidencia añadidos en esta carpeta; sin modificar `AGENTS.md`, código del producto ni auditoría v0.15. Sin commit ni push.
