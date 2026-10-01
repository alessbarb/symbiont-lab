# Agency Acquisition & Executive Action v1

**Estado:** especificación propuesta para implementación  
**Baseline de diseño:** `main@ba84be7f6cf959bc2e9b5b2dec95f86d9bdf0217`  
**Repositorio:** `alessbarb/symbiont-lab`  
**Ámbito:** `symbiont` core + integración necesaria en `symbiont_lab`, estudios y Observatory  
**Naturaleza:** evolución transversal de Sensorimotor v2. **No es Sensorimotor v3 y no reemplaza Sensorimotor v2.**  
**Compatibilidad conceptual:** Embodiment v2, Genome v2, Sensorimotor v2, Generative Cognition v1, Prospective Agency, Body Schema y arquitectura actual de ActionDomain.

---

# 1. Propósito

Esta especificación cierra el ciclo completo mediante el cual un Symbiont:

```text
1. actúa sin saber todavía qué puede hacer;
2. descubre regularidades entre sus intervenciones y sus consecuencias;
3. distingue qué cambios puede causar de forma reproducible;
4. construye dimensiones de acción y competencias a partir de esa experiencia;
5. reconoce cuándo esas competencias son utilizables en una situación concreta;
6. convierte una posibilidad cognitiva en una intención persistente;
7. obtiene autoridad motora mediante el ActionArbitrator;
8. ejecuta la competencia mediante controladores;
9. observa el resultado real;
10. reconcilia el resultado con lo que estaba intentando;
11. actualiza aprendizaje causal, agencia, competencia y cognición.
```

La tesis central es:

> **Symbiont no necesita otro sistema motor. Necesita cerrar la continuidad entre descubrimiento causal, adquisición de agencia, competencia, affordance, intención ejecutiva, ejecución física y feedback.**

La spec anterior ya separaba correctamente adquisición bottom-up, intención top-down y feedback. La revisión posterior introduce un ajuste esencial: entre `ActionAttempt` y `ActionDimension` debe existir una representación provisional capaz de agrupar intervenciones similares antes de que haya una dimensión o competencia aprendida: `InterventionSignature`. :chatgpt-content-reference{index="0"}

---

# 2. Problema actual

El `main` actual contiene casi todas las piezas necesarias:

```text
ActuatorSurface
ActuatorEvidenceModel
CompetenceDevelopmentEngine

EffectSpace
CausalEvidenceLedger
CompetenceEffectModel
ControllabilityModel
AgencyModel

ActionDimensionRegistry
BodySchemaEngine

MotorCompetence
CompetenceExecutionBindingRegistry
CompositionEngine

CognitiveBridge
Generative Cognition
ProspectiveAgency

ActionProposal
ActionArbitrator
ActionCommitment
Controller
MotorCommand
```

El problema no es ausencia de componentes, sino discontinuidad entre ellos.

Existen tres gaps principales.

---

# 3. Gap A — Agency Acquisition Bridge

## 3.1 Estado actual

Durante exploración, `ActionDomain` puede crear propuestas como:

```python
ActionProposal(
    source=ActionSource.EXPLORATION,
    effect_target_id=None,
    competence_id=None,
    ...
)
```

Esto es correcto: un organismo cognitivamente inmaduro debe poder explorar antes de poseer competencias.

Sin embargo, varios componentes de aprendizaje causal están organizados alrededor de:

```text
competence_id
+
effect_id
+
context
```

Por tanto aparece una dependencia circular:

```text
para aprender controllability/agency
    necesito una competence

pero

para formar una competence sólida
    debería haber aprendido primero controllability/agency
```

Éste es un gap arquitectónico real en el `main` actual. :chatgpt-content-reference{index="1"}

---

# 4. Gap B — Cognitive Executive Bridge

El sistema puede llegar a representar:

```text
"competence C existe"
"competence C suele producir effect E"
"competence C es executable"
"si ejecuto C, quizá ocurra E"
```

pero todavía no posee una entidad cognitiva canónica equivalente a:

```text
"voy a intentar producir E mediante C ahora"
```

Actualmente parte de la cognición puede desembocar directamente en:

```text
competence/readout
→ ActionProposal
```

La activación de una representación se aproxima demasiado a una orden ejecutiva.

Necesitamos separar explícitamente:

```text
KNOW
"I can do C"

CONSIDER
"C is relevant/possible"

INTEND
"I will attempt C now"

ACT
"C is being physically executed"
```

La distinción entre `KNOW`, `CONSIDER`, `INTEND` y `ACT` es uno de los fundamentos de esta spec. :chatgpt-content-reference{index="2"}

---

# 5. Gap C — Intentional Closed Loop

`main` ya posee piezas como:

```text
EffectPrediction
PredictionError
CompetenceEffectModel
ControllabilityModel
AgencyModel
```

y puede comparar:

```text
predicted_effect_id
vs
observed_effect_id
```

Pero el resultado de esa comparación todavía no gobierna un lifecycle ejecutivo persistente.

Necesitamos:

```text
ActionIntent
    ↓
anticipated Effect
    ↓
ActionCommitment
    ↓
Controller
    ↓
Body
    ↓
ObservedEffect
    ↓
progress / completion / mismatch
    ↓
continue / finish / reconsider / fail
```

---

# 6. Principio arquitectónico completo

La arquitectura queda dividida en tres bucles.

## 6.1 Acquisition loop

```text
ACTUATOR SURFACE
       ↓
physical motor opportunities
       ↓
ActionAttempt
       ↓
InterventionSignature
       ↓
MotorCommand / Actuation
       ↓
BODY
       ↓
observed changes
       ↓
Effect
       ↓
CausalEvidence
       ↓
contingency / counterfactual comparison
       ↓
Controllability
       ↓
Agency
       ↓
ActionDimension
       ↓
CompetenceCandidate
       ↓
MotorCompetence
```

Pregunta que responde:

> **¿Qué puedo causar?**

---

## 6.2 Executive loop

```text
INTERNAL STATE
       ↓
Cognition
       ↓
current affordances / anticipated effects
       ↓
Generative Cognition / ProspectiveAgency
       ↓
ActionIntent
       ↓
ActionProposal
       ↓
ActionArbitrator
       ↓
ActionCommitment
       ↓
MotorCompetence
       ↓
Controller
       ↓
MotorCommand
       ↓
BODY
```

Pregunta que responde:

> **De todo lo que puedo hacer, ¿qué voy a intentar ahora?**

---

## 6.3 Intentional feedback loop

```text
ActionIntent
       │
       ├── anticipated effect
       │
       ▼
ActionCommitment
       ↓
Controller
       ↓
BODY
       ↓
ObservedEffect
       ↓
EffectMatcher / PredictionError
       │
       ├── progress ───────→ continue
       ├── completion ─────→ satisfy
       ├── mismatch ───────→ revise / continue / fail
       ├── no progress ────→ fail / abandon policy
       └── invalidity ─────→ invalidate
```

Pregunta que responde:

> **¿Está ocurriendo lo que estaba intentando?**

Esta estructura de tres bucles es la arquitectura canónica de la spec. :chatgpt-content-reference{index="3"}

---

# 7. Invariantes constitucionales

## 7.1 Cognition nunca emite `MotorCommand`

Prohibido:

```text
Cognition → actuator
CognitiveGraph → MotorCommand
Generative Cognition → ControllerFrame
ActionIntent → physical channel values
```

Permitido:

```text
Cognition
→ anticipated effect
→ ActionIntent
→ competence reference
```

---

## 7.2 `ActionIntent` no es un controlador

`ActionIntent` responde a:

```text
WHAT
```

El controller responde a:

```text
HOW
```

Nunca se mezclarán.

---

## 7.3 Exploración no necesita competencia

Debe ser válido:

```text
competence_id = None
```

en una acción exploratoria.

---

## 7.4 Evidencia causal no necesita competencia

Debe poder existir antes de `MotorCompetence`:

```text
ActionAttempt
InterventionSignature
Effect
CausalEvidence
ControllabilityEvidence
AgencyEvidence
```

---

## 7.5 `ActionDimension` no equivale a `ActuatorChannel`

Prohibido conceptualmente:

```text
one actuator
=
one ActionDimension
```

Una dimensión aprendida puede corresponder a:

```text
un canal
varios canales
una combinación
una sinergia
un patrón temporal
una recurrencia motora
un controller seed
```

Este cambio es obligatorio. :chatgpt-content-reference{index="4"}

---

## 7.6 `ActionIntent` no gobierna toda acción

No necesitan intención cognitiva obligatoria:

```text
exploration
innate protection
reactive responses
emergency homeostatic actions
```

Un Symbiont recién encarnado debe poder actuar antes de formar intenciones complejas. :chatgpt-content-reference{index="5"}

---

## 7.7 Prediction match no equivale a agency

```text
prediction matched
≠
I caused it
```

`AgencyModel` debe seguir dependiendo de:

```text
temporal contingency
causal specificity
counterfactual contrast
prediction match
support
```

---

## 7.8 No semántica corporal hardcoded

No introducir:

```text
walk
step
balance
left_leg
right_leg
hip
knee
forward
stand
```

como conocimiento cognitivo innato para resolver esta spec.

---

## 7.9 No reward global

No introducir un:

```python
reward: float
global_utility: float
goal_score: float
```

que colapse toda conducta en un optimizador escalar.

---

## 7.10 Imaginación nunca es evidencia factual

Prohibido:

```text
Generative Cognition result
→ CausalEvidenceLedger
```

Sólo experiencia física real puede actualizar evidencia causal.

---

# 8. Entidades nuevas

Sólo se añaden como entidades canónicas nuevas:

```text
ActionAttempt
ActionIntent
```

Se añade como identidad causal provisional interna:

```text
InterventionSignature
```

Se añade como proyección derivada:

```text
ActionAffordance
```

No se introduce:

```text
ExecutiveChoice
ActionConsideration
MotorOpportunity entity
```

en v1.

---

# 9. `ActionAttempt`

## 9.1 Propósito

Representa:

> **esta intervención física concreta ocurrió.**

No representa una skill.

No afirma que el organismo sepa qué produjo.

No requiere `competence_id`.

---

## 9.2 Archivo

```text
src/symbiont/actuation/attempt.py
```

---

## 9.3 Modelo

```python
@dataclass(frozen=True, slots=True)
class ActionAttempt:
    attempt_id: str

    commitment_id: str
    controller_id: str

    competence_id: str | None

    intervention_signature_id: str

    context_ref: str
    embodiment_id: str | None
    surface_fingerprint: str

    motor_command_ref: str
    actuation_ref: str

    started_tick: int
    completed_tick: int | None
```

No es necesario almacenar en la entidad campos semánticos de actuadores.

Si se necesitan para trazabilidad de ejecución pueden resolverse desde el command/actuation referenciado.

---

# 10. Granularidad de `ActionAttempt`

Un `ActionAttempt` es el **átomo causal de ejecución**.

En v1:

```text
1 issued MotorCommand
→ 1 ActionAttempt
```

Esto simplifica trazabilidad.

Pero **no es la única escala causal**.

Muchos efectos requieren:

```text
command t
command t+1
command t+2
command t+3
      ↓
effect t+4
```

Por tanto `CausalEvidence` debe conservar simultáneamente:

```text
attempt_id
commitment_id
intervention_signature_id
```

para permitir análisis:

```text
single command
multi-tick commitment
recurrent intervention class
```

La revisión posterior identifica correctamente esta necesidad multiescala. :chatgpt-content-reference{index="6"}

---

# 11. `InterventionSignature`

## 11.1 Problema que resuelve

`attempt_id` identifica una ejecución única:

```text
attempt.1
attempt.2
attempt.3
```

Pero el organismo necesita descubrir que varios attempts representan variaciones del **mismo patrón provisional de intervención**.

Sin esa identidad no puede acumular correctamente:

```text
repeatability
effect consistency
controllability
counterfactual rate
causal advantage
```

---

## 11.2 Definición

```python
@dataclass(frozen=True, slots=True)
class InterventionSignature:
    signature_id: str

    channel_refs: tuple[str, ...]
    temporal_pattern_ref: str | None

    dimensionality: int
```

Los `channel_refs` son opacos.

No contienen nombres físicos.

---

## 11.3 Semántica

```text
ActionAttempt
    = "this concrete intervention happened"

InterventionSignature
    = "these concrete attempts appear to belong
       to the same provisional intervention family"
```

---

## 11.4 Identidad

La signature debe derivarse de estructura motora observable por el organismo, no de semántica corporal.

Puede usar:

```text
opaque channel set
relative activations
quantized activation pattern
temporal recurrence
controller seed
sequence structure
```

según lo que esté disponible.

---

## 11.5 Regla crítica

No puede necesitar `ActionDimension` para existir.

Debe romper:

```text
need dimension to group attempts
but
need grouped attempts to discover dimension
```

La agrupación pre-dimensión es puramente motor/temporal y no semántica. :chatgpt-content-reference{index="7"}

---

# 12. `InterventionSignatureRegistry`

Componente interno recomendado:

```text
src/symbiont/actuation/intervention.py
```

API orientativa:

```python
class InterventionSignatureRegistry:
    def signature_for_command(
        self,
        *,
        command: MotorCommand,
        controller_id: str,
        tick: int,
    ) -> InterventionSignature: ...
```

Para secuencias:

```python
def signature_for_sequence(
    self,
    *,
    command_refs: tuple[str, ...],
    controller_seed_ref: str | None,
) -> InterventionSignature: ...
```

No es necesario exponer este registry como dominio público.

---

# 13. `SensorimotorTransition`

Archivo actual:

```text
src/symbiont/actuation/evidence.py
```

Añadir:

```python
attempt_id: str | None
intervention_signature_id: str | None
```

Conservar:

```python
competence_id: str | None
commitment_id: str
```

---

## 13.1 Regla

Toda transición causada por una orden motora debe tener:

```text
attempt_id != None
intervention_signature_id != None
```

Una transición pasiva puede tener:

```text
attempt_id = None
intervention_signature_id = None
```

---

# 14. `CausalEvidence`

El ledger debe evolucionar para que el sujeto causal no sea obligatoriamente una competencia.

Campos mínimos:

```python
@dataclass(...)
class CausalEvidence:
    evidence_id: str

    attempt_id: str | None
    intervention_signature_id: str | None
    commitment_id: str | None
    competence_id: str | None

    effect_id: str | None
    context_ref: str | None

    observation_tick: int
    ...
```

---

# 15. Queries del ledger

Mantener compatibilidad:

```python
effect_opportunities(
    effect_id,
    competence_id=...,
    context_ref=...,
)
```

Añadir:

```python
signature_effect_opportunities(
    effect_id,
    *,
    intervention_signature_id: str,
    context_ref: str | None,
)
```

