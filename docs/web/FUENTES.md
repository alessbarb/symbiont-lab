# Fuentes — trazabilidad de docs/web/

Cada afirmación no trivial en `docs/web/` tiene una fila aquí, con un ID
estable y un localizador resoluble en ambos extremos. Un test
(`tests/docs/test_web_sources_exist.py`) verifica automáticamente que cada
ruta/símbolo/ancla citados existen de verdad.

## Tipos de fuente válidos

| Tipo | Fuentes válidas | Para qué |
| --- | --- | --- |
| `normative` | `docs/adr/`, `docs/architecture/`, `docs/design/`, `docs/roadmap.md`, `docs/artificial-life-model.md` | definiciones, fronteras, invariantes |
| `formal` | `docs/math/` | respaldo matemático |
| `implementation` | `src/`, `observatory/` + tests | comportamiento realmente implementado |
| `empirical` | `research/` + tests/estudios | resultados observados experimentalmente |

**Prohibida:** `docs/_internal/` nunca es fuente válida para `docs/web/`.

**Regla:** una afirmación empírica ("se observó", "mejoró", "resiste",
"emerge") no queda respaldada solo por una fuente `normative` o
`implementation`; necesita al menos una fila `empirical`.

## Claims

| Claim ID | Tipo | Chapter anchor | Source |
| --- | --- | --- | --- |
| _(vacío — las filas se añaden capítulo a capítulo en el plan de redacción)_ | | | |
