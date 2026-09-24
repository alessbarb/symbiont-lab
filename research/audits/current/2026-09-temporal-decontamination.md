# Audit Spec — Temporal Decontamination

Status: **required before repeating longitudinal re-embodiment studies**.

Fecha: 2026-09-24.

Esta auditoría clasifica todos los usos de tiempo del sistema para impedir que
vuelva a mezclarse:

- tiempo histórico del Symbiont;
- edad fisiológica del Body;
- edad/recencia de estructuras cognitivas.

---

## 1. Taxonomía obligatoria

Cada campo temporal debe pertenecer exactamente a una categoría.

### T-S — Symbiont historical time

Ejemplos:

- runtime tick;
- experience timestamps;
- episode chronology;
- model creation/validation;
- belief evidence recency;
- embodiment boundaries.

Puede sobrevivir a todos los bodies.

No produce senescencia.

### T-B — Body-local biological time

Ejemplos:

- body age;
- growth age;
- senescence onset;
- body death age;
- physical recovery time.

Se reinicia con fresh body.

### T-K — Knowledge/structure-local time

Ejemplos:

- edge age;
- sensor age;
- predictor support window;
- model staleness;
- memory recency;
- degradation-queue retention age.

Puede usar global ticks como coordenada, pero su semántica es local a la
estructura, no al organismo biológico.

### T-O — Observer/process time

Ejemplos:

- wall clock;
- run started_at;
- heartbeat time;
- file timestamps.

Nunca entra en cognición salvo transducción física explícita.

---

## 2. Archivos prioritarios a auditar

### Core

- `src/symbiont/core/orchestration/runtime.py`
- `src/symbiont/core/embodiment/physiology.py`
- `src/symbiont/core/embodiment/ontogeny.py`
- `src/symbiont/core/embodiment/development.py`
- `src/symbiont/core/embodiment/degradation.py`
- `src/symbiont/core/cognition/*`
- `src/symbiont/sensory/*`
- `src/symbiont/modeling/*`

### Physics3D / Lab

- `src/symbiont_lab/physics3d/runtime.py`
- `src/symbiont_lab/physics3d/reembodiment.py`
- `src/symbiont_lab/physics3d/engine.py`
- `src/symbiont_lab/app/physics3d_runs.py`
- observation/projection layers.

---

## 3. Patrones a buscar

Buscar nombres:

```text
tick
ticks
age
age_ticks
born_tick
death_tick
senescence
maturity
growth
development
declining
decay
aging
stale
recency
lifetime
timeout
last_seen
last_used
created_tick
```

Cada match debe documentar:

```text
field
owner
time_domain
reset_rule
checkpoint_rule
effect_on_behavior
effect_on_physiology
```

---

## 4. Hallazgo ya confirmado — P0

### TD-001 — Body age overwritten by Symbiont tick

Código conceptual actual:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.age_ticks = self._tick_count
```

Clasificación:

- `_tick_count`: T-S;
- `LivingBodyState.age_ticks`: T-B.

Resultado: contaminación T-S -> T-B.

Severidad: **P0**.

Impacto:

- senescencia prematura tras re-embodiment;
- comparaciones morfológicas inválidas;
- body death age incorrecta;
- fisiología dependiente del historial previo del Symbiont.

Fix requerido:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.advance_age()
```

---

## 5. Hallazgos a verificar

### TD-002 — `death_tick`

Determinar si todas las escrituras/lecturas asumen:

- body-local age;
- o global runtime tick.

Objetivo:

```text
LivingBodyState.death_tick = T-B
EmbodimentEpochSummary.ended_at_symbiont_tick = T-S
```

### TD-003 — `DevelopmentalTracker`

Verificar si `declining` o cualquier phase cambia por tick global.

Si describe cognición:

- no puede ser un proxy de vejez;
- debe depender de estado estructural/evidencia.

### TD-004 — DegradationQueue `aging_ticks`

Clasificar como T-K.

El nombre puede mantenerse si está inequívocamente documentado como edad de
retención de unidades, no edad del Symbiont.

Preferencia futura:

```text
retention_ticks
waste_delay_ticks
```

para reducir ambigüedad.

### TD-005 — Sensor `age_ticks`

Clasificar T-K.

Un sensor puede envejecer como estructura, pero eso no implica deterioro
biológico automático. Cualquier efecto de `age_ticks` debe ser funcional
(muestras/estabilidad/utility), no senescencia.

### TD-006 — Cognitive edge `age_ticks`

Clasificar T-K.

Debe influir solo en lifecycle de la edge, pruning/stability/support.

### TD-007 — model staleness

Debe depender de:

- tiempo desde validación;
- evidencia reciente;
- cambio de régimen;

no de edad global del individuo.

### TD-008 — plasticity

Buscar cualquier regla:

```text
global age -> less plasticity
```

Debe ser eliminada salvo justificación no biológica explícita.

### TD-009 — memory decay

Separar:

- recency-driven retention;
- age-driven biological decline.

Solo la primera es válida.

---

## 6. Regla de revisión

Para cada temporal field responder:

1. ¿Qué entidad envejece o acumula tiempo?
2. ¿Se reinicia al cambiar de body?
3. ¿Se conserva al suspender?
4. ¿Se conserva al re-embody?
5. ¿Puede afectar fisiología?
6. ¿Puede afectar cognición?
7. ¿Es observable por el Symbiont?
8. ¿Está serializado?
9. ¿Tiene migración?
10. ¿Tiene test de frontera?

Ningún campo temporal nuevo entra en main sin estas respuestas.

---

## 7. Invariantes automáticos

Añadir tests globales:

### A1

Fresh body con Symbiont antiguo:

```text
symbiont_tick >> 0
body_age_ticks == 0
senescence == 0
```

### A2

Dos cuerpos con igual edad y misma constitución tienen la misma senescencia
constitutiva independientemente de edad del Symbiont.

### A3

Re-embodiment no modifica timestamps cognitivos históricos.

### A4

Resume no reinicia body age.

### A5

Cambio de process/run no cambia ningún reloj biológico si no avanzan ticks del
body.

### A6

Dormancy fuera de ejecución no envejece el body salvo que exista explícitamente
una simulación física de tiempo durante dormancy.

---

## 8. Política de tiempo offline

Por defecto:

> **No pasa tiempo biológico mientras el runtime no ejecuta ticks.**

Cerrar la aplicación durante 24 horas reales no envejece el body.

Si en el futuro se desea tiempo físico offline deberá ser una feature explícita
del world/runtime, con fuente temporal reproducible. Nunca derivar del reloj de
pared del checkpoint.

---

## 9. Gate

La auditoría termina solo cuando:

- todos los matches están clasificados T-S/T-B/T-K/T-O;
- TD-001 está corregido;
- no existe flujo T-S -> senescence/growth/death;
- tests A1-A6 pasan;
- documentación canónica usa la misma terminología;
- los estudios longitudinales anteriores quedan marcados como contaminated para
  comparación de longevidad.
