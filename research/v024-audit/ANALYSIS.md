# Auditoría v0.24 — resultados y límites

Fecha: 2026-09-12. Fuente congelada: `a352c93d889aa901e53903bae844b894d78adeb6` (0.24.0). Se conservan las auditorías v0.15/v0.19. No se modifica el producto.

## Dictamen

**Hay correcciones reales de integridad y mejores experimentos, pero un defecto de arranque invalida una lectura general de los resultados de novedad causal.** El sensor continúa correctamente aislado en shadow. La herencia aprendida mejora recall en las cinco parejas probadas; esto no demuestra robustez frente a cambio ecológico.

## Correcciones verificadas respecto a v0.19

- Poisoning 0, .08 y .30 mantiene exactamente los mismos rasgos en cinco semillas.
- Recalibrar 50 veces sin reportes nuevos conserva confianza y número de evaluaciones.
- Recall longitudinal sin amenazas permanece `None`; los promedios excluyen generaciones sin patrones heredados, con test de regresión de la suite.
- Las listas duplicadas de semillas se rechazan.
- `direction_flips` se separa de `improved_reexports`, `worsened_reexports` y ganancia MAE. El alias legacy `corrected_reexports` sigue contando cruces de umbral; lectores antiguos deben migrar.
- El selector causal decide usando pasado y evento actual, sin consultar scores futuros; la prueba de invariancia de prefijo pasa. Conocer la longitud total y el presupuesto es un supuesto explícito.

La suite congelada completa pasa: **87 tests**. Las comprobaciones adicionales están en `diagnostics.json`.

## P1 — Novedad causal consume presupuesto en ceros de arranque

En `causal_budget.py:73–80,125–131`, tras 32 eventos el cuantil histórico sustituye al fallback; con historial de ceros el umbral vale cero. La condición `score >= threshold` acepta cada empate. `_score_events` asigna novedad cero mientras cada host tiene menos de seis observaciones.

Reproducción sobre 100 hosts, 300 pasos, semilla 7:

| Capacidad | Selecciones warmup | Novedad cero | Último paso seleccionado | Amenazas seleccionadas |
|---|---:|---:|---:|---:|
| 150 (5/mil) | 150 | 150 | 1 | 0 |
| 360 (12/mil) | 360 | 360 | 3 | 0 |
| 600 (20/mil) | 587 | 568 | 213 | 12 |

Las amenazas comienzan en el paso 50. No es una fuga de futuro: es una política causal degenerada por inicialización y empates. No usar estos resultados para concluir que la novedad es intrínsecamente inútil. `forced_selections` solo cuenta el guard de cuota final y no identifica esta selección masiva inicial.

**Cambio mínimo recomendado:** abstención durante falta de historial por host, tratamiento explícito de empates y diagnóstico de gasto por fase. Recalcular para todos los selectores la misma capacidad y elegibilidad; no excluir warmup solo a la estrategia favorecida. Añadir un test donde score cero no agote presupuesto de exploración por un artefacto de inicialización.

## P2 — La idempotencia no elimina replay de votos

La corrección de v0.21 resuelve exactamente las llamadas sin reportes nuevos. Sin embargo, `report()` incrementa `reports` incluso si el voto es idéntico, y cualquier nueva revisión del patrón vuelve a evaluar a todas sus fuentes.

Reproducción: cinco fuentes, cuatro votos positivos y uno negativo; tras primera calibración, mayoría .77 y minoría .695. Repetir 50 veces el mismo voto de **una sola fuente** y recalibrar lleva todas las fuentes a 51 evaluaciones; mayoría .94907 y minoría .20255. No se añadieron pares independientes ni cambiaron votos.

Esto es un límite residual, no la reaparición del fallo sin reportes. Definir si un mensaje repetido representa evidencia nueva; si se exige independencia, usar identidad/revisión de evidencia por fuente y evitar volver a premiar todos los votos históricos por un único reporte.

## Segunda observación: ruido y selección siguen siendo problemas distintos

Bloque de semillas publicadas v0.24: 211,223,239,251,269; presupuesto fijo 360 sobre 30.000 eventos. Ganancia Brier media sobre seleccionados (positivo = mejor):

