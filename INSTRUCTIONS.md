# Plan de migración no destructivo

## 1. Objetivo

Reorganizar progresivamente `symbiont-lab` hacia la nueva arquitectura conceptual sin perder código, historia funcional, evidencia científica ni capacidad de volver atrás.

Arquitectura objetivo:

```text
Symbiont
    El organismo, con evolución independiente.

Embodiment
    Librerías que acoplan el organismo a una forma concreta de existencia.

Modality
    Canales de señales de entrada/salida.
    Ejemplos: host, visión, lenguaje, abstracto, propiocepción.

Environment
    Medio donde el organismo interactúa y recibe consecuencias.

Lab
    Lugar donde se componen las piezas, se ejecutan experimentos,
    se observa, se analiza y se genera evidencia.
```

La migración debe demostrar las fronteras arquitectónicas antes de eliminar ninguna estructura antigua.

---

# 2. Principios obligatorios

## 2.1. No destruir durante la migración

Hasta completar la validación final:

- no borrar módulos antiguos;
- no eliminar APIs antiguas;
- no reescribir checkpoints;
- no modificar evidencia FROZEN;
- no mover estudios históricos de forma irreversible;
- no cambiar formatos persistidos salvo necesidad demostrada;
- no sustituir imports globalmente en una sola operación.

La primera migración debe ser fundamentalmente:

```text
COPY
→ ADAPT
→ VALIDATE
→ SWITCH
→ DEPRECATE
→ CLEANUP
```

Nunca:

```text
MOVE EVERYTHING
→ FIX WHAT BREAKS
```

---

# 3. Regla de procedencia

Todo artefacto existente debe conservarse hasta saber qué representa.

Antes de migrar un fichero o módulo, clasificarlo como:

```text
SYMBIONT
EMBODIMENT
MODALITY
ENVIRONMENT
LAB
OBSERVABILITY
GOVERNANCE
SHARED-UNRESOLVED
```

`SHARED-UNRESOLVED` significa:

> todavía no conocemos suficientemente su ownership.

No usar `shared`, `common` o `utils` como destino automático.

Si no está claro dónde pertenece algo, dejarlo temporalmente en su ubicación actual.

---

# 4. Estructura de destino

La nueva estructura ya habrá sido creada manualmente.

El agente debe tratarla como destino vacío o parcialmente vacío y no modificar su topología principal sin justificación.

Conceptualmente:

```text
<new-root>/
│
├── symbiont/
│
├── embodiment/
│
├── modality/
│
├── environment/
│
└── lab/
```

Subestructuras concretas pueden existir dentro de cada dominio, pero el agente debe respetar estas cinco responsabilidades.

---

# 5. Fase 0 — Congelar y documentar el estado inicial

Antes de copiar nada, registrar:

```text
current branch
HEAD SHA
origin/main SHA
working tree status
Python version
uv version
dependency lock hash
test baseline
known existing failures
```

También producir:

```text
migration/baseline.md
```

con:

- estructura actual relevante;
- suites de tests disponibles;
- número de tests passing/failing/skipped;
- fallos preexistentes;
- principales entry points;
- formatos persistidos relevantes;
- dependencias externas importantes.

No corregir problemas encontrados en esta fase salvo que impidan ejecutar la migración.

Separar claramente:

```text
PRE-EXISTING
```

de:

```text
INTRODUCED BY MIGRATION
```

---

# 6. Fase 1 — Inventario arquitectónico

Construir un inventario de módulos actuales.

Para cada módulo o paquete registrar:

```text
path
responsibility
main consumers
main dependencies
persistent formats used
tests
scientific impact
target domain
migration confidence
```

Ejemplo:

```text
src/.../genome
→ SYMBIONT

src/.../physics3d
→ ENVIRONMENT / EMBODIMENT candidate

src/.../body_schema
→ requires analysis

studies/
→ LAB

observatory backend/frontend
→ LAB / OBSERVABILITY
```

No migrar todavía elementos con ownership dudoso.

Resultado:

```text
migration/inventory.md
```

---

# 7. Fase 2 — Construir el grafo real de dependencias

