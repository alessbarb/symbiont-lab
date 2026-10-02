# Inventario completo de Pyright — actualizado 2026-10-02

Esta es una fotografía reproducible del diagnóstico global de Pyright sobre `src/` y `observatory/`, regenerada el **2026-10-02**. El nombre histórico del archivo se conserva para no romper enlaces. No modifica el comportamiento del código ni convierte los diagnósticos en excepciones. Cada entrada conserva archivo, línea, severidad, regla y mensaje normalizado.

## Comando y alcance

```bash
.venv/bin/pyright --outputjson > /tmp/pyright-inventory.json
```

Versión ejecutada: **Pyright 1.1.414**. La configuración aplicada es `pyrightconfig.json`; tests, artefactos generados e históricos permanecen fuera del alcance configurado. Este inventario es una fotografía fechada y debe regenerarse tras cada bloque de correcciones; no es un baseline aceptable para ocultar errores.

## Resumen

- Archivos analizados: **585**
- Archivos con diagnósticos: **90**
- Errores: **386**
- Warnings: **10**
- Informaciones: **0**
- Duración reportada: **25.967 s**

## Reglas por severidad

| Severidad | Regla | Casos |
|---|---|---:|
| error | `reportArgumentType` | 183 |
| error | `reportAttributeAccessIssue` | 98 |
| error | `reportOptionalMemberAccess` | 57 |
| error | `reportOperatorIssue` | 15 |
| error | `reportGeneralTypeIssues` | 13 |
| error | `reportCallIssue` | 7 |
| error | `reportOptionalOperand` | 5 |
| error | `reportIndexIssue` | 3 |
| error | `reportOptionalSubscript` | 3 |
| error | `reportAssignmentType` | 1 |
| error | `reportReturnType` | 1 |
| warning | `reportMissingImports` | 7 |
| warning | `reportUnsupportedDunderAll` | 2 |
| warning | `reportUnusedExpression` | 1 |

## Archivos por volumen

| Casos | Archivo |
|---:|---|
| 33 | `src/symbiont_lab/studies/perception/sensory_specialisation.py` |
| 28 | `src/symbiont_lab/physics3d/telemetry/v41.py` |
| 21 | `src/symbiont_lab/studies/learning/emergent_symbol_grounding.py` |
| 18 | `src/symbiont_lab/app/physics3d/monitor/viewer.py` |
| 17 | `src/symbiont_lab/physics3d/runtime.py` |
| 17 | `src/symbiont_lab/studies/learning/emergent_structured_communication.py` |
| 12 | `observatory/resident.py` |
| 9 | `src/symbiont/modeling/runtime.py` |
| 9 | `src/symbiont_lab/physics3d/engine.py` |
| 9 | `src/symbiont_lab/physics3d/humanoid.py` |
| 9 | `src/symbiont_lab/world/adapter.py` |
| 8 | `src/symbiont/core/signals/knowledge.py` |
| 7 | `src/symbiont/actuation/binding.py` |
| 7 | `src/symbiont/core/embodiment/body_schema.py` |
| 7 | `src/symbiont_lab/studies/learning/independent_symbol_grounding.py` |
| 7 | `src/symbiont_lab/studies/world/genesis_viability.py` |
| 6 | `src/symbiont_lab/physics3d/resource.py` |
| 6 | `src/symbiont_lab/physics3d/telemetry/binary.py` |
| 6 | `src/symbiont_lab/studies/attention/retrospective.py` |
| 5 | `src/symbiont_lab/studies/campaigns/campaign.py` |
| 5 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_counterfactual.py` |
| 5 | `src/symbiont_lab/studies/learning/generative_recombination_construction.py` |
| 4 | `src/symbiont/actuation/acquisition.py` |
| 4 | `src/symbiont/core/orchestration/resident.py` |
| 4 | `src/symbiont/modeling/culture.py` |
| 4 | `src/symbiont_lab/app/run_controller.py` |
| 4 | `src/symbiont_lab/observation/physics3d.py` |
| 4 | `src/symbiont_lab/physics3d/telemetry/tools.py` |
| 4 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_adaptation.py` |
| 4 | `src/symbiont_lab/studies/learning/canonical_sensorimotor_agency.py` |
| 4 | `src/symbiont_lab/studies/learning/embodied_model_comparison.py` |
| 4 | `src/symbiont_lab/studies/learning/generative_counterfactual_utility.py` |
| 4 | `src/symbiont_lab/studies/learning/structured_communication_characterization.py` |
| 4 | `src/symbiont_lab/studies/perception/autonomous_selection.py` |
| 4 | `src/symbiont_lab/studies/runtime_prediction_longitudinal.py` |
| 3 | `src/symbiont/agency/candidates.py` |
| 3 | `src/symbiont/core/domains/epistemic.py` |
| 3 | `src/symbiont/core/embodiment/memory.py` |
| 3 | `src/symbiont_lab/kernel_characterization/runner.py` |
| 3 | `src/symbiont_lab/observation/projection.py` |
| 3 | `src/symbiont_lab/physics3d/reembodiment.py` |
| 3 | `src/symbiont_lab/physics3d/telemetry/v3.py` |
| 3 | `src/symbiont_lab/studies/embodiment/label_invariance.py` |
| 3 | `src/symbiont_lab/world/transaction.py` |
| 2 | `observatory/adapter.py` |
| 2 | `observatory/server.py` |
| 2 | `src/symbiont/cognition/structure.py` |
| 2 | `src/symbiont/core/cognition/bridge_checkpoint.py` |
| 2 | `src/symbiont/genetics/migration.py` |
| 2 | `src/symbiont/modeling/private_runtime.py` |
| 2 | `src/symbiont/sensory/predictive_credit.py` |
| 2 | `src/symbiont_lab/cli/world.py` |
| 2 | `src/symbiont_lab/modeling/gateway.py` |
| 2 | `src/symbiont_lab/observation/observatory.py` |
| 2 | `src/symbiont_lab/server/server.py` |
| 2 | `src/symbiont_lab/studies/campaigns/comparative.py` |
| 2 | `src/symbiont_lab/studies/campaigns/interpretation.py` |
| 2 | `src/symbiont_lab/studies/heritage/stress.py` |
| 2 | `src/symbiont_lab/studies/learning/prospective_agency_embodied.py` |
| 2 | `src/symbiont_lab/studies/learning/temporal_private_model_controls.py` |
| 2 | `src/symbiont_lab/studies/runtime_prediction_promotion.py` |
| 2 | `src/symbiont_lab/studies/social_runtime_context_replay.py` |
| 2 | `src/symbiont_lab/workbench/runs.py` |
| 2 | `src/symbiont_lab/world/population.py` |
| 1 | `observatory/_node_harness.py` |
| 1 | `observatory/provenance.py` |
| 1 | `src/symbiont/actuation/sensorimotor.py` |
| 1 | `src/symbiont/actuation/surface.py` |
| 1 | `src/symbiont/cognition/generative/consolidation.py` |
| 1 | `src/symbiont/core/cognition/agent.py` |
| 1 | `src/symbiont/core/domains/action.py` |
| 1 | `src/symbiont/core/domains/cognition.py` |
| 1 | `src/symbiont/core/domains/physiology.py` |
| 1 | `src/symbiont/core/embodiment/metabolism.py` |
| 1 | `src/symbiont/core/embodiment/session.py` |
| 1 | `src/symbiont/core/orchestration/runtime.py` |
| 1 | `src/symbiont/genetics/genome.py` |
| 1 | `src/symbiont/host/checkpoint.py` |
| 1 | `src/symbiont/modeling/episodic.py` |
| 1 | `src/symbiont_lab/app/physics3d/session.py` |
| 1 | `src/symbiont_lab/integration/integrated_habitat.py` |
| 1 | `src/symbiont_lab/modeling/reservoir.py` |
| 1 | `src/symbiont_lab/physics3d/environments.py` |
| 1 | `src/symbiont_lab/physics3d/equivalence.py` |
| 1 | `src/symbiont_lab/physics3d/monitor.py` |
| 1 | `src/symbiont_lab/physics3d/observer_semantics.py` |
| 1 | `src/symbiont_lab/studies/heritage/ecological_shift.py` |
| 1 | `src/symbiont_lab/studies/integrated_habitat_runtime.py` |
| 1 | `src/symbiont_lab/studies/learning/cognitive_ecology_embodiment.py` |
| 1 | `src/symbiont_lab/studies/perception/__init__.py` |

