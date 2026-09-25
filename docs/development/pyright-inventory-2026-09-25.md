# Inventario completo de Pyright — 2026-09-25

Este documento es una fotografía reproducible del diagnóstico global de Pyright sobre `src/` y `observatory/`. No modifica el comportamiento del código ni convierte los diagnósticos en excepciones. Cada entrada conserva archivo, línea, severidad, regla y mensaje normalizado.

## Comando y alcance

```bash
.venv/bin/pyright --outputjson > /tmp/pyright-inventory.json
```

La configuración aplicada es `pyrightconfig.json`; tests, artefactos generados e históricos permanecen fuera del alcance configurado. El inventario debe regenerarse tras cada bloque de correcciones; no es un baseline aceptable para ocultar errores.

## Resumen

- Archivos analizados: **486**
- Archivos con diagnósticos: **148**
- Errores: **769**
- Warnings: **133**
- Informaciones: **0**

## Reglas por severidad

| Severidad | Regla | Casos |
|---|---|---:|
| error | `reportArgumentType` | 491 |
| error | `reportAttributeAccessIssue` | 116 |
| error | `reportOptionalMemberAccess` | 38 |
| error | `reportGeneralTypeIssues` | 31 |
| error | `reportIndexIssue` | 21 |
| error | `reportOperatorIssue` | 18 |
| error | `reportCallIssue` | 17 |
| error | `reportOptionalSubscript` | 15 |
| error | `reportOptionalOperand` | 11 |
| error | `reportOptionalIterable` | 6 |
| error | `reportReturnType` | 4 |
| error | `reportAssignmentType` | 1 |
| warning | `reportMissingImports` | 118 |
| warning | `reportUnsupportedDunderAll` | 14 |
| warning | `reportUnusedExpression` | 1 |

## Archivos por volumen

| Casos | Archivo |
|---:|---|
| 78 | `src/symbiont_lab/app/physics3d_monitor.py` |
| 33 | `src/symbiont_lab/studies/perception/sensory_specialisation.py` |
| 31 | `src/symbiont/modeling/culture.py` |
| 30 | `src/symbiont_lab/physics3d/telemetry_v41.py` |
| 28 | `src/symbiont/genetics/migration.py` |
| 27 | `src/symbiont_lab/physics3d/runtime.py` |
| 25 | `src/symbiont_lab/studies/heritage/ecological_shift.py` |
| 24 | `src/symbiont/core/embodiment/memory.py` |
| 21 | `src/symbiont_lab/studies/learning/emergent_symbol_grounding.py` |
| 19 | `src/symbiont/core/signals/knowledge.py` |
| 19 | `src/symbiont_lab/app/physics3d_session.py` |
| 19 | `src/symbiont_lab/physics3d/reembodiment.py` |
| 18 | `observatory/resident.py` |
| 17 | `src/symbiont_lab/studies/learning/emergent_structured_communication.py` |
| 16 | `src/symbiont/modeling/symbols.py` |
| 16 | `src/symbiont_lab/world/adapter.py` |
| 14 | `src/symbiont/core/embodiment/episode.py` |
| 14 | `src/symbiont_lab/studies/campaigns/campaign.py` |
| 13 | `src/symbiont_lab/physics3d/resource.py` |
| 12 | `src/symbiont/actuation/commitment.py` |
| 12 | `src/symbiont/core/__init__.py` |
| 12 | `src/symbiont_lab/studies/learning/prospective_agency_embodied.py` |
| 11 | `src/symbiont/core/embodiment/adaptation.py` |
| 11 | `src/symbiont_lab/physics3d/engine.py` |
| 11 | `src/symbiont_lab/studies/physics3d/primitive_effects.py` |
| 10 | `src/symbiont_lab/modeling/architectures.py` |
| 9 | `src/symbiont/cognition/structure.py` |
| 9 | `src/symbiont/modeling/runtime.py` |
| 9 | `src/symbiont_lab/physics3d/humanoid.py` |
| 8 | `src/symbiont/modeling/experience.py` |
| 8 | `src/symbiont/modeling/sequences.py` |
| 8 | `src/symbiont_lab/cli/archive.py` |
| 7 | `src/symbiont/core/embodiment/body_schema.py` |
| 7 | `src/symbiont/core/social/ecology.py` |
| 7 | `src/symbiont/modeling/private_runtime.py` |
| 7 | `src/symbiont_lab/integration/integrated_habitat.py` |
| 7 | `src/symbiont_lab/studies/learning/independent_symbol_grounding.py` |
| 7 | `src/symbiont_lab/studies/world/genesis_viability.py` |
| 6 | `src/symbiont/core/embodiment/dynamics.py` |
| 6 | `src/symbiont/core/social/relations.py` |
| 6 | `src/symbiont_lab/physics3d/telemetry_binary.py` |
| 6 | `src/symbiont_lab/studies/attention/retrospective.py` |
| 6 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_counterfactual.py` |
| 6 | `src/symbiont_lab/studies/social_runtime_generations.py` |
| 6 | `src/symbiont_lab/studies/social_runtime_lifecycle.py` |
| 5 | `observatory/adapter.py` |
| 5 | `src/symbiont/core/domains/action.py` |
| 5 | `src/symbiont/modeling/registry.py` |
| 5 | `src/symbiont_lab/observation/physics3d.py` |
| 5 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_adaptation.py` |
| 4 | `src/symbiont/core/cognition/bridge_checkpoint.py` |
| 4 | `src/symbiont/core/orchestration/resident.py` |
| 4 | `src/symbiont_lab/app/run_controller.py` |
| 4 | `src/symbiont_lab/physics3d/telemetry.py` |
| 4 | `src/symbiont_lab/physics3d/telemetry_tools.py` |
| 4 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_agency.py` |
| 4 | `src/symbiont_lab/studies/learning/embodied_model_comparison.py` |
| 4 | `src/symbiont_lab/studies/learning/structured_communication_characterization.py` |
| 4 | `src/symbiont_lab/studies/perception/autonomous_selection.py` |
| 4 | `src/symbiont_lab/studies/physiology.py` |
| 4 | `src/symbiont_lab/studies/runtime_population.py` |
| 4 | `src/symbiont_lab/studies/social_runtime_replay.py` |
| 4 | `src/symbiont_lab/world/population.py` |
| 3 | `observatory/server.py` |
| 3 | `src/symbiont/actuation/effects.py` |
| 3 | `src/symbiont/agency/candidates.py` |
| 3 | `src/symbiont/core/signals/prediction.py` |
| 3 | `src/symbiont/host/hypotheses.py` |
| 3 | `src/symbiont_lab/kernel_characterization/runner.py` |
| 3 | `src/symbiont_lab/observation/projection.py` |
| 3 | `src/symbiont_lab/studies/embodiment/label_invariance.py` |
| 3 | `src/symbiont_lab/studies/heritage/stress.py` |
| 3 | `src/symbiont_lab/studies/learning/signal_knowledge.py` |
| 3 | `src/symbiont_lab/studies/reproduction_runtime.py` |
| 3 | `src/symbiont_lab/studies/social_emergence.py` |
| 3 | `src/symbiont_lab/world/transaction.py` |
| 2 | `src/symbiont/actuation/binding.py` |
| 2 | `src/symbiont/actuation/composition.py` |
| 2 | `src/symbiont/actuation/dimension.py` |
| 2 | `src/symbiont/actuation/evidence.py` |
| 2 | `src/symbiont/actuation/sensorimotor.py` |
| 2 | `src/symbiont/cognition/graph.py` |
| 2 | `src/symbiont/core/domains/epistemic.py` |
| 2 | `src/symbiont/core/embodiment/reachability.py` |
| 2 | `src/symbiont/host/checkpoint.py` |
| 2 | `src/symbiont/modeling/episodic.py` |
| 2 | `src/symbiont/modeling/responsibility.py` |
| 2 | `src/symbiont/sensory/predictive_credit.py` |
| 2 | `src/symbiont_lab/cli/world.py` |
| 2 | `src/symbiont_lab/modeling/gateway.py` |
| 2 | `src/symbiont_lab/observation/observatory.py` |
| 2 | `src/symbiont_lab/physics3d/telemetry_v4.py` |
| 2 | `src/symbiont_lab/server/server.py` |
| 2 | `src/symbiont_lab/studies/campaigns/comparative.py` |
| 2 | `src/symbiont_lab/studies/campaigns/interpretation.py` |
| 2 | `src/symbiont_lab/studies/embodiment/causal_revision_sequence.py` |
| 2 | `src/symbiont_lab/studies/embodiment/heredity_leakage_challenge.py` |
| 2 | `src/symbiont_lab/studies/heritage/longitudinal.py` |
| 2 | `src/symbiont_lab/studies/learning/temporal_private_model_controls.py` |
| 2 | `src/symbiont_lab/studies/runtime_prediction_promotion.py` |
| 2 | `src/symbiont_lab/studies/shared_habitat_intake.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_adaptation.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_adversarial.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_competition.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_context.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_context_replay.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_denial_revision.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_emergence.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_longitudinal.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_preference.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_regime_shift.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_resource_adaptation.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_specialization.py` |
| 2 | `src/symbiont_lab/workbench/runs.py` |
| 1 | `observatory/_node_harness.py` |
| 1 | `observatory/provenance.py` |
| 1 | `src/symbiont/actuation/surface.py` |
| 1 | `src/symbiont/core/domains/physiology.py` |
| 1 | `src/symbiont/core/embodiment/metabolism.py` |
| 1 | `src/symbiont/core/embodiment/session.py` |
| 1 | `src/symbiont/core/orchestration/canonical_birth.py` |
| 1 | `src/symbiont/genetics/genome.py` |
| 1 | `src/symbiont/simulation/snapshots.py` |
| 1 | `src/symbiont_lab/cli/capsule.py` |
| 1 | `src/symbiont_lab/cli/organism.py` |
| 1 | `src/symbiont_lab/evaluation/advisory_evaluation.py` |
| 1 | `src/symbiont_lab/modeling/reservoir.py` |
| 1 | `src/symbiont_lab/physics3d/apparatus.py` |
| 1 | `src/symbiont_lab/physics3d/monitor.py` |
| 1 | `src/symbiont_lab/physics3d/observer_semantics.py` |
| 1 | `src/symbiont_lab/studies/continuity/recurrent_restoration.py` |
| 1 | `src/symbiont_lab/studies/embodiment/integrity_gates.py` |
| 1 | `src/symbiont_lab/studies/embodiment/somatic_correlation_trap.py` |
| 1 | `src/symbiont_lab/studies/embodiment/tool_body_distinction.py` |
| 1 | `src/symbiont_lab/studies/integrated_habitat_runtime.py` |
| 1 | `src/symbiont_lab/studies/learning/cognitive_ecology_embodiment.py` |
| 1 | `src/symbiont_lab/studies/learning/cognitive_graph_causal_composition.py` |
| 1 | `src/symbiont_lab/studies/learning/predictive_discovery.py` |
| 1 | `src/symbiont_lab/studies/learning/predictive_utility.py` |
| 1 | `src/symbiont_lab/studies/learning/structural_producer_fairness.py` |
| 1 | `src/symbiont_lab/studies/perception/__init__.py` |
| 1 | `src/symbiont_lab/studies/predictive_development_gates.py` |
| 1 | `src/symbiont_lab/studies/runtime_prediction_longitudinal.py` |
| 1 | `src/symbiont_lab/studies/social.py` |
| 1 | `src/symbiont_lab/studies/social_longitudinal.py` |
| 1 | `src/symbiont_lab/studies/social_reciprocity.py` |
| 1 | `src/symbiont_lab/studies/social_specialization.py` |
| 1 | `src/symbiont_lab/world/persistence.py` |

## Diagnósticos completos

### `observatory/_node_harness.py` (1)

- `3:6` · **warning** · `reportMissingImports` — Import "observatory.tests._node_harness" could not be resolved

### `observatory/adapter.py` (5)

- `880:21` · **error** · `reportOptionalOperand` — Operator ">=" not supported for "None"
- `884:21` · **error** · `reportOptionalOperand` — Operator ">=" not supported for "None"
- `1431:43` · **error** · `reportArgumentType` — Argument of type "CognitiveGraph | None" cannot be assigned to parameter "graph" of type "CognitiveGraph" in function "_developmental_divergence" Type "CognitiveGraph | None" is not assignable to type "CognitiveGraph" "None" is not assignable to "CognitiveGraph"
- `1594:10` · **warning** · `reportMissingImports` — Import "symbiont.core.governor" could not be resolved
- `1595:10` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `observatory/provenance.py` (1)

- `134:77` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `observatory/resident.py` (18)

- `39:12` · **error** · `reportReturnType` — Type "tuple[int, ...]" is not assignable to return type "tuple[int, int, int]" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate
- `179:10` · **warning** · `reportMissingImports` — Import "symbiont.core.capsule" could not be resolved
- `180:10` · **warning** · `reportMissingImports` — Import "symbiont.core.local_habitat" could not be resolved
- `195:14` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved
- `200:51` · **error** · `reportAttributeAccessIssue` — "_running_version" is unknown import symbol
- `243:35` · **error** · `reportArgumentType` — Argument of type "list[JournalSink] | list[Unknown]" cannot be assigned to parameter "sinks" of type "list[Sink]" in function "__init__" Type "list[JournalSink] | list[Unknown]" is not assignable to type "list[Sink]" "list[JournalSink]" is not assignable to "list[Sink]" Type parameter "_T@list" is invariant, but "JournalSink" is not the same as "Sink" Consider switching from "list" to "Sequence" which is covariant
- `406:63` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `406:78` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "models" for class "ModelRegistry" Attribute "models" is unknown
- `407:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "experience_ledger" for class "OrganismRuntime" Attribute "experience_ledger" is unknown
- `409:64` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "experience_ledger" for class "OrganismRuntime" Attribute "experience_ledger" is unknown
- `418:46` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `422:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "attach_private_model_bridge" for class "OrganismRuntime" Attribute "attach_private_model_bridge" is unknown
- `439:28` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "autonomous_private_learning_plan" for class "OrganismRuntime" Attribute "autonomous_private_learning_plan" is unknown
- `447:21` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "settle_private_model_training_compute" for class "OrganismRuntime" Attribute "settle_private_model_training_compute" is unknown
- `451:31` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime | OrganismRuntime" cannot be assigned to parameter "runtime" of type "ModeledOrganismRuntime" in function "adopt" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime | OrganismRuntime" is not assignable to type "ModeledOrganismRuntime" "OrganismRuntime" is not assignable to "ModeledOrganismRuntime"
- `452:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `461:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `465:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "attach_private_model_bridge" for class "OrganismRuntime" Attribute "attach_private_model_bridge" is unknown

