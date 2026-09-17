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
| boundary-adr1 | normative | 01#que-es | docs/adr/ADR-0001-two-package-boundary.md |
| ground-truth-adr2 | normative | 01#mecanismo | docs/adr/ADR-0002-ground-truth-isolation.md |
| boundary-enforced-import | implementation | 01#evidencia | tests/experimental_integrity/test_ground_truth_boundary.py::test_ast_symbiont_never_imports_symbiont_lab |
| boundary-enforced-signature | implementation | 01#evidencia | tests/experimental_integrity/test_ground_truth_boundary.py::test_agent_cognition_has_no_ground_truth_parameters |
| kernel-inmutable-limits | implementation | 01#mecanismo | src/symbiont/cognition/limits.py::KernelLimits |
| kernel-inmutable-design | normative | 01#mecanismo | docs/design/endogenous-plasticity.md |
| funcion-no-decoracion | normative | 01#no-metafora | docs/artificial-life-model.md |
| privacidad-capability | implementation | 02#mecanismo | src/symbiont/host/contracts.py::Capability |
| privacidad-reading-class | implementation | 02#mecanismo | src/symbiont/host/readings.py::ReadingPrivacyClass |
| welford-running-stats | implementation | 02#mecanismo | src/symbiont/host/acclimation.py::RunningStats |
| welford-capability-baseline | implementation | 02#mecanismo | src/symbiont/host/acclimation.py::CapabilityBaseline |
| drift-aware-baseline | implementation | 02#mecanismo | src/symbiont/host/drift.py::DriftAwareBaseline |
| adaptive-sense-model | implementation | 02#mecanismo | src/symbiont/host/adaptive.py::AdaptiveSenseModel |
| pair-accumulator-pruning | implementation | 02#mecanismo | src/symbiont/host/adaptive.py::PairAccumulator |
| regime-shift-observed | empirical | 02#evidencia | tests/unit/host/test_host_drift.py::test_sustained_shift_confirms_as_regime_shift_after_run_length |
| creep-observed | empirical | 02#evidencia | tests/unit/host/test_host_drift.py::test_slow_creep_confirms_after_creep_run_without_ever_triggering_regime_shift |
| no-classification-surface-observed | empirical | 02#evidencia | tests/unit/host/test_acclimation.py::test_baseline_exposes_no_classification_surface |
| redundancy-pruning-observed | empirical | 02#evidencia | tests/unit/test_adaptive_senses.py::test_highly_redundant_sense_is_skipped_when_complementary_signal_exists |
| node-edge-kinds | implementation | 03#mecanismo | src/symbiont/cognition/types.py::NodeKind |
| graph-activate | implementation | 03#mecanismo | src/symbiont/cognition/graph.py::activate |
| shadow-prediction-lifecycle | implementation | 03#mecanismo | src/symbiont/cognition/learning.py::ShadowPrediction |
| metaplasticity-objective | implementation | 03#mecanismo | src/symbiont/cognition/metaplasticity.py::LearningObjective |
| safety-state-frozen | implementation | 03#mecanismo | src/symbiont/cognition/metaplasticity.py::SafetyState |
| activation-order-independent-observed | empirical | 03#evidencia | tests/unit/cognition/test_graph.py::test_activation_is_independent_of_node_and_edge_construction_order |
| oja-update-observed | empirical | 03#evidencia | tests/unit/cognition/test_learning.py::test_oja_update_moves_weight_toward_correlated_activity |
| safe-mode-observed | empirical | 03#evidencia | tests/unit/cognition/test_metaplasticity.py::test_safety_state_freezes_after_three_consecutive_failures |
| attention-not-classification | normative | 04#mecanismo | docs/adr/ADR-0003-attention-is-not-classification.md |
| attention-budget | implementation | 04#mecanismo | src/symbiont/core/attention.py::AttentionBudget |
| belief-model | implementation | 04#mecanismo | src/symbiont/core/beliefs.py::BeliefModel |
| evidence-revision-ledger | implementation | 04#mecanismo | src/symbiont/core/evidence.py::EvidenceRevisionLedger |
| dissent-record | implementation | 04#mecanismo | src/symbiont/core/evidence.py::DissentRecord |
| infinite-uncertainty-wins-observed | empirical | 04#evidencia | tests/unit/core/test_attention.py::test_infinite_uncertainty_always_wins_over_finite |
| belief-strengthens-label-free-observed | empirical | 04#evidencia | tests/unit/core/test_beliefs.py::test_belief_strengthens_without_ground_truth |
| dissent-preserved-observed | empirical | 04#evidencia | tests/unit/core/test_evidence_revision.py::test_conflicting_evidence_still_revises_but_records_dissent |