## Diagnósticos completos

### `observatory/_node_harness.py` (1)

- `3:6` · **warning** · `reportMissingImports` — Import "observatory.tests._node_harness" could not be resolved

### `observatory/adapter.py` (2)

- `1535:43` · **error** · `reportArgumentType` — Argument of type "CognitiveGraph \| None" cannot be assigned to parameter "graph" of type "CognitiveGraph" in function "_developmental_divergence" Type "CognitiveGraph \| None" is not assignable to type "CognitiveGraph" "None" is not assignable to "CognitiveGraph"
- `1711:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cultural_observations" for class "OrganismRuntime" Attribute "cultural_observations" is unknown

### `observatory/provenance.py` (1)

- `134:77` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `observatory/resident.py` (12)

- `417:63` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `417:78` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "models" for class "ModelRegistry" Attribute "models" is unknown
- `418:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "experience_ledger" for class "OrganismRuntime" Attribute "experience_ledger" is unknown
- `420:64` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "experience_ledger" for class "OrganismRuntime" Attribute "experience_ledger" is unknown
- `429:46` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `433:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "attach_private_model_bridge" for class "OrganismRuntime" Attribute "attach_private_model_bridge" is unknown
- `456:28` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "autonomous_private_learning_plan" for class "OrganismRuntime" Attribute "autonomous_private_learning_plan" is unknown
- `464:21` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "settle_private_model_training_compute" for class "OrganismRuntime" Attribute "settle_private_model_training_compute" is unknown
- `468:31` · **error** · `reportArgumentType` — Argument of type "PrivateModelOrganismRuntime \| OrganismRuntime" cannot be assigned to parameter "runtime" of type "ModeledOrganismRuntime" in function "adopt" Type "PrivateModelOrganismRuntime \| OrganismRuntime" is not assignable to type "ModeledOrganismRuntime" "OrganismRuntime" is not assignable to "ModeledOrganismRuntime"
- `469:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `478:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "model_registry" for class "OrganismRuntime" Attribute "model_registry" is unknown
- `482:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "attach_private_model_bridge" for class "OrganismRuntime" Attribute "attach_private_model_bridge" is unknown

### `observatory/server.py` (2)

- `80:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "payload" for class "object" Attribute "payload" is unknown
- `89:51` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "events_after" for class "object" Attribute "events_after" is unknown

### `src/symbiont/actuation/acquisition.py` (4)

- `745:58` · **error** · `reportOptionalMemberAccess` — "entity_id" is not a known attribute of "None"
- `746:58` · **error** · `reportOptionalMemberAccess` — "version" is not a known attribute of "None"
- `828:50` · **error** · `reportOptionalMemberAccess` — "entity_id" is not a known attribute of "None"
- `828:94` · **error** · `reportOptionalMemberAccess` — "version" is not a known attribute of "None"

### `src/symbiont/actuation/binding.py` (7)

- `151:59` · **error** · `reportOptionalMemberAccess` — "status" is not a known attribute of "None"
- `151:76` · **error** · `reportOptionalMemberAccess` — "revision" is not a known attribute of "None"
- `221:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `221:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `222:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `222:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `223:30` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[_T@list]" in function "__init__" "object" is incompatible with protocol "Iterable[_T@list]" "__iter__" is not present

### `src/symbiont/actuation/sensorimotor.py` (1)

- `1848:48` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "int" and "int \| None" Operator ">" not supported for types "int" and "None"

### `src/symbiont/actuation/surface.py` (1)

- `134:15` · **error** · `reportArgumentType` — Argument of type "Sequence[str] \| bool" cannot be assigned to parameter "iterable" of type "Iterable[_T_co@tuple]" in function "__new__" Type "Sequence[str] \| bool" is not assignable to type "Iterable[_T_co@tuple]" "bool" is incompatible with protocol "Iterable[_T_co@tuple]" "__iter__" is not present

### `src/symbiont/agency/candidates.py` (3)

- `52:19` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_id" for class "object" Attribute "primitive_id" is unknown
- `54:22` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "maturity" for class "object" Attribute "maturity" is unknown
- `55:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_id" for class "object" Attribute "primitive_id" is unknown

### `src/symbiont/cognition/generative/consolidation.py` (1)

- `241:17` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "value" of type "str" in function "bounded_identifier" Type "Unknown \| None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont/cognition/structure.py` (2)

