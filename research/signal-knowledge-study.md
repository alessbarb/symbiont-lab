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