### `observatory/server.py` (3)

- `79:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `88:51` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "events_after" for class "object" Attribute "events_after" is unknown
- `208:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "request" of type "_RequestType" in function "handle_error" Type "object" is not assignable to type "_RequestType" "object" is not assignable to "socket" "object" is not assignable to "tuple[bytes, socket]"

### `src/symbiont/actuation/binding.py` (2)

- `150:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `150:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/actuation/commitment.py` (12)

- `112:30` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "effect_target_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `115:27` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "competence_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `118:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `118:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `121:27` · **error** · `reportArgumentType` — Argument of type "object | str | None" cannot be assigned to parameter "embodiment_id" of type "str | None" in function "__init__" Type "object | str | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `126:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `127:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `127:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `128:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `128:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `134:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `134:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/actuation/composition.py` (2)

- `117:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `117:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/actuation/dimension.py` (2)

- `137:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `137:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/actuation/effects.py` (3)

- `143:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `143:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `144:21` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont/actuation/evidence.py` (2)

- `161:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `161:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/actuation/sensorimotor.py` (2)

- `1374:48` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `1666:48` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "int" and "int | None" Operator ">" not supported for types "int" and "None"

### `src/symbiont/actuation/surface.py` (1)

- `134:15` · **error** · `reportArgumentType` — Argument of type "Sequence[str] | bool" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" Type "Sequence[str] | bool" is not assignable to type "Iterable[_T_co@tuple]" "bool" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present

### `src/symbiont/agency/candidates.py` (3)

- `52:19` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_id" for class "object" Attribute "primitive_id" is unknown
- `54:22` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "maturity" for class "object" Attribute "maturity" is unknown
- `55:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_id" for class "object" Attribute "primitive_id" is unknown

### `src/symbiont/cognition/graph.py` (2)

- `278:22` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `289:22` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont/cognition/structure.py` (9)

- `276:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `277:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `278:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `278:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `286:20` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `287:19` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `288:26` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "predicts_node_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `315:49` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `400:30` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont/core/__init__.py` (12)

- `258:5` · **warning** · `reportUnsupportedDunderAll` — "LivingBodyState" is specified in __all__ but is not present in module
- `259:5` · **warning** · `reportUnsupportedDunderAll` — "PhysiologyController" is specified in __all__ but is not present in module
- `260:5` · **warning** · `reportUnsupportedDunderAll` — "PhysiologySnapshot" is specified in __all__ but is not present in module
- `261:5` · **warning** · `reportUnsupportedDunderAll` — "VitalState" is specified in __all__ but is not present in module
- `262:5` · **warning** · `reportUnsupportedDunderAll` — "InteractionOutcome" is specified in __all__ but is not present in module
- `263:5` · **warning** · `reportUnsupportedDunderAll` — "RelationLedger" is specified in __all__ but is not present in module
- `264:5` · **warning** · `reportUnsupportedDunderAll` — "RelationValence" is specified in __all__ but is not present in module
- `265:5` · **warning** · `reportUnsupportedDunderAll` — "SocialHabitat" is specified in __all__ but is not present in module
- `266:5` · **warning** · `reportUnsupportedDunderAll` — "SocialInteractionEngine" is specified in __all__ but is not present in module
- `267:5` · **warning** · `reportUnsupportedDunderAll` — "SocialRelation" is specified in __all__ but is not present in module
- `268:5` · **warning** · `reportUnsupportedDunderAll` — "SocialPresence" is specified in __all__ but is not present in module
- `269:5` · **warning** · `reportUnsupportedDunderAll` — "SocialCompetitionRequest" is specified in __all__ but is not present in module

### `src/symbiont/core/cognition/bridge_checkpoint.py` (4)

- `287:26` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "entered_tick" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `288:33` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "last_evaluated_tick" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `349:44` · **error** · `reportArgumentType` — Argument of type "str" cannot be assigned to parameter "kind" of type "MutationKind" in function "__init__" Type "str" is not assignable to type "MutationKind" "str" is not assignable to type "Literal['add_edge']" "str" is not assignable to type "Literal['add_node']" "str" is not assignable to type "Literal['quarantine_edge']" "str" is not assignable to type "Literal['remove_edge']" "str" is not assignable to type "Literal['remove_node']"
- `359:27` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "eligible_tick" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"

### `src/symbiont/core/domains/action.py` (5)

- `1393:22` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `1393:22` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `1419:53` · **error** · `reportArgumentType` — Argument of type "Mapping[Unknown, Unknown]" cannot be assigned to parameter "payload" of type "dict[str, object]" in function "restore" "Mapping[Unknown, Unknown]" is not assignable to "dict[str, object]"
- `1421:65` · **error** · `reportArgumentType` — Argument of type "Mapping[Unknown, Unknown]" cannot be assigned to parameter "payload" of type "dict[str, object]" in function "restore" "Mapping[Unknown, Unknown]" is not assignable to "dict[str, object]"
- `1545:69` · **error** · `reportArgumentType` — Argument of type "Mapping[Unknown, Unknown]" cannot be assigned to parameter "payload" of type "dict[str, object]" in function "restore" "Mapping[Unknown, Unknown]" is not assignable to "dict[str, object]"

### `src/symbiont/core/domains/epistemic.py` (2)

- `106:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "acclimation" of type "HostAcclimation" in function "revise" "object" is not assignable to "HostAcclimation"
- `116:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "acclimation" of type "HostAcclimation" in function "narrate_host" "object" is not assignable to "HostAcclimation"

### `src/symbiont/core/domains/physiology.py` (1)

- `81:22` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "update_physiological_state" for class "object" Attribute "update_physiological_state" is unknown

### `src/symbiont/core/embodiment/adaptation.py` (11)

- `179:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `183:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `183:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `185:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `185:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `190:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `190:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `195:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `195:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `197:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `197:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/core/embodiment/body_schema.py` (7)

- `1395:17` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1396:20` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1397:20` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1400:16` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1406:31` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "support_count" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `1407:35` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "opportunity_count" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `1408:35` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "last_support_tick" of type "int" in function "__init__" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"

### `src/symbiont/core/embodiment/dynamics.py` (6)

