# v0.14 — Herencia longitudinal, evaluación aislada

## Procedencia

Commit congelado: `b85b7fb946c7260ae1d7afb39f1fbb7a62297c29`.
Exportado con `git archive` a `/tmp/symbiont-audit-b85b7fb`.
El motor se importa desde esa copia, no desde el checkout en evolución.
`longitudinal-v014.jsonl` conserva configuración y SHA-256 de cada archivo Python.
Esto evalúa ese commit de v0.14, no versiones posteriores que puedan aparecer.

La tanda anterior `replication.jsonl` también registra v0.14, pero ejecutó
simulaciones de una generación, sin herencia. No se mezcla con la tanda v0.13.
Su baseline de semilla 31 se reprodujo exactamente contra el archivo congelado
(métricas y hash de eventos). `summarize.py` rechaza agregación entre commits.

## Diseño

Cinco linajes independientes: semillas iniciales 3, 7, 11, 17 y 23.
Tres generaciones por linaje; semilla de generación `seed + (generation-1)*1009`.
100 hosts × 300 pasos por simulación. Cada generación tiene condición heredada
y control sin herencia. Son **30 simulaciones y 900.000 observaciones**.
Tasa de amenazas 0.018; reporteros invertidos 0.08; heterogeneidad 0.12;
deriva 0.35 de hosts, magnitud 0.22; límite de herencia 24 patrones.

Generación 1: sin herencia, paridad exacta en las cinco métricas comparadas,
en los cinco linajes (assertions del runner). Es control interno, no una
observación del efecto de heredar.

Para estimar efectos se promedian generaciones 2–3 dentro de cada linaje y
luego los cinco linajes. Las generaciones de un mismo linaje no se tratan
como réplicas independientes. El promedio nativo incluye generación 1 y reduce
el efecto por un factor 2/3 en este diseño; se conserva en los datos crudos,
pero no es el resumen primario aquí.

## Resultados: heredado menos control

Todos los cambios son **puntos porcentuales**, no cambios relativos.

| Métrica | Media por linaje | Rango de medias de linaje | Dirección |
|---|---:|---:|---|
| Recall de atención | -0.026 | -0.992 a +1.130 | Sube en 2/5 |
| Precisión de atención | +0.593 | -0.359 a +1.411 | Sube en 4/5 |
| FPR de atención | -0.0135 | -0.0186 a -0.0034 | Baja en 5/5 |
| Error de calibración del motor | -0.0328 | -0.0504 a -0.0104 | Baja en 5/5 |
| Blind-spot rate del motor | +0.432 | -0.291 a +1.214 | Sube en 3/5 |

Los linajes terminan exportando 6, 8, 8, 6 y 8 patrones respectivamente.
Retener patrones no demuestra que esos patrones sean correctos ni beneficiosos.

**Conclusión del piloto:** la herencia muestra una pequeña reducción consistente
de investigaciones benignas, pero no una mejora consistente del recall. Hay
una mejora media pequeña de precisión de atención. No hay evidencia suficiente
para afirmar que la especie detecta mejor gracias a la herencia. Los resultados
no equivalen a significación estadística y no miden clasificación por familia.

## Qué cambia respecto a v0.13

La memoria colectiva heredada sí entra ahora en la decisión a través de
`CollectiveMemory.belief`. Por tanto, sería incorrecto extender a esta herencia
la observación de que la memoria episódica local no se consulta. Esta última
observación sigue correspondiendo a `Agent.assess`, que no cambió en este diff.

Los cambios añaden `heritage.py`, `longitudinal.py` y CLI de generaciones.
La exportación exige evidencia viva y diversidad de fuentes, sin copiar
reputación ni memoria de hosts. Es una separación útil. Aun así, los votos vivos
pueden estar influidos por priors heredados: “evidencia viva” no significa
independencia causal respecto a la herencia.

## Siguientes mejoras del estudio, por orden

1. **Mantener la fijación de versión.** Todo informe debe incluir commit,
   parámetros, semillas y hashes. Comparar releases solo sobre mundos fijados.
2. **Reportar efecto post-herencia aparte de generación 1.** Conservar generación
   1 como test de paridad; mostrar efectos por linaje y generación. No confundir
   persistencia de patrones con utilidad predictiva.
3. **Extender la instrumentación a la vía longitudinal.** Incorporar matrices de
   clasificación y atención por familia, y por ventana temprana/tardía. El
   efecto de acelerar aprendizaje puede diluirse al promediar 300 pasos.
4. **Controlar herencia vacía, incorrecta y obsoleta.** Comparar priors aprendidos,
   ausentes y perturbados dentro del mundo sintético, incluyendo cambio de
   ecología entre generaciones. Medir recuperación frente a una creencia heredada
   equivocada, no únicamente estabilidad del conocimiento.
5. **Más linajes reservados antes de ajustar límites/pesos.** Esta tanda tiene
   cinco unidades independientes y tres generaciones; no representa madurez
   longitudinal. No optimizar pesos sobre estas mismas semillas y presentar
   después ese ajuste como validación.
6. **Resolver el contrato de métricas compartido.** `detection_rate` sigue siendo
   atención; calibración y blind spots conservan las limitaciones detalladas
   en `ANALYSIS.md`. La vía longitudinal replica el bucle de simulación: cualquier
   corrección debe mantener paridad entre ambas rutas para no generar controles
   incompatibles.

## Reproducción y validación

```bash
mkdir -p /tmp/symbiont-audit-b85b7fb
git archive b85b7fb | tar -x -C /tmp/symbiont-audit-b85b7fb
PYTHONPATH=/tmp/symbiont-audit-b85b7fb/src .venv/bin/python \
  research/2026-09-12/run_v014.py --output /tmp/longitudinal-v014-replay.jsonl
```

El runner crea su salida exclusivamente y se negará a sobrescribirla; para una
nueva ejecución se debe elegir un `--output` nuevo. Los 43 tests
de v0.14 aislada y tres tests del observador están registrados en
`validation-v014-isolated.txt` y `validation-observer.txt`.
Un intento de ejecutar ambos directorios de tests en una sola invocación
falló al recolectar desde un ancestro común ajeno al proyecto; el error
se conserva en `validation-v014.txt`. Se resolvió ejecutando las suites
por separado, sin cambiar tests ni motor. No se modificó código del motor ni se hizo commit/push.