- `315:49` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `400:30` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont/core/cognition/agent.py` (1)

- `56:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "host_id" for class "HostModel" Attribute "host_id" is unknown

### `src/symbiont/core/cognition/bridge_checkpoint.py` (2)

- `353:44` · **error** · `reportArgumentType` — Argument of type "str" cannot be assigned to parameter "kind" of type "MutationKind" in function "__init__" Type "str" is not assignable to type "MutationKind" "str" is not assignable to type "Literal['add_edge']" "str" is not assignable to type "Literal['add_node']" "str" is not assignable to type "Literal['quarantine_edge']" "str" is not assignable to type "Literal['remove_edge']" "str" is not assignable to type "Literal['remove_node']"
- `363:27` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "eligible_tick" of type "int" in function "__init__" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"

### `src/symbiont/core/domains/action.py` (1)

- `2568:69` · **error** · `reportArgumentType` — Argument of type "Mapping[Unknown, Unknown]" cannot be assigned to parameter "payload" of type "dict[str, Any]" in function "restore" "Mapping[Unknown, Unknown]" is not assignable to "dict[str, Any]"

### `src/symbiont/core/domains/cognition.py` (1)

- `166:81` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "signal" of type "GenerativeConsolidationSignal" in function "is_mature" "object" is not assignable to "GenerativeConsolidationSignal"

### `src/symbiont/core/domains/epistemic.py` (3)

- `114:33` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "acclimation" of type "HostAcclimation" in function "revise" "object" is not assignable to "HostAcclimation"
- `124:13` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "acclimation" of type "HostAcclimation" in function "narrate_attended" "object" is not assignable to "HostAcclimation"
- `131:17` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "acclimation" of type "HostAcclimation" in function "narrate_host" "object" is not assignable to "HostAcclimation"

### `src/symbiont/core/domains/physiology.py` (1)

- `81:22` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "update_physiological_state" for class "object" Attribute "update_physiological_state" is unknown

### `src/symbiont/core/embodiment/body_schema.py` (7)

- `1435:17` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1436:20` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1437:20` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1440:16` · **error** · `reportOptionalOperand` — Operator ">" not supported for "None"
- `1446:31` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "support_count" of type "int" in function "__init__" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"
- `1447:35` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "opportunity_count" of type "int" in function "__init__" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"
- `1448:35` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "last_support_tick" of type "int" in function "__init__" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"

### `src/symbiont/core/embodiment/memory.py` (3)

- `394:17` · **error** · `reportArgumentType` — Argument of type "Unknown \| Any \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown \| Any \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `394:17` · **error** · `reportArgumentType` — Argument of type "Unknown \| Any \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown \| Any \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `407:15` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"

### `src/symbiont/core/embodiment/metabolism.py` (1)

- `63:21` · **error** · `reportGeneralTypeIssues` — Union syntax cannot be used with string operand; use quotes around entire expression

### `src/symbiont/core/embodiment/session.py` (1)

- `127:44` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "port_id" for class "str" Attribute "port_id" is unknown

### `src/symbiont/core/orchestration/resident.py` (4)

- `91:43` · **error** · `reportOptionalMemberAccess` — "state" is not a known attribute of "None"
- `98:43` · **error** · `reportOptionalMemberAccess` — "state" is not a known attribute of "None"
- `149:48` · **error** · `reportAttributeAccessIssue` — "load_base_graph" is unknown import symbol
- `165:48` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "export_checkpoint" for class "OrganismRuntime" Attribute "export_checkpoint" is unknown

### `src/symbiont/core/orchestration/runtime.py` (1)

- `2248:28` · **error** · `reportOperatorIssue` — Operator "<" not supported for types "Literal['normal', 'elevated', 'severe', 'unrecoverable']" and "float" Operator "<" not supported for types "Literal['normal']" and "float" when expected type is "list[str]" Operator "<" not supported for types "Literal['elevated']" and "float" when expected type is "list[str]" Operator "<" not supported for types "Literal['severe']" and "float" when expected type is "list[str]" Operator "<" not supported for types "Literal['unrecoverable']" and "float" when expected type is "list[str]"

### `src/symbiont/core/signals/knowledge.py` (8)

- `183:12` · **error** · `reportOperatorIssue` — Operator "<" not supported for types "int" and "int \| None" Operator "<" not supported for types "int" and "None"
- `336:72` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `336:72` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `344:38` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `344:38` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `618:15` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "observed_opportunities" for class "SignalProfile" Expression of type "Unknown \| None" cannot be assigned to attribute "observed_opportunities" of class "SignalProfile" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"
- `618:41` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "valid_observations" for class "SignalProfile" Expression of type "Unknown \| None" cannot be assigned to attribute "valid_observations" of class "SignalProfile" Type "Unknown \| None" is not assignable to type "int" "None" is not assignable to "int"
- `762:16` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_candidate_pairs" for class "SignalKnowledgeEngine*" Expression of type "set[tuple[str, ...]]" cannot be assigned to attribute "_candidate_pairs" of class "SignalKnowledgeEngine" "set[tuple[str, ...]]" is not assignable to "set[tuple[str, str]]" Type parameter "_T@set" is invariant, but "tuple[str, ...]" is not the same as "tuple[str, str]" Consider switching from "set" to "Container" which is covariant

### `src/symbiont/genetics/genome.py` (1)

- `301:22` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "prefix" of type "str" in function "walk" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont/genetics/migration.py` (2)

- `179:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "max_nodes" for class "object" Attribute "max_nodes" is unknown
- `183:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "max_edges" for class "object" Attribute "max_edges" is unknown

### `src/symbiont/host/checkpoint.py` (1)

- `116:54` · **error** · `reportArgumentType` — Argument of type "DriftAwareBaseline" cannot be assigned to parameter "baseline" of type "CapabilityBaseline" in function "consolidate_baseline" "DriftAwareBaseline" is not assignable to "CapabilityBaseline"

### `src/symbiont/modeling/culture.py` (4)

- `1182:47` · **error** · `reportOptionalMemberAccess` — "generation" is not a known attribute of "None"
- `1232:17` · **error** · `reportArgumentType` — Argument of type "list[SocialClaim \| None]" cannot be assigned to parameter "iterable" of type "Iterable[SocialClaim]" in function "extend"
- `1428:44` · **error** · `reportOptionalMemberAccess` — "transmission_depth" is not a known attribute of "None"
- `1431:44` · **error** · `reportOptionalMemberAccess` — "mutation_depth" is not a known attribute of "None"