y opcionalmente:

```python
commitment_effect_opportunities(...)
attempt_effect_opportunities(...)
```

---

# 16. Evidencia pasiva

Necesitamos poder responder:

```text
¿este efecto aparece cuando hago X?
```

y:

```text
¿también aparece cuando no hago X?
```

Por tanto, el ledger debe conservar ventanas sin intervención.

No hace falta nueva entidad pública.

Representación válida:

```text
attempt_id = None
intervention_signature_id = None
```

acompañada de contexto suficiente.

---

# 17. ActionDimensions aprendidas

## 17.1 Estado actual a eliminar

Debe desaparecer del bootstrap:

```python
for actuator_id in surface.actuator_ids:
    self.action_dimensions.discover(actuator_id)
```

---

## 17.2 Nuevo significado

`ActionDimension` significa:

> **una dimensión de intervención que el organismo ha descubierto como repetible y causalmente diferenciable.**

No:

> “existe un actuador físico”.

---

# 18. Modelo revisado de `ActionDimension`

El actual:

```python
actuator_slot_id: str
```

ya no puede ser identidad fundamental.

Propuesta:

```python
@dataclass(frozen=True, slots=True)
class ActionDimension:
    dimension_id: str

    intervention_signature_refs: tuple[str, ...]

    availability: bool

    controllability: float
    confidence: float

    usage_count: int

    embodiment_bound: bool
```

Opcionalmente:

```python
effect_refs: tuple[str, ...]
```

si se considera útil, aunque la relación factual principal debería seguir viviendo en el ledger/modelos causales.

---

# 19. Formación de dimensiones

Pipeline:

```text
ActionAttempt
    ↓
InterventionSignature
    ↓
repeated real Effects
    ↓
causal consistency
    ↓
counterfactual contrast
    ↓
ActionDimension
```

No requiere `MotorCompetence`.

No requiere agencia fuerte.

Pero sí requiere evidencia superior a la mera existencia del actuator surface.

---

# 20. Gate de dimensión

No congelamos valores científicos definitivos.

v1 debe encapsularlos en:

```text
ActionDimensionDiscoveryPolicy
```

Por ejemplo:

```python
@dataclass(frozen=True)
class ActionDimensionDiscoveryPolicy:
    minimum_attempt_support: int = 2
    minimum_effect_support: int = 2
    minimum_consistency: float = ...
```

Los números concretos son parámetros experimentales.

No dispersarlos por `ActionDomain`.

---

# 21. Controllability pre-competencia

El modelo actual centrado en `competence_id` debe ampliarse.

Necesitamos dos niveles:

```text
InterventionSignature / ActionDimension
→ Effect
```

y:

```text
MotorCompetence
→ Effect
```

---

## 21.1 Fuente causal generalizada

Recomendación:

```python
class CausalSourceKind(StrEnum):
    INTERVENTION = "intervention"
    DIMENSION = "dimension"
    COMPETENCE = "competence"
```

```python
@dataclass(frozen=True, slots=True)
class ControllabilityEstimate:
    source_kind: CausalSourceKind
    source_ref: str

    effect_id: str
    context_id: str | None

    confidence: float
    reliability: float

    counterfactual_rate: float | None
    causal_advantage: float | None

    action_support: int
    counterfactual_support: int

    last_updated_tick: int
```

Esto evita mantener tres implementaciones matemáticamente duplicadas.

---

# 22. Agency pre-competencia

`AgencyModel` debe aceptar fuentes causales anteriores a la competence.

Conceptualmente:

```text
InterventionSignature
    ↓
Effect
    ↓
temporal contingency
+
causal specificity
+
counterfactual advantage
+
prediction agreement
+
support
    ↓
AgencyEstimate
```

---

# 23. Agency nunca depende sólo de prediction match

Debe permanecer esta regla:

```text
agency
=
contingency
+
specificity
+
intervention evidence
+
counterfactual evidence
+
prediction match
+
support
```

No:

```text
agency
=
prediction matched
```

---

# 24. Exploración orientada a información causal

La exploración actual puede usar:

```text
uncertainty
novelty
learning progress
effect relevance
controllability potential
physiological cost
risk
```

Añadir:

```text
causal_information_gain
```

Representa cuánto puede aclarar una intervención una relación causal todavía incierta.

No es reward.

No significa que Lab diseñe el experimento.

---

# 25. Ejemplos de causal information gain

Puede aumentar cuando:

```text
una signature apenas se ha probado
existe un effect recurrente pero causalidad incierta
faltan ventanas sin intervención
faltan variantes de intensidad
faltan comparaciones con signatures cercanas
```

La exploración puede favorecer esas oportunidades.

---

# 26. Body Schema

Archivo:

```text
src/symbiont/core/embodiment/body_schema.py
```

## Problema

Parte de la evidencia sensorimotora actual llega demasiado tarde porque depende de competence.

---

## Nueva regla

```text
body ownership
≠
motor competence
```

Un organismo puede descubrir que algo forma parte de su cuerpo controlable antes de poseer una skill madura.

---

# 27. API propuesta para Body Schema

```python
def observe_agentic_sensorimotor_evidence(
    self,
    *,
    causal_source_ref: str,
    effect_id: str,
    feature_refs: tuple[str, ...],
    controllability_confidence: float,
    agency_confidence: float,
    tick: int,
) -> None: ...
```

Puede ser invocada desde evidencia de dimensión/intervención.

---

# 28. Competence acquisition

`CompetenceDevelopmentEngine` se mantiene.

Pero deja de ser una ruta paralela aislada.

La candidatura de competence debe converger con el mismo conocimiento causal:

```text
recurrent motor pattern
+
InterventionSignature history
+
stable Effect
+
ActionDimension
+
controllability
+
reproducibility
+
agency
    ↓
CompetenceCandidate
```

---

# 29. `MotorCompetence`

Mantener:

```text
controller_id
effect_id
evidence
parent_competence_ids
controller_strategy_ref
```

La competence significa:

> **el organismo ha aprendido una forma reproducible de producir aproximadamente un efecto.**

No significa:

> “hay un actuator”.

---

# 30. EffectSpace

`EffectSpace` pasa a ser la bisagra entre aprendizaje y ejecución.

Debe soportar:

```text
action → effect
```

y permitir consultas derivadas en sentido:

```text
effect → possible actions
```

---

# 31. Forward mapping

Ya existe conceptualmente:

```text
CompetenceEffectModel

(C, Context)
→ Effect
```

Se mantiene.

---

# 32. Reverse mapping

No guardar una segunda verdad factual.

Derivar:

```text
Effect
+
Context
+
Embodiment
    ↓
possible MotorCompetences
```

desde:

```text
CompetenceEffectModel
ControllabilityModel
CompetenceExecutionBindingRegistry
current embodiment
```

---

# 33. Effect equivalence

El código actual tiende a usar `effect_id` exacto.

Para no bloquear la evolución futura, introducir:

```python
class EffectMatcher:
    def similarity(
        self,
        expected: EffectRepresentation,
        observed: EffectRepresentation,
    ) -> float: ...
```

v1 puede usar:

```text
same id → 1.0
otherwise → 0.0
```

Pero ninguna lógica nueva de `ActionIntent` debe comparar directamente IDs sin pasar por `EffectMatcher`.

---

# 34. ActionAffordance

Archivo:

```text
src/symbiont/agency/affordance.py
```

