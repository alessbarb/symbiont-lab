---
id: explanation.web.fuentes
title: "Sources"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Sources — traceability of docs/web/

Each non-trivial claim in `docs/web/` has a row here, with a stable ID and a resolvable locator at both ends. A test
(`tests/docs/test_web_sources_exist.py`) automatically verifies that each
route/symbol/anchor cited truly exists.

## Valid source types

| Type | Valid sources | What for |
| --- | --- | --- |
| `normative` | `docs/adr/`, `docs/architecture.md`, `docs/design/`, `docs/roadmap.md` | definitions, boundaries, invariants |
| `formal` | `docs/math/` | mathematical backing |
| `implementation` | `src/`, `observatory/` + tests | actually implemented behavior |
| `empirical` | `research/` + tests/studies | experimentally observed results |
| `historical` | `docs/CHANGELOG.md`, `docs/history/` | historical context, not proof of current state |

Only the five types in the table above are valid sources — there is no
internal working directory from which to cite in this repository.

**Rule:** an empirical claim ("observed", "improved", "resists",
"emerges") is not backed only by a `normative` or
`implementation` source; it needs at least one `empirical` row.

A locator `#anchor` in the Source column is only valid when the
source itself is another chapter of `docs/web/` (which will have explicit `<a id="...">`
anchors by convention of this same document); citing a canonical normative/design document
must use the full path to the file, without
a `#anchor` fragment (if a section needs to be referenced, it is named in the
text of the claim, not through an anchor).

The seventh check of the specification — "every empirical claim
labeled in its chapter has at least one `empirical` row" — is
deferred: it is not implementable until there are chapters from which to read
those labels.

## Claims

The cells of the Source column are flat paths (without backticks or additional Markdown markup): `path`, `path::symbol`, or `path#anchor` are the only
permitted forms.