### `src/symbiont/modeling/episodic.py` (1)

- `1225:17` · **error** · `reportArgumentType` — Argument of type "float" cannot be assigned to parameter "value" of type "int" in function "__setitem__" "float" is not assignable to "int"

### `src/symbiont/modeling/private_runtime.py` (2)

- `905:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `910:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"

### `src/symbiont/modeling/runtime.py` (9)

- `333:24` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `459:24` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `462:21` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `500:24` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `503:21` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `533:24` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `536:21` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
- `1695:28` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `1698:67` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"

### `src/symbiont/sensory/predictive_credit.py` (2)

- `110:23` · **error** · `reportArgumentType` — Argument of type "Any \| None" cannot be assigned to parameter "source_id" of type "str" in function "__init__" Type "Any \| None" is not assignable to type "str" "None" is not assignable to "str"
- `111:23` · **error** · `reportArgumentType` — Argument of type "Any \| None" cannot be assigned to parameter "target_id" of type "str" in function "__init__" Type "Any \| None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont_lab/app/physics3d/monitor/viewer.py` (18)

- `328:43` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `328:73` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `329:29` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "control" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `329:46` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "control" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `331:39` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `332:39` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `335:45` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `336:45` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `339:38` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `340:38` · **error** · `reportArgumentType` — Argument of type "Sequence[Mapping[str, Any]]" cannot be assigned to parameter "sample" of type "list[Mapping[str, Any]]" in function "mean" "Sequence[Mapping[str, Any]]" is not assignable to "list[Mapping[str, Any]]"
- `377:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "Process" for class "BaseContext" Attribute "Process" is unknown
- `2139:38` · **error** · `reportArgumentType` — Argument of type "bytearray" cannot be assigned to parameter "data" of type "bytes \| SupportsArrayInterface" in function "frombuffer" Type "bytearray" is not assignable to type "bytes \| SupportsArrayInterface" "bytearray" is not assignable to "bytes" Set disableBytesTypePromotions to false to enable type promotion behavior for "bytearray" and "memoryview" "bytearray" is incompatible with protocol "SupportsArrayInterface" "__array_interface__" is not present
- `2245:47` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2246:43` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2282:37` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2306:32` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2437:38` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2456:38` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "pos" of type "tuple[float, float, float]" in function "_project" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate

### `src/symbiont_lab/app/physics3d/session.py` (1)

- `88:55` · **error** · `reportArgumentType` — Argument of type "ObservationBus" cannot be assigned to parameter "sink" of type "EventSink" in function "__init__" "ObservationBus" is incompatible with protocol "EventSink" "push" is an incompatible type Type "(event: dict[str, Any]) -> int" is not assignable to type "(event: dict[str, Any]) -> None" Function return type "int" is incompatible with type "None" "int" is not assignable to "None"

### `src/symbiont_lab/app/run_controller.py` (4)

- `102:25` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_process" for class "RunController*" Type "SpawnProcess" is not assignable to type "Process \| None" "SpawnProcess" is not assignable to "Process" "SpawnProcess" is not assignable to "None"
- `107:23` · **error** · `reportOptionalMemberAccess` — "start" is not a known attribute of "None"
- `119:25` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_process" for class "RunController*" Type "SpawnProcess" is not assignable to type "Process \| None" "SpawnProcess" is not assignable to "Process" "SpawnProcess" is not assignable to "None"
- `124:23` · **error** · `reportOptionalMemberAccess` — "start" is not a known attribute of "None"

### `src/symbiont_lab/cli/world.py` (2)

- `8:6` · **warning** · `reportMissingImports` — Import "observatory.config" could not be resolved
- `9:6` · **warning** · `reportMissingImports` — Import "observatory.server" could not be resolved

### `src/symbiont_lab/integration/integrated_habitat.py` (1)

- `236:9` · **error** · `reportArgumentType` — Argument of type "OrganismRuntime" cannot be assigned to parameter "value" of type "ModeledOrganismRuntime" in function "__setitem__" "OrganismRuntime" is not assignable to "ModeledOrganismRuntime"

### `src/symbiont_lab/kernel_characterization/runner.py` (3)

- `216:55` · **error** · `reportOptionalMemberAccess` — "graph" is not a known attribute of "None"
- `660:50` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present
- `675:44` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "obj" of type "Sized" in function "len" "object" is incompatible with protocol "Sized" "__len__" is not present

### `src/symbiont_lab/modeling/gateway.py` (2)

- `119:29` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "parameters" for class "object" Attribute "parameters" is unknown
- `123:22` · **error** · `reportCallIssue` — Object of type "object" is not callable Attribute "__call__" is unknown

### `src/symbiont_lab/modeling/reservoir.py` (1)

- `179:9` · **warning** · `reportUnusedExpression` — Expression value is unused

### `src/symbiont_lab/observation/observatory.py` (2)

- `152:49` · **error** · `reportArgumentType` — Argument of type "Unknown \| float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown \| float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `152:49` · **error** · `reportArgumentType` — Argument of type "Unknown \| float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown \| float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"

### `src/symbiont_lab/observation/physics3d.py` (4)

- `272:30` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `272:30` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Unknown \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"
- `298:30` · **error** · `reportArgumentType` — Argument of type "Any \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Any \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `298:30` · **error** · `reportArgumentType` — Argument of type "Any \| None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "Any \| None" is not assignable to type "ConvertibleToInt" Type "None" is not assignable to type "ConvertibleToInt" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsInt" "__int__" is not present "None" is incompatible with protocol "SupportsIndex"

### `src/symbiont_lab/observation/projection.py` (3)

- `194:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `297:39` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `297:39` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "Unknown \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"

### `src/symbiont_lab/physics3d/engine.py` (9)

- `597:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `597:38` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `598:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `598:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `599:46` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `599:46` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `600:53` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `601:58` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `602:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/physics3d/environments.py` (1)

- `169:35` · **error** · `reportArgumentType` — Argument of type "Unknown \| None" cannot be assigned to parameter "name" of type "str" in function "environment_recipe" Type "Unknown \| None" is not assignable to type "str" "None" is not assignable to "str"

### `src/symbiont_lab/physics3d/equivalence.py` (1)

- `202:28` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/humanoid.py` (9)

- `842:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `843:35` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `924:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `924:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `925:55` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `926:53` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `927:47` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `928:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `928:37` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/physics3d/monitor.py` (1)