Antes de reorganizar código, determinar qué depende actualmente de qué.

Como mínimo analizar:

```text
Symbiont ↔ World
Symbiont ↔ Physics3D
Symbiont ↔ Lab
Symbiont ↔ Observatory
Symbiont ↔ Embodiment
Embodiment ↔ Physics3D
Modality ↔ Environment
```

Buscar especialmente imports que violen la arquitectura objetivo.

Ejemplos:

```text
cognition → physics3d
genome → lab
symbiont core → observatory
learning → humanoid
```

No arreglarlos todavía silenciosamente.

Documentarlos en:

```text
migration/dependency-audit.md
```

clasificados como:

```text
VALID
TRANSITIONAL
ARCHITECTURAL VIOLATION
UNCERTAIN
```

---

# 8. Fase 3 — Extraer primero Symbiont lógicamente

`Symbiont` es la frontera prioritaria.

Copiar al nuevo árbol únicamente aquello que representa al organismo.

Objetivo:

```text
symbiont/
```

debe contener el estado y comportamiento intrínsecos del organismo.

Ejemplos probables:

```text
cognition
memory
learning
development
genetics
agency
prediction
private models
self-model
lineage
organism persistence
```

Pero la clasificación debe basarse en el código real.

No copiar dentro de `symbiont`:

```text
PyBullet
humanoid definitions
world geometry
experiment runners
observatory
study protocols
UI
environment semantics
```

---

# 9. Fase 4 — Crear una API explícita de Symbiont

Antes de migrar consumidores, identificar la superficie pública necesaria.

El objetivo es que el resto del sistema no tenga que importar internals del organismo.

Crear o consolidar una API equivalente a:

```text
symbiont.api
```

que exponga únicamente capacidades necesarias.

Por ejemplo:

```text
organism lifecycle
signal ingestion
action production
checkpoint/load/save
identity
lineage
public telemetry
capability discovery
```

No introducir tipos semánticos propios de modalidades concretas.

Evitar:

```text
VisionFrame
LanguageToken
HumanoidJoint
PhysicsObservation
```

dentro del núcleo salvo que ya exista una justificación arquitectónica independiente del dominio.

---

# 10. Fase 5 — Compatibilidad temporal

La estructura antigua debe seguir funcionando mientras la nueva se valida.

Usar temporalmente adaptadores o reexports:

```python
old.path.Symbol
    →
new.path.Symbol
```

cuando sea razonable.

El objetivo es evitar cambiar centenares de consumidores a la vez.

Marcar explícitamente estos puentes como:

```text
MIGRATION COMPATIBILITY LAYER
```

y mantener una lista de ellos.

Resultado:

```text
migration/compatibility-layer.md
```

No permitir que esta capa se convierta en arquitectura permanente.

---

# 11. Fase 6 — Migrar Embodiment

Clasificar aquí únicamente mecanismos de acoplamiento.

Embodiment debe responder:

> ¿Cómo se conecta este organismo con una determinada configuración externa?

Puede incluir:

```text
body adapters
receptor/effectors binding
apparatus binding
re-embodiment
embodiment epochs
sensorimotor coupling
```

No debe absorber automáticamente:

```text
vision
language
physics
world dynamics
cognition
```

Si un componente mezcla varias responsabilidades, dividirlo solo después de haber identificado claramente las responsabilidades existentes.

---

# 12. Fase 7 — Migrar Modality

Crear modalidades como canales reutilizables.

Ejemplos conceptuales:

```text
host
vision
audio
proprioception
language-signal
abstract
```

Una Modality debe describir:

```text
signal structure
sampling
input/output transport
normalization if necessary
timing
channel capabilities
```

No debe introducir significado cognitivo.

Ejemplo:

```text
CORRECT:
2D receptor array

INCORRECT:
recognized object = "chair"
```

Para lenguaje:

```text
CORRECT:
discrete/continuous signal stream

QUESTIONABLE:
noun
verb
semantic role
syntax tree
```

Cualquier semántica predefinida debe revisarse antes de migrarse como modality.

---

# 13. Fase 8 — Migrar Environment

Environment representa el lugar donde ocurre la interacción.

Puede incluir:

```text
Physics3D
world state
surfaces
obstacles
resources
environment dynamics
external actors
ground truth
```

Debe mantenerse el principio:

```text
Environment may contain truth.

Symbiont must not receive that truth
unless it can obtain it through its modalities.
```

Separar cuidadosamente:

```text
environment internal state
```

de:

```text
observable signal
```

---

# 14. Fase 9 — Consolidar Lab

Solo después de haber identificado las demás fronteras.

Lab debe terminar conteniendo principalmente:

```text
composition
experiments
protocols
studies
baselines
ablations
runners
analysis
evidence
evaluation
scientific orchestration
```

Lab puede depender de:

```text
Symbiont
Embodiment
Modality
Environment
```

pero estos no deben depender de Lab.

Regla esperada:

```text
LAB → everything

everything -X→ LAB
```

salvo interfaces de control claramente justificadas.

---

# 15. Observatory y Governance

No forzar su clasificación inmediata dentro de las cinco categorías si hacerlo empeora las fronteras.

Durante esta migración pueden permanecer temporalmente donde están.

Tratar:

```text
Observatory
Governance
```

como sistemas auxiliares con ownership explícito.

No convertirlos en repositorios separados en esta fase.

---

# 16. Validación incremental

Después de migrar cada dominio:

1. ejecutar tests unitarios del dominio;
2. ejecutar tests de integración directamente relacionados;
3. ejecutar architectural/import checks;
4. comparar comportamiento con baseline;
5. verificar persistencia;
6. verificar checkpoint restore;
7. verificar re-embodiment cuando corresponda;
8. ejecutar equivalence si el cambio toca ejecución científica relevante.

No esperar al final para descubrir roturas.

---

# 17. Validación específica de identidad del organismo

Debe demostrarse expresamente que la reorganización no cambia qué es el Symbiont.

Probar:

```text
old load → old runtime
old load → new runtime
new save → new load
checkpoint → restore
checkpoint → reembodiment → restore
lineage preservation
development preservation
cognition preservation
```

Cuando sea posible, comparar:

```text
state hashes
serialized fields
telemetry
behavior
```

No exigir byte equality cuando el formato legítimamente cambie, pero cualquier diferencia debe estar explicada.

---

# 18. Prueba de independencia de Symbiont

Esta es una condición esencial.

La nueva unidad `symbiont` debe poder:

```text
install
import
run unit tests
create organism
save organism
load organism
```

sin requerir:

```text
PyBullet
Physics3D
Observatory
specific bodies
studies
experimental datasets
Lab UI
```

Si no se puede cumplir, documentar qué dependencia sigue impidiendo la separación.

No ocultarla.

---

# 19. Tests arquitectónicos nuevos

Añadir enforcement automático.

Como mínimo:

```text
symbiont -X→ lab
symbiont -X→ environment
symbiont -X→ physics3d
symbiont -X→ observatory
symbiont -X→ concrete modality implementations
```

Y revisar:

```text
symbiont → embodiment
```

porque idealmente el organismo debería depender solo de abstracciones propias o interfaces muy estrechas.

Además:

```text
environment -X→ cognition internals
modality -X→ cognition internals
embodiment -X→ cognition internals
```

salvo APIs públicas expresamente permitidas.

---

# 20. No modificar persistencia prematuramente

Los checkpoints y `.symbiont` existentes son especialmente sensibles.

Durante la primera migración:

- preservar schema actual;
- preservar loaders;
- preservar migrations;
- preservar lineage;
- preservar embodiment history;
- preservar genome;
- preservar private models.

Si la nueva arquitectura exige un nuevo schema, tratarlo como una migración independiente posterior.

No mezclar:

```text
filesystem/module migration
```

con:

```text
persistent-state migration
```

salvo necesidad estricta.

---

# 21. Estudios y evidencia

No mover ni reescribir evidencia histórica solo para adaptarla a la nueva estructura.

Los experimentos anteriores deben seguir siendo interpretables.

Mantener:

```text
study identifiers
manifest formats
frozen evidence
preregistrations
results
revision IDs
execution fingerprints
```

Si cambian rutas de código, registrar mecanismos de compatibilidad.

