# Investigación

Esta carpeta contiene protocolos, estudios y auditorías reproducibles. No es una
segunda fuente del estado del producto: para capacidades implementadas consultar
primero [`../docs/roadmap.md`](../docs/roadmap.md).

## Ciclo de trabajo

1. **Protocolo** — define antes de ejecutar la pregunta, matriz, semillas, métricas y
   criterios de validez.
2. **Ejecución** — produce artefactos en `.symbiont/runs/` u otra ruta explícita de
   trabajo; esos datos son mutables y no constituyen por sí solos un resultado.
3. **Estudio congelado** — copia el protocolo, resultados, manifest y checksums en
   `studies/<fecha>-<nombre>/` cuando el resultado está cerrado y reproducible.
4. **Auditoría** — documenta procedencia, límites, fallos y correcciones en `audits/`.

## Inventario actual

### Protocolos activos

- [`protocols/README.md`](protocols/README.md): atención causal, second look,
  heritage stress y simulación sintética.
- [`signal-knowledge-study.md`](signal-knowledge-study.md): estudio de aceptación
  del conocimiento de señales, con límites de muestra y recursos documentados.

### Auditorías históricas

Las auditorías `v0.13`, `v0.14`, `v0.15`, `v0.19` y `v0.24` están congeladas por
commit y conservan sus propios protocolos y resultados. Son evidencia histórica y
metodológica; no deben agregarse entre versiones ni presentarse como validación del
runtime actual.

- [`audits/2026-09-v013/`](audits/2026-09-v013/) — ronda exploratoria inicial.
- [`audits/2026-09-v014/`](audits/2026-09-v014/) — herencia longitudinal.
- [`audits/2026-09-v015/`](audits/2026-09-v015/) — integridad experimental y rendimiento.
- [`audits/2026-09-v019/`](audits/2026-09-v019/) — presupuesto, second look y estrés.
- [`audits/2026-09-v024/`](audits/2026-09-v024/) — auditoría corregida; conserva límites
  y un defecto de warmup documentado, por lo que no es un cierre general de capacidad.

### Estudios congelados

[`studies/`](studies/) contiene el formato reservado para resultados cerrados
(`PROTOCOL.md`, `ANALYSIS.md`, `MANIFEST.json`, `RESULTS.json` y `checksums.txt`).
Actualmente no hay carpetas de estudios congelados; los resultados existentes
permanecen en auditorías o estudios nombrados explícitamente en la raíz.

### Decisiones

[`decisions/`](decisions/) contiene ADRs que fijan límites de arquitectura y método.
Las decisiones no sustituyen a un protocolo ni prueban una capacidad.

## Reglas de interpretación

- Un resultado exploratorio no es una mejora demostrada.
- No mezclar commits, semillas o matrices que cada auditoría mantenga separadas.
- La verdad del simulador/evaluador no entra en las decisiones del organismo.
- Las mediciones del host real y la observabilidad tienen que declarar su alcance;
  una prueba de contrato no equivale a QA visual ni a una medición de producción.