- `10:1` · **warning** · `reportUnsupportedDunderAll` — Operation on "__all__" is not supported, so exported symbol list may be incorrect

### `src/symbiont_lab/physics3d/observer_semantics.py` (1)

- `36:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown

### `src/symbiont_lab/physics3d/reembodiment.py` (3)

- `656:13` · **error** · `reportOptionalMemberAccess` — "append" is not a known attribute of "None"
- `672:15` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable
- `800:20` · **error** · `reportOptionalSubscript` — Object of type "None" is not subscriptable

### `src/symbiont_lab/physics3d/resource.py` (6)

- `44:28` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createCollisionShape" for class "object" Attribute "createCollisionShape" is unknown
- `45:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "GEOM_SPHERE" for class "object" Attribute "GEOM_SPHERE" is unknown
- `49:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createVisualShape" for class "object" Attribute "createVisualShape" is unknown
- `50:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "GEOM_SPHERE" for class "object" Attribute "GEOM_SPHERE" is unknown
- `55:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "createMultiBody" for class "object" Attribute "createMultiBody" is unknown
- `86:27` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "getContactPoints" for class "object" Attribute "getContactPoints" is unknown

### `src/symbiont_lab/physics3d/runtime.py` (17)

- `387:54` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "distance_to" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `730:32` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `734:48` · **error** · `reportOptionalMemberAccess` — "get" is not a known attribute of "None"
- `764:17` · **error** · `reportArgumentType` — Argument of type "Any \| Mapping[Unknown, Unknown] \| None" cannot be assigned to parameter "payload" of type "Mapping[str, Any]" in function "restore" Type "Any \| Mapping[Unknown, Unknown] \| None" is not assignable to type "Mapping[str, Any]" "None" is not assignable to "Mapping[str, Any]"
- `1091:35` · **error** · `reportArgumentType` — Argument of type "object \| None" cannot be assigned to parameter "body_schema_prior" of type "Mapping[str, Any] \| None" in function "archive_episode_checkpoint" Type "object \| None" is not assignable to type "Mapping[str, Any] \| None" Type "object" is not assignable to type "Mapping[str, Any] \| None" "object" is not assignable to "Mapping[str, Any]" "object" is not assignable to "None"
- `1094:29` · **error** · `reportArgumentType` — Argument of type "object \| None" cannot be assigned to parameter "living_body" of type "Mapping[str, Any] \| None" in function "archive_episode_checkpoint" Type "object \| None" is not assignable to type "Mapping[str, Any] \| None" Type "object" is not assignable to type "Mapping[str, Any] \| None" "object" is not assignable to "Mapping[str, Any]" "object" is not assignable to "None"
- `1523:49` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "field_at" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `1744:55` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "point" of type "tuple[float, float, float]" in function "distance_to" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `1863:76` · **error** · `reportOptionalMemberAccess` — "surface_fingerprint" is not a known attribute of "None"
- `1905:15` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "str" Attribute "value" is unknown
- `1991:82` · **error** · `reportOptionalMemberAccess` — "items" is not a known attribute of "None"
- `2000:77` · **error** · `reportOptionalMemberAccess` — "checkpoint" is not a known attribute of "None"
- `2202:21` · **error** · `reportGeneralTypeIssues` — Expected mapping for dictionary unpack operator
- `2273:27` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "base_position" of type "tuple[float, float, float]" in function "__init__" "tuple[float, ...]" is not assignable to "tuple[float, float, float]" Tuple size mismatch; expected 3 but received indeterminate
- `2274:30` · **error** · `reportArgumentType` — Argument of type "tuple[float, ...]" cannot be assigned to parameter "base_orientation" of type "tuple[float, float, float, float]" in function "__init__" "tuple[float, ...]" is not assignable to "tuple[float, float, float, float]" Tuple size mismatch; expected 4 but received indeterminate
- `2459:26` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined
- `2462:49` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/telemetry/binary.py` (6)

- `185:52` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "id" for class "BinaryStringTableReader" Attribute "id" is unknown
- `198:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "id" for class "BinaryStringTableReader" Attribute "id" is unknown
- `227:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "BinaryStringTableWriter" Attribute "get" is unknown
- `230:22` · **error** · `reportAssignmentType` — Type "list[Any]" is not assignable to declared type "dict[str, Any]" "list[Any]" is not assignable to "dict[str, Any]"
- `233:24` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "append" for class "dict[str, Any]" Attribute "append" is unknown
- `241:37` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "BinaryStringTableWriter" Attribute "get" is unknown

### `src/symbiont_lab/physics3d/telemetry/tools.py` (4)

