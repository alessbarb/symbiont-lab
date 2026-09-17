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
| `historica` | `docs/releases/archive/`, `docs/history/` | contexto histórico, no prueba del estado actual |

**Prohibida:** `docs/_internal/` nunca es fuente válida para `docs/web/`.

**Regla:** una afirmación empírica ("se observó", "mejoró", "resiste",
"emerge") no queda respaldada solo por una fuente `normative` o
`implementation`; necesita al menos una fila `empirical`.

Un locator `#anchor` en la columna Source solo es válido cuando la propia
fuente es otro capítulo de `docs/web/` (que tendrá anclas `<a id="...">`
explícitas por convención de este mismo documento); citar un documento
normativo/de diseño canónico debe usar la ruta completa al archivo, sin
fragmento `#anchor` (si hace falta referenciar una sección, se nombra en el
texto de la afirmación, no mediante ancla).

El séptimo chequeo de la especificación — "toda afirmación empírica
etiquetada en su capítulo tiene al menos una fila `empirical`" — queda
diferido: no es implementable hasta que existan capítulos de los que leer
esas etiquetas.

## Claims

Las celdas de la columna Source son rutas planas (sin backticks ni marcado
Markdown adicional): `path`, `path::symbol`, o `path#anchor` son las únicas
formas permitidas.

| Claim ID | Tipo | Chapter anchor | Source |
| --- | --- | --- | --- |
| _(vacío — las filas se añaden capítulo a capítulo en el plan de redacción)_ | | | |
