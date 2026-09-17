# Portal Canónico de Documentación de Symbiont

Este portal organiza de forma sistemática la arquitectura, estado normativo, fundamentos matemáticos, diseños técnicos y evidencia experimental del monorepo **Symbiont Lab**.

La política de versionado y ciclo de vida de releases se define en [`VERSIONING.md`](VERSIONING.md).

---

## 1. Estado Normativo y Orientación del Proyecto

- [`roadmap.md`](roadmap.md) — **Fuente canónica del estado activo de desarrollo (north star, invariantes, hitos I/J/K vigentes).**
- [`history/roadmap-log.md`](history/roadmap-log.md) — **Historia completa de hitos A-H y bitácora de tracking por versión.**
- [`CHANGELOG.md`](CHANGELOG.md) — Historial consolidado de las 139 notas de release individuales.
- [`../ORGANISM.md`](../ORGANISM.md) — Registro histórico y evolutivo de las capacidades del organismo.
- [`glossary.md`](glossary.md) — Glosario técnico y vocabulario epistémico compartido.

---

## 2. Arquitectura del Sistema, la Entidad `symbiont` y Vida Artificial

- [`architecture.md`](architecture.md) — **Frontera epistemológica de dos paquetes** (`symbiont` como sujeto experimental vs `symbiont_lab` como aparato científico), **Tratado Técnico Integral del Organismo Symbiont** (estudio exhaustivo de los módulos de código `core`, `cognition`, `host`, `environment`, dinámica de activación en grafos recurrentes, contabilidad metabólica, homeostasis, memoria consolidada y ciclo de ejecución de ticks) y el **Modelo funcional de Vida Artificial (ALife)** con la justificación rigurosa de las analogías biológicas frente a metáforas decorativas.
- [`adr/README.md`](adr/README.md) — **Registro de Decisiones de Arquitectura (ADRs):** Justificación formal e invariantes permanentes (ADR-0001 a ADR-0007).
- [`safety/README.md`](safety/README.md) — **Límites de Seguridad y Consentimiento:** Contratos de telemetría de solo lectura y ciclo de vida del residente en anfitriones reales.

---

## 3. Compendio Matemático

- [`math/README.md`](math/README.md) — **Compendio Matemático Formal:** Demostraciones analíticas, estabilidad de Welford, EWMA con suelo congelado, atención causal por mochila voraz 0/1, actualización bayesiana, dinámica de Oja y selección causal con Treaps.
  - *Itinerario A:* Teoría de la decisión y seguridad bayesiana ([Caps. 01, 04, 05, 06, 07](math/README.md#rutas-pedagógicas-recomendadas)).
  - *Itinerario B:* Procesamiento de señales y estabilidad de Welford en el anfitrión ([Caps. 02, 03, 08](math/README.md#rutas-pedagógicas-recomendadas)).
  - *Itinerario C:* Arquitectura neuronal plástica y calibración estadística ([Caps. 09, 10](math/README.md#rutas-pedagógicas-recomendadas)).

---

## 4. Diseños Técnicos por Hito (`docs/design/`)

- [`design/README.md`](design/README.md) — **Índice temático de especificaciones ontogenéticas:**
  - *Hito E (Embodiment):* [`percepcion-y-embodiment.md`](design/percepcion-y-embodiment.md).
  - *Hito E2 (Plasticidad):* [`cognicion-y-plasticidad.md`](design/cognicion-y-plasticidad.md) y [`percepcion-y-embodiment.md`](design/percepcion-y-embodiment.md).
  - *Hitos F e I (Fisiología):* [`fisiologia-y-reproduccion.md`](design/fisiologia-y-reproduccion.md).
  - *Hito G (Población y Linaje):* [`fisiologia-y-reproduccion.md`](design/fisiologia-y-reproduccion.md) y [`cognicion-y-plasticidad.md`](design/cognicion-y-plasticidad.md).
  - *Hitos J y K (Predicción y Sociedad):* [`sociabilidad-y-desarrollo-predictivo.md`](design/sociabilidad-y-desarrollo-predictivo.md).

> [!NOTE]
> En la versión v0.80.15, los Hitos I (fisiología integrada), J (desarrollo predictivo) y K (sociabilidad emergente) cuentan con implementaciones consolidadas en el runtime, validadas mediante matrices de gates longitudinales; sus generalizaciones abiertas permanecen documentadas en cada especificación.

---

## 5. Metodología Experimental e Integridad Científica

- [`methodology/README.md`](methodology/README.md) — Metodología experimental y protocolos pre-registrados.
- [`../research/protocols/`](../research/protocols/) — Protocolos formales declarados con anterioridad a la recolección de datos.
- [`../research/studies/`](../research/studies/) — Especificaciones declarativas de estudios de replicación.
- [`../research/audits/`](../research/audits/) — Informes de auditoría adversarial, análisis de colapsos y verificación de límites.
- [`../research/decisions/`](../research/decisions/) — Registro histórico de decisiones metodológicas.

---

## 6. Operación Local y Trazabilidad Histórica

- **Lanzador Local de Residentes:** El script [`../scripts/run-ecosystem.sh`](../scripts/run-ecosystem.sh) orquesta la ejecución local de residentes y Observatory bajo un supervisor de ciclo de vida transparente (`--no-stdout`, persistencia en directorio de estado y selección de intérprete mediante `SYMBIONT_PYTHON`).
- **Planes Históricos:** [`_internal/plans/`](_internal/plans/) conserva planes de trabajo anteriores como evidencia de trazabilidad histórica (los campos `pending` reflejan el estado en el instante en que fueron redactados).

---

## 7. Documentación de Publicación Web

- [`web/README.md`](web/README.md) — **Puerta narrativa pública sobre qué es un Symbiont y qué muestra la experimentación**, sin sustituir el portal técnico. Cada capítulo cita su fuente exacta en [`web/FUENTES.md`](web/FUENTES.md).