- `164:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `165:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `165:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `167:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `168:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `168:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/core/embodiment/episode.py` (14)

- `223:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `223:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `259:23` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `259:23` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `260:37` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `260:37` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `264:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `264:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `268:33` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `268:33` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `276:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `285:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `290:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `296:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"

### `src/symbiont/core/embodiment/memory.py` (24)

- `132:31` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "body_schema_prior" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `133:28` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "dynamics_prior" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `134:38` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "execution_binding_priors" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `221:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `221:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `225:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `225:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `226:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `226:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `292:12` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `292:12` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `313:28` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "dynamics_prior" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `316:38` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "execution_binding_priors" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `328:37` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "historical_causal_state" of type "dict[str, object] | None" in function "__init__" Type "object | None" is not assignable to type "dict[str, object] | None" Type "object" is not assignable to type "dict[str, object] | None" "object" is not assignable to "dict[str, object]" "object" is not assignable to "None"
- `380:26` · **error** · `reportArgumentType` — Argument of type "object | Literal[1]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[1]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `380:26` · **error** · `reportArgumentType` — Argument of type "object | Literal[1]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[1]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `390:38` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `390:38` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `392:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `392:30` · **error** · `reportArgumentType` — Argument of type "object | Literal[0]" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object | Literal[0]" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `394:17` · **error** · `reportArgumentType` — Argument of type "Unknown | object | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown | object | None" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex"
- `394:17` · **error** · `reportArgumentType` — Argument of type "Unknown | object | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown | object | None" is not assignable to type "ConvertibleToInt" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `407:15` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "object" Attribute "get" is unknown
- `407:15` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"

### `src/symbiont/core/embodiment/metabolism.py` (1)

- `63:21` · **error** · `reportGeneralTypeIssues` — Union syntax cannot be used with string operand; use quotes around entire expression

### `src/symbiont/core/embodiment/reachability.py` (2)

- `102:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `102:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/core/embodiment/session.py` (1)

- `127:44` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "port_id" for class "str" Attribute "port_id" is unknown

### `src/symbiont/core/orchestration/canonical_birth.py` (1)

- `25:12` · **error** · `reportReturnType` — Type "tuple[int, ...]" is not assignable to return type "tuple[int, int, int]" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont/core/orchestration/resident.py` (4)

- `87:43` · **error** · `reportOptionalMemberAccess` — "state" is not a known attribute of "None"
- `94:43` · **error** · `reportOptionalMemberAccess` — "state" is not a known attribute of "None"
- `156:48` · **error** · `reportAttributeAccessIssue` — "load_base_graph" is unknown import symbol
- `170:48` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "export_checkpoint" for class "OrganismRuntime" Attribute "export_checkpoint" is unknown

### `src/symbiont/core/signals/knowledge.py` (19)

- `151:44` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `183:12` · **error** · `reportOperatorIssue` — Operator "<" not supported for types "int" and "int | None" Operator "<" not supported for types "int" and "None"
- `235:26` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `243:17` · **error** · `reportArgumentType` — Argument of type "list[Claim] | None" cannot be assigned to parameter "obj" of type "Sized" in function "len" Type "list[Claim] | None" is not assignable to type "Sized" "None" is incompatible with protocol "Sized" "__len__" is not present
- `244:24` · **error** · `reportArgumentType` — Argument of type "list[Claim] | None" cannot be assigned to parameter "obj" of type "Sized" in function "len" Type "list[Claim] | None" is not assignable to type "Sized" "None" is incompatible with protocol "Sized" "__len__" is not present
- `247:49` · **error** · `reportArgumentType` — Argument of type "list[Claim] | None" cannot be assigned to parameter "obj" of type "Sized" in function "len" Type "list[Claim] | None" is not assignable to type "Sized" "None" is incompatible with protocol "Sized" "__len__" is not present
- `259:18` · **error** · `reportOptionalMemberAccess` — "append" is not a known attribute of "None"
- `268:22` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `284:50` · **error** · `reportOptionalMemberAccess` — "remove" is not a known attribute of "None"
- `336:72` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `336:72` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `344:38` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `344:38` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `473:26` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `503:30` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `548:80` · **error** · `reportOptionalIterable` — Object of type "None" cannot be used as iterable value
- `618:15` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "observed_opportunities" for class "SignalProfile" Expression of type "Unknown | None" cannot be assigned to attribute "observed_opportunities" of class "SignalProfile" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `618:41` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "valid_observations" for class "SignalProfile" Expression of type "Unknown | None" cannot be assigned to attribute "valid_observations" of class "SignalProfile" Type "Unknown | None" is not assignable to type "int" "None" is not assignable to "int"
- `762:16` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_candidate_pairs" for class "SignalKnowledgeEngine*" Expression of type "set[tuple[str, ...]]" cannot be assigned to attribute "_candidate_pairs" of class "SignalKnowledgeEngine" "set[tuple[str, ...]]" is not assignable to "set[tuple[str, str]]" Type parameter "_T@set" is invariant, but "tuple[str, ...]" is not the same as "tuple[str, str]" Consider switching from "set" to "Container" which is covariant

### `src/symbiont/core/signals/prediction.py` (3)

- `120:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `120:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `121:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont/core/social/ecology.py` (7)

- `135:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `135:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `136:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `137:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `138:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `139:44` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `140:39` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont/core/social/relations.py` (6)

- `201:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `201:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `339:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `339:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `609:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `609:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont/genetics/genome.py` (1)

- `301:22` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "prefix" of type "str" in function "walk" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont/genetics/migration.py` (28)

- `27:14` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `27:14` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `28:14` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `28:14` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `34:18` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `34:18` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `35:19` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `35:19` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `36:19` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `36:19` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `43:37` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `43:37` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `44:37` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `44:37` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `46:29` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "object" Attribute "get" is unknown
- `46:29` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `48:33` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `48:33` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `52:49` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `52:49` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `61:40` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `61:40` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `98:36` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `98:36` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `99:45` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `99:45` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `176:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "max_nodes" for class "object" Attribute "max_nodes" is unknown
- `180:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "max_edges" for class "object" Attribute "max_edges" is unknown

### `src/symbiont/host/checkpoint.py` (2)

- `113:54` · **error** · `reportArgumentType` — Argument of type "DriftAwareBaseline" cannot be assigned to parameter "baseline" of type "CapabilityBaseline" in function "consolidate_baseline" "DriftAwareBaseline" is not assignable to "CapabilityBaseline"
- `272:14` · **warning** · `reportMissingImports` — Import "..core.selfmodel" could not be resolved

### `src/symbiont/host/hypotheses.py` (3)

- `174:39` · **error** · `reportArgumentType` — Argument of type "tuple[str, ...]" cannot be assigned to parameter "key" of type "tuple[str, str]" in function "setdefault" "tuple[str, ...]" is not assignable to "tuple[str, str]" Tuple size mismatch; expected 2 but received indeterminate
- `174:61` · **error** · `reportArgumentType` — Argument of type "tuple[str, ...]" cannot be assigned to parameter "source_ids" of type "tuple[str, str]" in function "__init__" "tuple[str, ...]" is not assignable to "tuple[str, str]" Tuple size mismatch; expected 2 but received indeterminate
- `221:13` · **error** · `reportArgumentType` — Argument of type "tuple[str, ...]" cannot be assigned to parameter "key" of type "tuple[str, str]" in function "__setitem__" "tuple[str, ...]" is not assignable to "tuple[str, str]" Tuple size mismatch; expected 2 but received indeterminate

### `src/symbiont/modeling/culture.py` (31)

- `118:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "decision_tick" of type "int" in function "__init__" "object" is not assignable to "int"
- `121:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `122:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "selected_recipient_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `123:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "cost" of type "int" in function "__init__" "object" is not assignable to "int"
- `390:18` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "seed" of type "int" in function "__init__" "object" is not assignable to "int"
- `391:43` · **error** · `reportCallIssue` — Argument expression after ** must be a mapping with a "str" key type
- `628:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `631:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `632:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `633:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "created_tick_class" of type "int" in function "__init__" "object" is not assignable to "int"
- `634:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "received_tick_class" of type "int | None" in function "__init__" Type "object | None" is not assignable to type "int | None" Type "object" is not assignable to type "int | None" "object" is not assignable to "int" "object" is not assignable to "None"
- `636:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "confidence_class" of type "int" in function "__init__" "object" is not assignable to "int"
- `637:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "transmission_depth" of type "int" in function "__init__" "object" is not assignable to "int"
- `638:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "mutation_depth" of type "int" in function "__init__" "object" is not assignable to "int"
- `735:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_claims" of type "int" in function "__init__" "object" is not assignable to "int"
- `841:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `842:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `843:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `844:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `845:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "generation" of type "int" in function "__init__" "object" is not assignable to "int"
- `846:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "created_tick_class" of type "int" in function "__init__" "object" is not assignable to "int"
- `947:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_composites" of type "int" in function "__init__" "object" is not assignable to "int"
- `1182:47` · **error** · `reportOptionalMemberAccess` — "generation" is not a known attribute of "None"
- `1232:17` · **error** · `reportArgumentType` — Argument of type "list[SocialClaim | None]" cannot be assigned to parameter "iterable" of type "Iterable[SocialClaim]" in function "extend"
- `1341:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_claims" of type "int" in function "__init__" "object" is not assignable to "int"
- `1342:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_assessments" of type "int" in function "__init__" "object" is not assignable to "int"
- `1343:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_composites" of type "int" in function "__init__" "object" is not assignable to "int"
- `1345:44` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `1354:13` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "payload" of type "Mapping[str, object] | None" in function "restore" Type "object | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `1428:44` · **error** · `reportOptionalMemberAccess` — "transmission_depth" is not a known attribute of "None"
- `1431:44` · **error** · `reportOptionalMemberAccess` — "mutation_depth" is not a known attribute of "None"

### `src/symbiont/modeling/episodic.py` (2)

- `209:26` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "action_token" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `1184:17` · **error** · `reportArgumentType` — Argument of type "float" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "float" is not assignable to "int"

### `src/symbiont/modeling/experience.py` (8)

- `152:58` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `152:72` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `152:86` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `168:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "record_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `169:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "organism_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `171:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `173:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `175:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present

### `src/symbiont/modeling/private_runtime.py` (7)

- `318:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "_last_executed_competence_id" for class "PrivateModelOrganismRuntime*" Attribute "_last_executed_competence_id" is unknown
- `787:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `792:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `799:17` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_pending_private_frame" for class "ModeledOrganismRuntime" Attribute "_pending_private_frame" is unknown
- `803:17` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_pending_outcome_value_credit" for class "ModeledOrganismRuntime" Attribute "_pending_outcome_value_credit" is unknown
- `804:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "_prospective_agency" for class "ModeledOrganismRuntime" Attribute "_prospective_agency" is unknown
- `818:25` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_prospective_agency" for class "ModeledOrganismRuntime" Attribute "_prospective_agency" is unknown

### `src/symbiont/modeling/registry.py` (5)

- `171:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "model_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `172:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "organism_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `174:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "corpus_hash" of type "str" in function "__init__" "object" is not assignable to "str"
- `175:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "tokenizer_hash" of type "str" in function "__init__" "object" is not assignable to "str"
- `181:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "artifact_hash" of type "str" in function "__init__" "object" is not assignable to "str"

### `src/symbiont/modeling/responsibility.py` (2)

- `121:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `122:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont/modeling/runtime.py` (9)