Modelo:

```python
@dataclass(frozen=True, slots=True)
class ActionAffordance:
    affordance_id: str

    competence_id: str
    anticipated_effect_id: str

    context_ref: str | None
    embodiment_id: str | None

    prediction_confidence: float
    controllability: float
    executability_confidence: float

    prediction_ref: str | None
    evidence_refs: tuple[str, ...]
```

---

# 35. Semántica de affordance

Representa:

> **esta competence parece actualmente ejecutable y se espera que pueda producir este Effect en esta situación.**

No significa:

```text
"do it"
```

---

# 36. ActionAffordance no persiste

No se checkpointa.

No tiene lifecycle.

No autoriza acción.

No es conocimiento factual separado.

Se deriva cada vez de estado actual.

---

# 37. AffordanceResolver

Archivo:

```text
src/symbiont/agency/affordances.py
```

Dos APIs **obligatorias** de primera clase:

```python
class AffordanceResolver:
    def for_effect(
        self,
        *,
        effect_id: str,
        context_ref: str | None,
        embodiment_id: str | None,
    ) -> tuple[ActionAffordance, ...]: ...
```

y:

```python
def current(
    self,
    *,
    context_ref: str | None,
    embodiment_id: str | None,
) -> tuple[ActionAffordance, ...]: ...
```

`current()` no es opcional.

La revisión posterior identifica correctamente que el organismo no siempre parte de “quiero E”; muchas veces debe partir de “dado S, ¿qué puedo hacer?”. :chatgpt-content-reference{index="8"}

---

# 38. Dos sentidos de affordance

## Effect-directed

```text
E
→ what can probably produce E?
```

## Opportunity-directed

```text
current state S
→ what actions are currently afforded?
→ what effect is associated with each?
```

Generative Cognition puede usar ambos.

---

# 39. ActionIntent

Nueva entidad canónica central.

Archivo:

```text
src/symbiont/agency/intention.py
```

---

# 40. IntentStatus

```python
class IntentStatus(StrEnum):
    PENDING = "pending"

    ACTIVE = "active"

    SATISFIED = "satisfied"
    FAILED = "failed"
    REJECTED = "rejected"
    INTERRUPTED = "interrupted"
    INVALIDATED = "invalidated"
```

---

# 41. Razón de `REJECTED`

Existe una diferencia causal real entre:

```text
intent formed
→ proposal considered
→ motor authority never granted
```

y:

```text
intent ACTIVE
→ execution started
→ later superseded
```

El primero:

```text
REJECTED
```

El segundo:

```text
INTERRUPTED
```

Esta distinción mejora mucho la trazabilidad. :chatgpt-content-reference{index="9"}

---

# 42. Lifecycle

```text
PENDING
   ├──→ ACTIVE
   ├──→ REJECTED
   └──→ INVALIDATED

ACTIVE
   ├──→ SATISFIED
   ├──→ FAILED
   ├──→ INTERRUPTED
   └──→ INVALIDATED
```

No introducir aún:

```text
PROGRESSING
ABANDONED
SUSPENDED
CONTRADICTED
```

como estados.

Pueden representarse mediante evidencia/termination reasons.

---

# 43. Modelo ActionIntent

```python
@dataclass(slots=True)
class ActionIntent:
    intent_id: str

    competence_id: str
    anticipated_effect_id: str | None

    context_ref: str | None
    embodiment_id: str | None

    origin_refs: tuple[str, ...]
    prediction_ref: str | None

    confidence: float
    epistemic_relevance: float
    homeostatic_relevance: float

    supporting_affordance_id: str | None

    created_tick: int
    activated_tick: int | None
    last_progress_tick: int

    status: IntentStatus
    termination_reason: str | None
```

---

# 44. Prohibiciones dentro de ActionIntent

No debe contener:

```text
actuator ids
joint names
body labels
trajectory
controller gains
torque
motor vector
reward
global utility
```

---

# 45. IntentionDomain

Nuevo dominio recomendado:

```text
src/symbiont/core/domains/intention.py
```

Responsabilidades:

```python
class IntentionDomain:

    active: ActionIntent | None

    def form(...)
    def activate(...)
    def reject(...)
    def observe_effect(...)
    def fail(...)
    def interrupt(...)
    def invalidate(...)

    def checkpoint(...)
    def restore(...)
```

---

# 46. IntentionDomain NO decide motores

No hace:

```text
arbitrate
issue_command
select actuator
run controller
```

Su responsabilidad es:

> **poseer el compromiso cognitivo persistente con una consecuencia anticipada.**

---

# 47. Executive admission

No toda representación activa produce intención.

Este punto es obligatorio.

Prohibido:

```text
primitive readout active
→ automatically ActionIntent
```

porque un readout puede representar:

```text
memory
rehearsal
prediction
association
simulation
latent availability
actual executive demand
```

---

# 48. Gate explícito para intención desde readout

Debe existir:

```text
primitive readout active
+
current ActionAffordance exists
+
executive/prospective admission
    ↓
ActionIntent
```

No es necesario un rollout generativo completo.

Pero debe haber una transición explícita:

```text
represented
→ selected for realization
```

La revisión posterior considera este gate obligatorio. :chatgpt-content-reference{index="10"}

---

# 49. ProspectiveAgency

Archivo:

```text
src/symbiont/agency/prospective.py
```

No debe devolver sólo un `competence_id`.

---

# 50. ProspectiveDecision

Nueva proyección temporal:

```python
@dataclass(frozen=True, slots=True)
class ProspectiveDecision:
    competence_id: str

    anticipated_effect_id: str | None

    prediction_ref: str | None

    confidence: float
    epistemic_relevance: float
    homeostatic_relevance: float

    origin_refs: tuple[str, ...]
```

No se checkpointa.

No es otra autoridad.

Se transforma en `ActionIntent`.

---

# 51. No introducir ExecutiveChoice

El sistema ya tiene:

```text
Generative Cognition
ProspectiveAgency
ActionArbitrator
```

No añadir otro selector central.

Evitar:

```text
GC selects
ProspectiveAgency selects
ExecutiveChoice selects
ActionArbitrator selects
```

La selección debe permanecer clara.

---

# 52. `_choose_acquired_competence()`

Actualmente:

```python
def _choose_acquired_competence(...) -> str | None
```

debe evolucionar.

Preferencia:

```python
def _choose_acquired_action(...) -> ProspectiveDecision | None
```

Si el rename produce demasiado ruido, puede mantenerse temporalmente el nombre antiguo, pero no el contrato.

---

# 53. Formación de ActionIntent

Pipeline:

```text
Cognition
+
current affordances
+
Generative Cognition / ProspectiveAgency
    ↓
ProspectiveDecision
    ↓
IntentionDomain.form(...)
    ↓
ActionIntent(PENDING)
```

---

# 54. ActionProposal

Archivo:

```text
src/symbiont/actuation/action.py
```

Añadir:

```python
intent_id: str | None = None
```

---

# 55. Reglas ActionProposal

```text
source == PROSPECTION
→ intent_id expected

source == COMPETENCE from cognitive executive admission
→ intent_id expected

source == EXPLORATION
→ intent_id MUST be None

source == PROTECTION
→ intent_id normally None
```

Durante migración pueden tolerarse propuestas cognitivas históricas sin `intent_id`, pero deben desaparecer al completar la implementación.

---

# 56. ActionArbitrator

No cambia de responsabilidad.

Continúa siendo la única autoridad de:

```text
multiple demands
→ which one receives motor authority?
```

---

# 57. ActionIntent ≠ ActionCommitment

Ejemplo:

```text
ActionIntent(PENDING)
    ↓
ActionProposal
    ↓
ActionArbitrator chooses another proposal
    ↓
ActionIntent(REJECTED)
```

No hubo motor authority.

---

# 58. ActionCommitment

Archivo:

```text
src/symbiont/actuation/commitment.py
```

Añadir:

```python
intent_id: str | None
```

---

# 59. Intent activation

Cuando el arbitrator concede autoridad a la propuesta ligada al intent:

```text
PENDING
→ ACTIVE
```

`activated_tick` se fija.

---

# 60. Intent rejection

Si el arbitrator procesa la propuesta y selecciona otra:

```text
PENDING
→ REJECTED
```

`termination_reason` debe reflejar:

```text
proposal_not_selected
superseded_by_protection
superseded_by_other_action
```

según el caso.

---

# 61. ActionCommitment y control

Una vez activo:

```text
ActionIntent
    ↓
ActionProposal
    ↓
ActionCommitment
    ↓
MotorCompetence
    ↓
Controller
    ↓
MotorCommand
```

El intent nunca genera el command.

---

# 62. Cadena causal completa

Un acto cognitivo deliberado debe ser trazable:

```text
intent.I
  ↓
proposal.P
  ↓
commitment.C
  ↓
command.M
  ↓
attempt.A
  ↓
intervention.signature.S
  ↓
transition.T
  ↓
effect.E
```

---

# 63. Trazabilidad inversa

Debe poder preguntarse:

```text
Why is the body moving?
```

y reconstruirse:

```text
MotorCommand
← ActionCommitment
← ActionProposal
← ActionIntent
← ActionAffordance
← prospective/generative origin
```

Sin explicación narrativa inventada.

---

# 64. Reconciliación de intención

`IntentionDomain.observe_effect()` recibe:

```python
observed_effect_id
prediction_error
effect_similarity
tick

commitment_status
competence_executable
embodiment_id
```

---

# 65. Satisfaction

Puede ocurrir cuando:

```text
anticipated_effect exists
+
EffectMatcher says sufficient match
+
minimum evidence of progress/completion
```

Entonces:

```text
ACTIVE
→ SATISFIED
```

---

# 66. Progress

No necesita estado `PROGRESSING`.

Actualizar:

```python
last_progress_tick = tick
```

y mantener:

```text
status = ACTIVE
```

---

# 67. Mismatch

Un mismatch aislado no implica fallo.

Debe poder ocurrir:

```text
expected E1
observed E2

→ remain ACTIVE
→ accumulate mismatch
→ allow controller correction
```

---

# 68. Failure

Puede ocurrir por:

```text
controller terminal failure
commitment terminal failure
repeated high mismatch
stagnation
competence exhausted without anticipated consequence
```

Entonces:

```text
ACTIVE
→ FAILED
```

---

# 69. Invalidated

Por:

```text
embodiment changed
surface incompatible
competence no longer executable
required causal binding invalidated
```

---

# 70. Interrupted

Sólo una intención que llegó a `ACTIVE`.

Ejemplos:

```text
protection takes priority
new motor authority supersedes current commitment
homeostatic emergency
```

---

# 71. Persistencia

Una vez `ACTIVE`, no se recrea cada tick.

Prohibido:

```text
tick N
form intent C17

tick N+1
form identical intent C17 again
```

Debe mantenerse la misma identidad mientras continúe siendo válida.

---

# 72. Generative Cognition

Puede producir:

```text
anticipated effects
counterfactual futures
hypotheses
epistemic relevance
```

pero nunca autoridad motora directa.

---

# 73. Integración GC → affordance → intent

```text
Generative hypothesis
      ↓
anticipated Effect
      ↓
AffordanceResolver.for_effect(...)
      ↓
candidate ActionAffordances
      ↓
ProspectiveAgency
      ↓
ProspectiveDecision
      ↓
ActionIntent
```

---

# 74. Opportunity-driven GC

También:

```text
current state
      ↓
AffordanceResolver.current(...)
      ↓
{C1→E1, C2→E2, C3→E3}
      ↓
Generative Cognition
      ↓
compare possible futures
      ↓
ProspectiveDecision
```

---

# 75. Imagination boundary

Nunca:

```text
imagined Effect
→ EffectSpace.observe(...)
```

Nunca:

```text
generated state
→ CausalEvidenceLedger
```

Sólo el Body produce evidencia factual.

---

# 76. Tick ordering definitivo

Éste sustituye el ordering de la spec anterior.

La reconciliación de la intención debe ocurrir **antes** de generar cognición nueva. :chatgpt-content-reference{index="11"}

---

## T0 — Acquire percepts

```text
Body
→ sensory acquisition
→ Percepts(t)
```

---

## T1 — Close previous ActionAttempt

```text
pending ActionAttempt(t-1)
+
Percepts(t)
    ↓
ObservedEffect
    ↓
SensorimotorTransition
```

---

## T2 — Causal learning

```text
Transition
→ CausalEvidenceLedger

→ InterventionSignature statistics
→ EffectSpace
→ Controllability
→ Agency
→ ActionDimension discovery
→ BodySchema
→ competence evidence
```

---

## T3 — Reconcile active ActionIntent

Usar realidad ya observada:

```text
ObservedEffect
+
PredictionError
+
commitment result
    ↓
ActionIntent lifecycle
```

La cognición del mismo tick debe conocer si el intent anterior:

```text
progressed
succeeded
failed
was invalidated
```

---

## T4 — Cognition

```text
Percepts
+
updated causal state
+
updated intention state
    ↓
CognitiveBridge
```

---

## T5 — Build current ActionAffordances

```text
current context
+
current embodiment
+
MotorCompetences
+
EffectModel
+
bindings
+
controllability
    ↓
ActionAffordances
```

---

## T6 — Executive deliberation

Sólo cuando corresponda:

```text
no active valid intent

OR

active intent terminated

OR

reconsideration triggered
```

Entonces:

```text
Generative Cognition
+
ProspectiveAgency
+
affordances
    ↓
ProspectiveDecision
    ↓
ActionIntent(PENDING)
```

---

## T7 — Build ActionProposals

Fuentes paralelas:

```text
protection
exploration
active/pending cognitive intent
```

---

## T8 — Arbitration

```text
ActionArbitrator
```

Resultados relevantes:

```text
intent proposal wins
→ intent ACTIVE

intent proposal loses
→ intent REJECTED
```

---

## T9 — Controller

```text
ActionCommitment
→ MotorCompetence
→ controller
→ MotorIntent(s)
→ MotorCommand
```

---

## T10 — Execute

```text
MotorCommand
→ ActuatorSystem
→ Body
```

---

## T11 — Open ActionAttempt

Crear:

```text
ActionAttempt
InterventionSignature
pending sensorimotor baseline
```

para observar consecuencias en ticks posteriores.

---

# 77. Multi-horizon causal learning

No limitar causalidad a:

```text
t → t+1
```

Los modelos deben admitir evidencia sobre:

```text
1 tick
short sequence
full commitment/controller episode
```

En v1 no hace falta implementar un predictor multihorizon complejo, pero la estructura de datos no debe impedirlo.

---

# 78. Commitment-level evidence

`CausalEvidenceLedger` debe poder responder:

```text
what happened across this commitment?
```

