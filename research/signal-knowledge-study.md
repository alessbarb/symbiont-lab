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
