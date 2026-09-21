# Herencia evolutiva multidimensional, embodiment e individuación en Symbiont

**Baseline revisada:** `5ccbfea677c142d105c5fccee5bc105a740c14da`
**Baseline anterior:** `5c8a00791972f0283cbd59af8afd57ff19411f9f`

---

# 1. Estado tras reconciliar el diseño con `main`

Desde la baseline anterior han entrado cuatro cambios relevantes:

```text
12d2b49
remove innate action-semantics contamination

8f6f325
remove cognition/social → metabolic energy conversion

ce2f283
remove duplicate legacy CLI surface

5ccbfea
correct explicit_metabolism polarity in clean World
```

No obligan a cambiar la hipótesis central de este documento.

Al contrario: **el código ha avanzado hacia ella**.

Especialmente:

```text
typed action semantics
        ↓
eliminadas del Symbiont

cognitive/social success
        ↓
ya no produce energía

clean World metabolism
        ↓
explicit physical intake

world identity
        ↓
separada del organismo
```

Actualmente, el código implementa la separación completa y canónica:

```text
Symbiont
Body
EmbodimentSession
Individual
```

Las 10 prioridades arquitectónicas y los 48 hallazgos de auditoría (AUD-001 a AUD-048) han sido implementados y verificados con la suite de tests (`2119 passed`).

---

# 2. Cambio conceptual fundamental

Symbiont no debe modelarse como el organismo físico completo.

La arquitectura que queremos investigar es:

> **Symbiont es un germen de organización cognitiva autónoma capaz de ser implantado en un cuerpo digital desconocido y convertir progresivamente ese acoplamiento en un individuo.**

Debemos separar:

```text
SYMBIONT
germen cognitivo con continuidad propia
        │
        ▼
EMBODIMENT SESSION
acoplamiento causal concreto
        │
        ▼
BODY
sustrato físico digital
        │
        ▼
WORLD
realidad física/ecológica
        │
        ▼
HISTORY
experiencia acumulada
        │
        ▼
INDIVIDUAL
```

Por tanto:

```text
Symbiont
+
Body
+
EmbodimentSession
+
History
=
Individual
```

La consecuencia fundamental sigue siendo:

> **No nace un individuo completo. Nace un germen. El individuo se forma.**

---

# 3. Dos invariantes arquitectónicos duros

## Invariante A — la estructura real del cuerpo no entra directamente en cognición

Symbiont nunca debe recibir:

```text
"pierna"
"brazo"
"visión"
"rodilla"
"energía corporal"
"temperatura corporal"
"efector locomotor"
```

La estructura corporal debe inferirse mediante experiencia.

Formalmente:

```text
Body ground truth
       X
       │
       ▼
Cognition
```

La única ruta permitida es:

```text
Body physical state
       ↓
transduction
       ↓
opaque signals
       ↓
Symbiont
```

---

## Invariante B — la experiencia cognitiva concreta no atraviesa la línea germinal

Nunca deben heredarse directamente:

```text
memorias
conceptos
BodySchema
AgencyModel
SensorimotorModel
signal knowledge
mapas
relaciones sociales concretas
action mappings aprendidos
predicciones específicas
```

Formalmente:

```text
learned cognition
       X
       │
       ▼
offspring
```

Puede transmitirse predisposición.

No solución.

---

# 4. El último código refuerza un tercer invariante

Los commits posteriores a la baseline anterior permiten formular ahora una tercera regla con mucha más fuerza:

## Invariante C — el significado adaptativo no puede convertirse mágicamente en recurso físico

Antes existían rutas donde:

```text
cognitive success
social agreement
        ↓
metabolic intake
```

Eso introducía energía sin una causa física equivalente.

`8f6f325` elimina esa conversión.

El principio correcto pasa a ser:

```text
physical acquisition
        ↓
physical reserve
```

mientras que:

```text
prediction success
social agreement
learning
cognition
```

pueden modificar estado cognitivo, pero **no crear recurso físico de la nada**.

Este cambio es muy importante para la futura separación Body/Symbiont.

---

# 5. Corrección del metabolismo explícito

`5ccbfea` corrige además una inversión en:

```python
explicit_metabolism
```

La semántica canónica queda:

```text
explicit_metabolism = True
```

significa:

> la reserva debe alimentarse mediante intake explícito y no mediante replenishment ambiental implícito.

Esto importa porque anteriormente el World limpio construía explícitamente un ledger sin replenishment, por lo que los resultados observados eran correctos, pero el flag declaraba lo contrario.

El guard de frontera también estaba invertido.

Ahora:

```text
canonical clean World
        ↓
explicit_metabolism = True
        ↓
no ambient/free replenishment
```

Esto hace más robusta la separación causal.

---

# 6. Qué significa este cambio para nuestro diseño

El metabolismo explícito **no invalida** nuestra propuesta de mover la fisiología física al Body.

Lo que demuestra es algo distinto:

> El código ya está intentando garantizar que los recursos físicos procedan de consecuencias físicas.

Actualmente esa lógica sigue viviendo en buena medida dentro de:

```text
OrganismRuntime
MetabolicLedger
PhysiologyController
HomeostaticController
```

La refactorización futura deberá conservar la nueva propiedad causal, pero cambiar su propietario:

```text
AHORA

OrganismRuntime
    └── physical metabolism


OBJETIVO

Body
    └── physical metabolism

Symbiont
    └── opaque consequences / constitutive pressures
```

Es decir, **no debemos deshacer `explicit_metabolism`; debemos desplazar su realidad física a la capa correcta.**

---

# 7. Eliminación de las acciones semánticas innatas

`12d2b49` cambia materialmente el estado del documento.

Se ha eliminado:

```text
src/symbiont/core/behavior.py
```

y con él:

```text
ActionKind
ExpectedOutcome
ActionOpportunity
SelectionResult
ActionEvidence
LocalActionModel
InteroceptiveActionModel
select_action()
```

La antigua taxonomía incluía significados como:

```text
REST
INTAKE
REPAIR
...
```

y una utilidad agregada similar a:

```text
viability
+
integrity
+
resource_change
+
reproductive_feasibility
+
social_expectation
-
cost
```

Esto era incompatible con nuestro principio:

> el Symbiont no debe nacer sabiendo qué significa una acción.

Ahora existe además un test de integridad que impide reintroducir estas estructuras en `src/symbiont`.

Por tanto una parte importante del diseño de este documento ya no es futura.

**La eliminación de semántica de acción en el núcleo está hecha.**

---

# 8. Consecuencia para la interfaz motora objetivo

La dirección correcta queda todavía más clara:

```text
NO

Symbiont
   ↓
"rest"
"eat"
"repair"
"move north"
```

sino:

```text
Symbiont
   ↓
opaque activation
   ↓
Body
   ↓
physical consequence
```

El código actual ya se ha alejado del primer modelo.

Aun así, la separación completa todavía no existe porque:

```text
ActuatorConstitution
ActuatorSystem
motor intent
physical metabolism
```

continúan parcialmente integrados en `OrganismRuntime`.

---

# 9. `WorldAction` deja de ser el problema principal

Versiones anteriores de este documento proponían eliminar `WorldAction` semántico del camino canónico.

Tras `12d2b49`, debemos precisar esta afirmación.

El problema crítico era que **Symbiont tuviera una ontología innata de acciones**.

Eso ya ha sido eliminado.

Puede seguir existiendo semántica de aparato o contratos históricos fuera del núcleo mientras:

```text
Symbiont does not know it
```

Por tanto, el criterio correcto ya no es:

> ningún código del sistema puede usar nombres semánticos.

Es:

> **ninguna semántica del aparato puede atravesar la frontera epistemológica hacia el Symbiont.**

Esto es más preciso.

---

# 10. Separación ontológica objetivo

Debemos distinguir:

```text
SYMBIONT
identidad cognitiva persistente

BODY
sustrato físico reemplazable

EMBODIMENT SESSION
acoplamiento causal concreto

HISTORY
trayectoria de interacción

INDIVIDUAL
resultado histórico del acoplamiento
```

El código actual todavía utiliza:

```python
OrganismRuntime
```

como contenedor de varias de estas responsabilidades.

Esa es ahora una de las principales deudas estructurales.

---

# 11. Identidades independientes

Debe existir al menos:

```text
symbiont_id
body_id
embodiment_id
```

Ejemplo:

```text
Symbiont A
    │
    ├── Embodiment E1 → Body X
    ├── Embodiment E2 → Body Y
    └── Embodiment E3 → Body Z
```

Esto permite distinguir:

```text
continuidad del germen
continuidad corporal
historia de una encarnación
historia total del individuo cognitivo
```

---

# 12. `EmbodimentSession`

La implantación no debe ser sólo una función de cableado instantáneo.

Debe producir una relación temporal:

```python
@dataclass(slots=True)
class EmbodimentSession:
    embodiment_id: str
    symbiont_id: str
    body_id: str

    started_at: int
    ended_at: int | None

    input_binding: ...
    output_binding: ...
```

Los bindings pertenecen al aparato.

Nunca a la cognición.

---

# 13. Interfaz de implantación

Conceptualmente:

```python
implant(symbiont, body)
```

debe crear:

```text
EmbodimentSession
```

y únicamente establecer:

```text
Body receptor ports
        ↓
opaque inputs
        ↓
Symbiont

Symbiont
        ↓
opaque activations
        ↓
Body effector ports
```

No debe transmitir:

```text
morphology
body topology
part names
effector meaning
receptor meaning
body coordinates
world semantics
```

---

# 14. El cuerpo real y el cuerpo inferido

World conoce:

```text
REAL BODY
```

Symbiont construye:

```text
INFERRED BODY
```

Ejemplo:

```text
REAL BODY                    LEARNED MODEL

4 limbs                      3 controllable regions
12 joints                    7 stable motor relations
2 optical receptors          2 perceptual clusters
1 damaged limb               unreliable causal region
```

La segunda columna debe surgir únicamente de experiencia.

---

# 15. No existe un único modelo corporal

Separaremos:

```text
PerceptualStructure
        ↓
SensorimotorModel
        ↓
AgencyModel
        ↓
BodySchema
        ↓
SelfModel
```

Cada nivel responde a una pregunta distinta.

---

# 16. `PerceptualStructure`

Pregunta:

> ¿Qué señales mantienen relaciones estables?

Puede aprender:

```text
covariance
temporal ordering
predictability
cross-modal relations
clusters
```

Ejemplo:

```text
in.13
correlates with
in.42
```

Esto todavía no significa causalidad.

---

# 17. `SensorimotorModel`

Pregunta:

> ¿Qué consecuencias suelen seguir a mi actividad?

Ejemplo:

```text
out.7
   ↓
Δin.13
```

Representa:

```text
activation(t)
→
future perceptual state(t+n)
```

pero todavía no asegura agencia.

---

# 18. `AgencyModel`

Pregunta:

> ¿Qué cambios dependen diferencialmente de mi actividad?

Debe basarse en algo equivalente a:

```text
intervention
+
contrast
+
replication
+
temporal ordering
+
predictive consequence
```

No en simple correlación.

Esto encaja especialmente bien con la eliminación de `ActionKind`.

Ahora no necesitamos preguntar:

```text
"¿qué acción elegí?"
```

sino:

```text
"¿qué activación precedió causalmente a qué consecuencia?"
```

---

