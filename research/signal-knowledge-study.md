# Estudio inicial de conocimiento de señales

Este estudio ejecuta el motor con dos señales sintéticas opacas y una relación
contemporánea/predictiva. La verdad de la relación y la generación de datos
permanecen exclusivamente en `symbiont_lab`.

## Reproducción

```bash
python - <<'PY'
from symbiont_lab.studies.learning.signal_knowledge import run_signal_knowledge
for seed in (101, 127, 149):
    print(run_signal_knowledge(seed))
PY
```

Resultados observados con 192 ticks por semilla: 2 perfiles y 6 claims por
semilla; con la promoción por tres épocas no solapadas el predictor produjo 0
claims `supported` en las semillas 101, 127 y 149. Esto es una prueba de
integración y reproducibilidad, no una aceptación estadística: el fixture no
alcanza todavía las tres épocas favorables exigidas y debe ampliarse en el
estudio completo de §10.

La matriz inicial `run_acceptance_scenarios(101, ticks=256)` cubre constante,
AR positiva/negativa, retardo, causa común, huecos e intercambio de ID. En esta
semilla el caso de retardo produjo 1 claim apoyado; los controles constante,
AR, causa común y cambio de ID no produjeron apoyo; el caso con huecos mantuvo
una cobertura de 0,8008 y se abstuvo de apoyar. Estos resultados son una
comprobación inicial del arnés, no el cierre de aceptación: deben repetirse con
las semillas 127 y 149 y medirse precisión, latencia, coste y memoria.

La ejecución congelada `run_acceptance_suite()` se repitió con las tres semillas:
el escenario de retardo obtuvo apoyo en `101`, `127` y `149`; el escenario con
huecos mantuvo cobertura `0,8008` y ningún apoyo en las tres. La matriz sigue
siendo un arnés de aceptación parcial: aún no calcula precisión agregada,
latencia de descubrimiento, RSS/tracemalloc ni crecimiento del journal.

Ahora `summarize_acceptance(run_acceptance_suite())` deja explícitas las métricas
que sí son reproducibles en este arnés: 21 escenarios, 5 con alguna afirmación
`supported`, 3 verdaderos positivos (retardo), 2 falsos positivos (AR positiva
en dos semillas), precisión de apoyo `0,60`, recall del caso de retardo `1,00`
y cobertura media `0,97154`. Estas etiquetas son del evaluador y no se envían
al motor. La latencia media hasta el primer apoyo observado es `217,6` ticks
entre los cinco escenarios que apoyaron, y el coste acumulado es `5223` lecturas
seleccionadas. La precisión no se presenta como una tasa poblacional: el
conjunto es pequeño y deliberadamente sintético. Siguen pendientes las
mediciones de RSS/tracemalloc y crecimiento del journal indicadas arriba.

La medición opcional `measure_acceptance_resources()` registró en este entorno
`707695` bytes de pico de `tracemalloc` y `3218` bytes para el JSON compacto de
resultados. Es una medición del proceso Python y del informe del evaluador, no
del RSS del host completo ni de la retención del journal; ambos límites siguen
requiriendo una prueba integrada específica.

`run_full_acceptance_suite(seeds=(101,))` incorpora además cambio de régimen,
pares con ruido, escala, tendencia y calidad inválida. En esa ejecución el
cambio de régimen terminó `contested`, los controles de ruido/escala/tendencia
no obtuvieron apoyo y la calidad inválida redujo la cobertura a `0,859375` sin
promoción. La repetición de esta matriz extendida con las tres semillas queda
como puerta de aceptación, no como resultado ya generalizado.