- `267:24` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `393:24` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `396:21` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `434:24` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `437:21` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `467:24` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `470:21` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `1502:28` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `1505:67` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"

### `src/symbiont/modeling/sequences.py` (8)

- `122:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "decision_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `123:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "organism_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `124:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "decision_tick" of type "int" in function "__init__" "object" is not assignable to "int"
- `125:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "candidate_set_digest" of type "str" in function "__init__" "object" is not assignable to "str"
- `127:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "selected_sequence_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `129:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "selected_recipient_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `130:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "cost" of type "int" in function "__init__" "object" is not assignable to "int"
- `327:52` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_associations" of type "int" in function "__init__" "object" is not assignable to "int"

### `src/symbiont/modeling/symbols.py` (16)

- `110:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "decision_tick" of type "int" in function "__init__" "object" is not assignable to "int"
- `113:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "selected_symbol_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `114:17` · **error** · `reportArgumentType` — Argument of type "object | None" cannot be assigned to parameter "selected_recipient_id" of type "str | None" in function "__init__" Type "object | None" is not assignable to type "str | None" Type "object" is not assignable to type "str | None" "object" is not assignable to "str" "object" is not assignable to "None"
- `115:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "cost" of type "int" in function "__init__" "object" is not assignable to "int"
- `348:20` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `353:20` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `356:52` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_associations" of type "int" in function "__init__" "object" is not assignable to "int"
- `357:20` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `359:20` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `364:20` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `367:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[dict[str, object]]" in function "extend" "object" is incompatible with protocol "Iterable[dict[str, object]]" "__iter__" is not present
- `623:16` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `627:18` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "seed" of type "int" in function "__init__" "object" is not assignable to "int"
- `628:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `629:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "max_bias_entries" of type "int" in function "__init__" "object" is not assignable to "int"
- `631:20` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont/sensory/predictive_credit.py` (2)

- `110:23` · **error** · `reportArgumentType` — Argument of type "Any | None" cannot be assigned to parameter "source_id" of type "str" in function "__init__" Type "Any | None" is not assignable to type "str" "None" is not assignable to "str"
- `111:23` · **error** · `reportArgumentType` — Argument of type "Any | None" cannot be assigned to parameter "target_id" of type "str" in function "__init__" Type "Any | None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont/simulation/snapshots.py` (1)

- `8:10` · **warning** · `reportMissingImports` — Import "symbiont.core.curiosity" could not be resolved

### `src/symbiont_lab/app/physics3d_monitor.py` (78)

- `243:16` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `243:16` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `258:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `259:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `270:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `271:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `288:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `288:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `289:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `289:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `310:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `311:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `346:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `355:50` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `358:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `382:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `382:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `415:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "Process" for class "BaseContext" Attribute "Process" is unknown
- `565:51` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `565:77` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `569:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `570:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `571:26` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `571:57` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `576:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T@list]" in function "__init__" "object" is incompatible with protocol "Iterable[_T@list]" "__iter__" is not present
- `577:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T@list]" in function "__init__" "object" is incompatible with protocol "Iterable[_T@list]" "__iter__" is not present
- `581:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T@list]" in function "__init__" "object" is incompatible with protocol "Iterable[_T@list]" "__iter__" is not present
- `602:15` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `603:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `604:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `1062:9` · **error** · `reportArgumentType` — Argument of type "tuple[Canvas, int]" cannot be assigned to parameter "value" of type "Canvas" in function "__setitem__" "tuple[Canvas, int]" is not assignable to "Canvas"
- `2037:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2037:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2039:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2039:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2040:55` · **error** · `reportArgumentType` — Argument of type "list[dict[Unknown, Unknown]]" cannot be assigned to parameter "records" of type "list[Mapping[str, object]]" in function "_event_context" "list[dict[Unknown, Unknown]]" is not assignable to "list[Mapping[str, object]]" Type parameter "_T@list" is invariant, but "dict[Unknown, Unknown]" is not the same as "Mapping[str, object]" Consider switching from "list" to "Sequence" which is covariant
- `2050:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2050:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2052:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2052:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2053:55` · **error** · `reportArgumentType` — Argument of type "list[dict[Unknown, Unknown]]" cannot be assigned to parameter "records" of type "list[Mapping[str, object]]" in function "_event_context" "list[dict[Unknown, Unknown]]" is not assignable to "list[Mapping[str, object]]" Type parameter "_T@list" is invariant, but "dict[Unknown, Unknown]" is not the same as "Mapping[str, object]" Consider switching from "list" to "Sequence" which is covariant
- `2170:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2170:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2173:41` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2173:41` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2175:47` · **error** · `reportArgumentType` — Argument of type "list[dict[str, object]]" cannot be assigned to parameter "records" of type "list[Mapping[str, object]]" in function "_event_context" "list[dict[str, object]]" is not assignable to "list[Mapping[str, object]]" Type parameter "_T@list" is invariant, but "dict[str, object]" is not the same as "Mapping[str, object]" Consider switching from "list" to "Sequence" which is covariant
- `2342:38` · **error** · `reportArgumentType` — Argument of type "bytearray" cannot be assigned to parameter "data" of type "bytes | SupportsArrayInterface" in function "frombuffer" Type "bytearray" is not assignable to type "bytes | SupportsArrayInterface" "bytearray" is not assignable to "bytes" Set disableBytesTypePromotions to false to enable type promotion behavior for "bytearray" and "memoryview" "bytearray" is incompatible with protocol "SupportsArrayInterface" "__array_interface__" is not present
- `2448:47` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2449:43` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2458:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2485:37` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2492:33` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2509:32` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2521:45` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2640:38` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2649:26` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2659:38` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2709:26` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2775:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2776:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2780:54` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2801:24` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `2802:26` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `2805:18` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2877:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2877:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2884:79` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2884:79` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2914:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2914:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `2980:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `2980:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `3007:16` · **error** · `reportArgumentType` — Argument of type "list[float]" cannot be assigned to parameter "values" of type "list[float | None]" in function "series" "list[float]" is not assignable to "list[float | None]" Type parameter "_T@list" is invariant, but "float" is not the same as "float | None" Consider switching from "list" to "Sequence" which is covariant
- `3008:16` · **error** · `reportArgumentType` — Argument of type "list[float]" cannot be assigned to parameter "values" of type "list[float | None]" in function "series" "list[float]" is not assignable to "list[float | None]" Type parameter "_T@list" is invariant, but "float" is not the same as "float | None" Consider switching from "list" to "Sequence" which is covariant
- `3056:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `3056:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `3058:39` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `3058:39` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont_lab/app/physics3d_session.py` (19)

- `83:55` · **error** · `reportArgumentType` — Argument of type "ObservationBus" cannot be assigned to parameter "sink" of type "EventSink" in function "__init__" "ObservationBus" is incompatible with protocol "EventSink" "push" is an incompatible type Type "(event: dict[str, Any]) -> int" is not assignable to type "(event: dict[str, Any]) -> None" Function return type "int" is incompatible with type "None" "int" is not assignable to "None"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "body_file" of type "Path" in function "run" "object" is not assignable to "Path"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "body_kind" of type "str" in function "run" "object" is not assignable to "str"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "checkpoint_interval" of type "int" in function "run" "object" is not assignable to "int"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "cognition_hz" of type "int" in function "run" "object" is not assignable to "int"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "enable_slm" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "fresh_body" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "headless" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "hz" of type "int" in function "run" "object" is not assignable to "int"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "mechanical_work_cost_per_joule" of type "float" in function "run" "object" is not assignable to "float"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "new_symbiont" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "seed" of type "int" in function "run" "object" is not assignable to "int"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "show_monitor" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "slm_device" of type "str" in function "run" "object" is not assignable to "str"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "slm_train_interval" of type "int" in function "run" "object" is not assignable to "int"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "symbiont_file" of type "Path" in function "run" "object" is not assignable to "Path"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "telemetry_file" of type "Path" in function "run" "object" is not assignable to "Path"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "telemetry_physics_trace" of type "bool" in function "run" "object" is not assignable to "bool"
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "ticks" of type "int" in function "run" "object" is not assignable to "int"

### `src/symbiont_lab/app/run_controller.py` (4)

- `102:25` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_process" for class "RunController*" Type "SpawnProcess" is not assignable to type "Process | None" "SpawnProcess" is not assignable to "Process" "SpawnProcess" is not assignable to "None"
- `107:23` · **error** · `reportOptionalMemberAccess` — "start" is not a known attribute of "None"
- `119:25` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_process" for class "RunController*" Type "SpawnProcess" is not assignable to type "Process | None" "SpawnProcess" is not assignable to "Process" "SpawnProcess" is not assignable to "None"
- `124:23` · **error** · `reportOptionalMemberAccess` — "start" is not a known attribute of "None"

### `src/symbiont_lab/cli/archive.py` (8)

- `63:24` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `63:24` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `63:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `63:60` · **error** · `reportArgumentType` — Argument of type "Literal['parameter_value']" cannot be assigned to parameter "key" of type "bytes" in function "get" "Literal['parameter_value']" is not assignable to "bytes"
- `64:23` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `64:23` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `64:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `64:58` · **error** · `reportArgumentType` — Argument of type "Literal['parameter_value']" cannot be assigned to parameter "key" of type "bytes" in function "get" "Literal['parameter_value']" is not assignable to "bytes"

### `src/symbiont_lab/cli/capsule.py` (1)

- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.capsule" could not be resolved

### `src/symbiont_lab/cli/organism.py` (1)

- `58:10` · **warning** · `reportMissingImports` — Import "symbiont.core.epistemic" could not be resolved

### `src/symbiont_lab/cli/world.py` (2)

- `8:6` · **warning** · `reportMissingImports` — Import "observatory.config" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "observatory.server" could not be resolved

### `src/symbiont_lab/evaluation/advisory_evaluation.py` (1)

- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.advisory" could not be resolved

### `src/symbiont_lab/integration/integrated_habitat.py` (7)

- `16:6` · **warning** · `reportMissingImports` — Import "symbiont.core.birth_authority" could not be resolved
- `17:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `18:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `19:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `211:14` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `253:18` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `262:18` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved

### `src/symbiont_lab/kernel_characterization/runner.py` (3)

- `15:6` · **warning** · `reportMissingImports` — Import "symbiont.core.consolidation" could not be resolved
- `16:6` · **warning** · `reportMissingImports` — Import "symbiont.core.weight_stability" could not be resolved
- `213:55` · **error** · `reportOptionalMemberAccess` — "graph" is not a known attribute of "None"

### `src/symbiont_lab/modeling/architectures.py` (10)

- `153:27` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `153:27` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `154:24` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `154:24` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `155:20` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `155:20` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `156:19` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `156:19` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `157:29` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `157:29` · **error** · `reportArgumentType` — Argument of type "int | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "int | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/modeling/gateway.py` (2)

