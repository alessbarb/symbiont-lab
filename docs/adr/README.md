# Registro de Decisiones de Arquitectura (`docs/adr/`)

Este directorio contiene los **Architecture Decision Records (ADR)** canónicos de Symbiont y Symbiont Lab. Cada documento registra una decisión arquitectónica fundamental, su contexto, motivación, alternativas descartadas y consecuencias para la integridad experimental.

---

## Catálogo de Decisiones Aceptadas

| ADR | Título | Estado | Invariante Central |
| :--- | :--- | :--- | :--- |
| **[ADR-0001](ADR-0001-two-package-boundary.md)** | Two-Package Architecture Boundary | Aceptado | Desacoplamiento estricto: `symbiont` jamás importa `symbiont_lab`. |
| **[ADR-0002](ADR-0002-ground-truth-isolation.md)** | Synthetic Ground Truth Isolation | Aceptado | Cero conocimiento descendente (*zero downward knowledge*): el organismo solo observa señales opacas. |
| **[ADR-0003](ADR-0003-attention-is-not-classification.md)** | Attention is Not Classification | Aceptado | La atención es asignación causal de presupuesto finito, nunca un juicio de amenaza o detección de intrusiones. |
| **[ADR-0004](ADR-0004-separated-rng-streams.md)** | Separated RNG Streams | Aceptado | Flujos pseudoaleatorios desacoplados vía SHA-256 (SplitMix64) para garantizar independencia causal entre rasgos, anfitriones e intervenciones. |
| **[ADR-0005](ADR-0005-shadow-only-second-look.md)** | Shadow-Only Second-Look Evidence Probes | Aceptado | El segundo vistazo (*second look*) profundiza en resolución de muestreo sin alterar el estado del anfitrión ni ejecutar remediación. |
| **[ADR-0006](ADR-0006-evidence-revision-identity.md)** | Evidence Revision Identity | Aceptado | La contradicción se preserva en registros de disidencia (`DissentRecord`); el sistema nunca suaviza discrepancias estadísticas significativas. |
| **[ADR-0007](ADR-0007-common-causal-eligibility.md)** | Common Causal Eligibility for Attention Allocation | Aceptado | Elegibilidad previa al muestreo basada exclusivamente en información causal disponible en el tick actual ($t$). |
| **[ADR-0008](ADR-0008-experience-versus-world-execution.md)** | Experience versus World Execution (EW-001) | Aceptado | Cada ejecución declara un `RunKind`; la adquisición termina antes de la pérdida irreversible de viabilidad; el World no rescata el cuerpo. |
| **[ADR-0009](ADR-0009-state-x-immutable-run-provenance.md)** | State-X and Immutable Run Provenance (EW-002) | Aceptado | Cada ejecución referencia un checkpoint inicial y final inmutable y direccionado por contenido. |
| **[ADR-0010](ADR-0010-observer-architecture-preservation.md)** | Observer Architecture Preservation (EW-003) | Aceptado | P0–P7 son normativos: sin proyecciones por tick, sin bus paralelo, independencia de observabilidad. |