---

# 22. Estrategia Git

La migración debe realizarse en commits pequeños y conceptualmente coherentes.

Ejemplo:

```text
1. add migration skeleton
2. add Symbiont package copy
3. establish Symbiont public API
4. add compatibility imports
5. migrate internal consumers
6. add architecture guards
7. migrate embodiment
8. migrate modalities
9. migrate environment
10. consolidate lab
11. remove dead compatibility code
```

No mezclar en el mismo commit:

```text
mass moves
behavioral fixes
scientific changes
formatting
new features
```

Un commit de migración debe intentar ser semánticamente neutro.

---

# 23. Regla ante bugs encontrados

La migración probablemente descubrirá bugs existentes.

No arreglarlos automáticamente dentro del mismo cambio.

Clasificarlos como:

```text
PRE-EXISTING BUG
MIGRATION BLOCKER
MIGRATION-INTRODUCED BUG
```

Solo corregir inmediatamente:

```text
MIGRATION BLOCKER
MIGRATION-INTRODUCED BUG
```

Los demás deben registrarse como trabajo separado.

---

# 24. Condición para empezar a retirar la estructura antigua

No eliminar rutas antiguas hasta cumplir simultáneamente:

```text
all relevant imports migrated
unit tests pass
integration tests pass
architecture gates pass
checkpoint compatibility verified
scientific equivalence verified where applicable
no runtime consumer uses legacy paths
documentation points to new paths
```

Solo entonces marcar las rutas anteriores como deprecated.

---

# 25. Fase de deprecación

Primero:

```text
old path
→ compatibility import
→ warning/documentation
```

Después de un ciclo completo de validación:

```text
remove compatibility import
```

No hacer ambas cosas dentro de la migración inicial.

---

# 26. Criterios de éxito

La migración se considera correcta cuando:

### Symbiont

```text
tiene identidad propia
es instalable/probable independientemente
no conoce Environment
no conoce Lab
no conoce modalidades concretas
no conoce Physics3D
mantiene sus estados persistidos
```

### Embodiment

```text
acopla sin aportar cognición
puede cambiar sin redefinir Symbiont
permite reembodiment sin reset cognitivo
```

### Modality

```text
transporta señales
no inyecta significado
es reutilizable entre embodiments/environments cuando proceda
```

### Environment

```text
posee dinámica y ground truth
no filtra semántica privada al organismo
solo afecta al organismo mediante interacción legítima
```

### Lab

```text
compone
ejecuta
observa
experimenta
analiza
```

y no constituye una dependencia del organismo.

---

# 27. Entregables del agente

Al finalizar, el agente debe producir:

```text
migration/baseline.md
migration/inventory.md
migration/dependency-audit.md
migration/mapping.md
migration/compatibility-layer.md
migration/validation-report.md
migration/open-issues.md
```

`mapping.md` debe permitir rastrear:

```text
old path
→ new path
→ status
→ compatibility layer
→ validation
```

Ejemplo:

```text
src/foo/bar.py
→ symbiont/.../bar.py
→ MIGRATED
→ old import re-export active
→ unit + integration PASS
```

---

# 28. Estado final de esta primera migración

Esta primera fase NO debe intentar dejar el proyecto «perfectamente limpio».

El estado deseado es:

```text
NEW ARCHITECTURE WORKS
+
OLD ARCHITECTURE REMAINS RECOVERABLE
+
BEHAVIOR IS PRESERVED
+
BOUNDARIES ARE ENFORCED
+
REMAINING DEBT IS EXPLICIT
```

Después podrá ejecutarse una segunda operación específicamente de limpieza.

---

# 29. Instrucción principal para el agente

Durante toda la migración:

> Prioriza preservación sobre limpieza. Si existe duda sobre el ownership, comportamiento, procedencia o compatibilidad de un elemento, no lo elimines ni lo fuerces dentro de la nueva arquitectura. Documenta la incertidumbre, mantén el original y continúa con las partes cuya migración pueda demostrarse con evidencia.

La migración debe hacer la nueva arquitectura posible sin convertir decisiones todavía inciertas en pérdidas irreversibles.