- `77:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `101:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `102:23` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown
- `180:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "iter_records" for class "TelemetryReaderProtocol" Attribute "iter_records" is unknown

### `src/symbiont_lab/physics3d/telemetry/v3.py` (3)

- `249:19` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `249:24` · **error** · `reportArgumentType` — Argument of type "Mapping[str, Any] \| None" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" Type "Mapping[str, Any] \| None" is not assignable to type "Iterable[list[bytes]]" "Mapping[str, Any]" is not assignable to "Iterable[list[bytes]]" Type parameter "_T_co@Iterable" is covariant, but "str" is not a subtype of "list[bytes]" "str" is not assignable to "list[bytes]"
- `369:57` · **error** · `reportGeneralTypeIssues` — "object" is not iterable "__iter__" method not defined

### `src/symbiont_lab/physics3d/telemetry/v41.py` (28)

- `969:39` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" cannot be assigned to parameter "schemas" of type "BinaryFrameSchemaReader" in function "__init__" Type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" is not assignable to type "BinaryFrameSchemaReader" "FrameSchemaRegistryReader" is not assignable to "BinaryFrameSchemaReader"
- `969:54` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `978:17` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader \| StructuralPathRegistryReader" cannot be assigned to parameter "paths" of type "BinaryPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader \| StructuralPathRegistryReader" is not assignable to type "BinaryPathRegistryReader" "StructuralPathRegistryReader" is not assignable to "BinaryPathRegistryReader"
- `979:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `987:17` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" cannot be assigned to parameter "schemas" of type "BinaryFrameSchemaReader" in function "__init__" Type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" is not assignable to type "BinaryFrameSchemaReader" "FrameSchemaRegistryReader" is not assignable to "BinaryFrameSchemaReader"
- `988:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `996:40` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `999:41` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1003:17` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader \| StructuralPathRegistryReader" cannot be assigned to parameter "paths" of type "BinaryPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader \| StructuralPathRegistryReader" is not assignable to type "BinaryPathRegistryReader" "StructuralPathRegistryReader" is not assignable to "BinaryPathRegistryReader"
- `1004:17` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"
- `1012:39` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1021:52` · **error** · `reportArgumentType` — Argument of type "BinaryPathRegistryReader \| StructuralPathRegistryReader" cannot be assigned to parameter "registry" of type "StructuralPathRegistryReader" in function "__init__" Type "BinaryPathRegistryReader \| StructuralPathRegistryReader" is not assignable to type "StructuralPathRegistryReader" "BinaryPathRegistryReader" is not assignable to "StructuralPathRegistryReader"
- `1025:59` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1034:48` · **error** · `reportArgumentType` — Argument of type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" cannot be assigned to parameter "registry" of type "FrameSchemaRegistryReader" in function "__init__" Type "BinaryFrameSchemaReader \| FrameSchemaRegistryReader" is not assignable to type "FrameSchemaRegistryReader" "BinaryFrameSchemaReader" is not assignable to "FrameSchemaRegistryReader"
- `1044:42` · **error** · `reportArgumentType` — Argument of type "ObjectStore \| None" cannot be assigned to parameter "object_store" of type "ObjectStore" in function "__init__" Type "ObjectStore \| None" is not assignable to type "ObjectStore" "None" is not assignable to "ObjectStore"
- `1109:32` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "FrameStreamReader" Attribute "decode_record" is unknown
- `1110:43` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "FrameStreamReader" Attribute "decode_record" is unknown
- `1111:42` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "StructuralDeltaReader" Attribute "decode_record" is unknown
- `1111:42` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "LegacyStructuralStreamReader" Attribute "decode_record" is unknown
- `1112:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "EventStreamReader" Attribute "decode_record" is unknown
- `1113:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "_StaticStreamReader" Attribute "decode_record" is unknown
- `1114:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "decode_record" for class "dict[str, Any]" Attribute "decode_record" is unknown
- `1148:37` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "MethodType" Attribute "get" is unknown
- `1204:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "apply" for class "dict[str, Any]" Attribute "apply" is unknown
- `1204:34` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "apply" for class "dict[Unknown, Unknown]" Attribute "apply" is unknown
- `1205:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "MethodType" Attribute "get" is unknown
- `1237:30` · **error** · `reportArgumentType` — Argument of type "Any \| Unknown \| BinaryDeltaReader \| dict[str, Any] \| dict[Unknown, Unknown]" cannot be assigned to parameter "fallback" of type "Mapping[str, Any]" in function "reassemble_state" Type "Any \| Unknown \| BinaryDeltaReader \| dict[str, Any] \| dict[Unknown, Unknown]" is not assignable to type "Mapping[str, Any]" "BinaryDeltaReader" is not assignable to "Mapping[str, Any]"
- `1391:41` · **error** · `reportArgumentType` — Argument of type "BinaryStringTableReader \| None" cannot be assigned to parameter "strings" of type "BinaryStringTableReader" in function "__init__" Type "BinaryStringTableReader \| None" is not assignable to type "BinaryStringTableReader" "None" is not assignable to "BinaryStringTableReader"

### `src/symbiont_lab/server/server.py` (2)

- `41:14` · **warning** · `reportMissingImports` — Import "observatory.config" could not be resolved
- `257:48` · **error** · `reportArgumentType` — Argument of type "ObservationBus" cannot be assigned to parameter "sink" of type "EventSink" in function "__init__" "ObservationBus" is incompatible with protocol "EventSink" "push" is an incompatible type Type "(event: dict[str, Any]) -> int" is not assignable to type "(event: dict[str, Any]) -> None" Function return type "int" is incompatible with type "None" "int" is not assignable to "None"

### `src/symbiont_lab/studies/attention/retrospective.py` (6)

- `192:16` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `192:21` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `193:5` · **error** · `reportCallIssue` — No overloads for "__init__" match the provided arguments
- `193:10` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "iterable" of type "Iterable[list[bytes]]" in function "__init__" "object" is incompatible with protocol "Iterable[list[bytes]]" "__iter__" is not present
- `197:24` · **error** · `reportCallIssue` — No overloads for "get" match the provided arguments
- `197:37` · **error** · `reportArgumentType` — Argument of type "Literal['benign:normal', 'benign:update', 'benign:backup', 'benign:build', 'pathogen:ransom_sim', 'pathogen:bot_sim', 'pathogen:stealth_sim']" cannot be assigned to parameter "key" of type "bytes" in function "get" Type "Literal['benign:normal', 'benign:update', 'benign:backup', 'benign:build', 'pathogen:ransom_sim', 'pathogen:bot_sim', 'pathogen:stealth_sim']" is not assignable to type "bytes" "Literal['benign:backup']" is not assignable to "bytes"

### `src/symbiont_lab/studies/campaigns/campaign.py` (5)

- `52:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `141:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `142:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `144:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `144:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/studies/campaigns/comparative.py` (2)

- `144:48` · **error** · `reportArgumentType` — Argument of type "object \| Any" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object \| Any" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" ...
- `144:48` · **error** · `reportArgumentType` — Argument of type "object \| Any" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object \| Any" is not assignable to type "ConvertibleToFloat" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex"

### `src/symbiont_lab/studies/campaigns/interpretation.py` (2)

- `273:13` · **error** · `reportOptionalOperand` — Operator "*" not supported for "None"
- `273:52` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "arg2" of type "SupportsRichComparisonT@min" in function "min" Type "float \| None" is not assignable to type "float" "None" is not assignable to "float"

### `src/symbiont_lab/studies/embodiment/label_invariance.py` (3)

- `18:6` · **warning** · `reportMissingImports` — Import "symbiont.core.body" could not be resolved
- `19:6` · **warning** · `reportMissingImports` — Import "symbiont.core.individual" could not be resolved
- `20:6` · **warning** · `reportMissingImports` — Import "symbiont.core.symbiont" could not be resolved

### `src/symbiont_lab/studies/heritage/ecological_shift.py` (1)

- `135:20` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "get" for class "object" Attribute "get" is unknown

### `src/symbiont_lab/studies/heritage/stress.py` (2)

- `151:55` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "live_belief" for class "SocialEvidenceLedger" Attribute "live_belief" is unknown
- `152:46` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "belief" for class "SocialEvidenceLedger" Attribute "belief" is unknown

### `src/symbiont_lab/studies/integrated_habitat_runtime.py` (1)

- `80:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "telemetry" for class "IntegratedHabitatRuntime" Expression of type "_DisabledTelemetry" cannot be assigned to attribute "telemetry" of class "IntegratedHabitatRuntime" "_DisabledTelemetry" is not assignable to "CommunicationTelemetry"

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_adaptation.py` (4)

- `140:50` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `141:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `143:22` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `145:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "object" of type "dict[str, object]" in function "append" "object" is not assignable to "dict[str, object]"

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_agency.py` (4)