- `119:29` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "parameters" for class "object" Attribute "parameters" is unknown
- `123:22` · **error** · `reportCallIssue` — Object of type "object" is not callable Attribute "__call__" is unknown

### `src/symbiont_lab/modeling/reservoir.py` (1)

- `179:9` · **warning** · `reportUnusedExpression` — Expression value is unused

### `src/symbiont_lab/observation/observatory.py` (2)

- `150:49` · **error** · `reportArgumentType` — Argument of type "Unknown | float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown | float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `150:49` · **error** · `reportArgumentType` — Argument of type "Unknown | float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown | float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/observation/physics3d.py` (5)

- `184:29` · **error** · `reportArgumentType` — Argument of type "DataclassInstance | type[DataclassInstance]" cannot be assigned to parameter "obj" of type "DataclassInstance" in function "asdict" Type "DataclassInstance | type[DataclassInstance]" is not assignable to type "DataclassInstance" "__dataclass_fields__" is defined as a ClassVar in protocol
- `269:30` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `269:30` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `292:30` · **error** · `reportArgumentType` — Argument of type "Any | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Any | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `292:30` · **error** · `reportArgumentType` — Argument of type "Any | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Any | None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/observation/projection.py` (3)

- `194:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `297:39` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `297:39` · **error** · `reportArgumentType` — Argument of type "Unknown | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/physics3d/apparatus.py` (1)

- `13:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved

### `src/symbiont_lab/physics3d/engine.py` (11)

- `413:13` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "attach_existing" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" is not assignable to type "_PrivateModelRuntime" "ModeledOrganismRuntime" is incompatible with protocol "_PrivateModelRuntime" "settle_private_model_training_compute" is an incompatible type Type "(*, request_id: str, steps_completed: int) -> bool" is not assignable to type "(*, request_id: str, steps_completed: int) -> None" Function return type "bool" is incompatible with type "None" "adopt_private_model" is an incompatible type Type "(artifact: ModelArtifactManifest, *, evaluation_summary: tuple[int, ...] = ()) -> ModelRecord" is not assignable to type "(manifest: Any, *, evaluation_summary: tuple[int, ...]) -> Any" Parameter name mismatch: "manifest" versus "artifact"
- `499:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `499:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `500:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `500:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `501:46` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `501:46` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `502:53` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `503:58` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `545:36` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "maybe_schedule" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" is not assignable to type "_PrivateModelRuntime" "ModeledOrganismRuntime" is incompatible with protocol "_PrivateModelRuntime" "settle_private_model_training_compute" is an incompatible type Type "(*, request_id: str, steps_completed: int) -> bool" is not assignable to type "(*, request_id: str, steps_completed: int) -> None" Function return type "bool" is incompatible with type "None" "adopt_private_model" is an incompatible type Type "(artifact: ModelArtifactManifest, *, evaluation_summary: tuple[int, ...] = ()) -> ModelRecord" is not assignable to type "(manifest: Any, *, evaluation_summary: tuple[int, ...]) -> Any" Parameter name mismatch: "manifest" versus "artifact"
- `771:39` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "handler" of type "_HANDLER" in function "signal" Type "object" is not assignable to type "_HANDLER" Type "object" is not assignable to type "(int, FrameType | None) -> Any" "object" is not assignable to "int" "object" is not assignable to "Handlers" "object" is not assignable to "None"

### `src/symbiont_lab/physics3d/humanoid.py` (9)

- `838:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `839:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `920:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `920:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `921:55` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `922:53` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `923:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `924:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `924:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont_lab/physics3d/monitor.py` (1)

- `10:1` · **warning** · `reportUnsupportedDunderAll` — Operation on "__all__" is not supported, so exported symbol list may be incorrect

### `src/symbiont_lab/physics3d/observer_semantics.py` (1)

- `34:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown

### `src/symbiont_lab/physics3d/reembodiment.py` (19)

- `86:8` · **error** · `reportOptionalOperand` — Operator "<=" not supported for "None"
- `86:29` · **error** · `reportOptionalOperand` — Operator "<" not supported for "None"
- `89:20` · **error** · `reportOptionalOperand` — Operator "-" not supported for "None"
- `95:12` · **error** · `reportOptionalOperand` — Operator "-" not supported for "None"
- `102:16` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "int" and "Unknown | None" Operator "-" not supported for types "int" and "None" when expected type is "SupportsAbs[Unknown]"
- `102:49` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "int" and "Any | None" Operator "-" not supported for types "int" and "None" when expected type is "SupportsAbs[Any | Unknown]"
- `109:20` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "int" and "Unknown | None" Operator "-" not supported for types "int" and "None" when expected type is "SupportsAbs[Unknown]"
- `109:58` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "int" and "Any | None" Operator "-" not supported for types "int" and "None" when expected type is "SupportsAbs[Any | Unknown]"
- `744:13` · **error** · `reportOptionalMemberAccess` — "append" is not a known attribute of "None"
- `760:15` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `848:5` · **error** · `reportCallIssue` — No overloads for "update" match the provided arguments
- `848:20` · **error** · `reportArgumentType` — Argument of type "dict[str, object]" cannot be assigned to parameter "m" of type "Iterable[tuple[str, int]]" in function "update" "dict[str, object]" is not assignable to "Iterable[tuple[str, int]]" Type parameter "_T_co@Iterable" is covariant, but "str" is not a subtype of "tuple[str, int]" "str" is not assignable to "tuple[str, int]"
- `849:5` · **error** · `reportArgumentType` — Argument of type "str" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "str" is not assignable to "int"
- `865:9` · **error** · `reportArgumentType` — Argument of type "str" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "str" is not assignable to "int"
- `876:13` · **error** · `reportArgumentType` — Argument of type "str" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "str" is not assignable to "int"
- `883:9` · **error** · `reportArgumentType` — Argument of type "dict[str, Any]" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "dict[str, Any]" is not assignable to "int"
- `890:20` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `900:21` · **error** · `reportArgumentType` — Argument of type "int | Unknown | dict[str, Any] | None" cannot be assigned to parameter "metrics" of type "Mapping[str, Any] | None" in function "build_epoch_summary" Type "int | Unknown | dict[str, Any] | None" is not assignable to type "Mapping[str, Any] | None" Type "int" is not assignable to type "Mapping[str, Any] | None" "int" is not assignable to "Mapping[str, Any]" "int" is not assignable to "None"
- `905:9` · **error** · `reportArgumentType` — Argument of type "dict[str, Any]" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "dict[str, Any]" is not assignable to "int"

### `src/symbiont_lab/physics3d/resource.py` (13)

- `44:28` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createCollisionShape" for class "object" Attribute "createCollisionShape" is unknown
- `45:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "GEOM_SPHERE" for class "object" Attribute "GEOM_SPHERE" is unknown
- `49:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createVisualShape" for class "object" Attribute "createVisualShape" is unknown
- `50:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "GEOM_SPHERE" for class "object" Attribute "GEOM_SPHERE" is unknown
- `55:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createMultiBody" for class "object" Attribute "createMultiBody" is unknown
- `86:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "getContactPoints" for class "object" Attribute "getContactPoints" is unknown
- `135:16` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `135:16` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `137:52` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `144:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `145:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `146:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `147:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/physics3d/runtime.py` (27)

- `20:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `21:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `359:54` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "distance_to" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `694:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `698:48` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `728:17` · **error** · `reportArgumentType` — Argument of type "Any | Mapping[Unknown, Unknown] | None" cannot be assigned to parameter "payload" of type "Mapping[str, object]" in function "restore" Type "Any | Mapping[Unknown, Unknown] | None" is not assignable to type "Mapping[str, object]" "None" is not assignable to "Mapping[str, object]"
- `1059:35` · **error** · `reportArgumentType` — Argument of type "object | Any | None" cannot be assigned to parameter "body_schema_prior" of type "Mapping[str, object] | None" in function "archive_episode_checkpoint" Type "object | Any | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `1062:29` · **error** · `reportArgumentType` — Argument of type "object | Any | None" cannot be assigned to parameter "living_body" of type "Mapping[str, object] | None" in function "archive_episode_checkpoint" Type "object | Any | None" is not assignable to type "Mapping[str, object] | None" Type "object" is not assignable to type "Mapping[str, object] | None" "object" is not assignable to "Mapping[str, object]" "object" is not assignable to "None"
- `1476:49` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "field_at" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `1670:55` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "distance_to" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `1797:76` · **error** · `reportOptionalMemberAccess` — "surface_fingerprint" is not a known attribute of "None"
- `1833:15` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "str" Attribute "value" is unknown
- `1841:46` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_decision" for class "ModeledOrganismRuntime" Attribute "last_prospective_decision" is unknown
- `1847:50` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_query_count" for class "ModeledOrganismRuntime" Attribute "last_prospective_query_count" is unknown
- `1866:48` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_value_samples" for class "ModeledOrganismRuntime" Attribute "last_prospective_value_samples" is unknown
- `1870:47` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_cost" for class "ModeledOrganismRuntime" Attribute "last_prospective_cost" is unknown
- `1871:55` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "prospective_outcome_value_count" for class "ModeledOrganismRuntime" Attribute "prospective_outcome_value_count" is unknown
- `1898:78` · **error** · `reportOptionalMemberAccess` — "items" is not a known attribute of "None"
- `1903:76` · **error** · `reportOptionalMemberAccess` — "is_executable" is not a known attribute of "None"
- `1910:73` · **error** · `reportOptionalMemberAccess` — "checkpoint" is not a known attribute of "None"
- `2114:27` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "base_position" of type "tuple[float, float, float]" in function "__init__" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2115:30` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "base_orientation" of type "tuple[float, float, float, float]" in function "__init__" "tuple[float, ...]" is not assignable to "tuple[float, float, float, float]" Tuple size mismatch; expected 4 but received indeterminate
- `2187:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_query_count" for class "ModeledOrganismRuntime" Attribute "last_prospective_query_count" is unknown
- `2206:57` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_value_samples" for class "ModeledOrganismRuntime" Attribute "last_prospective_value_samples" is unknown
- `2210:50` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "last_prospective_cost" for class "ModeledOrganismRuntime" Attribute "last_prospective_cost" is unknown
- `2300:26` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2303:49` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/telemetry.py` (4)

- `60:23` · **error** · `reportArgumentType` — Argument of type "DataclassInstance | type[DataclassInstance]" cannot be assigned to parameter "obj" of type "DataclassInstance" in function "asdict" Type "DataclassInstance | type[DataclassInstance]" is not assignable to type "DataclassInstance" "__dataclass_fields__" is defined as a ClassVar in protocol
- `249:19` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `249:24` · **error** · `reportArgumentType` — Argument of type "Mapping[str, Any] | None" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" Type "Mapping[str, Any] | None" is not assignable to type "Iterable[list[bytes]]" "Mapping[str, Any]" is not assignable to "Iterable[list[bytes]]" Type parameter "_T_co@Iterable" is covariant, but "str" is not a subtype of "list[bytes]" "str" is not assignable to "list[bytes]"
- `369:57` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/telemetry_binary.py` (6)

