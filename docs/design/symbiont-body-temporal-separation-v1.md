# Spec — Separación temporal Symbiont / Body v1

Status: **proposed canonical architecture**.

Fecha: 2026-09-24.

Esta especificación nace del primer experimento longitudinal completo de
re-embodiment:

```text
H -> H -> H -> Crawler -> Asymmetric -> H
```

El experimento demostró que la identidad, la memoria y la cognición del
Symbiont pueden persistir a través de múltiples cuerpos, pero también reveló
una contaminación temporal heredada del modelo antiguo `organism == body`.

La conclusión canónica es:

> **El Symbiont no envejece biológicamente. El Body sí.**

> **El Symbiont acumula historia; el Body acumula edad fisiológica.**

---

## 1. Problema encontrado

El runtime mantiene un contador histórico global `_tick_count`, que representa
la continuidad temporal de la identidad del Symbiont. Después de cada tick el
código actual hace:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.age_ticks = self._tick_count
```

Esto era coherente cuando un Symbiont nacía con un único body y ambos
compartían toda su vida.

Ya no lo es tras introducir re-embodiment.

En el experimento longitudinal, el epoch 6 comenzó en el tick global 19948 y
terminó en 23315. Su body vivió aproximadamente 3367 ticks, pero
`LivingBodyState.age_ticks` terminó alrededor de 23314. Como la senescencia
canónica comienza a `senescence_start_ticks = 2048`, ese body fue tratado
como fisiológicamente viejo casi desde el comienzo.

Esto contamina:

- senescencia;
- desgaste por senescencia;
- edad de muerte;
- cualquier futura capacidad física dependiente de edad;
- comparaciones de supervivencia entre morfologías.

Por tanto, los resultados observados de duración de crawler, asymmetric y el
humanoide de retorno **no son todavía evidencia limpia de diferencias
morfológicas**.

---

## 2. Tres relojes canónicos

El sistema debe distinguir tres clases de tiempo.

### 2.1 `symbiont_tick` — historia de identidad

Equivale conceptualmente al actual `OrganismRuntime._tick_count`.

Propiedades:

- monotónico durante toda la continuidad del Symbiont;
- no se reinicia entre bodies;
- no produce senescencia;
- no determina crecimiento físico;
- no determina muerte biológica;
- sirve para ordenar memoria, experiencia y causalidad.

Ejemplo:

```text
Symbiont #17
symbiont_tick:
0 -> 4513 -> 8922 -> 13323 -> 16775 -> 19948 -> 23315
```

Usos legítimos:

- timestamps de experiencias;
- orden de episodios;
- creación/validación de modelos;
- support/recency de creencias;
- historia de embodiments;
- estructura cognitiva;
- causalidad temporal;
- reproducibilidad.

### 2.2 `body_age_ticks` — edad fisiológica local

Es propiedad del body actual.

Propiedades:

- empieza en cero en un body nuevo;
- aumenta exactamente un tick mientras ese body está vivo;
- persiste en `resume` del mismo body;
- nunca se copia a un body fresco;
- controla ontogenia y senescencia físicas.

Ejemplo:

```text
symbiont_tick = 19948
new body
body_age_ticks = 0

...