- `101:38` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "primitive_replay_active" for class "Tick3D" Attribute "primitive_replay_active" is unknown
- `102:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_motor_primitives" for class "Tick3D" Attribute "cognitive_motor_primitives" is unknown
- `115:35` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "motor_primitives" for class "Tick3D" Attribute "motor_primitives" is unknown
- `116:45` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_motor_primitives" for class "Tick3D" Attribute "cognitive_motor_primitives" is unknown

### `src/symbiont_lab/studies/learning/canonical_sensorimotor_counterfactual.py` (5)

- `109:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `110:30` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "cognitive_primitives" for class "SensorimotorSnapshot" Attribute "cognitive_primitives" is unknown
- `119:41` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "replay_primitive_id" for class "SensorimotorSnapshot" Attribute "replay_primitive_id" is unknown
- `177:30` · **error** · `reportIndexIssue` — "__getitem__" method not defined on type "object"
- `180:28` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "object" of type "dict[str, object]" in function "append" "object" is not assignable to "dict[str, object]"

### `src/symbiont_lab/studies/learning/cognitive_ecology_embodiment.py` (1)

- `90:37` · **error** · `reportOptionalMemberAccess` — "development" is not a known attribute of "None"

### `src/symbiont_lab/studies/learning/embodied_model_comparison.py` (4)

- `102:29` · **error** · `reportOptionalMemberAccess` — "value" is not a known attribute of "None"
- `102:29` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "list[float]" Attribute "value" is unknown
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
- `258:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `258:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `262:40` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `263:34` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `264:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `264:32` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `266:54` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "Literal[0]"
- `267:36` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"
- `268:32` · **error** · `reportOperatorIssue` — Operator ">" not supported for types "object" and "object"
- `270:57` · **error** · `reportOperatorIssue` — Operator "-" not supported for types "object" and "float"

### `src/symbiont_lab/studies/learning/emergent_symbol_grounding.py` (21)

- `148:26` · **error** · `reportArgumentType` — Argument of type "str \| None" cannot be assigned to parameter "key" of type "str" in function "__getitem__" Type "str \| None" is not assignable to type "str" "None" is not assignable to "str"
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

### `src/symbiont_lab/studies/learning/generative_counterfactual_utility.py` (4)

- `199:82` · **error** · `reportOptionalMemberAccess` — "comparison_score" is not a known attribute of "None"
- `200:64` · **error** · `reportOptionalMemberAccess` — "comparison_score" is not a known attribute of "None"
- `216:23` · **error** · `reportOptionalMemberAccess` — "expected_hypothesis_discrimination" is not a known attribute of "None"
- `220:19` · **error** · `reportOptionalMemberAccess` — "expected_hypothesis_discrimination" is not a known attribute of "None"

### `src/symbiont_lab/studies/learning/generative_recombination_construction.py` (5)

- `99:69` · **error** · `reportOptionalMemberAccess` — "origin" is not a known attribute of "None"
- `101:19` · **error** · `reportOptionalMemberAccess` — "source_episode_ids" is not a known attribute of "None"
- `102:42` · **error** · `reportOptionalMemberAccess` — "episode" is not a known attribute of "None"
- `105:80` · **error** · `reportOptionalMemberAccess` — "source_state_ids" is not a known attribute of "None"
- `110:48` · **error** · `reportOptionalMemberAccess` — "features" is not a known attribute of "None"

### `src/symbiont_lab/studies/learning/independent_symbol_grounding.py` (7)

- `266:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "symbol_id" of type "str" in function "__init__" "object" is not assignable to "str"
- `267:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "context_token" of type "str" in function "__init__" "object" is not assignable to "str"
- `268:31` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "outcome_token" of type "str" in function "__init__" "object" is not assignable to "str"
- `269:45` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "organism_id" for class "object" Attribute "organism_id" is unknown
- `271:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "tick" of type "int" in function "__init__" "object" is not assignable to "int"
- `272:25` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "success" of type "bool" in function "__init__" "object" is not assignable to "bool"
- `274:31` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "report_symbol_reinforcement" for class "object" Attribute "report_symbol_reinforcement" is unknown

### `src/symbiont_lab/studies/learning/prospective_agency_embodied.py` (2)

- `155:33` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "predict_primitive_outcome" for class "PrivateModelOrganismRuntime" Attribute "predict_primitive_outcome" is unknown
- `161:22` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "predict_primitive_outcome" for class "PrivateModelOrganismRuntime" Attribute "predict_primitive_outcome" is unknown

### `src/symbiont_lab/studies/learning/structured_communication_characterization.py` (4)

- `377:40` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "condition" for class "object" Attribute "condition" is unknown
- `382:9` · **error** · `reportArgumentType` — Argument of type "tuple[object, ...]" cannot be assigned to parameter "per_seed" of type "tuple[CommunicationSeedResult, ...]" in function "__init__" "tuple[object, ...]" is not assignable to "tuple[CommunicationSeedResult, ...]" Tuple entry 1 is incorrect type "object" is not assignable to "CommunicationSeedResult"
- `390:54` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "receiver_prediction_gain" for class "object" Attribute "receiver_prediction_gain" is unknown
- `392:53` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "classification" for class "object" Attribute "classification" is unknown

### `src/symbiont_lab/studies/learning/temporal_private_model_controls.py` (2)

- `213:21` · **error** · `reportCallIssue` — No overloads for "min" match the provided arguments
- `213:40` · **error** · `reportArgumentType` — Argument of type "Overload[(key: str, default: None = None, /) -> (float \| None), (key: str, default: float, /) -> float, (key: str, default: _T@get, /) -> (float \| _T@get)]" cannot be assigned to parameter "key" of type "(_T@min) -> SupportsRichComparison" in function "min" No overloaded function matches type "(str) -> SupportsRichComparison"

### `src/symbiont_lab/studies/perception/__init__.py` (1)

