# Implementation Plan — Longitudinal Re-embodiment v1

Status: **implementation-ready**.

Este documento traduce las specs longitudinales a cambios concretos de código.

---

## P0 — Separación temporal

### 1. `src/symbiont/core/embodiment/physiology.py`

Objetivo:

- mantener `LivingBodyState` como owner de fisiología;
- cambiar la semántica de `age_ticks` a body-local;
- mantener `advance_age()` como única operación de incremento;
- documentar `death_tick` como body-local.

No cambiar todavía claves serializadas si no es necesario.

Añadir:

- invariantes de edad local;
- documentación explícita;
- validación de `death_tick <= age_ticks` cuando aplique.

Futuro schema:

```text
body_age_ticks
body_death_age_ticks
```

pero la migración de nombres puede separarse de la corrección semántica.

### 2. `src/symbiont/core/orchestration/runtime.py`

Eliminar:

```python
self._living_body_state.age_ticks = self._tick_count
```

Sustituir por:

```python
self._living_body_state.advance_age()
```

Mantener `self._tick_count` como historial global.

Auditar llamadas a:

- `PhysiologyController.advance(... tick=...)`;
- `mark_dead(tick)`;
- creación de hijos;
- restore.

Separar argumentos si una API necesita:

```text
symbiont_tick
body_age_tick
```

No pasar el global cuando la semántica esperada sea body-local.

### 3. `src/symbiont/core/embodiment/ontogeny.py`

No requiere nuevo state owner.

Verificar que:

```python
body.age_ticks >= senescence_start_ticks
```

ahora significa exclusivamente body-local.

Añadir test de independencia de `symbiont_tick`.

### 4. `src/symbiont_lab/physics3d/reembodiment.py`

Fresh body:

- age 0;
- senescence 0;
- growth state canónico fresh;
- death tick null;
- fresh physiology completa.

No copiar ningún temporal physiological field desde previous.

Añadir helper de migración:

```text
repair_contaminated_body_age(payload)
```

solo para checkpoint claramente identificable.

### 5. `src/symbiont_lab/physics3d/runtime.py`

Exponer por telemetría:

- `symbiont_tick`;
- `body_age_ticks`;
- `embodiment_epoch`;
- senescence corporal;
- reacclimation.

No enviar estos nombres como señales cognitivas.

### 6. `src/symbiont_lab/observation/projection.py`

Proyección observer-only separada:

```json
{
  "symbiont_tick": 25000,
  "embodiment_epoch": 7,
  "body_age_ticks": 812
}
```

---

## P0 — Migración de checkpoint

### Detector

Para checkpoint con lifecycle:

```text
started = current.started_tick
saved = saved_at_tick
expected_local = saved - started
stored = living_body.age_ticks
```

Contaminación fuerte si:

```text
started > 0
stored approx saved
stored != expected_local
```

La migración:

- corrige `age_ticks`;
- corrige `death_tick` si representa el mismo reloj contaminado;
- no toca energía/integridad/senescencia retrospectivamente;
- marca metadata de migración.

Importante:

> No intentar “desenvejecer” retrospectivamente integridad o energía de un body
> que ya vivió bajo senescencia contaminada.

Esos runs siguen científicamente contaminados.

La migración solo permite continuar el checkpoint con semántica correcta en un
nuevo body.

---

## P1 — EmbodimentEpochSummary

### 7. `src/symbiont_lab/physics3d/reembodiment.py`

Añadir dataclass/model:

```text
EmbodimentEpochSummary
```

Cerrar summary antes de incrementar epoch.

### 8. `src/symbiont_lab/physics3d/runtime.py`

Mantener acumuladores bounded por epoch:

- absorbed material;
- mechanical work;
- cost;
- repair;
- time in vital states;
- motor learning counters.

### 9. `src/symbiont_lab/physics3d/engine.py`

En checkpoint final:

- cerrar epoch si body muere o se re-embody;
- no cerrar epoch en stop/resume del mismo body.

### 10. `src/symbiont_lab/app/physics3d_runs.py`

Mostrar summary relevante en catálogo:

- current epoch;
- previous end reason;
- body age;
- lifetime;
- last contract.

---

## P1 — EmbodimentMemory

### 11. Nuevo módulo sugerido

```text
src/symbiont/core/embodiment/memory.py
```