además de:

```text
what happened after this command?
```

---

# 79. InterventionSignature temporal

`temporal_pattern_ref` existe precisamente para permitir:

```text
signature of one-channel probe
signature of coordinated multi-channel action
signature of short recurring controller sequence
```

sin convertir esas signatures todavía en skills.

---

# 80. Re-embodiment

Al cambiar de Body:

## Mantener

```text
historical Effects
historical MotorCompetences
historical ActionDimensions
causal knowledge
organism-owned models
```

cuando su identidad no dependa de un binding físico concreto.

---

## Invalidar

```text
current ActionAffordances
current ActionIntent requiring old embodiment
pending ActionAttempt
execution bindings incompatible with new surface
```

---

# 81. ActionDimensions tras re-embodiment

Una `ActionDimension` puede permanecer:

```text
known historically
```

pero dejar de estar:

```text
currently available/bound
```

Mantener esta separación.

---

# 82. Checkpointing

## 82.1 Sensorimotor schema

Incrementar:

```text
v3
→ v4
```

---

## 82.2 Persistir

```text
ActionDimensionRegistry
InterventionSignature learning state where necessary
active causal statistics
```

---

## 82.3 Pending attempt

Persistir sólo si es necesario para reanudar correctamente una transición abierta.

No conservar todos los `ActionAttempt` históricos fuera del ledger/traces.

---

## 82.4 ActionIntent

Nueva sección:

```json
{
  "executive_intention": {
    "schema_version": 1,
    "active": {}
  }
}
```

Una intención terminal histórica no necesita necesariamente permanecer en el core checkpoint si Observatory/history ya la recoge.

---

# 83. Migración desde Sensorimotor v3

Prohibido migrar así:

```text
current surface
→ generate all ActionDimensions
```

Migración correcta:

```text
action_dimensions = empty
```

salvo que puedan reconstruirse legítimamente desde evidencia histórica almacenada.

---

# 84. Compatibilidad con Reduced Symbiont

Existe también lógica reducida en:

```text
src/symbiont/core/orchestration/symbiont.py
```

La nueva semántica no puede implementarse sólo en full runtime.

Debe compartirse:

```text
ActionAttempt
InterventionSignature
Effect learning
Controllability
Agency
Dimension discovery
```

mediante componentes reutilizables.

---

# 85. Observatory

La UI debe hacer visible el desarrollo de agencia.

---

## 85.1 Agency acquisition

Mostrar:

```text
Physical motor opportunities
Observed intervention signatures
Discovered ActionDimensions
Agentic ActionDimensions
Known Effects
Causal relations
MotorCompetences
```

---

## 85.2 Executive state

Mostrar:

```text
Active intent
Status
Age
Anticipated Effect
Competence
Supporting affordance
Prediction confidence
Last progress
Current commitment
```

---

# 86. Trace de intención

Ejemplo:

```text
INTENT
  intent.a12

STATUS
  active

ORIGIN
  hypothesis.h8
  prospective.decision.14

AFFORDANCE
  competence.c9 → effect.e7

PROPOSAL
  proposal.p31

COMMITMENT
  commitment.k18

COMMAND
  command.m81

ATTEMPT
  attempt.a81

INTERVENTION
  intervention.s4

OBSERVED
  effect.e7

MATCH
  1.00

RESULT
  satisfied
```

---

# 87. Trace de exploración

```text
INTENT
  none

SOURCE
  exploration

COMMAND
  command.x17

ATTEMPT
  attempt.x17

INTERVENTION
  intervention.s2

OBSERVED
  effect.e3

CAUSAL UPDATE
  support +1
  controllability +...
  agency +...
  dimension candidate support +1
```

---

# 88. Cognitive Atlas

Nodos persistentes posibles:

```text
effect
action_dimension
motor_competence
action_intent
```

No representar cada `ActionAttempt` como nodo permanente.

Attempts pertenecen a:

```text
timeline
trace
inspection
```

---

# 89. Affordances en UI

Como overlay temporal:

```text
current possible action
predicted effect
confidence
controllability
executability
```

No como conocimiento estructural checkpointed.

---

# 90. Métricas nuevas

Añadir:

```text
action_attempt_count
intervention_signature_count

action_dimension_count
agentic_action_dimension_count

causal_evidence_count
effect_count

affordance_count

active_intent_id
active_intent_status
active_intent_age
active_intent_last_progress_age

intent_satisfied_count
intent_failed_count
intent_rejected_count
intent_interrupted_count
intent_invalidated_count

intent_prediction_match
```

---

# 91. Métricas observacionales no alimentan automáticamente al organismo

El hecho de que Observatory calcule:

```text
intent success rate
dimension growth
agency count
```

no convierte esas métricas en inputs.

---

# 92. Tests — ActionAttempt

```text
test_exploration_creates_attempt_without_competence
test_competence_action_creates_attempt_with_competence
test_attempt_references_exact_commitment
test_attempt_references_exact_motor_command
test_attempt_keeps_embodiment_identity
test_attempt_closes_on_observation
test_attempt_does_not_assert_effect_before_observation
```

---

# 93. Tests — InterventionSignature

```text
test_same_motor_pattern_reuses_signature
test_different_pattern_creates_distinct_signature
test_signature_identity_is_semantically_opaque
test_signature_can_span_multiple_channels
test_signature_can_reference_temporal_pattern
test_signature_does_not_require_action_dimension
test_signature_does_not_require_motor_competence
```

---

# 94. Tests — ActionDimension

```text
test_surface_does_not_bootstrap_action_dimensions
test_single_attempt_does_not_create_dimension
test_repeated_related_interventions_can_create_dimension
test_dimension_can_span_multiple_channels
test_dimension_identity_does_not_equal_actuator_identity
test_dimension_survives_checkpoint
test_reembodiment_does_not_fake_current_binding
```

---

# 95. Tests — causal evidence

```text
test_exploration_without_competence_produces_causal_evidence
test_causal_evidence_preserves_attempt_id
test_causal_evidence_preserves_commitment_id
test_causal_evidence_preserves_intervention_signature_id

test_passive_window_contributes_counterfactual_evidence
test_effect_present_without_intervention_reduces_causal_advantage
test_repeated_specific_intervention_increases_controllability
```

---

# 96. Tests — Agency

```text
test_prediction_match_alone_does_not_create_agency
test_temporal_contingency_increases_agency
test_counterfactual_specificity_increases_agency
test_effect_common_without_action_reduces_agency
test_agency_can_exist_before_motor_competence
```

---

# 97. Tests — Body Schema

```text
test_body_schema_can_learn_before_competence
test_body_schema_requires_agentic_or_sensorimotor_evidence
test_body_schema_does_not_treat_command_echo_as_body_ownership
```

---

# 98. Tests — Competence convergence

```text
test_recurrent_pattern_without_stable_effect_does_not_promote
test_stable_effect_without_reproducible_control_does_not_promote
test_causal_dimension_plus_recurrent_controller_can_form_candidate
test_competence_effect_comes_from_effect_space
```

---

# 99. Tests — Affordances

```text
test_affordance_is_derived_not_checkpointed
test_for_effect_returns_executable_competences
test_for_effect_excludes_unbound_competence
test_current_returns_state_applicable_affordances
test_affordance_does_not_authorize_action
test_affordance_contains_no_actuator_semantics
```

---

# 100. Tests — ActionIntent