- `34:1` · **warning** · `reportUnsupportedDunderAll` — Operation on "__all__" is not supported, so exported symbol list may be incorrect

### `src/symbiont_lab/studies/perception/autonomous_selection.py` (4)

- `172:15` · **error** · `reportCallIssue` — No overloads for "min" match the provided arguments
- `172:38` · **error** · `reportArgumentType` — Argument of type "Overload[(key: str, default: None = None, /) -> (float \| None), (key: str, default: float, /) -> float, (key: str, default: _T@get, /) -> (float \| _T@get)]" cannot be assigned to parameter "key" of type "(_T@min) -> SupportsRichComparison" in function "min" No overloaded function matches type "(str) -> SupportsRichComparison"
- `388:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present ...
- `388:22` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" Type "object" is not assignable to type "ConvertibleToInt" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsInt" "__int__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/studies/perception/sensory_specialisation.py` (33)

- `28:16` · **error** · `reportReturnType` — Type "dict[str, Any \| bool]" is not assignable to return type "dict[str, object]" "dict[str, Any \| bool]" is not assignable to "dict[str, object]" Type parameter "_VT@dict" is invariant, but "Any \| bool" is not the same as "object" Consider switching from "dict" to "Mapping" which is covariant in the value type
- `90:33` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `90:33` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `156:43` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `156:43` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `157:46` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `157:46` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `226:37` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `226:37` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `227:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `227:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `228:37` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `228:37` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `229:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `229:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `313:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown
- `316:60` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `317:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `416:33` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `416:33` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `417:34` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `417:34` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `420:35` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `420:35` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `462:25` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "name" for class "object" Attribute "name" is unknown
- `465:56` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `466:71` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `467:71` · **error** · `reportAttributeAccessIssue` — Cannot access attribute "value" for class "object" Attribute "value" is unknown
- `484:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex" ...
- `484:36` · **error** · `reportArgumentType` — Argument of type "float \| None" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "float \| None" is not assignable to type "ConvertibleToFloat" Type "None" is not assignable to type "ConvertibleToFloat" "None" is not assignable to "str" "None" is incompatible with protocol "Buffer" "__buffer__" is not present "None" is incompatible with protocol "SupportsFloat" "__float__" is not present "None" is incompatible with protocol "SupportsIndex"
- `566:36` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `583:23` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present
- `584:27` · **error** · `reportArgumentType` — Argument of type "object" cannot be assigned to parameter "x" of type "ConvertibleToFloat" in function "__new__" Type "object" is not assignable to type "ConvertibleToFloat" "object" is not assignable to "str" "object" is incompatible with protocol "Buffer" "__buffer__" is not present "object" is incompatible with protocol "SupportsFloat" "__float__" is not present "object" is incompatible with protocol "SupportsIndex" "__index__" is not present

### `src/symbiont_lab/studies/runtime_prediction_longitudinal.py` (4)

- `29:34` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `81:35` · **error** · `reportOptionalMemberAccess` — "development" is not a known attribute of "None"
- `85:34` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `90:48` · **error** · `reportOptionalMemberAccess` — "graph" is not a known attribute of "None"

### `src/symbiont_lab/studies/runtime_prediction_promotion.py` (2)

- `111:33` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `112:32` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"

### `src/symbiont_lab/studies/social_runtime_context_replay.py` (2)

- `52:42` · **error** · `reportOptionalMemberAccess` — "target_id" is not a known attribute of "None"
- `52:92` · **error** · `reportOptionalMemberAccess` — "target_id" is not a known attribute of "None"

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

### `src/symbiont_lab/world/adapter.py` (9)

- `667:34` · **error** · `reportOptionalMemberAccess` — "_habitat" is not a known attribute of "None"
- `668:24` · **error** · `reportOptionalMemberAccess` — "_habitat" is not a known attribute of "None"
- `676:30` · **error** · `reportOptionalMemberAccess` — "tick_count" is not a known attribute of "None"
- `682:28` · **error** · `reportOptionalMemberAccess` — "_most_depleted_metabolic_kind" is not a known attribute of "None"
- `683:21` · **error** · `reportOptionalMemberAccess` — "request_resource_intake" is not a known attribute of "None"
- `751:29` · **error** · `reportOptionalMemberAccess` — "_physiology" is not a known attribute of "None"
- `769:34` · **error** · `reportOptionalMemberAccess` — "apply_environmental_damage" is not a known attribute of "None"
- `786:26` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `812:38` · **error** · `reportOptionalMemberAccess` — "apply_environmental_damage" is not a known attribute of "None"

### `src/symbiont_lab/world/population.py` (2)

- `802:44` · **error** · `reportOptionalMemberAccess` — "tick" is not a known attribute of "None"
- `806:80` · **error** · `reportOptionalMemberAccess` — "last_actuation" is not a known attribute of "None"

### `src/symbiont_lab/world/transaction.py` (3)

- `95:37` · **error** · `reportOptionalMemberAccess` — "history" is not a known attribute of "None"
- `99:31` · **error** · `reportAttributeAccessIssue` — Cannot assign to attribute "_snapshot_rigs" for class "IntegratedWorldTickTransaction*" Type "dict[str, tuple[Any, int \| None]]" is not assignable to type "dict[str, _OrganismRig] \| None" "dict[str, tuple[Any, int \| None]]" is not assignable to "dict[str, _OrganismRig]" Type parameter "_VT@dict" is invariant, but "tuple[Any, int \| None]" is not the same as "_OrganismRig" Consider switching from "dict" to "Mapping" which is covariant in the value type "dict[str, tuple[Any, int \| None]]" is not assignable to "None"
- `142:44` · **error** · `reportOptionalMemberAccess` — "history" is not a known attribute of "None"

## Criterio de resolución

Los errores se corrigen por contrato y causa raíz: primero límites entre paquetes/imports, después modelos explícitos de persistencia, telemetría, física y entradas dinámicas, y finalmente checks opcionales locales. Los warnings de imports entre `symbiont` y `symbiont_lab` no se silencian globalmente: requieren resolver el límite arquitectónico. No se aceptan `# pyright: ignore`, exclusiones amplias ni `cast` sin contrato documentado.

Los diagnósticos que representen una incompatibilidad histórica o una dependencia opcional deben quedar señalados cerca del límite con `# TODO(pyright)`/`# NOTE(pyright)` y registrados también en `docs/development/type-checking.md`.