| Claim ID | Type | Chapter anchor | Source |
| --- | --- | --- | --- |
| boundary-adr1 | normative | 01#que-es | docs/adr/ADR-0001-two-package-boundary.md |
| ground-truth-adr2 | normative | 01#mecanismo | docs/adr/ADR-0002-ground-truth-isolation.md |
| boundary-enforced-import | implementation | 01#evidencia | tests/experimental_integrity/test_ground_truth_boundary.py::test_ast_symbiont_never_imports_symbiont_lab |
| boundary-enforced-signature | implementation | 01#evidencia | tests/experimental_integrity/test_ground_truth_boundary.py::test_agent_cognition_has_no_ground_truth_parameters |
| kernel-inmutable-limits | implementation | 01#mecanismo | src/symbiont/cognition/limits.py::KernelLimits |
| kernel-inmutable-design | normative | 01#mecanismo | docs/explanation/concepts/03-cognition-and-plasticity.md |
| funcion-no-decoracion | normative | 01#no-metafora | docs/architecture.md |
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
| attention-budget | implementation | 04#mecanismo | src/symbiont/core/cognition/attention.py::AttentionBudget |
| belief-model | implementation | 04#mecanismo | src/symbiont/core/cognition/beliefs.py::BeliefModel |
| evidence-revision-ledger | implementation | 04#mecanismo | src/symbiont/core/cognition/evidence.py::EvidenceRevisionLedger |
| dissent-record | implementation | 04#mecanismo | src/symbiont/core/cognition/evidence.py::DissentRecord |
| infinite-uncertainty-wins-observed | empirical | 04#evidencia | tests/unit/core/test_attention.py::test_infinite_uncertainty_always_wins_over_finite |
| belief-strengthens-label-free-observed | empirical | 04#evidencia | tests/unit/core/test_beliefs.py::test_belief_strengthens_without_ground_truth |
| dissent-preserved-observed | empirical | 04#evidencia | tests/unit/core/test_evidence_revision.py::test_conflicting_evidence_still_revises_but_records_dissent |
| metabolic-ledger | implementation | 05#mecanismo | src/symbiont/core/embodiment/metabolism.py::MetabolicLedger |
| homeostatic-controller | implementation | 05#mecanismo | src/symbiont/core/embodiment/homeostasis.py::HomeostaticController |
| physiology-controller | implementation | 05#mecanismo | src/symbiont/core/embodiment/physiology.py::PhysiologyController |
| organism-dead-error | implementation | 05#mecanismo | src/symbiont/core/orchestration/runtime.py::OrganismDeadError |
| degradation-queue | implementation | 05#mecanismo | src/symbiont/core/embodiment/degradation.py::DegradationQueue |
| death-irreversible-observed | empirical | 05#evidencia | tests/unit/core/test_physiology.py::test_unrecoverable_pressure_causes_irreversible_death |
| death-refuses-execution-observed | empirical | 05#evidencia | tests/unit/core/test_physiology.py::test_runtime_refuses_execution_after_death |
| homeostasis-pauses-plasticity-observed | empirical | 05#evidencia | tests/unit/core/test_homeostasis.py::test_pressure_reduces_activity_and_pauses_plasticity |
| repair-not-free-observed | empirical | 05#evidencia | tests/unit/core/test_homeostasis.py::test_constitutive_repair_uses_resources_without_cognitive_request |
| excretion-observed | empirical | 05#evidencia | tests/unit/core/test_degradation.py::test_state_ages_and_is_excreted |
| ontogeny-controller | implementation | 06#mecanismo | src/symbiont/core/embodiment/ontogeny.py::OntogenyController |
| habitat-birth-authority | implementation | 06#mecanismo | src/symbiont/core/lineage/birth_authority.py::HabitatBirthAuthority |
| reproduction-boundary | implementation | 06#mecanismo | src/symbiont/core/orchestration/runtime.py::OrganismRuntime |
| reproduction-design | normative | 06#respaldo-formal | docs/explanation/concepts/06-reproduction-and-lineage.md |
| growth-costs-energy-observed | empirical | 06#evidencia | tests/unit/core/test_ontogeny.py::test_growth_is_constitutive_and_consumes_physical_energy |
| denied-birth-preserves-energy-observed | empirical | 06#evidencia | tests/unit/core/test_physiology.py::test_denied_birth_does_not_consume_parent_energy |
| birth-conserves-energy-observed | empirical | 06#evidencia | tests/unit/core/test_physiology.py::test_materialized_birth_conserves_parent_child_energy |
| germinal-tabula-rasa-observed | empirical | 06#evidencia | tests/unit/cognition/test_birth.py::test_base_graph_is_a_true_tabula_rasa |
| social-relation | implementation | 07#mecanismo | src/symbiont/core/social/relations.py::SocialRelation |
| resource-evidence-ledger | implementation | 07#mecanismo | src/symbiont/core/social/relations.py::ResourceEvidenceLedger |
| social-habitat | implementation | 07#mecanismo | src/symbiont/core/social/relations.py::SocialHabitat |
| diseno-sociabilidad-k | normative | 07#respaldo-formal | docs/explanation/concepts/07-ecology-and-sociability.md |
| valence-evidence-based-observed | empirical | 07#evidencia | tests/unit/core/test_social.py::test_relation_valence_is_evidence_based |
| relation-dimensions-separate-observed | empirical | 07#evidencia | tests/unit/core/test_social.py::test_relation_tracks_reciprocity_conflict_and_freshness |
| resource-evidence-revision-observed | empirical | 07#evidencia | tests/unit/core/test_social.py::test_resource_evidence_revises_a_previously_useful_token_after_repeated_denials |
| autonomous-emergence-observed | empirical | 07#implementado | tests/integration/studies/test_social_runtime_emergence.py::test_runtime_emergence_study_is_deterministic_and_uses_local_choices |
| shadow-lifecycle-j | implementation | 08#mecanismo | src/symbiont/cognition/learning.py::ShadowPrediction |
| structural-plasticity | implementation | 08#mecanismo | src/symbiont/cognition/structure.py::StructuralPlasticity |
| causal-selection-treap | implementation | 08#mecanismo | src/symbiont_lab/studies/common/causal_selection.py::OrderStatisticHistory |
| diseno-predictivo-j | normative | 08#respaldo-formal | docs/explanation/concepts/08-predictive-development.md |
| no-promotion-without-gain-observed | empirical | 08#evidencia | tests/unit/test_shadow_prediction.py::test_shadow_prediction_does_not_promote_without_gain |
| structural-memory-bounded-observed | empirical | 08#evidencia | tests/unit/cognition/test_structure.py::test_reconcile_bounds_memory_growth_over_many_distinct_pairs |
| methodology-principles | normative | 09#metodologia | docs/methodology/README.md |
| protocols-preregistration | normative | 09#preregistro | research/protocols/README.md |
| studies-declarative | normative | 09#preregistro | research/studies/README.md |
| audit-v013-provenance-correction | empirical | 09#preregistro | research/audits/historical/v013/ANALYSIS.md |