```text
test_prospective_decision_can_form_pending_intent
test_pending_intent_has_no_motor_authority
test_selected_proposal_activates_intent
test_unselected_proposal_rejects_intent
test_active_intent_can_be_interrupted
test_active_intent_can_be_invalidated
test_matching_effect_satisfies_intent
test_single_mismatch_does_not_immediately_fail
test_repeated_terminal_mismatch_can_fail
test_same_intent_persists_across_ticks
test_identical_intent_is_not_recreated_every_tick
```

---

# 101. Tests — primitive readout admission

```text
test_primitive_readout_alone_does_not_form_intent
test_readout_plus_affordance_without_executive_admission_does_not_form_intent
test_readout_plus_affordance_plus_admission_can_form_intent
```

Este bloque es obligatorio para no volver a convertir activación en intención. :chatgpt-content-reference{index="12"}

---

# 102. Tests — Authority

```text
test_cognition_cannot_issue_motor_command
test_action_intent_contains_no_actuator_ids
test_action_intent_cannot_call_controller_directly
test_exploration_does_not_require_action_intent
test_protection_does_not_require_action_intent
test_action_arbitrator_remains_single_motor_authority
test_motor_command_requires_action_commitment
```

---

# 103. Tests — Intent feedback ordering

```text
test_previous_effect_reconciles_intent_before_new_deliberation
test_cognition_sees_intent_satisfaction_same_tick
test_failed_intent_is_not_reused_as_active
```

---

# 104. Integration test — Fresh organism

Debe iniciar:

```text
0 ActionDimensions
0 MotorCompetences
0 ActionIntents
```

pero poder:

```text
explore
issue MotorCommands
create ActionAttempts
observe Effects
```

---

# 105. Integration test — Dimension emergence

Demostrar:

```text
fresh organism
→ repeated intervention signatures
→ repeated Effects
→ causal evidence
→ ActionDimension
```

sin fixture que diga:

```text
this actuator is an action dimension
```

---

# 106. Integration test — pre-competence body schema

Debe ser posible:

```text
ActionDimension > 0
BodySchema sensorimotor evidence > 0
MotorCompetence = 0
```

---

# 107. Integration test — competence acquisition

Demostrar:

```text
exploration
→ InterventionSignature
→ ActionDimension
→ Effect
→ controllability
→ agency
→ MotorCompetence
```

sin shortcut.

---

# 108. Integration test — affordance

Después de acquire competence:

```text
current state
→ AffordanceResolver.current()
→ ActionAffordance
```

sin acceso cognitivo a actuadores.

---

# 109. Integration test — intentional execution

```text
ActionAffordance
→ ProspectiveDecision
→ ActionIntent
→ ActionProposal
→ ActionCommitment
→ MotorCommand
```

---

# 110. Integration test — satisfaction

```text
ActionIntent anticipates E
→ physical execution
→ E observed
→ EffectMatcher accepts
→ intent SATISFIED
```

---

# 111. Integration test — rejection

```text
cognitive intent pending
+
protection proposal higher priority
→ cognitive proposal loses
→ intent REJECTED
→ protection executes
```

---

# 112. Scientific experiment E1 — Agency acquisition ablation

Comparar:

```text
A full system

B no counterfactual evidence

C no AgencyModel
```

Medir:

```text
ActionDimensions discovered
false-positive dimensions
causal specificity
competences acquired
reproducibility
```

---

# 113. E2 — Executive bridge ablation

Comparar:

```text
A current-style competence/readout → proposal

B competence → ActionIntent → proposal
```

Medir:

```text
effect realization
action switching
prediction error
commitment failure
```

---

# 114. E3 — Intent persistence

Comparar:

```text
persistent ActionIntent
vs
re-decide every tick
```

Medir:

```text
successful effect realization
movement fragmentation
commitment interruption
controller completion
energy use
```

---

# 115. E4 — Embodied causal intervention

Condiciones:

```text
normal mapping
permuted outputs
broken effector
```

El organismo debe revisar:

```text
controllability
agency
ActionDimensions
BodySchema
affordances
```

---

# 116. E5 — Intentional causal advantage

Este experimento se añade obligatoriamente. :chatgpt-content-reference{index="13"}

Condiciones:

```text
A
competence/readout → direct ActionProposal

B
competence → ActionIntent
without persistent real-effect reconciliation

C
full ActionIntent
+ persistence
+ observed effect reconciliation
```

Mismo:

```text
Body
initial state
experience
competences
```

Medir:

```text
effect realization rate
switches per successful effect
prediction error
failed commitments
mean intent duration
intent satisfaction
energy per realized effect
```

El objetivo es probar que el intent no es sólo una nueva clase, sino una mejora causal real.

---

# 117. E6 — Acquisition → deliberate reuse closure

Éste será el **release gate científico principal**. :chatgpt-content-reference{index="14"}

Primera fase:

```text
exploration
→ ActionAttempts
→ InterventionSignatures
→ ActionDimensions
→ Effects
→ Agency
→ MotorCompetence
```

Sin resetear el organismo.

Segunda fase:

```text
learned competence
→ current affordance
→ ActionIntent
→ execution
→ expected real effect
```

No se permite al Lab suministrar:

```text
correct competence id
correct actuator
correct motor pattern
```

El organismo debe reutilizar lo que él mismo descubrió.

---

# 118. Release gate arquitectónico

La implementación NO se considera terminada porque existan:

```text
ActionAttempt class
ActionIntent class
AffordanceResolver class
```

Debe observarse:

```text
fresh organism
    ↓
exploration
    ↓
ActionAttempts
    ↓
InterventionSignatures
    ↓
real Effects
    ↓
causal regularities
    ↓
ActionDimensions
    ↓
Agency
    ↓
MotorCompetence
```

seguido, en el mismo organismo, por:

```text
current situation
    ↓
ActionAffordance
    ↓
cognitive admission
    ↓
ActionIntent
    ↓
ActionProposal
    ↓
ActionCommitment
    ↓
physical execution
    ↓
expected real Effect
    ↓
intent reconciliation
```

Ese círculo completo es el criterio de éxito. :chatgpt-content-reference{index="15"}

---

# 119. Waves de implementación

## Wave 1 — ActionAttempt + InterventionSignature

Implementar:

```text
ActionAttempt
InterventionSignature
attempt_id in transitions
signature_id in evidence
multi-scale trace identity
```

### Exit gate

Exploración con:

```text
competence_id = None
```

produce:

```text
attempt
signature
transition
causal evidence
```

---

# 120. Wave 2 — Learned ActionDimensions

Eliminar:

```text
surface → ActionDimension
```

Implementar:

```text
InterventionSignature history
→ dimension candidate
→ ActionDimension
```

### Exit gate

Fresh organism:

```text
0/N dimensions
```

El numerador sólo crece por experiencia.

---

# 121. Wave 3 — pre-competence controllability / agency / BodySchema

Implementar aprendizaje causal antes de skill.

### Exit gate

Debe existir una ejecución real con:

```text
agency evidence > 0
body schema sensorimotor evidence > 0
MotorCompetence = 0
```

---

# 122. Wave 4 — competence convergence

Conectar:

```text
recurrent pattern
+
stable Effect
+
ActionDimension
+
controllability
+
agency
→ MotorCompetence
```

### Exit gate

No debe existir una ruta paralela que fabrique una competence completamente al margen del ledger causal.

---

# 123. Wave 5 — Affordances

Implementar:

```text
AffordanceResolver.current()
AffordanceResolver.for_effect()
```