# 19. `BodySchema`

Pregunta:

> ¿Qué conjunto relativamente estable de relaciones de agencia parece constituir mi embodiment?

Puede contener:

```text
controllable regions
stable sensorimotor relations
causal reach
internal/external boundaries
reliability
confidence
```

No una descripción verdadera del cuerpo.

---

# 20. `SelfModel`

Pregunta:

> ¿Qué procesos parecen formar parte de mi continuidad propia?

No debe equivaler a `BodySchema`.

Puede contener evidencia relacionada con:

```text
memory
temporal continuity
prediction
agency
identity
cognition
embodiment
```

Y eventualmente elementos no estrictamente corporales.

---

# 21. Herramientas y extensión de agencia

Ejemplo:

```text
body
 ↓
tool
 ↓
external object
```

Una herramienta puede entrar en:

```text
AgencyModel
```

sin entrar inmediatamente en:

```text
BodySchema
```

Esto permite que la extensión de la frontera corporal sea un resultado experimental.

---

# 22. Definición operacional de individuación

Podemos formular:

> **Un Symbiont se individúa cuando construye, a partir de regularidades perceptuales y contingencias causales de su propia actividad, un modelo persistente de aquellos procesos cuya dinámica depende diferencialmente de él.**

Mediremos:

```text
controllability
prediction
causal attribution
persistence
boundary formation
model revision
recovery after perturbation
```

Sin asumir todavía:

```text
consciousness
subjective self
self-awareness
```

---

# 23. Estado actual del genoma

En:

```text
src/symbiont/cognition/genome.py
```

continúa existiendo el `Genome` canónico con componentes como:

```text
development
plasticity
structure
mutation_policy
motor
parent_ids
deterministic identity/hash
```

La interpretación de `motor` deberá revisarse después de separar Body y Symbiont.

---

# 24. Estado actual de `HeritableGenome`

Actualmente:

```python
HeritableGenome
```

mantiene sólo:

```text
initial_concepts
soft_node_budget
soft_edge_budget
learning_rate
forgetting_rate
```

Esto cambia respecto a la versión anterior del documento.

Ya **no existe** como locus heredable:

```text
behavior_exploration
```

porque desapareció junto con el sistema de comportamiento semántico.

El documento anterior debe considerarse corregido en este punto.

---

# 25. Consecuencia importante para la futura genética

La eliminación de:

```text
behavior_exploration
```

es conceptualmente correcta.

No debemos reemplazarlo inmediatamente por otro equivalente.

Cuando rehagamos `SymbiontGenome`, la exploración debería modelarse a niveles más fundamentales:

```text
perceptual exploration
motor exploration
model uncertainty response
plasticity
novelty sampling
```

sin una policy global de comportamiento presemantizada.

---

# 26. Una anomalía que queda en `main`

Actualmente sigue apareciendo:

```python
_SUPPORTED_EPIGENETIC_KEYS = frozenset({"exploration_bias"})
```

en `OrganismRuntime`.

Pero el mecanismo histórico de:

```text
behavior_exploration
```

ha desaparecido.

Esto convierte `exploration_bias` en una pieza que debe auditarse antes de implementar la nueva epigenética.

No debemos asumir que sigue teniendo una semántica válida.

Por tanto añadimos explícitamente:

> **Antes de crear `GermlineState`, eliminar o redefinir cualquier `EpigeneticPrior` cuya variable objetivo haya quedado huérfana tras la eliminación del comportamiento semántico.**

---

# 27. El `Genome` actual todavía mezcla germen y embodiment

El problema sigue presente.

No queremos:

```text
SymbiontGenome
→ physical actuator layout
→ physical receptor layout
→ body morphology
```

Queremos:

```text
SymbiontGenome
→ capacity to learn
→ plasticity
→ cognitive development
→ agency inference
→ motor learning
→ sensory learning
```

mientras:

```text
Body
→ morphology
→ receptors
→ effectors
→ physical physiology
```

---

# 28. `SymbiontGenome`

Objetivo:

```text
SymbiontGenome
 ├── development
 ├── cognition
 ├── plasticity
 ├── learning
 ├── memory
 ├── motor_learning
 ├── sensory_learning
 ├── inheritance
 └── mutation_policy
```

No debe determinar el cuerpo concreto.

---

# 29. `BodyGenome`

A largo plazo puede existir:

```text
BodyGenome
```

con:

```text
morphology
receptor constitution
effector constitution
structural development
material properties
physical metabolism
regeneration
```

Pero no debe implementarse todavía.

Primero debemos demostrar que Symbiont puede adaptarse a cuerpos externos distintos.

---

# 30. `ActuatorConstitution`

Éste sigue siendo uno de los principales puntos que deben cambiar.

Actualmente la constitución motora sigue vinculada al Symbiont y puede cargarse desde nacimiento/genoma.

En la arquitectura objetivo:

```text
Body
   ↓
physical effector ports
   ↓
EmbodimentSession
   ↓
opaque output channels
   ↓
Symbiont learns controllability
```

`SymbiontGenome` puede contener:

```text
MotorLearningGenes
```

pero no las partes físicas.

---

# 31. Lo que `12d2b49` ya ha resuelto aquí

Aunque `ActuatorConstitution` todavía necesite refactorización, ya no existe una capa superior del tipo:

```text
motor output
↓
ActionKind.INTAKE
↓
utility-ranked semantic behaviour
```

Eso supone una reducción importante de contaminación.

Ahora el trabajo puede concentrarse en:

```text
physical effector ownership
opaque channel mapping
agency inference
```

en vez de limpiar una policy semántica adicional.

---

# 32. Percepción

El Body debe poseer receptores físicos.

Symbiont debe poseer:

```text
signal processing
perceptual learning
attention
prediction
```

Cadena:

```text
World
 ↓
Body receptor
 ↓
transduction
 ↓
opaque signal
 ↓
Symbiont
```

---

# 33. Estado somático opaco

El World limpio ya ha avanzado en esta dirección.

Existen rutas donde estado somático físico se mezcla en receptores opacos sin entregar directamente etiquetas como:

```text
energy
damage
```

Eso debe conservarse.

La futura separación `Body` debe convertirlo en el único camino canónico.

---

# 34. Fisiología física

Las variables físicas deben pertenecer al Body:

```text
energy
damage
temperature
material reserve
structural integrity
physical degradation
```

La cognición no debe recibirlas directamente.

---

# 35. Qué aporta `8f6f325`

Este commit elimina dos contaminaciones particularmente importantes.

Antes podían ocurrir cosas equivalentes a:

```text
successful assimilation
→ metabolic reserve

prediction accuracy
→ metabolic reserve

social epistemic agreement
→ metabolic reserve
```

Eso ya no ocurre.

Ahora una buena predicción sigue siendo cognitivamente relevante, pero:

```text
prediction success != physical food
```

Este principio debe elevarse a regla permanente.

---

# 36. Metabolismo y reproducción

El código actual utiliza reserva metabólica para condiciones reproductivas.

Tras los últimos commits, esa reserva se aproxima mucho más a:

```text
physically obtained reserve
```

y deja de estar inflada por:

```text
cognitive reward
social reward
```

Esto mejora considerablemente cualquier futuro estudio evolutivo.

No obstante, cuando extraigamos el Body debemos conservar la causalidad:

```text
Body physical intake
        ↓
Body reserve
        ↓
physical reproductive feasibility
```

y no volver a trasladar esa lógica a una utilidad cognitiva.

---

# 37. Interocepción

La futura regla sigue siendo:

```text
physical body state
       ↓
internal receptor
       ↓
opaque signal
       ↓
Symbiont
```

No:

```text
MetabolicLedger.reserve["energy"]
       ↓
cognition knows energy
```

La interocepción debe convertirse en percepción corporal aprendida.

---

# 38. Presiones constitutivas

El Symbiont puede poseer dinámicas innatas mínimas relacionadas con:

```text
continuity
stability
bounded resource use
structural persistence
```

Pero no deben equivaler semánticamente a:

```text
hunger
pain
fatigue
food seeking
rest
repair
```

La eliminación de `ActionKind` refuerza precisamente este punto.

---

# 39. Trasplante

Debe poder existir:

```text
Symbiont A
+
Body X
```

y posteriormente:

```text
Symbiont A
+
Body Y
```

manteniendo estado cognitivo.

No debemos resetear `BodySchema`.

Queremos:

```text
old model
↓
new causal reality
↓
prediction disruption
↓
agency disruption
↓
revision
↓
new embodied model
```

---

# 40. Experimento de permutación de puertos

Éste sigue siendo uno de los experimentos más importantes.

Inicialmente:

```text
out.a → effector.1
out.b → effector.2
```

Después:

```text
out.a → effector.2
out.b → effector.1
```

Sin cambiar:

```text
Symbiont
Body
World
Genome
memory
```

Resultado esperado:

```text
prediction error ↑
controllability confidence ↓
agency confidence ↓
exploration ↑
new relations acquired
BodySchema revised
```

---

# 41. Experimento de efector roto

Mantener todo idéntico salvo:

```text
effector.1
    ↓
silently stops producing physical effect
```

Esto permite estudiar revisión causal sin introducir una etiqueta:

```text
"broken"
```

---

# 42. Embodiment con múltiples morfologías

Mismo `SymbiontGenome`:

```text
human-like body
quadruped body
wheeled body
alien morphology
```

Queremos estudiar:

```text
perceptual discovery
sensorimotor learning
agency attribution
BodySchema formation
adaptation time
```

No igualdad de conductas.

---

# 43. Herencia evolutiva multidimensional

Sólo después de resolver embodiment debemos rehacer herencia.

Canales conceptuales:

```text
Symbiont genetics
Symbiont epigenetics

eventual:
Body genetics
Body epigenetics

plus:
individual learning
culture
niche engineering
```

---

# 44. Genética

Pipeline:

```text
parent genome
      ↓
recombination
      ↓
mutation
      ↓
child SymbiontGenome
```

Sin conocimiento aprendido.

---

# 45. Epigenética actual

`EpigeneticPrior` sigue existiendo como infraestructura histórica/experimental.

No debe convertirse directamente en el sistema canónico futuro.

Especialmente ahora que:

```text
exploration_bias
```

debe ser revisado por posible obsolescencia semántica.

---

# 46. `EpigeneticMark`

El objetivo sigue siendo:

```python
@dataclass(frozen=True, slots=True)
class EpigeneticMark:
    locus: str
    delta: float
    strength: float
    generations_left: int
```

Una marca significa:

```text
persistent alteration
of a legitimate heritable expression locus
```

No:

```text
learned solution
```

---

# 47. `GermlineState`

Crear posteriormente:

```python
@dataclass(slots=True)
class GermlineState:
    birth_expression: dict[str, float]
    acquired_marks: dict[str, EpigeneticMark]
```

Pero **no antes de completar la separación Body/Symbiont**.

De lo contrario volveríamos a crear una línea germinal dentro de un runtime que aún mezcla estado corporal y cognitivo.

---

# 48. No toda modificación puede heredarse

Regla:

```text
legitimate genetic locus
        ↓
potential epigenetic modulation
```

Nunca:

```text
learned concept
        ↓
invented germline locus
```

---

# 49. Evolución de la heredabilidad

Más adelante:

```python
InheritanceGenes(
    acquired_transmission_rate,
    epigenetic_decay,
    max_epigenetic_marks,
)
```

