# Research Protocols

Protocols define immutable scientific procedures and measurement methodologies independently of software version numbers.

## Active Protocols
- **`attention.causal` (v3):** Evaluates sequential causal attention allocation under fixed per-1000 observation budgets with common eligibility filtering (ADR-0007).
- **`evidence.second-look` (v2):** Quantifies information gain and Brier score revision via shadow-mode evidence sensors across noise regimes (ADR-0005, ADR-0006).
- **`heritage.stress` (v2):** Tests multi-generation epistemic resilience and prior transfer under adversarial reporter poisoning and ecological shifts.
- **`simulate` (v1):** Synthetic ecology baseline run with deterministic orthogonal RNG streams (ADR-0004).
- **`perception.identity-equivalence` (v1):** Verifica que el bridge sensorial identidad conserva exactamente el valor del camino histórico.
- **`perception.adaptive-delta-discovery` (v1):** Caracteriza si una transformación desarrollada sin target evaluator-side captura cambio temporal útil.
- **`perception.temporal-scale-specialisation` (v1):** Contrasta nichos perceptivos rápidos y lentos sobre una misma fuente.
- **`perception.modality-specialisation` (v1):** Evalúa contribución funcional diferenciada de modalidades opacas.
- **`perception.sensory-duplication-divergence` (v1):** Audita lineage, divergencia y boundedness de duplicación sensorial.
- **`perception.sensory-ablation` (v1):** Exige evidencia causal mediante ablación de receptores frente a controles.
- **`perception.multisource-specialisation` (v1):** Compara integración multisource adaptativa contra single-source y control frozen.
- **`perception.same-world-phenotype-divergence` (v1):** Mide convergencia o divergencia perceptiva sin exigir una como resultado positivo.
- **`perception.autonomous-sensory-selection` (v1):** Evalúa selección organism-side de receptores frente a controles frozen/random sin target evaluator-side.
- **`perception.sensory-regime-reversal` (v1):** Comprueba reversión de preferencia perceptiva tras cambio de régimen.
- **`perception.sensory-null-selection` (v1):** Control nulo contra falsa especialización sobre ruido independiente.
- **`perception.experience-conditioned-phenotype` (v1):** Caracteriza convergencia/divergencia bajo microdiferencias de experiencia.

## Relación con ejecuciones

Los protocolos activos no implican que exista un resultado congelado. Las ejecuciones
provisionales pertenecen a `.symbiont/runs/` o a una ruta de trabajo indicada por el
runner; solo una carpeta completa bajo `research/studies/` se considera estudio
congelado.

### Adaptive Sensory System

Los ocho protocolos iniciales `perception.*` tienen resultados registrados.
Los cuatro protocolos de selección autónoma están preregistrados y registrados
en el runner, pero permanecen sin resultado hasta su ejecución real. Las
etiquetas evaluator-side se calculan después de producir perceptos y nunca se
retroalimentan al organismo.