### Exit gate

El organismo puede obtener:

```text
"what can I probably do now?"
```

y:

```text
"what can probably produce E?"
```

sin consultar actuadores desde cognition.

---

# 124. Wave 6 — ActionIntent

Implementar:

```text
ProspectiveDecision
IntentionDomain
ActionIntent lifecycle
REJECTED semantics
intent_id propagation
executive admission gate
```

### Exit gate

ProspectiveAgency ya no salta directamente a ejecución cognitiva sin representación persistente.

---

# 125. Wave 7 — Intent feedback

Conectar:

```text
ObservedEffect
PredictionError
EffectMatcher
commitment status
→ ActionIntent reconciliation
```

### Exit gate

Un intent persiste varios ticks y termina por evidencia real.

---

# 126. Wave 8 — Generative Cognition integration

Implementar:

```text
generated anticipated Effects
→ affordances
→ ProspectiveDecision
→ ActionIntent
```

### Exit gate

La imaginación puede producir conducta sin contaminar el conocimiento factual.

---

# 127. Wave 9 — Observatory

Visualizar:

```text
attempts
intervention signatures
dimensions
effects
agency
competences
affordances
intents
commitments
effects
intent outcomes
```

---

# 128. Archivos nuevos previstos

```text
src/symbiont/actuation/attempt.py
src/symbiont/actuation/intervention.py

src/symbiont/agency/affordance.py
src/symbiont/agency/affordances.py
src/symbiont/agency/intention.py

src/symbiont/core/domains/intention.py
```

---

# 129. Archivos principales a modificar

```text
src/symbiont/actuation/dimension.py
src/symbiont/actuation/evidence.py
src/symbiont/actuation/model.py
src/symbiont/actuation/effects.py
src/symbiont/actuation/action.py
src/symbiont/actuation/commitment.py
src/symbiont/actuation/exploration.py

src/symbiont/core/domains/action.py
src/symbiont/core/embodiment/body_schema.py
src/symbiont/core/orchestration/runtime.py
src/symbiont/core/orchestration/symbiont.py

src/symbiont/agency/prospective.py
src/symbiont/modeling/private_runtime.py

src/symbiont/core/cognition/bridge.py
```

Más los serializers/snapshots/projections correspondientes.

---

# 130. Lo que expresamente NO forma parte de esta spec

No se implementa:

```text
walking controller
balance controller
step primitive
forward objective
locomotion reward
human joint semantics
language
abstract mathematics
social cognition
sleep
dreaming
multi-environment simultaneous cognition
```

---

# 131. Tampoco promete caminar

Esta spec no tiene como acceptance criterion:

```text
Symbiont walks
```

Su acceptance criterion es mucho más fundamental:

```text
Symbiont learns what it can cause
and later deliberately reuses what it learned
```

La locomoción compleja sería una posible consecuencia posterior.

---

# 132. Consecuencia para locomoción emergente

Después de implementar esta arquitectura, una ruta plausible sería:

```text
opaque motor interventions
    ↓
InterventionSignatures
    ↓
ActionDimensions
    ↓
local Effects
    ↓
local MotorCompetences
    ↓
compositions
    ↓
distal anticipated Effects
    ↓
persistent ActionIntent
    ↓
closed-loop correction
```

Sin hardcodear:

```text
walk
step
left_leg
forward
balance
```

---

# 133. Lectura correcta de Observatory

Hoy puede verse algo como:

```text
Known action dimensions   0/62
Action/effect relations   0
Body-schema parts         0
Motor competences         0
Motor origin              none
```

Después de la implementación no debemos simplemente subir esos contadores.

Debe aparecer desarrollo real.

Ejemplo:

```text
tick 0

62 physical opportunities
0 intervention signatures
0 ActionDimensions
0 MotorCompetences
```

Más tarde:

```text
tick N

62 physical opportunities
7 recurring InterventionSignatures
2 ActionDimensions
18 causal observations
0 MotorCompetences
```

Después:

```text
tick M

9 InterventionSignatures
4 ActionDimensions
2 BodySchema parts
1 competence candidate
```

Después:

```text
tick K

5 agentic dimensions
3 MotorCompetences
6 current affordances
0 active intent
```

Y finalmente:

```text
active intent = intent...
competence = competence...
anticipated effect = effect...
motor authority = commitment...
observed effect = effect...
intent result = satisfied
```

Eso demostraría que no hemos maquillado la UI.

---

# 134. Ontología final

```text
ActuatorSurface
    "physical intervention opportunities exist"

ActionAttempt
    "this intervention happened"

InterventionSignature
    "these attempts belong to a similar provisional motor pattern"

Effect
    "something changed"

CausalEvidence
    "this intervention and this consequence co-occurred under this context"

ActionDimension
    "I have discovered a repeatable causal dimension I can vary"

AgencyEstimate
    "I probably caused this consequence"

MotorCompetence
    "I know a reproducible way of producing this type of consequence"

ActionAffordance
    "this competence appears usable now and is expected to produce this effect"

Generative Cognition
    "what might happen if...?"

ProspectiveDecision
    "this candidate has been selected for executive admission"

ActionIntent
    "I am trying to produce this consequence"

ActionProposal
    "request motor authority"

ActionArbitrator
    "which competing demand gets motor authority?"

ActionCommitment
    "motor authority granted"

MotorController
    "how to physically realize the competence"

MotorCommand
    "actual command crossing the body boundary"

ObservedEffect
    "what physically happened"

PredictionError
    "expected versus actual"

Intent reconciliation
    "continue / satisfy / fail / reject / interrupt / invalidate"

Causal learning
    "revise what I believe I can cause"
```

---

# 135. Resultado conceptual

La arquitectura completa queda:

```text
"I moved"
    ↓
"I repeatedly moved in a similar way"
    ↓
"something repeatedly changed"
    ↓
"that change depends on this intervention"
    ↓
"I probably cause it"
    ↓
"I can vary this"
    ↓
"I know a way to reproduce it"
    ↓
"I could do it now"
    ↓
"I will try to do it now"
    ↓
"I am doing it"
    ↓
"this is what happened"
    ↓
"it worked / progressed / failed"
    ↓
"I update what I know"
```

---

# 136. Decisión final de arquitectura

**Agency Acquisition & Executive Action v1** no reemplaza el sistema actual.

Lo unifica.

Conserva:

```text
EffectSpace
CausalEvidenceLedger
ControllabilityModel
AgencyModel
BodySchemaEngine
CompetenceDevelopmentEngine
MotorCompetence
CompetenceEffectModel
CompositionEngine
Generative Cognition
ProspectiveAgency
ActionArbitrator
ActionCommitment
Controller
```

Añade únicamente las piezas necesarias para cerrar las discontinuidades:

```text
ActionAttempt
InterventionSignature
ActionAffordance
ActionIntent
```

y cambia la semántica de `ActionDimension` para que sea realmente adquirida.

La diferencia esencial respecto del estado actual puede resumirse así:

```text
BEFORE

surface
→ motor activity
→ some learning
→ competence/readout
→ proposal
→ command


AFTER

surface
→ ActionAttempt
→ InterventionSignature
→ Effect
→ causal evidence
→ ActionDimension
→ agency
→ MotorCompetence
→ ActionAffordance
→ ActionIntent
→ ActionProposal
→ ActionCommitment
→ Controller
→ Body
→ ObservedEffect
→ intent reconciliation
→ revised causal knowledge
```
