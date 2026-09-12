# Protocolo de actualización v0.19

- Fuente: `eff5a0f30b26e72573df0a95333229c2f380985d` (`0.19.0`), congelada mediante `git archive` en `/tmp/symbiont-audit-eff5a0f`. Fecha: 2026-09-12.
- Alcance: auditar nuevas capas experimentales y comprobar pendientes de v0.15. Sin cambios de motor, commits, endpoints reales ni escrituras en `.symbiont/`.
- Matriz principal: semillas 3, 7, 11, 17, 23; 100 hosts y 300 pasos; restantes parámetros por defecto del commit. Presupuesto natural para `budget`; presupuesto fijo de 300 observaciones (10/1000) para `evidence`; ruido 0.18 y 0.50. Herencia: fuente = semilla, destino = semilla + 1009, cuatro condiciones y límite 24.
- 5 análisis de presupuesto + 10 de evidencia + 5 estudios de herencia × 5 simulaciones = **40 simulaciones / 1.200.000 eventos procesados**. Son mundos reutilizados para comparaciones, no 40 réplicas independientes; unidad experimental: cinco semillas o parejas fuente/destino.
- Medias entre semillas, rangos y signos; sin inferencia confirmatoria ni selección de la mejor semilla. Los rankings usan el flujo completo: son comparadores retrospectivos, no políticas online desplegables.
- `results.jsonl`: un encabezado y 20 estudios; `summary.json`: agregados reproducibles. `run.py` usa creación exclusiva para no sobreescribir resultados.
- `check_semantics.py`: cinco simulaciones adicionales del caso fuente 7/destino 1016, repetido para observar exportaciones; wrappers restaurados, sin alterar valores retornados ni decisiones. Incluye comprobación pequeña de semillas duplicadas. No contar como nuevas réplicas independientes.
- `diagnostics.json`: repetición del diagnóstico v0.15 con imports congelados v0.19. `tests.txt`: suite del commit. `snapshot.json`: hashes de fuente y versión Python.

## Reproducción

```bash
# Crear la carpeta de snapshot solo si no existe; no mezclar árboles.
mkdir /tmp/symbiont-audit-eff5a0f
git archive eff5a0f30b26e72573df0a95333229c2f380985d | tar -x -C /tmp/symbiont-audit-eff5a0f
PYTHONPATH=/tmp/symbiont-audit-eff5a0f/src .venv/bin/python -m pytest -q /tmp/symbiont-audit-eff5a0f/tests
# Copiar los scripts a otra carpeta de resultados para preservar esta evidencia.
PYTHONPATH=/tmp/symbiont-audit-eff5a0f/src .venv/bin/python research/v019-audit/run.py
.venv/bin/python research/v019-audit/summarize.py
PYTHONPATH=/tmp/symbiont-audit-eff5a0f/src .venv/bin/python research/v019-audit/check_semantics.py
PYTHONPATH=/tmp/symbiont-audit-eff5a0f/src .venv/bin/python research/v015-audit/diagnostics.py
```

Las salidas históricas de `research/v015-audit/` se conservan intactas. No se repiten sus nueve escenarios ni el estudio longitudinal completo; se verifica que sus módulos de motor siguen idénticos y se vuelven a ejecutar los diagnósticos residuales.
