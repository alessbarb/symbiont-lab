# Protocolo exploratorio — 2026-09-12

## Alcance

Motor v0.13.0 sin modificaciones. Solo simulación sintética. El observador intercepta los generadores para registrar etiquetas y hashes; las decisiones siguen recibiendo exclusivamente observaciones. No se modifican los archivos históricos `.symbiont/`.

## Primera ronda

100 hosts × 300 pasos; semillas 3, 7, 11, 17, 23. Diez condiciones:
configuración por defecto; sin reporteros invertidos; 30% de reporteros invertidos;
sin heterogeneidad; sin deriva; deriva de magnitud 0.45; sin amenazas;
curiosidad local anulada; creencia colectiva neutralizada; reputación fija.

Las tres últimas son ablaciones temporales mediante `unittest.mock.patch`,
restauradas al terminar cada ejecución. La creencia neutral es `(0.5, 0.0)`:
retira a la vez probabilidad y certeza colectiva, pero mantiene los reportes.
No equivale a retirar solamente el término colectivo del score.

Se registran resultados individuales, parámetros, versión Python, commit,
hash del runner, SHA-256 de la secuencia de eventos y conteos por tipo de evento.
No se ajustan umbrales del motor durante esta ronda.

## Preguntas

- ¿Qué proporción de amenazas se investiga y cuál se clasifica como amenaza?
- ¿Dónde se concentran los fallos: ransomware, bot o stealth sintéticos?
- ¿Cuánto cuestan curiosidad y conocimiento colectivo en atención a benignos?
- ¿La deriva, diversidad o inversión de reportes deterioran las métricas?
- ¿Una semilla idéntica conserva la misma ecología entre condiciones?

## Interpretación

Cinco semillas constituyen un piloto, no una validación concluyente. Promedios
entre semillas y diferencias por semilla son descriptivos. Los hashes distintos
impiden describir las comparaciones como reproducción de los mismos eventos.
El porcentaje de semillas concordantes no es una probabilidad de verdad.

La métrica original `detection_rate` es recall de atención. La clasificación
usa `believes_threat` independientemente de si se investigó. Las tasas sin
denominador deben considerarse no definidas, aunque el motor devuelva cero.
La precisión no sustituye al coste de investigación; el control sin amenazas
permite medir atención innecesaria. Brier y calibración del motor requieren
revisar cómo se construye su probabilidad antes de interpretarlos.

## Reproducción

```bash
mkdir -p /tmp/symbiont-replay-6edb4c2
git archive 6edb4c2 | tar -x -C /tmp/symbiont-replay-6edb4c2
PYTHONPATH=/tmp/symbiont-replay-6edb4c2/src .venv/bin/python \
  research/2026-09-12/run_experiments.py --commit 6edb4c2 \
  --output /tmp/symbiont-audit.jsonl
```

El destino debe ser nuevo; el runner no sobrescribe resultados existentes.

## Cambio concurrente de versión

El checkout avanzó a v0.14 durante el trabajo. `results.jsonl` registra
6edb4c2; `replication.jsonl` registra b85b7fb. No agregar ambas tandas como
réplicas de una misma versión. Las siguientes ejecuciones usan archivos
exportados de commits explícitos en `/tmp/symbiont-audit-<commit>`, nunca
el `src/` que está evolucionando. `validation.txt` contiene 46 tests y no
debe atribuirse a v0.13; la validación aislada de v0.14 se registra aparte.

El runner se endureció después de las tandas iniciales: exige `--commit` y
verifica los archivos Python frente a ese commit. Los hashes del runner en
los JSON originales corresponden a la versión utilizada entonces; no se
reescriben retrospectivamente.
