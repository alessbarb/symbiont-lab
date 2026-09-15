# Estudio inicial de conocimiento de señales

Este estudio ejecuta el motor con observaciones sintéticas opacas. La verdad de
las relaciones permanece exclusivamente en `symbiont_lab` y nunca se entrega al
organismo.

## Reproducción

```bash
python - <<'PY'
from symbiont_lab.studies.learning.signal_knowledge import *
print(summarize_acceptance(run_acceptance_suite()))
print(summarize_acceptance(run_full_acceptance_suite()))
print(run_signal_pressure())
print(measure_acceptance_resources())
PY
```

La suite base contiene 21 casos (constante, AR positiva/negativa, retardo,
causa común, huecos y cambio de ID), con semillas 101, 127 y 149. Observa 3
casos apoyados: los 3 positivos `lag`; no hay falsos positivos. La precisión y
recall del positivo son `1,00`, cobertura media `0,97154`, latencia media hasta
el primer apoyo `192` ticks y coste acumulado `5223` lecturas seleccionadas.

La suite extendida contiene 36 casos (añade cambio de régimen, múltiples pares
ruidosos, escala, tendencia y calidad inválida). También apoya únicamente los 3
casos `lag`, sin falsos positivos: precisión y recall `1,00`, cobertura media
`0,97168` y `8955` lecturas seleccionadas. Son resultados de una partición
pequeña y sintética, no una tasa poblacional.

La presión de 64 señales durante 256 ticks conserva los límites del kernel:
`64` perfiles, `192` claims globales y como máximo `4` claims por señal. El
bloque compacto de conocimiento ocupa `117840` bytes (límite 256 KiB). En el
flujo integrado, `OrganismRuntime` genera y guarda un checkpoint host de
`119031` bytes; el límite host de 2 MiB rechaza payloads sobredimensionados sin
reemplazar el archivo anterior.

`measure_acceptance_resources()` registró en este entorno `96359` bytes de pico
de `tracemalloc` y `3220` bytes para el JSON compacto del informe. No es una
medición de RSS del host completo. El journal sigue siendo un transporte
acotado: rota por segmentos completos y conserva como máximo 20 segmentos de
500 líneas por defecto; no es una segunda fuente durable de conocimiento.

Estas ejecuciones validan el arnés, los límites y la separación evaluador/
organismo. No sustituyen QA visual del Observatory ni una caracterización de RSS
del proceso completo en producción.
