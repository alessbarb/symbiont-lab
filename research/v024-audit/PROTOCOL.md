# Protocolo v0.24

Fecha: 2026-09-12. Commit congelado: `a352c93d889aa901e53903bae844b894d78adeb6`, versión 0.24.0. Fuente extraída mediante `git archive` a `/tmp/symbiont-audit-a352c93`. No modificar motor, AGENTS.md, auditorías previas ni hacer commits.

## Matriz

100 hosts, 300 pasos y parámetros ecológicos por defecto del commit:

- Continuidad: semillas 3,7,11,17,23. Ruido .08,.18,.30,.50 con presupuesto 300 (20 simulaciones); herencia con destino semilla+1009 (25 simulaciones); atención causal con presupuestos 5,12,20 por mil (15 simulaciones); baseline (5).
- Comprobación en semillas distintas de las auditorías anteriores: barrido de ruido con todos los defaults v0.24 (211,223,239,251,269; .08,.18,.30,.45; presupuesto 360; 20 simulaciones). Atención causal con 101,127,149,173,199 y 12 por mil (5 simulaciones).
- Total previsto y sujeto a finalización de los archivos: 90 simulaciones principales, 2.700.000 eventos procesados. No son 90 mundos independientes: se reutilizan mundos entre condiciones. Cinco réplicas por bloque; las semillas publicadas por el proyecto no son un holdout secreto.
- Diagnósticos separados: invariancia de rasgos, idempotencia sin reportes, replay de votos idénticos, N/A longitudinal, rechazo de semillas duplicadas y cronología de selección de novedad.

## Interpretación

Resultados exploratorios: medias y rangos entre semillas, pares por mundo, sin significación estadística. El baseline v0.24 puede cambiar por RNG de agentes y recalibración; no atribuir la diferencia de versión a una sola corrección. El mundo exógeno conserva sus streams. El segundo sensor y los selectores son observadores, no intervenciones en el agente vivo.

Los archivos de estudios contienen agregados nativos, parámetros y duración; `baseline.json` contiene resultados por semilla. No se conserva un flujo individual de millones de eventos. Los digests de herencia sí se conservan. El barrido de ruido comprueba cantidad y Brier previo, no hashes de identidades seleccionadas: documentar esta limitación.

## Reproducción

Crear el snapshot solo en una carpeta nueva:

```bash
mkdir /tmp/symbiont-audit-a352c93
git archive a352c93 | tar -x -C /tmp/symbiont-audit-a352c93
PYTHONPATH=/tmp/symbiont-audit-a352c93/src .venv/bin/python -m pytest -q /tmp/symbiont-audit-a352c93/tests
```

Copiar `run.py`, `validation_seeds.py` y `diagnostics.py` a otra carpeta para conservar estos resultados. Ejecutar cada uno con el mismo `PYTHONPATH` y `.venv/bin/python`. Los estudios usan creación exclusiva (`open('x')`): no sobrescriben salidas existentes. Los diagnósticos escriben su propio JSON. `snapshot.json` registra hashes del snapshot y scripts.