| Selector | Ruido .08 | .18 | .30 | .45 |
|---|---:|---:|---:|---:|
| Riesgo | .071895 | .061727 | .041604 | .015639 |
| Novedad | .063086 | .052153 | .031636 | .005274 |
| Riesgo+novedad | .069533 | .060019 | .040805 | .015484 |
| Curiosidad shadow | .063775 | .054299 | .035298 | .010496 |
| Aleatorio | .011993 | .009814 | .004568 | −.003983 |

A ruido .45, riesgo y curiosidad mejoran Brier en 5/5 semillas; novedad en 3/5; aleatorio en 1/5. En las semillas históricas con presupuesto 300 y ruido .50, curiosidad tiene ganancia media −.010559 y novedad −.011014. **No es una contradicción:** cambian semillas, capacidad y ruido. No se ha identificado un umbral universal de fallo ni se ha validado señal nula o sesgada.

Las cuatro estrategias dirigidas tienen cero runs con tasa de corrección stealth definida en el bloque nuevo: no seleccionaron stealth. Esta carencia no se resuelve reduciendo ruido. Aleatorio sí tiene denominador definido en cuatro semillas.

El prior shadow y el peso .70 del posterior no se ajustan a la calidad del sensor. `evidence.py` sigue seleccionando con ranking retrospectivo, no con el selector causal nuevo. La línea de atención causal y la línea de segunda observación **todavía no forman una política causal conjunta**. Comparar primero un objetivo explícito (Brier poblacional, recall por familia, correcciones netas), sin alimentar verdad al agente.

### P2 — Garantía de emparejamiento más débil que el texto

`evidence_noise_sweep.py:210–215` comprueba número seleccionado y Brier previo, no identidad de eventos. El código actual de selección es independiente del ruido; no observé cambios de conjunto. Pero igualdad de cantidad y media no prueba igualdad de identidades ni detectaría toda regresión. Añadir digest ordenado de `(step, host_index)` y del mundo. El README afirma una comprobación del conjunto más fuerte que la implementada.

## Herencia: mejora acotada, no inmunidad a priors malos

Cinco parejas fuente 3,7,11,17,23 y destino +1009; cuatro condiciones con digest de mundo idéntico por pareja.

| Condición | Recall clasificación | Precisión clasificación | Brier |
|---|---:|---:|---:|
| Sin herencia | 21.257% | 92.567% | .024301 |
| Aprendida | 22.511% | 92.535% | .024301 |
| Invertida | 24.683% | 85.676% | .024672 |
| Desalineada | 20.887% | 90.367% | .024375 |

La herencia aprendida mejora recall **+1.254 pp**, rango **+.211 a +3.548 pp**, en **5/5 parejas**; Brier medio prácticamente sin cambio (+.000000457, ligeramente peor). Las reexportaciones aprendidas incluyen media 3.2 mejoras y 1.2 empeoramientos: ahora el diagnóstico distingue ambos correctamente.

Frente a la auditoría v0.19 hay una señal más consistente, pero el motor cambió en RNG de rasgos y confianza; no atribuir causalmente toda la diferencia a una sola corrección. Los priors invertidos todavía elevan recall a costa de precisión y Brier. Falta cambio ecológico explícito fuente→destino, curva temporal de recuperación y seguimiento multigeneracional.

## Prioridades

1. Corregir arranque/empates del selector de novedad y registrar gasto por fase; repetir la comparación causal.
2. Especificar y probar independencia/idempotencia de evidencia repetida, no solo de llamadas vacías.
3. Fortalecer emparejamiento del barrido con identidades; cruzar selección causal × ruido × exploración pequeña bajo capacidad común.
4. Probar herencia en cambio ecológico antes de añadir aprendizaje más complejo o conectar el segundo sensor al agente.

El historial completo se ordena de nuevo en cada decisión causal (`sorted(history)`), con memoria creciente y coste superlineal. Es un límite de escalabilidad visible en código, no una comparación de rendimiento controlada. Primero corregir semántica; después, si se amplía el tamaño, sustituirlo por una estructura de cuantiles apropiada y validar equivalencia.