- `185:52` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "id" for class "BinaryStringTableReader" Attribute "id" is unknown
- `198:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "id" for class "BinaryStringTableReader" Attribute "id" is unknown
- `227:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "BinaryStringTableWriter" Attribute "get" is unknown
- `230:22` · **error** · `reportAssignmentType` — Type "list[Any]" is not assignable to declared type "dict[str, Any]" "list[Any]" is not assignable to "dict[str, Any]"
- `233:24` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "append" for class "dict[str, Any]" Attribute "append" is unknown
- `241:37` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "BinaryStringTableWriter" Attribute "get" is unknown

### `src/symbiont_lab/physics3d/telemetry_tools.py` (4)

- `77:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `101:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `102:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `180:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown

### `src/symbiont_lab/physics3d/telemetry_v4.py` (2)

- `41:23` · **error** · `reportArgumentType` — Argument of type "DataclassInstance | type[DataclassInstance]" cannot be assigned to parameter "obj" of type "DataclassInstance" in function "asdict" Type "DataclassInstance | type[DataclassInstance]" is not assignable to type "DataclassInstance" "__dataclass_fields__" is defined as a ClassVar in protocol
- `356:57` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/telemetry_v41.py` (30)

- `70:23` · **error** · `reportArgumentType` — Argument of type "DataclassInstance | type[DataclassInstance]" cannot be assigned to parameter "obj" of type "DataclassInstance" in function "asdict" Type "DataclassInstance | type[DataclassInstance]" is not assignable to type "DataclassInstance" "__dataclass_fields__" is defined as a ClassVar in protocol
- `839:57` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `1034:39` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" cannot be assigned to parameter "schemas" of type "BinaryFrameSchemaReader" in function "__init__" Type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" is not assignable to type "BinaryFrameSchemaReader" "FrameSchemaRegistryReader" is not assignable to "BinaryFrameSchemaReader"
- `1034:54` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1043:17` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader | StructuralPathRegistryReader" cannot be assigned to parameter "paths" of type "BinaryPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader | StructuralPathRegistryReader" is not assignable to type "BinaryPathRegistryReader" "StructuralPathRegistryReader" is not assignable to "BinaryPathRegistryReader"
- `1044:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1052:17` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" cannot be assigned to parameter "schemas" of type "BinaryFrameSchemaReader" in function "__init__" Type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" is not assignable to type "BinaryFrameSchemaReader" "FrameSchemaRegistryReader" is not assignable to "BinaryFrameSchemaReader"
- `1053:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1061:40` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1064:41` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1068:17` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader | StructuralPathRegistryReader" cannot be assigned to parameter "paths" of type "BinaryPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader | StructuralPathRegistryReader" is not assignable to type "BinaryPathRegistryReader" "StructuralPathRegistryReader" is not assignable to "BinaryPathRegistryReader"
- `1069:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1077:39` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1086:52` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader | StructuralPathRegistryReader" cannot be assigned to parameter "registry" of type "StructuralPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader | StructuralPathRegistryReader" is not assignable to type "StructuralPathRegistryReader" "BinaryPathRegistryReader" is not assignable to "StructuralPathRegistryReader"
- `1090:59` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1099:48` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader | FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1109:42` · **error** · `reportArgumentType` — Argument of type "ObjectStore | None" cannot be assigned to parameter "object_store" of type "ObjectStore" in function "__init__" Type "ObjectStore | None" is not assignable to type "ObjectStore" "None" is not assignable to "ObjectStore"
- `1174:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "FrameStreamReader" Attribute "decode_record" is unknown
- `1175:43` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "FrameStreamReader" Attribute "decode_record" is unknown
- `1176:42` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "LegacyStructuralStreamReader" Attribute "decode_record" is unknown
- `1176:42` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "StructuralDeltaReader" Attribute "decode_record" is unknown
- `1177:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "EventStreamReader" Attribute "decode_record" is unknown
- `1178:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "_StaticStreamReader" Attribute "decode_record" is unknown
- `1179:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "dict[str, Any]" Attribute "decode_record" is unknown
- `1213:37` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "MethodType" Attribute "get" is unknown
- `1269:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "apply" for class "dict[Unknown, Unknown]" Attribute "apply" is unknown
- `1269:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "apply" for class "dict[str, Any]" Attribute "apply" is unknown
- `1270:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "MethodType" Attribute "get" is unknown
- `1302:30` · **error** · `reportArgumentType` — Argument of type "Any | Unknown | BinaryDeltaReader | dict[str, Any] | dict[Unknown, Unknown]" cannot be assigned to parameter "fallback" of type "Mapping[str, Any]" in function "reassemble_state" Type "Any | Unknown | BinaryDeltaReader | dict[str, Any] | dict[Unknown, Unknown]" is not assignable to type "Mapping[str, Any]" "BinaryDeltaReader" is not assignable to "Mapping[str, Any]"
- `1456:41` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader | None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader | None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"

### `src/symbiont_lab/server/server.py` (2)

- `38:14` · **warning** · `reportMissingImports` — Import "observatory.config" could not be resolved
- `205:48` · **error** · `reportArgumentType` — Argument of type "ObservationBus" cannot be assigned to parameter "sink" of type "EventSink" in function "__init__" "ObservationBus" is incompatible with protocol "EventSink" "push" is an incompatible type Type "(event: dict[str, Any]) -> int" is not assignable to type "(event: dict[str, Any]) -> None" Function return type "int" is incompatible with type "None" "int" is not assignable to "None"

### `src/symbiont_lab/studies/attention/retrospective.py` (6)

- `192:16` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `192:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `193:5` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `193:10` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `197:24` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `197:37` · **error** · `reportArgumentType` — Argument of type "Literal['benign:normal', 'benign:update', 'benign:backup', 'benign:build', 'pathogen:ransom_sim', 'pathogen:bot_sim', 'pathogen:stealth_sim']" cannot be assigned to parameter "key" of type "bytes" in function "get" Type "Literal['benign:normal', 'benign:update', 'benign:backup', 'benign:build', 'pathogen:ransom_sim', 'pathogen:bot_sim', 'pathogen:stealth_sim']" is not assignable to type "bytes" "Literal['benign:backup']" is not assignable to "bytes"

### `src/symbiont_lab/studies/campaigns/campaign.py` (14)

- `44:22` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `44:22` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `44:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `44:58` · **error** · `reportArgumentType` — Argument of type "Literal['parameter_value']" cannot be assigned to parameter "key" of type "bytes" in function "get" "Literal['parameter_value']" is not assignable to "bytes"
- `45:21` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `45:21` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `45:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `45:56` · **error** · `reportArgumentType` — Argument of type "Literal['parameter_value']" cannot be assigned to parameter "key" of type "bytes" in function "get" "Literal['parameter_value']" is not assignable to "bytes"
- `46:19` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" "object" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present
- `52:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `141:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `142:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `144:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `144:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont_lab/studies/campaigns/comparative.py` (2)

- `144:48` · **error** · `reportArgumentType` — Argument of type "object | Any" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | Any" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex"
- `144:48` · **error** · `reportArgumentType` — Argument of type "object | Any" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | Any" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/studies/campaigns/interpretation.py` (2)

- `273:13` · **error** · `reportOptionalOperand` — Operator "*" not supported for "None"
- `273:52` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "arg2" of type "SupportsRichComparisonT@min" in function "min" Type "float | None" is not assignable to type "float" "None" is not assignable to "float"

### `src/symbiont_lab/studies/continuity/recurrent_restoration.py` (1)

- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved

### `src/symbiont_lab/studies/embodiment/causal_revision_sequence.py` (2)

- `16:6` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved
- `17:6` · **warning** · `reportMissingImports` — Import "symbiont.core.individual" could not be resolved

### `src/symbiont_lab/studies/embodiment/heredity_leakage_challenge.py` (2)

- `18:6` · **warning** · `reportMissingImports` — Import "symbiont.core.germline" could not be resolved
- `27:6` · **warning** · `reportMissingImports` — Import "symbiont.core.symbiont" could not be resolved

### `src/symbiont_lab/studies/embodiment/integrity_gates.py` (1)

- `12:6` · **warning** · `reportMissingImports` — Import "symbiont.core.symbiont" could not be resolved

### `src/symbiont_lab/studies/embodiment/label_invariance.py` (3)

- `18:6` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved
- `19:6` · **warning** · `reportMissingImports` — Import "symbiont.core.individual" could not be resolved
- `20:6` · **warning** · `reportMissingImports` — Import "symbiont.core.symbiont" could not be resolved

### `src/symbiont_lab/studies/embodiment/somatic_correlation_trap.py` (1)

- `14:6` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved

### `src/symbiont_lab/studies/embodiment/tool_body_distinction.py` (1)

- `16:6` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved

### `src/symbiont_lab/studies/heritage/ecological_shift.py` (25)

- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.collective" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.heritage" could not be resolved
- `136:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "object" Attribute "get" is unknown
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_fraction" of type "float" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_magnitude" of type "float" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_step" of type "int | None" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "int | None" Type "float" is not assignable to type "int | None" "float" is not assignable to "int" "float" is not assignable to "None"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "heterogeneity" of type "float" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "hosts" of type "int" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "on_event" of type "((EventContext) -> None) | None" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "((EventContext) -> None) | None" Type "float" is not assignable to type "((EventContext) -> None) | None" Type "float" is not assignable to type "(EventContext) -> None" "float" is not assignable to "None"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "on_snapshot" of type "((SimulationSnapshot) -> None) | None" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "((SimulationSnapshot) -> None) | None" Type "float" is not assignable to type "((SimulationSnapshot) -> None) | None" Type "float" is not assignable to type "(SimulationSnapshot) -> None" "float" is not assignable to "None"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "poison_fraction" of type "float" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "seed" of type "int" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "steps" of type "int" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `188:38` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "threat_rate" of type "float" in function "run_simulation" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_fraction" of type "float" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_magnitude" of type "float" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "drift_step" of type "int | None" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "int | None" Type "float" is not assignable to type "int | None" "float" is not assignable to "int" "float" is not assignable to "None"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "heterogeneity" of type "float" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "hosts" of type "int" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "on_event" of type "((EventContext) -> None) | None" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "((EventContext) -> None) | None" Type "float" is not assignable to type "((EventContext) -> None) | None" Type "float" is not assignable to type "(EventContext) -> None" "float" is not assignable to "None"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "on_snapshot" of type "((SimulationSnapshot) -> None) | None" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "((SimulationSnapshot) -> None) | None" Type "float" is not assignable to type "((SimulationSnapshot) -> None) | None" Type "float" is not assignable to type "(SimulationSnapshot) -> None" "float" is not assignable to "None"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "poison_fraction" of type "float" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "seed" of type "int" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "steps" of type "int" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "int" "float" is not assignable to "int"
- `193:15` · **error** · `reportArgumentType` — Argument of type "float | ((event: EventContext) -> None)" cannot be assigned to parameter "threat_rate" of type "float" in function "_run_population" Type "float | ((event: EventContext) -> None)" is not assignable to type "float" "FunctionType" is not assignable to "float"

### `src/symbiont_lab/studies/heritage/longitudinal.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.collective" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.heritage" could not be resolved