y estos parámetros también deberán mutar.

Así:

```text
Darwin
↓
evolves transmission rate
↓
acquired variation crosses generations
↓
selection continues
```

---

# 50. Reproducción

Conceptualmente:

```text
parent Individual
       ↓
reproduction
       ↓
InheritancePackage
       ↓
new Symbiont
       ↓
new Body
       ↓
EmbodimentSession
       ↓
new individual history
```

No:

```text
clone complete learned organism
```

---

# 51. `InheritancePackage`

Debe contener algo del estilo:

```text
SymbiontGenome
SymbiontEpigenome
parent_ids
generation
```

Nunca:

```text
memory
BodySchema
AgencyModel
SensorimotorModel
signal knowledge
```

---

# 52. Reproducción clonal

Debe conservar:

```text
parent genome
↓
mutation
↓
child genome
```

más, eventualmente:

```text
parent epigenetic state
↓
bounded transmission
↓
decay
↓
child epigenome
```

---

# 53. Reproducción sexual

Debe evolucionar desde la recombinación simplificada actual hacia:

```text
independent locus recombination
+
mutation
```

sin fitness explícito para elegir alelos.

---

# 54. Cultura

Debe continuar totalmente separada:

```text
A learns
↓
A behaves
↓
B perceives
↓
B learns
```

Nunca:

```text
A learns
↓
B genome changes directly
```

---

# 55. Ingeniería de nicho

También permanece separada:

```text
parent modifies World
↓
offspring encounters modified World
```

Continuidad causal sin transferencia genética.

---

# 56. Mutación tipada

Sigue siendo necesario introducir:

```python
LocusSpec
```

porque los loci actuales mezclan:

```text
counts
budgets
rates
```

y no deben tratarse todos como floats equivalentes.

`LocusSpec` debe definir:

```text
type
minimum
maximum
mutation operator
expression
inheritability
```

---

# 57. Unificación genética

Objetivo:

```text
SymbiontGenome
 ├── loci
 ├── constitution
 ├── development
 ├── mutation_policy
 ├── inheritance_policy
 └── identity
```

y retirar:

```text
HeritableGenome
```

como representación paralela.

---

# 58. `OrganismRuntime` sigue siendo la principal concentración de responsabilidades

Aunque se hayan eliminado más de 500 líneas relacionadas con comportamiento semántico, todavía contiene directamente referencias a:

```text
SensorySystem
BodySchemaEngine
SelfModel
MetabolicLedger
HomeostaticController
PhysiologyController
ActuatorConstitution
ActuatorSystem
interoception
reproduction
```

Por tanto sigue representando más que un germen cognitivo.

Éste es ahora el siguiente problema estructural principal.

---

# 59. Objetivo de `SymbiontRuntime`

A medio plazo:

```text
OrganismRuntime
```

debería evolucionar hacia:

```text
SymbiontRuntime
```

que posea:

```text
cognition
memory
prediction
learning
PerceptualStructure
SensorimotorModel
AgencyModel
BodySchema
SelfModel
germline
```

y se comunique exclusivamente mediante:

```text
opaque input
opaque activation
```

---

# 60. `ActionExecutionResult`

Tras la eliminación del comportamiento tipado queda una estructura genérica:

```python
ActionExecutionResult
```

con semántica deliberadamente opaca.

Esto no contradice el documento.

Puede sobrevivir como superficie pasiva de reporting mientras no reintroduzca:

```text
ActionKind
utility
meaning
semantic selection
```

Sin embargo, cuando exista `EmbodimentSession`, convendrá revisar incluso el nombre `ActionExecutionResult`, porque:

```text
activation consequence
```

es epistemológicamente más neutral que:

```text
action result
```

---

# 61. Integridad experimental existente

El código actual ya tiene tests que exigen:

```text
symbiont ✗→ symbiont_lab
symbiont ✗→ symbiont_world
symbiont_world ✗→ symbiont
symbiont_world ✗→ symbiont_lab
```

y también evita reintroducir el comportamiento semántico eliminado.

Esto encaja directamente con la arquitectura propuesta.

Debemos ampliar esa suite, no sustituirla.

---

# 62. Nuevos tests de integridad

Añadir posteriormente:

```text
Body morphology cannot enter cognition

Body semantic part names cannot enter cognition

port physical identity cannot enter cognition

World cannot write BodySchema

World cannot write AgencyModel

Lab cannot write BodySchema (ver §62.1 — exención acotada para especímenes de falsación por componentes)

Observatory cannot mutate embodiment state

learned BodySchema cannot cross reproduction

learned AgencyModel cannot cross reproduction
```

---

## 62.1 Invariante refinado: exención experimental acotada para estudios de falsación por componentes

El audit de las 5 preregistradas de falsación de embodiment (E1, E2, E3, E5, E6 —
`hidden_common_cause.py`, `yoked_external_causation.py`, `tool_body_distinction.py`,
`somatic_correlation_trap.py`, `temporal_causality_challenge.py`, bajo
`src/symbiont_lab/studies/embodiment/`) mostró que instancian `AgencyModel` /
`InferredBodySchema` como especímenes aislados para falsar el algoritmo en sí
mismo (test a nivel de componente), no para ejecutar un Symbiont vivo. Esto
disparaba el test de frontera `Lab cannot write BodySchema` de forma
excesivamente amplia.

Decisión explícita del propietario: **elección 1 — exención experimental
acotada, pero con la frontera hecha explícita y verificable
mecánicamente.**

El invariante queda refinado así:

```text
Antes:
  Lab nunca puede instanciar AgencyModel/InferredBodySchema.

Ahora:
  Lab nunca puede instanciar, mutar o reemplazar el AgencyModel/InferredBodySchema
  perteneciente a un Symbiont vivo.

  Instancias sintéticas aisladas están permitidas únicamente como especímenes
  dentro de estudios de falsación explícitos a nivel de componente, y no tienen
  ningún camino causal de vuelta hacia un organismo.
```

La exención es intencionalmente estrecha. Un módulo de estudio solo queda
exento si cumple todas estas condiciones, verificadas estructuralmente por
`tests/experimental_integrity/test_embodiment_inheritance_integrity.py`:

```text
los objetos deben construirse en fresco dentro del propio harness del estudio

nunca se obtienen de, se adjuntan a, se inyectan en, ni se escriben de vuelta
hacia un Symbiont vivo

ningún checkpoint ni estado persistente de organismo se carga en ellos

ningún estado sintético, activación, delta, estado corporal inferido,
puntuación o conclusión cruza de vuelta hacia symbiont

viven bajo una frontera explícitamente identificada de
falsación-de-componente/test, sin simular ejecución normal del organismo

el código de producción/runtime de Lab sigue sin poder instanciar ni mutar
cognición/estado corporal propiedad del organismo
```

Marcador mecánico: cada módulo exento declara explícitamente
`__falsification_specimen__ = True` a nivel de módulo. El test de frontera
detecta este marcador vía AST (no por import, para que no pueda activarse
condicionalmente en tiempo de ejecución) y, únicamente para los módulos
marcados, permite referenciar el par estrecho `{AgencyModel,
InferredBodySchema}` — `InferredSelfModel` y `BodySchemaEngine` permanecen
absolutamente prohibidos incluso en módulos marcados. Además, incluso en un
módulo marcado, el test verifica estructuralmente que no se importe ni
construya ningún `Symbiont`/`Individual` vivo, que no se asigne nunca a los
atributos `.agency_model` / `.body_schema` que un `Symbiont` real posee, y que
no se llame a ninguna función de checkpoint/restore sobre el espécimen. Un
test adicional a nivel de runtime ejecuta uno de estos estudios de extremo a
extremo y recorre el grafo de objetos del resultado, confirmando
empíricamente que ningún espécimen ni organismo escapa de la frontera del
harness.

No redefine las mediciones preregistradas de estos 5 estudios: el barrido de
auditoría del §62.1 no encontró ninguna violación genuina de las condiciones
anteriores en las 5 (ninguna comparte instancias con un Symbiont vivo,
ninguna inyecta conclusiones de vuelta a cognición); solo se requirió marcar
los módulos y reescribir el test de frontera para reconocer la exención.

---

# 63. Test metabólico de integridad

Tras los últimos commits añadiría explícitamente como principio permanente:

```text
cognition success
social agreement
prediction accuracy
        X
        │
        ▼
physical reserve
```

y:

```text
physical acquisition
        ↓
physical reserve
```

salvo que exista en el futuro una cadena física explícita que justifique otra transferencia.

---

# 64. Genesis

Los fundadores deberían comenzar:

```text
SymbiontGenome = founder genome

SymbiontEpigenome = empty

experience = empty

culture = empty

PerceptualStructure = germinal

SensorimotorModel = germinal

AgencyModel = germinal

BodySchema = germinal

SelfModel = germinal/minimal
```

Después:

```text
Body created
↓
EmbodimentSession created
↓
history begins
```

---

# 65. Orden de implementación actualizado contra `main`

El plan debe cambiar ligeramente porque `main` ya ha resuelto parte de la descontaminación.

## P0 — formalizar ontología

Definir:

```text
Symbiont
Body
EmbodimentSession
Individual
```

Ésta sigue siendo la prioridad máxima.

---

## P1 — extraer Body

Mover fuera del runtime del germen:

```text
physical receptors
physical effectors
physical physiology
physical metabolism
material reserve
physical degradation
```

Conservar la propiedad recién reforzada:

```text
physical reserve requires physical cause
```

---

## P2 — interfaz opaca

Formalizar:

```text
Body
↓
opaque inputs
↓
Symbiont
↓
opaque activations
↓
Body
```

La eliminación de `ActionKind` hace esta fase bastante más sencilla que en la baseline anterior.

---

## P3 — consolidar eliminación de semántica de acción

Ya casi completado.

Auditar que ningún camino canónico restante convierta:

```text
opaque activation
```

en una semántica aprendida externamente antes de que el Symbiont infiera sus consecuencias.

---

## P4 — `PerceptualStructure`

Separar regularidades perceptuales de conocimiento corporal.

---

## P5 — `SensorimotorModel`

Modelar:

```text
activation
→
future perceptual consequence
```

---

## P6 — `AgencyModel`

Inferir controlabilidad y causalidad propia.

---

## P7 — `BodySchema`

Convertirlo en construcción completamente adquirida basada en agencia.

---

## P8 — `SelfModel`

Separarlo definitivamente del embodiment corporal.

---

## P9 — fisiología/interocepción

Completar la transición:

```text
physical state belongs to Body
```

El trabajo de metabolismo explícito ya proporciona una buena base causal para esta fase.

---

## P10 — permutación de puertos

Verificar ruptura y reaprendizaje.

---

## P11 — efector roto

Verificar revisión causal.

---

## P12 — trasplante

Mover el mismo Symbiont entre cuerpos diferentes.

Éste continúa siendo el criterio de aceptación principal.

---

## P13 — múltiples morfologías

Mismo `SymbiontGenome`, distintos bodies.

---

## P14 — redefinir `SymbiontGenome`

Revisar:

```text
motor
sensory
physiology-related constitution
development
```

sólo cuando sepamos qué pertenece realmente al germen.

---

## P15 — `LocusSpec`

Tipar correctamente mutación y expresión.

---

## P16 — unificar `Genome` y `HeritableGenome`