symbiont_tick = 23315
body_age_ticks = 3367
```

### 2.3 Edad/recencia de estructuras cognitivas

Conceptos, sensores, edges, modelos, episodios o hipótesis pueden mantener
contadores de edad o recencia propios.

Ejemplos:

- `edge.age_ticks`;
- `sensor.age_ticks`;
- `last_seen_tick`;
- `created_tick`;
- `last_validated_tick`;
- clases de recencia de memoria.

Estos contadores describen historia epistemológica o vida de una estructura.
No representan edad biológica del Symbiont.

---

## 3. Propiedad de estado

### 3.1 Estado exclusivo del Body

Los siguientes campos pertenecen al body/embodiment físico:

- `energy_reserve`;
- `max_energy`;
- `structural_integrity`;
- `temperature`;
- `fatigue`;
- `growth_progress`;
- `senescence`;
- `body_age_ticks`;
- `vital_state`;
- daño/repair por estructura;
- estado fisiológico;
- muerte física.

La muerte es irreversible **para ese body**.

### 3.2 Estado exclusivo del Symbiont

El Symbiont persistente posee:

- `organism_id`;
- `symbiont_tick`;
- memoria;
- experiencia;
- episodios;
- cognición;
- modelos privados;
- beliefs;
- conocimiento causal;
- historia de embodiments;
- linaje de identidad.

No posee:

- juventud;
- madurez biológica;
- senescencia;
- edad corporal;
- muerte corporal.

### 3.3 Estado de Embodiment

El vínculo entre un Symbiont y un Body posee:

- `embodiment_epoch`;
- `body_kind`;
- opaque sensorimotor contract;
- `started_at_symbiont_tick`;
- `ended_at_symbiont_tick`;
- `body_age_ticks`;
- estado de reaclimatación;
- body schema activo;
- conocimiento sensorimotor específico.

---

## 4. Lifecycle canónico

### 4.1 Symbiont

```text
created
  -> active/embodied
  -> dormant
  -> active/embodied
  -> dormant
  -> ...
```

Estados válidos de ejecución:

- `active`: ejecutándose en un body;
- `dormant`: identidad persistida sin ejecución activa;
- `suspended`: ejecución temporalmente congelada con intención de continuar.

El Symbiont no pasa por:

```text
young -> mature -> senescent -> dead
```

como consecuencia del tiempo.

### 4.2 Body

```text
birth
 -> growth
 -> maturity
 -> senescence
 -> death
```

Este lifecycle se reinicia con cada body fresco.

### 4.3 Re-embodiment

Un body muerto no puede hacer `resume`.

```text
Body A DEAD
Symbiont DORMANT
      |
      v
fresh Body B age=0
Symbiont ACTIVE
embodiment_epoch += 1
```

---

## 5. Cambios requeridos en código

### 5.1 `LivingBodyState`

Renombrado conceptual:

```text
age_ticks -> body_age_ticks
death_tick -> body_death_age_ticks
```

Una migración física de nombres puede hacerse en una versión posterior; v1
puede conservar claves serializadas por compatibilidad, pero la semántica debe
quedar definida como **local al body**.

Regla de incremento:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.advance_age()
```

Prohibido:

```python
body.age_ticks = symbiont_tick
```

### 5.2 `PhysiologyController`

Las transiciones deben recibir tanto contexto global como local solo cuando sea
necesario.

La muerte física se registra como:

```text
body_death_age_ticks
```

El tick global de la muerte pertenece al resumen del epoch:

```text
ended_at_symbiont_tick
```

No deben confluir en un único campo.

### 5.3 `OntogenyController`

Debe consultar exclusivamente:

- `body_age_ticks`;
- growth;
- energía;
- integridad;
- senescencia;
- estado vital.

Nunca:

- `symbiont_tick`;
- edad de identidad;
- número de embodiments;
- cantidad de memoria;
- experiencia cognitiva.

### 5.4 `DevelopmentalTracker`

Debe permanecer descriptivo y cognitivo, nunca biológico.

Estados tipo:

```text
developing
consolidating
stable
reorganizing
```

son aceptables si derivan de evidencia cognitiva.

Estados tipo:

```text
young
adult
old
senescent
declining because age
```

no son aceptables como propiedades del Symbiont.

El nombre `declining` debe auditarse: si deriva de carga, estrés o salud
estructural puede mantenerse como telemetría descriptiva; si deriva de
antigüedad global debe eliminarse o renombrarse.

---

## 6. Senescencia

La senescencia pertenece exclusivamente al Body.

Regla:

```text
if body_age_ticks >= senescence_start_ticks:
    apply body senescence
```

Nunca:

```text
if symbiont_tick >= senescence_start_ticks:
    apply senescence
```

La senescencia puede afectar:

- reparación física;
- desgaste;
- capacidad motora;
- metabolismo;
- reproducción del body.

No puede afectar directamente:

- capacidad cognitiva;
- memoria;
- plasticidad;
- número de conceptos;
- SLM;
- predictor budget.

Cualquier futura disminución de plasticidad debe justificarse por:

- estabilidad;
- incertidumbre;
- resource pressure;
- saturación estructural;
- falta de utilidad;
- evidencia contradictoria;

no por "edad del Symbiont".

---

## 7. Memoria, olvido y paso del tiempo

El hecho de que el Symbiont no envejezca no implica memoria infinita.

El olvido puede derivar de:

- capacidad acotada;
- falta de uso;
- interferencia;
- evidencia contradictoria;
- baja utilidad;
- consolidación fallida;
- presión computacional.

El tiempo puede participar en recencia, pero no como mecanismo de vejez.

Ejemplo legítimo:

```text
last_used_tick << current_tick
AND low_support
AND low_utility
=> candidate for retirement
```

Ejemplo prohibido:

```text
symbiont_tick > 50000
=> cognitive decay
```

---

## 8. Migración de checkpoints

### 8.1 Checkpoints con `embodiment_lifecycle`

Para el body actual:

```text
expected_body_age =
    saved_at_tick - embodiment_lifecycle.current.started_tick
```

Si el checkpoint fue producido por la implementación contaminada y:

```text
living_body.age_ticks ~= saved_at_tick
AND current.started_tick > 0
```

se debe migrar a:

```text
living_body.age_ticks = expected_body_age
```

No se debe migrar silenciosamente un checkpoint ambiguo.

La migración debe:

1. detectar inequívocamente el patrón antiguo;
2. registrar versión de migración;
3. fail-closed si los campos se contradicen;
4. no modificar memoria/cognición.

### 8.2 Legacy sin embodiment lifecycle

Para epoch 1 histórico:

- conservar `living_body.age_ticks`;
- comprobar que no exceda `saved_at_tick`;
- crear lifecycle inicial con `started_tick = 0`.

No inferir epochs inexistentes.

---

## 9. Telemetría requerida

Cada tick Physics3D debe poder proyectar de forma pasiva:

```text
symbiont_tick
embodiment_epoch
body_age_ticks
body_vital_state
body_senescence
reacclimation_remaining
```

Observer-only.

El organismo sigue recibiendo únicamente sus señales opacas.

---

## 10. Tests obligatorios

### T1 — body fresco

```text
Symbiont tick 10_000
fresh body
=> body_age_ticks = 0
```

### T2 — avance independiente

Tras 100 ticks:

```text
symbiont_tick = 10_100
body_age_ticks = 100
```

### T3 — resume

Parar/reanudar el mismo body conserva:

```text
body_age_ticks
senescence
growth
integrity
```

### T4 — re-embodiment

Cambiar a fresh body:

```text
body_age_ticks = 0
senescence = 0
growth = canonical fresh state
```

sin modificar:

```text
organism_id
symbiont_tick
memory
experience
cognition
```

### T5 — senescencia

Dos Symbionts con distinto `symbiont_tick` pero bodies de igual edad deben
tener la misma dinámica constitutiva de senescencia, todo lo demás igual.

### T6 — muerte

`body_death_age_ticks` debe estar en coordenadas locales del body.

El epoch debe conservar por separado:

```text
ended_at_symbiont_tick
```

### T7 — checkpoint migration

Un checkpoint contaminado conocido debe migrar de forma determinista y un
checkpoint ambiguo debe fallar cerrado.

---

## 11. Criterio de aceptación

Esta spec queda cerrada cuando:

1. ningún body obtiene su edad a partir del tick global;
2. senescencia depende exclusivamente de edad corporal;
3. un Symbiont viejo puede recibir un body fisiológicamente joven;
4. re-embodiment no rejuvenece ni envejece al Symbiont porque el Symbiont no
   posee edad biológica;
5. memoria/cognición conservan tiempo histórico global;
6. telemetría distingue los dos relojes;
7. los tests impiden volver a fusionarlos.

---

## 12. Consecuencia científica

Los experimentos anteriores H->H->H->C->A->H son útiles como descubrimiento de
arquitectura, pero no como comparación limpia de longevidad entre cuerpos.

Después de implementar esta separación debe repetirse el mismo protocolo antes
de afirmar diferencias de supervivencia o senescencia por morfología.