### `src/symbiont_lab/studies/heritage/stress.py` (3)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.collective" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.heritage" could not be resolved
- `14:6` · **warning** · `reportMissingImports` — Import "symbiont.core.model" could not be resolved

### `src/symbiont_lab/studies/integrated_habitat_runtime.py` (1)

- `80:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "telemetry" for class "IntegratedHabitatRuntime" Expression of type "_DisabledTelemetry" cannot be assigned to attribute "telemetry" of class "IntegratedHabitatRuntime" "_DisabledTelemetry" is not assignable to "CommunicationTelemetry"

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_adaptation.py` (5)

- `47:21` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `140:50` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `141:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `143:22` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `145:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "object" of type "dict[str, object]" in function "append" "object" is not assignable to "dict[str, object]"

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_agency.py` (4)

- `101:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_replay_active" for class "Tick3D" Attribute "primitive_replay_active" is unknown
- `102:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_motor_primitives" for class "Tick3D" Attribute "cognitive_motor_primitives" is unknown
- `115:35` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "motor_primitives" for class "Tick3D" Attribute "motor_primitives" is unknown
- `116:45` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_motor_primitives" for class "Tick3D" Attribute "cognitive_motor_primitives" is unknown

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_counterfactual.py` (6)

- `109:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `110:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_primitives" for class "SensorimotorSnapshot" Attribute "cognitive_primitives" is unknown
- `119:41` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `177:30` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `180:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "object" of type "dict[str, object]" in function "append" "object" is not assignable to "dict[str, object]"
- `204:21` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/studies/learning/cognitive_ecology_embodiment.py` (1)

- `90:37` · **error** · `reportOptionalMemberAccess` — "development" is not a known attribute of "None"

### `src/symbiont_lab/studies/learning/cognitive_graph_causal_composition.py` (1)

- `22:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved

### `src/symbiont_lab/studies/learning/embodied_model_comparison.py` (4)

- `102:29` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "list[float]" Attribute "value" is unknown
- `102:29` · **error** · `reportOptionalMemberAccess` — "value" is not a known attribute of "None"
- `104:42` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "TemporalPrediction[tuple[float, ...]]"
- `104:42` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable

### `src/symbiont_lab/studies/learning/emergent_structured_communication.py` (17)

- `241:36` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "organism_id" for class "object" Attribute "organism_id" is unknown
- `243:28` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "sequence_grounding_ledger" for class "object" Attribute "sequence_grounding_ledger" is unknown
- `246:17` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "autonomous_retransmit_sequence" for class "object" Attribute "autonomous_retransmit_sequence" is unknown
- `251:54` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `252:42` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `253:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `254:46` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `258:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `258:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `262:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `263:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `264:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `264:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `266:54` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "Literal[0]"
- `267:36` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"
- `268:32` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"
- `270:57` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "object" and "float"

### `src/symbiont_lab/studies/learning/emergent_symbol_grounding.py` (21)

- `148:26` · **error** · `reportArgumentType` — Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str | None" is not assignable to type "str" "None" is not assignable to "str"
- `276:26` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "symbol_emissions" of type "int" in function "__init__" "object" is not assignable to "int"
- `277:29` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "unique_symbols_used" of type "int" in function "__init__" "object" is not assignable to "int"
- `278:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "receivers_exposed" of type "int" in function "__init__" "object" is not assignable to "int"
- `279:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "grounding_updates" of type "int" in function "__init__" "object" is not assignable to "int"
- `280:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "grounding_gain" of type "float" in function "__init__" "object" is not assignable to "float"
- `281:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "prediction_gain" of type "float" in function "__init__" "object" is not assignable to "float"
- `282:24` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "no_signal_gain" of type "float" in function "__init__" "object" is not assignable to "float"
- `283:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "convention_agreement" of type "float" in function "__init__" "object" is not assignable to "float"
- `284:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `285:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "random_signal_gain" of type "float" in function "__init__" "object" is not assignable to "float"
- `286:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "permuted_symbol_gain" of type "float" in function "__init__" "object" is not assignable to "float"
- `288:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "newborn_acquisition_ticks" of type "int" in function "__init__" "object" is not assignable to "int"
- `290:32` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "Literal[0]"
- `290:64` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "Literal[1]"
- `291:32` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "Literal[0]"
- `292:33` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"
- `293:28` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "float"
- `294:35` · **error** · `reportOperatorIssue` — Operator ">=" not supported for types "object" and "float"
- `296:34` · **error** · `reportOperatorIssue` — Operator "<=" not supported for types "object" and "Literal[4]"
- `298:41` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"

### `src/symbiont_lab/studies/learning/independent_symbol_grounding.py` (7)

- `266:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `267:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "context_token" of type "str" in function "__init__" "object" is not assignable to "str"
- `268:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "outcome_token" of type "str" in function "__init__" "object" is not assignable to "str"
- `269:45` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "organism_id" for class "object" Attribute "organism_id" is unknown
- `271:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "tick" of type "int" in function "__init__" "object" is not assignable to "int"
- `272:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "success" of type "bool" in function "__init__" "object" is not assignable to "bool"
- `274:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "report_symbol_reinforcement" for class "object" Attribute "report_symbol_reinforcement" is unknown

### `src/symbiont_lab/studies/learning/predictive_discovery.py` (1)

- `29:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved

### `src/symbiont_lab/studies/learning/predictive_utility.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved

### `src/symbiont_lab/studies/learning/prospective_agency_embodied.py` (12)

- `132:33` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "attach_existing" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" is not assignable to type "_PrivateModelRuntime" "ModeledOrganismRuntime" is incompatible with protocol "_PrivateModelRuntime" "settle_private_model_training_compute" is an incompatible type Type "(*, request_id: str, steps_completed: int) -> bool" is not assignable to type "(*, request_id: str, steps_completed: int) -> None" Function return type "bool" is incompatible with type "None" "adopt_private_model" is an incompatible type Type "(artifact: ModelArtifactManifest, *, evaluation_summary: tuple[int, ...] = ()) -> ModelRecord" is not assignable to type "(manifest: Any, *, evaluation_summary: tuple[int, ...]) -> Any" Parameter name mismatch: "manifest" versus "artifact"
- `143:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_prospective_agency" for class "ModeledOrganismRuntime" Attribute "_prospective_agency" is unknown
- `155:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "predict_primitive_outcome" for class "ModeledOrganismRuntime" Attribute "predict_primitive_outcome" is unknown
- `155:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "predict_primitive_outcome" for class "PrivateModelOrganismRuntime" Attribute "predict_primitive_outcome" is unknown
- `161:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "predict_primitive_outcome" for class "ModeledOrganismRuntime" Attribute "predict_primitive_outcome" is unknown
- `161:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "predict_primitive_outcome" for class "PrivateModelOrganismRuntime" Attribute "predict_primitive_outcome" is unknown
- `185:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_pending_outcome_value_credit" for class "ModeledOrganismRuntime" Attribute "_pending_outcome_value_credit" is unknown
- `190:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_schedule_observed_outcome_value_credit" for class "ModeledOrganismRuntime" Attribute "_schedule_observed_outcome_value_credit" is unknown
- `362:30` · **error** · `reportArgumentType` — Argument of type "PyBulletEmbodimentRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "poll" "PyBulletEmbodimentRuntime" is incompatible with protocol "_PrivateModelRuntime" "model_registry" is not present "attach_private_model_bridge" is not present "autonomous_private_learning_plan" is not present "settle_private_model_training_compute" is not present "adopt_private_model" is not present "activate_private_model" is not present "retire_private_model" is not present
- `368:46` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_motor_competence_candidates" for class "Tick3D" Attribute "cognitive_motor_competence_candidates" is unknown
- `453:25` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "maybe_schedule" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" is not assignable to type "_PrivateModelRuntime" "ModeledOrganismRuntime" is incompatible with protocol "_PrivateModelRuntime" "settle_private_model_training_compute" is an incompatible type Type "(*, request_id: str, steps_completed: int) -> bool" is not assignable to type "(*, request_id: str, steps_completed: int) -> None" Function return type "bool" is incompatible with type "None" "adopt_private_model" is an incompatible type Type "(artifact: ModelArtifactManifest, *, evaluation_summary: tuple[int, ...] = ()) -> ModelRecord" is not assignable to type "(manifest: Any, *, evaluation_summary: tuple[int, ...]) -> Any" Parameter name mismatch: "manifest" versus "artifact"
- `460:45` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" cannot be assigned to parameter "runtime" of type "_PrivateModelRuntime" in function "wait_until_idle" Type "PrivateModelOrganismRuntime | ModeledOrganismRuntime" is not assignable to type "_PrivateModelRuntime" "ModeledOrganismRuntime" is incompatible with protocol "_PrivateModelRuntime" "settle_private_model_training_compute" is an incompatible type Type "(*, request_id: str, steps_completed: int) -> bool" is not assignable to type "(*, request_id: str, steps_completed: int) -> None" Function return type "bool" is incompatible with type "None" "adopt_private_model" is an incompatible type Type "(artifact: ModelArtifactManifest, *, evaluation_summary: tuple[int, ...] = ()) -> ModelRecord" is not assignable to type "(manifest: Any, *, evaluation_summary: tuple[int, ...]) -> Any" Parameter name mismatch: "manifest" versus "artifact"

### `src/symbiont_lab/studies/learning/signal_knowledge.py` (3)

- `13:6` · **warning** · `reportMissingImports` — Import "symbiont.core.signal_identity" could not be resolved
- `14:6` · **warning** · `reportMissingImports` — Import "symbiont.core.signal_knowledge" could not be resolved
- `15:6` · **warning** · `reportMissingImports` — Import "symbiont.core.signal_knowledge_types" could not be resolved

### `src/symbiont_lab/studies/learning/structural_producer_fairness.py` (1)

- `6:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved

### `src/symbiont_lab/studies/learning/structured_communication_characterization.py` (4)

- `377:40` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "condition" for class "object" Attribute "condition" is unknown
- `382:9` · **error** · `reportArgumentType` — Argument of type "tuple[object, ...]" cannot be assigned to parameter "per_seed" of type "tuple[CommunicationSeedResult, ...]" in function "__init__" "tuple[object, ...]" is not assignable to "tuple[CommunicationSeedResult, ...]" Tuple entry 1 is incorrect type "object" is not assignable to "CommunicationSeedResult"
- `390:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "receiver_prediction_gain" for class "object" Attribute "receiver_prediction_gain" is unknown
- `392:53` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "classification" for class "object" Attribute "classification" is unknown

### `src/symbiont_lab/studies/learning/temporal_private_model_controls.py` (2)

- `213:21` · **error** · `reportCallIssue` — No overloads for "min" match the provided arguments
- `213:40` · **error** · `reportArgumentType` — Argument of type "Overload[(key: str, default: None = None, /) -> (float | None), (key: str, default: float, /) -> float, (key: str, default: _T@get, /) -> (float | _T@get)]" cannot be assigned to parameter "key" of type "(_T@min) -> SupportsRichComparison" in function "min" No overloaded function matches type "(str) -> SupportsRichComparison"

### `src/symbiont_lab/studies/perception/__init__.py` (1)

- `34:1` · **warning** · `reportUnsupportedDunderAll` — Operation on "__all__" is not supported, so exported symbol list may be incorrect

### `src/symbiont_lab/studies/perception/autonomous_selection.py` (4)

- `172:15` · **error** · `reportCallIssue` — No overloads for "min" match the provided arguments
- `172:38` · **error** · `reportArgumentType` — Argument of type "Overload[(key: str, default: None = None, /) -> (float | None), (key: str, default: float, /) -> float, (key: str, default: _T@get, /) -> (float | _T@get)]" cannot be assigned to parameter "key" of type "(_T@min) -> SupportsRichComparison" in function "min" No overloaded function matches type "(str) -> SupportsRichComparison"
- `388:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `388:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...

### `src/symbiont_lab/studies/perception/sensory_specialisation.py` (33)

- `28:16` · **error** · `reportReturnType` — Type "dict[str, Any | bool]" is not assignable to return type "dict[str, object]" "dict[str, Any | bool]" is not assignable to "dict[str, object]" Type parameter "_VT@dict" is invariant, but "Any | bool" is not the same as "object" Consider switching from "dict" to "Mapping" which is covariant in the value type
- `90:33` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `90:33` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `156:43` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `156:43` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `157:46` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `157:46` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `226:37` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `226:37` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `227:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `227:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `228:37` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `228:37` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `229:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `229:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `313:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown
- `316:60` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `317:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `416:33` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `416:33` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `417:34` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `417:34` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `420:35` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `420:35` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `462:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown
- `465:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `466:71` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `467:71` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `484:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `484:36` · **error** · `reportArgumentType` — Argument of type "float | None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float | None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `566:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `583:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `584:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/studies/physics3d/primitive_effects.py` (11)

- `107:12` · **error** · `reportReturnType` — Type "tuple[float, ...]" is not assignable to return type "tuple[float, float, float]" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `175:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `175:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `178:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `178:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `219:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex"
- `219:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `223:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex"
- `223:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `229:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex"
- `229:31` · **error** · `reportArgumentType` — Argument of type "object | float" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object | float" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" ...

### `src/symbiont_lab/studies/physiology.py` (4)

- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.homeostasis" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `11:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/predictive_development_gates.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.attention" could not be resolved

### `src/symbiont_lab/studies/reproduction_runtime.py` (3)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.birth_authority" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved
- `31:77` · **error** · `reportArgumentType` — Argument of type "tuple[int, ...]" cannot be assigned to parameter "running_version" of type "tuple[int, int, int]" in function "load_base_genome" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont_lab/studies/runtime_population.py` (4)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.birth_authority" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved
- `32:77` · **error** · `reportArgumentType` — Argument of type "tuple[int, ...]" cannot be assigned to parameter "running_version" of type "tuple[int, int, int]" in function "load_base_genome" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont_lab/studies/runtime_prediction_longitudinal.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/runtime_prediction_promotion.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.cognition_bridge" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/shared_habitat_intake.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.ecology" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved

### `src/symbiont_lab/studies/social_emergence.py` (3)

- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `50:9` · **error** · `reportArgumentType` — Argument of type "tuple[str, ...]" cannot be assigned to parameter "key" of type "tuple[str, str]" in function "__getitem__" "tuple[str, ...]" is not assignable to "tuple[str, str]" Tuple size mismatch; expected 2 but received indeterminate
- `50:9` · **error** · `reportArgumentType` — Argument of type "tuple[str, ...]" cannot be assigned to parameter "key" of type "tuple[str, str]" in function "__setitem__" "tuple[str, ...]" is not assignable to "tuple[str, str]" Tuple size mismatch; expected 2 but received indeterminate

### `src/symbiont_lab/studies/social_longitudinal.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved

### `src/symbiont_lab/studies/social_reciprocity.py` (1)

- `12:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved

### `src/symbiont_lab/studies/social_runtime_adaptation.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_adversarial.py` (2)

- `12:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `13:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_competition.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_context.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_context_replay.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_denial_revision.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_emergence.py` (2)

- `14:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `15:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_generations.py` (6)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.birth_authority" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `11:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved
- `38:77` · **error** · `reportArgumentType` — Argument of type "tuple[int, ...]" cannot be assigned to parameter "running_version" of type "tuple[int, int, int]" in function "load_base_genome" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont_lab/studies/social_runtime_lifecycle.py` (6)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.birth_authority" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `11:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved
- `36:77` · **error** · `reportArgumentType` — Argument of type "tuple[int, ...]" cannot be assigned to parameter "running_version" of type "tuple[int, int, int]" in function "load_base_genome" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont_lab/studies/social_runtime_longitudinal.py` (2)

- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_preference.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_regime_shift.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_replay.py` (4)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `10:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_resource_adaptation.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_runtime_specialization.py` (2)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved
- `8:6` · **warning** · `reportMissingImports` — Import "symbiont.core.runtime" could not be resolved

### `src/symbiont_lab/studies/social_specialization.py` (1)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.interactions" could not be resolved

### `src/symbiont_lab/studies/world/genesis_viability.py` (7)

- `181:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "tick" for class "object" Attribute "tick" is unknown
- `183:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `197:42` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `200:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `207:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `208:52` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `232:41` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "tick" for class "object" Attribute "tick" is unknown

### `src/symbiont_lab/workbench/runs.py` (2)

- `268:20` · **error** · `reportArgumentType` — Argument of type "BaseException" cannot be assigned to parameter "exc" of type "Exception" in function "fail" "BaseException" is not assignable to "Exception"
- `375:20` · **error** · `reportArgumentType` — Argument of type "BaseException" cannot be assigned to parameter "exc" of type "Exception" in function "fail" "BaseException" is not assignable to "Exception"

### `src/symbiont_lab/world/adapter.py` (16)

- `18:6` · **warning** · `reportMissingImports` — Import "symbiont.core.ecology" could not be resolved
- `19:6` · **warning** · `reportMissingImports` — Import "symbiont.core.metabolism" could not be resolved
- `20:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `317:25` · **error** · `reportArgumentType` — Argument of type "tuple[int, ...]" cannot be assigned to parameter "running_version" of type "tuple[int, int, int]" in function "load_base_genome" "tuple[int, ...]" is not assignable to "tuple[int, int, int]" Tuple size mismatch; expected 3 but received indeterminate
- `522:14` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved
- `523:14` · **warning** · `reportMissingImports` — Import "symbiont.core.individual" could not be resolved
- `524:14` · **warning** · `reportMissingImports` — Import "symbiont.core.symbiont" could not be resolved
- `665:34` · **error** · `reportOptionalMemberAccess` — "_habitat" is not a known attribute of "None"
- `666:24` · **error** · `reportOptionalMemberAccess` — "_habitat" is not a known attribute of "None"
- `674:30` · **error** · `reportOptionalMemberAccess` — "tick_count" is not a known attribute of "None"
- `680:28` · **error** · `reportOptionalMemberAccess` — "_most_depleted_metabolic_kind" is not a known attribute of "None"
- `681:21` · **error** · `reportOptionalMemberAccess` — "request_resource_intake" is not a known attribute of "None"
- `749:29` · **error** · `reportOptionalMemberAccess` — "_physiology" is not a known attribute of "None"
- `767:34` · **error** · `reportOptionalMemberAccess` — "apply_environmental_damage" is not a known attribute of "None"
- `784:26` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `808:38` · **error** · `reportOptionalMemberAccess` — "apply_environmental_damage" is not a known attribute of "None"

### `src/symbiont_lab/world/persistence.py` (1)

- `20:6` · **warning** · `reportMissingImports` — Import "symbiont.core.ecology" could not be resolved

### `src/symbiont_lab/world/population.py` (4)

- `7:6` · **warning** · `reportMissingImports` — Import "symbiont.core.physiology" could not be resolved
- `766:38` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved
- `806:33` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `807:80` · **error** · `reportOptionalMemberAccess` — "last_actuation" is not a known attribute of "None"

### `src/symbiont_lab/world/transaction.py` (3)

- `95:37` · **error** · `reportOptionalMemberAccess` — "history" is not a known attribute of "None"
- `99:31` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_snapshot_rigs" for class "IntegratedWorldTickTransaction*" Type "dict[str, tuple[Any, int | None]]" is not assignable to type "dict[str, _OrganismRig] | None" "dict[str, tuple[Any, int | None]]" is not assignable to "dict[str, _OrganismRig]" Type parameter "_VT@dict" is invariant, but "tuple[Any, int | None]" is not the same as "_OrganismRig" Consider switching from "dict" to "Mapping" which is covariant in the value type "dict[str, tuple[Any, int | None]]" is not assignable to "None"
- `142:44` · **error** · `reportOptionalMemberAccess` — "history" is not a known attribute of "None"

## Criterio de resolución

Los errores se corrigen por contrato y causa raíz: primero límites entre paquetes/imports, después modelos explícitos de persistencia, telemetría, física y entradas dinámicas, y finalmente checks opcionales locales. Los warnings de imports entre `symbiont` y `symbiont_lab` no se silencian globalmente: requieren resolver el límite arquitectónico. No se aceptan `# pyright: ignore`, exclusiones amplias ni `cast` sin contrato documentado.

Los diagnósticos que representen una incompatibilidad histórica o una dependencia opcional deben quedar señalados cerca del límite con `# TODO(pyright)`/`# NOTE(pyright)` y registrados también en `docs/development/type-checking.md`.