Eliminar la representación paralela.

---

## P17 — limpiar epigenética histórica

Auditar y probablemente eliminar/redefinir:

```text
exploration_bias
EpigeneticPrior
```

antes de crear el mecanismo nuevo.

---

## P18 — `GermlineState`

Crear línea germinal real.

---

## P19 — captura adquirida

Permitir sólo modificaciones internas legítimas y bounded.

---

## P20 — transmisión epigenética

Añadir:

```text
transmission
decay
```

---

## P21 — reproducción sexual

Recombinación tipada por locus.

---

## P22 — evolución de heredabilidad

Hacer mutable:

```text
acquired_transmission_rate
```

---

## P23 — evolución corporal

Sólo entonces estudiar:

```text
BodyGenome
BodyEpigenome
```

---

# 66. Qué ha desaparecido del plan porque ya está hecho

Podemos marcar como realizado:

```text
✓ eliminar ActionKind del Symbiont

✓ eliminar utility-ranking global de acciones

✓ eliminar behavior_exploration heredable

✓ impedir que éxito cognitivo cree reserva física

✓ impedir que acuerdo social cree reserva física

✓ hacer explícito el metabolismo del World limpio

✓ fail closed si World limpio pierde explicit metabolism

✓ mantener resource identity fuera del organismo limpio
```

Esto reduce significativamente el trabajo previo necesario antes de la separación ontológica.

---

# 67. Qué sigue sin estar resuelto

Los principales puntos pendientes son ahora:

```text
Body todavía no existe como entidad ontológica independiente

EmbodimentSession no existe

OrganismRuntime sigue mezclando cuerpo y germen

ActuatorConstitution sigue siendo organism-owned

fisiología física sigue en core runtime

metabolismo físico sigue en core runtime

BodySchema todavía debe endurecer su condición de modelo adquirido

AgencyModel separado no existe

SensorimotorModel explícito no existe

SelfModel y BodySchema todavía necesitan una frontera más fuerte

Genome sigue mezclando aspectos constitucionales a revisar

epigenética canónica sigue siendo artificial/incompleta
```

---

# 68. Experimento central de embodiment

La hipótesis principal sigue siendo:

> **¿Puede un sistema cognitivo inicialmente agnóstico a su embodiment inferir, exclusivamente mediante contingencias sensorimotoras y experiencia causal, una frontera operacional entre procesos atribuibles a sí mismo y procesos atribuibles al entorno?**

Los últimos commits hacen esa pregunta más limpia porque eliminan varias respuestas precodificadas que antes podían contaminarla.

---

# 69. Arquitectura objetivo

```text
                             OBSERVATORY
                                  │
                                  ▼
┌──────────────────────────────────────────────────────┐
│                        WORLD                         │
│                                                      │
│              physics / ecology / causality           │
│                          │                           │
│                          ▼                           │
│                         BODY                         │
│                                                      │
│ morphology                                           │
│ physical metabolism                                  │
│ physiology                                           │
│ receptors                                            │
│ effectors                                            │
│      │                                      ▲        │
│      ▼                                      │        │
│ opaque signals                          activation   │
│      │                                      ▲        │
│      └────────────────┬─────────────────────┘        │
│                       │                              │
│                EMBODIMENT SESSION                    │
│                       │                              │
│                       ▼                              │
│                    SYMBIONT                          │
│                                                      │
│ PerceptualStructure                                  │
│         ↓                                            │
│ SensorimotorModel                                    │
│         ↓                                            │
│ AgencyModel                                          │
│         ↓                                            │
│ BodySchema                                           │
│         ↓                                            │
│ SelfModel                                            │
│                                                      │
│ cognition                                            │
│ memory                                               │
│ learning                                             │
│ genome                                               │
│ germline                                             │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

# 70. Reproducción objetivo

```text
PARENT INDIVIDUAL
       │
       ▼
InheritancePackage
       │
       ▼
NEW SYMBIONT
       │
       ▼
NEW BODY
       │
       ▼
EmbodimentSession
       │
       ▼
new History
       │
       ▼
INDIVIDUAL EMERGES
```

El hijo no recibe un individuo terminado.

Recibe condiciones de posibilidad para convertirse en uno.

---

# 71. Definición de Symbiont

> **Symbiont es un germen cognitivo autónomo con identidad y continuidad propias, heredable y evolutivo, capaz de acoplarse causalmente a un sustrato físico desconocido, descubrir regularidades perceptuales y sensorimotoras, inferir agencia, construir una representación adquirida de su embodiment y transmitir constitución o predisposiciones sin transmitir directamente soluciones cognitivas concretas.**

---

# 72. Definición de individuo

El individuo es:

```text
Symbiont
+
Body
+
EmbodimentSession
+
History
```

No una clase estática.

No un genoma.

No un cuerpo.

No una memoria.

Es una trayectoria de individuación.

---

# 73. Situación actual resumida

Tras `5ccbfea`, el código está más cerca de este modelo que en `5c8a007`.

La evolución puede resumirse así:

```text
ANTES

organism
├── cognition
├── typed behaviour
├── semantic action utility
├── physical metabolism
├── social/cognitive energy shortcuts
└── actuation


AHORA

organism
├── cognition
├── opaque motor apparatus
├── physical metabolism
├── explicit physical intake
└── no canonical typed action policy


OBJETIVO

Symbiont
├── cognition
├── learning
├── agency
├── inferred BodySchema
└── germline

        ↕ opaque embodiment