o, si se mantiene Physics3D-specific inicialmente:

```text
src/symbiont_lab/physics3d/embodiment_memory.py
```

Preferencia arquitectónica: core solo si el concepto deja de depender de
Physics3D.

Tipos:

```text
EmbodimentContractFingerprint
EmbodimentMemory
HistoricalMotorSurface
HistoricalPrimitive
RevalidationState
```

### 12. `src/symbiont_lab/physics3d/reembodiment.py`

Al salir de contract:

- consolidate current body-specific state;
- archive;
- remove active authority.

Al entrar:

```text
different fingerprint -> fresh
same historical fingerprint -> candidate revalidation
```

### 13. `src/symbiont/core/orchestration/runtime.py`

No necesita saber body_kind.

Debe aceptar un conjunto bounded de hipótesis históricas opacas y someterlas a
las mismas reglas de evidence/support que conocimiento nuevo.

### 14. `src/symbiont/modeling/*`

Private model histórico:

- preserve artifact;
- ACTIVE -> DEGRADED al cambiar contract;
- candidate on known-contract return;
- reactivation requires validation.

---

## P1 — BodySchema naming

### 15. `src/symbiont/core/embodiment/body_schema.py`

Revisar:

```text
undeveloped
partial
```

Propuesta:

```text
undeveloped
developing
established
revising
```

Gates por:

- support;
- stable dependencies;
- observation count;
- confidence/consistency;

no por anatomical completeness.

---

## Auditoría temporal

### 16. `src/symbiont/core/embodiment/development.py`

Clasificar cada contador.

`declining` no puede significar “Symbiont viejo”.

### 17. `src/symbiont/core/embodiment/degradation.py`

Documentar sus `aging_ticks` como T-K (retention lifecycle).

Considerar rename posterior para reducir ambigüedad.

### 18. `src/symbiont/sensory/*`

`sensor.age_ticks` = edad de estructura sensorial, T-K.

No conectar a senescencia del Symbiont.

### 19. `src/symbiont/cognition/*`

`edge.age_ticks`, support, recency = T-K.

Buscar cualquier global-age driven decay.

### 20. `src/symbiont/modeling/*`

Model staleness debe ser evidence/validation-driven.

---

## Tests nuevos

### Core

Crear/actualizar:

```text
tests/unit/core/test_temporal_domains.py
tests/unit/core/test_ontogeny.py
tests/unit/core/test_physiology.py
```

Casos:

- old Symbiont + fresh body;
- same body resume;
- fresh re-embodiment;
- senescence independence;
- death local tick.

### Physics3D

```text
tests/unit/lab/physics3d/test_reembodiment.py
tests/integration/test_physics3d_existing_reuse.py
tests/integration/test_physics3d_temporal_domains.py
```

### Memory

```text
tests/unit/lab/physics3d/test_embodiment_memory.py
tests/integration/test_known_contract_return.py
```

### Summary

```text
tests/unit/lab/physics3d/test_epoch_summary.py
```

---

## Orden de PRs recomendado

### PR-T1 — temporal domain fix

Solo:

- body age;
- death tick semantics;
- migration;
- tests.

No mezclar EmbodimentMemory.

### PR-T2 — epoch summaries

Observer/persistence only.

### PR-T3 — EmbodimentMemory archival

Archivar correctamente, sin reactivar todavía.

### PR-T4 — known-contract revalidation

Candidate -> supported/contradicted.

### PR-T5 — BodySchema states

Naming/telemetry después de cerrar mecanismos.

### PR-T6 — longitudinal study v2

Repetición preregistrada.

---

## No mezclar en estos PRs

- metabolismo tuning;
- energy capacity changes;
- new rewards;
- locomotion targets;
- model-size increases;
- cognitive budget increases;
- hand-written cross-body mappings.

---

## Definition of done

El paquete longitudinal v1 está implementado cuando:

1. los tres dominios temporales están separados;
2. fresh body siempre nace con edad fisiológica local 0;
3. senescencia no ve `symbiont_tick`;
4. epoch history es científicamente reconstruible;
5. body knowledge histórico no se pierde ni se restaura ciegamente;
6. known-contract return se revalida por evidencia;
7. el estudio H->H->H->C->A->H puede repetirse sin contaminación conocida.
