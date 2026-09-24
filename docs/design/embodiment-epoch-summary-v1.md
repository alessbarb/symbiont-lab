# Spec — Embodiment Epoch Summary v1

Status: **proposed observer/persistence contract**.

Fecha: 2026-09-24.

Objetivo:

> **Poder reconstruir la historia corporal completa de un Symbiont desde un
> checkpoint sin depender de conservar toda la telemetría raw externa.**

El experimento longitudinal reveló que `embodiment_history` conserva identidad
del body, ticks y parte del conocimiento archivado, pero no un resumen
fisiológico/cognitivo suficiente para comparar epochs de forma fiable.

---

## 1. Nueva entidad

```text
EmbodimentEpochSummary
```

Pertenece a persistencia/observer. No es una señal para cognición.

Cada epoch cerrado genera exactamente un resumen inmutable.

Campos mínimos:

```text
epoch
contract_fingerprint
body_kind_observer_only

started_at_symbiont_tick
ended_at_symbiont_tick
duration_body_ticks

end_reason
body_vital_state
body_death_age_ticks

final_energy_ratio
final_structural_integrity
final_senescence
final_fatigue

absorbed_material_total
mechanical_work_total
physiological_cost_total

body_schema_state
body_schema_part_count
motor_primitive_count
motor_candidate_count
motor_supported_count
motor_readout_count
predictor_count

private_model_state_counts
active_private_model_id

reacclimation_ticks_consumed
reacclimation_completed
```

---

## 2. End reason

Valores cerrados:

- `dead_energy`;
- `dead_structure`;
- `dead_unrecoverable_pressure`;
- `stopped_alive`;
- `suspended`;
- `reembodied_alive`;
- `startup_failed`;
- `unknown`.

No inferir causas ambiguas.

Si varias condiciones terminales son simultáneas, registrar:

```text
end_reason = unknown
terminal_facts = [...]
```

observer-side.

---

## 3. Dos coordenadas temporales

Cada summary debe guardar ambas:

```text
started_at_symbiont_tick
ended_at_symbiont_tick
duration_body_ticks
```

Nunca derivar edad corporal futura desde tick global salvo migración explícita.

Invariante:

```text
duration_body_ticks == final_body_age_ticks
```

para un body que empezó fresco.

Para resume del mismo body:

```text
duration_body_ticks
```

incluye toda su vida física acumulada, no solo el último proceso.

---

## 4. Acumuladores por epoch

No almacenar raw telemetry completa.

Mantener acumuladores bounded durante el run:

- energía absorbida;
- coste fisiológico;
- mechanical work;
- número de eventos de reparación;
- número de cambios de vital state;
- tiempo en stress/dormant/agonizing;
- ticks de reaclimatación;
- primitives creadas/revalidadas;
- model promotions/degradations.

Estos acumuladores se cierran al terminar el epoch.

---

## 5. Inmutabilidad

Una vez cerrado:

```text
EmbodimentEpochSummary(epoch=N)
```

no cambia.

Si se descubre un error de migración:

- no reescribir silenciosamente;
- añadir `summary_revision`;
- registrar `derived_from_checkpoint_schema`;
- permitir regeneración determinista en tooling, no en runtime cognitivo.

---

## 6. Bounded history

El checkpoint puede mantener:

- últimos N summaries completos;
- agregados históricos de epochs más antiguos.

No descartar:

- primer epoch;
- último epoch de cada contract conocido;
- epochs con contract transitions;
- epochs seleccionados como scientific milestones.

Política exacta debe fijarse por budget, no por valor semántico humano.

---

## 7. Uso científico

Permite comparar:

### Misma morfología

```text
H1 vs H2 vs H3
```

### Morfologías distintas

```text
H vs Crawler vs Asymmetric
```

### Retorno

```text
H1/H2/H3 vs H6
```

### Re-embodiment vivo vs post-mortem

```text
end_reason = reembodied_alive
vs
end_reason = dead_*
```

---

## 8. Tests

### E1 — cierre por muerte

Summary contiene:

- duración local;
- vital state dead;
- causa compatible con hechos;
- final body age.

### E2 — cierre vivo

Cambiar de body sin muerte genera:

```text
end_reason = reembodied_alive
```

sin fabricar death tick.

### E3 — resume

Parar y continuar el mismo body no crea un epoch nuevo.

### E4 — boundedness

Miles de ticks no aumentan sin límite el tamaño del summary.

### E5 — no leakage

El summary puede contener body_kind porque es observer-side, pero no entra en:

- sensory system;
- cognitive graph;
- model inputs;
- action selector.

---

## 9. Criterio de aceptación

Desde un único `.symbiont` debe poder responderse de forma determinista:

- cuántos cuerpos habitó;
- cuánto vivió cada body;
- cómo terminó;
- qué contract tenía;
- cuánto aprendió corporalmente;
- qué estado fisiológico tenía al finalizar;
- qué modelo privado gobernaba;
- cuánto tardó en reaclimatarse;

sin necesitar un ZIP de telemetría separado.