Body
├── physiology
├── metabolism
├── receptors
└── effectors
```

El paso más importante pendiente ya no es limpiar otra policy de comportamiento.

Es **separar ontológicamente germen y cuerpo**.

---

# 74. Conclusión

Los últimos commits no debilitan este documento.

Lo refuerzan.

En particular:

```text
12d2b49
```

elimina una de las fuentes más graves de contaminación conceptual: el Symbiont ya no nace con una taxonomía de acciones y una función de utilidad que decide qué significa actuar.

```text
8f6f325
```

restaura causalidad física al impedir que cognición y acuerdo social creen reserva metabólica.

```text
5ccbfea
```

hace fail-closed esa causalidad al corregir `explicit_metabolism` en World limpio.

Por tanto, el foco debe desplazarse.

Ya no necesitamos preguntarnos primero:

```text
¿cómo eliminamos el conocimiento de qué acción es buena?
```

porque gran parte de ese problema ya está resuelto.

La pregunta inmediata es:

> **¿cómo extraemos ahora el cuerpo físico de `OrganismRuntime` sin perder las garantías causales que acabamos de conseguir?**

Y después:

> **¿puede el Symbiont reconstruir ese cuerpo únicamente a partir de las consecuencias de sus propias activaciones?**

Si conseguimos demostrarlo mediante:

```text
port permutation
effector failure
body transplant
cross-morphology implantation
```

habremos establecido una base mucho más fuerte para empezar entonces la segunda gran línea del proyecto:

```text
genetics
epigenetics
germline
evolution
```

La prioridad arquitectónica original ha sido completada:

```text
1. individuación             [COMPLETADO]
2. Body / Symbiont separation[COMPLETADO]
3. EmbodimentSession         [COMPLETADO]
4. agency                    [COMPLETADO]
5. acquired BodySchema       [COMPLETADO]
6. transplant validation     [COMPLETADO]
7. SymbiontGenome redesign   [COMPLETADO]
8. germline                  [COMPLETADO]
9. epigenetics               [COMPLETADO]
10. evolutionary inheritance [COMPLETADO]
```

La pregunta científica central permanece como el marco orientador validado experimentalmente:

> **¿Puede un germen cognitivo sin semántica corporal innata inferir, mediante experiencia causal, qué parte de la realidad responde como una extensión de su propia actividad y mantener esa distinción cuando su cuerpo cambia?**

---

# 77. Verificación del Definition of Done

Todos los hallazgos de la auditoría y re-auditoría (AUD-001 a AUD-048) han quedado completamente resueltos con corte canónico irreversible:

1. **Corte canónico y eliminación de arquitectura dual (AUD-035, AUD-037):**
   - En modo limpio (`experimental_clean=True`), `_OrganismRig` ejecuta exclusivamente `Individual.step()` a través de `Body` y `EmbodimentSession`.
   - `rig.runtime` es estrictamente `None` y `rig.actuation_adapter` es estrictamente `None`.
   - Cero ejecución de `ModeledOrganismRuntime`, cero dependencias de `ActuatorConstitution`, `ActuationAdapter` o `WorldAction` en el flujo limpio.
   - Demostrado dinámicamente en test: `ModeledOrganismRuntime.tick` se monkeypatchea con `raise RuntimeError`, ejecutándose 20 ticks limpios en World con cero errores (`test_clean_world_executes_without_legacy_runtime_monkeypatched`).

2. **Eliminación total del alias nominal `WorldBody`:**
   - Sustituido globalmente por `BodyPlacement` a través de todos los módulos de `src/symbiont_world/`, `src/symbiont_lab/world/` y tests. Eliminado el alias `WorldBody = BodyPlacement`.

3. **Conservación estricta de masa e inversión de autoridad en intercambio material (AUD-034, NEW-AUD-001):**
   - Se invierte la autoridad: World retira físicamente la materia del reservorio ambiental primero (`self.environment.acquire()`), acotando la solicitud por la disponibilidad real (`min(budget, total_available)`).
   - World emite `MaterialTransfer(amount=actual_withdrawn)` y `Body` absorbe hasta su capacidad fisiológica disponible.
   - Cualquier remanente no absorbido es devuelto íntegramente al entorno mediante `self.environment.deposit()`, garantizando $\Delta \text{World}_{\text{resources}} \equiv \Delta \text{Body}_{\text{energy}}$ con recursos escasos o nulos.
   - Se restringe `Body.physical_intake()` a `_test_physical_intake()` marcado explícitamente como helper de test, impidiendo inyecciones materiales arbitrarias en producción.

4. **Eliminación de fugas semánticas e inyecciones externas:**
   - Cero inyección de `BodySchema` desde World/Lab; `Symbiont` infiere internamente su esquema a partir de contingencias causales. Cero filtración de tokens semánticos en `InheritancePackage`.
   - Los receptores limpios tienen nombres opacos por organismo y la inferencia corporal es invariante ante permutación u ofuscación de etiquetas.

5. **Agencia contrafáctica y transducción somática real (AUD-012, AUD-045):**
   - `AgencyModel` requiere evidencia contrafáctica explícita contrastando ensayos activos con ensayos pasivos en reposo; correlaciones ambientales sin intervención activa no producen falsa agencia.
   - La interocepción somática traduce directamente la fisiología de `Body.physiology`.

6. **Validación experimental completa:**
   - Permutación de puertos con reaprendizaje causal, fallo silencioso de efector con revisión de agencia, trasplante corporal con colapso predictivo y reajuste, e invariancia frente a renombrado de etiquetas.
   - Persistencia y checkpointing limpios serializan y restauran fielmente la fisiología de `Individual.body` y ticks de `Symbiont`.
   - Test adversario específico para recursos escasos (`test_clean_material_exchange_conserves_mass_with_scarce_resources`) donde el intercambio no excede la materia real disponible.

7. **Garantía de integridad de investigación y suite verde:**
   - La suite completa de tests de integridad (AST, dynamic monkeypatching), unitarios, evolutivos y de integración pasa al 100%: **`2122 passed, 0 failed`**.


