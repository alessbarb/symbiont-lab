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

Resultados observados con 192 ticks por semilla: 2 perfiles, 6 claims y 0
claims `supported` en cada semilla. Esto es una prueba de integración y
reproducibilidad, no una aceptación estadística del protocolo predictivo.
