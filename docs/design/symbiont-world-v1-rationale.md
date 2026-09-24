Sí. He cruzado la idea con el estado actual de vuestro repositorio y con antecedentes de Artificial Life, evolución digital, mundos multiagente y open-ended evolution. La conclusión es bastante clara:

> **No necesitamos inventar “otro simulador”. Necesitamos construir el hábitat natural permanente del Symbiont.**

Y además el momento es bueno porque el organismo ya tiene casi todos los componentes que antes faltaban: fisiología, muerte, reproducción, herencia, cultura, comunicación opaca, ecología básica, sensores adaptativos y un runtime integrado. Lo que falta es proporcionarles **espacio, causalidad ambiental y continuidad ecológica real**.

## 1. Qué nos enseñan los experimentos anteriores

Tierra y Avida demuestran que puede existir evolución digital genuina cuando hay replicación, variación heredable y competencia, sin necesidad de asignar una puntuación humana explícita a cada individuo. Avida, además, convirtió esto en una plataforma experimental controlable y medible. ([MIT Press Direct][1])

Polyworld añadió algo fundamental para nosotros: organismos situados espacialmente, percepción, movimiento, recursos, reproducción y aprendizaje durante la vida mediante redes neuronales. Es probablemente el antepasado conceptual más cercano a lo que queremos. ([PubMed Central (PMC)][2])

Neural MMO mostró la importancia de mundos persistentes, muchos individuos simultáneos, recursos distribuidos y formación de nichos. Pero continúa siendo principalmente un entorno de reinforcement learning diseñado alrededor de observaciones, acciones y recompensa. ([OpenAI][3])

Melting Pot demuestra que el **entorno social** también debe considerarse parte del problema: cooperación, competencia, reciprocidad o confianza pueden aparecer dependiendo de cómo los individuos se afectan mutuamente. Su objetivo, sin embargo, es evaluación de agentes ya entrenados, no evolución autónoma de organismos. ([Google DeepMind][4])

POET aporta una lección distinta: la diversidad de entornos puede generar stepping stones que una única trayectoria no descubriría. Pero yo **no permitiría todavía que el propio mundo evolucione sus leyes**, porque organismo y entorno cambiando simultáneamente destruirían nuestra capacidad de atribuir causalidad. ([arXiv][5])

La investigación reciente sobre open-ended evolution insiste además en algo que debemos tomar muy en serio: **que algo corra indefinidamente no significa que sea open-ended**. Hay que medir innovación adaptativa, diversidad, complejidad, formación de nichos y estructura filogenética. ([MIT Press Direct][6])

Y trabajos recientes continúan encontrando que **espacio, ecología y presión selectiva dejan señales distintas en las filogenias**. Eso refuerza que la geometría del mundo no debería ser meramente decorativa. ([MIT Press Direct][7])

La cultura también merece tratarse como un proceso evolutivo diferente del genético. La literatura reciente sobre open-ended cultural evolution encaja especialmente bien con la línea que ya tiene Symbiont de procedencia cultural, composición y transmisión entre organismos. ([MIT Press Direct][8])

---

# 2. Lo que ya tenemos

Aquí está la parte interesante. Revisando `main`, **Symbiont World no partiría de cero**.

El `README.md` actual ya declara como implementados:

```text
digital physiology
reproduction + heredity
bounded digital ecology
social development
Private SLM
culture
opaque symbol grounding
structured communication
Integrated Habitat Runtime
Passive Observatory
```

Y `research/STATUS.md` confirma algo todavía más importante: `IntegratedHabitatRuntime` ya consiguió integrar población, fisiología, aprendizaje, Private SLM, cultura, grounding, comunicación, checkpoint/replay y telemetría dentro del mismo hábitat.

Además tenemos:

```text
src/symbiont/core/social/ecology.py
    SharedHabitat

src/symbiont/core/lineage/heredity.py
    HeritableGenome

src/symbiont/core/lineage/inheritance.py
    genética
    epigenética
    cultura

src/symbiont/core/social/interactions.py
    EcologicalResourcePool
```

Y ahora el nuevo sistema sensorial ya diferencia correctamente:

```text
WORLD
 ↓
ObservableSource
 ↓
RawSample
 ↓
Sensor
 ↓
Percept
 ↓
SENSE
 ↓
CognitiveGraph
```

Eso es exactamente la frontera que necesitamos para un mundo artificial.

El mundo puede saber:

```text
resource.type = 17
position = (43, 91)
toxicity = .61
energy = 8.4
```

mientras el organismo recibe únicamente algo equivalente a:

```text
signal.4ab1
signal.981c
signal.a20f
```

a través de sus sensores.

Ese desacoplamiento es extraordinariamente importante.

---

# 3. Mi propuesta: `Symbiont World`

Yo lo definiría así:

> **Symbiont World es un entorno digital espacial, persistente, causal, finito y no semántico desde la perspectiva de sus habitantes, capaz de mantener indefinidamente una ecología de Symbionts y producir un registro reproducible completo de su historia.**

No es un juego.

No tiene misiones.

No tiene score.

No tiene fitness explícito.

No tiene NPCs diseñados para enseñarles cosas.

No tiene recompensas.

La única «recompensa» existente consiste en **las consecuencias físicas que las acciones producen sobre el organismo**.

---

# 4. Arquitectura

Lo separaría en cuatro dominios estrictos:

```text
┌────────────────────────────────────────────┐
│              SYMBIONT WORLD                │
│                                            │
│  espacio · tiempo · campos · recursos      │
│  causalidad · clima · objetos · ecología   │
└──────────────────┬─────────────────────────┘
                   │
             interacción física
                   │
                   ▼
┌────────────────────────────────────────────┐
│                 SYMBIONT                   │
│                                            │
│ sensores · cuerpo · cognición · memoria    │
│ fisiología · cultura · comunicación        │
└──────────────────┬─────────────────────────┘
                   │
              evidence only
                   ▼
┌────────────────────────────────────────────┐
│               WORLD JOURNAL                │
│                                            │
│ event log · checkpoints · genealogy        │
│ observer truth · replay                    │
└──────────────────┬─────────────────────────┘
                   │
                  READ
                   ▼
┌────────────────────────────────────────────┐
│               OBSERVATORY                  │
│                                            │
│ World · Phenotype · Self · Mind · History  │
└────────────────────────────────────────────┘
```

La propiedad más importante sería:

```text
Observatory → World
```

**no existe.**

Ni siquiera como API deshabilitada.

---

# 5. Espacio: empezaría discreto, no continuo

Aunque visualmente podamos mostrar algo orgánico, para v1 elegiría una geometría **2D discreta**.

Concretamente:

> **malla hexagonal finita.**

Cada celda tiene seis vecinas.

¿Por qué hexagonal?

Porque evita parte de la anisotropía de una cuadrícula:

```text
cuadrícula
  ↑
← ● →
  ↓

hexagonal

  ↖ ↑ ↗
   \|/
  ← ● →
   /|\
  ↙ ↓ ↘
```

y sigue siendo determinista, barato y extremadamente fácil de guardar/reproducir.

Ejemplo:

```text
World 256 × 256 hex cells
≈ 65.000 posiciones
```

No todos los organismos pueden observar todo el mundo.

Cada uno ocupa:

```text
position = cell_id
orientation = 0..5
```

pero **el organismo no debería recibir necesariamente esos conceptos explícitos**.

---

# 6. El mundo tendría campos, no «cosas» semánticas

Este punto me parece central.

No llenaría el mundo inicialmente de:

```text
árbol
agua
montaña
comida
veneno
```

Eso introduce demasiada ontología humana.

Lo construiría a partir de **campos y recursos**.

Por ejemplo:

```text
field.01
field.02
field.03
field.04
```

Nosotros sabemos que representan algo como:

```text
temperature
radiation
humidity
medium resistance
```

pero el Symbiont no.

Una celda podría tener:

```text
cell.001728

field.01 = 0.42
field.02 = 0.13
field.03 = 0.88

resource.01 = 2.31
resource.07 = 0.00

hazard.03 = 0.21
```

Y estos valores evolucionan mediante reglas físicas propias.

---

# 7. Necesitamos causalidad real

No basta con ruido ambiental.

El mundo necesita **regularidades descubribles**.

Ejemplo:

```text
field.A ↑
   ↓ después de ~20 ticks
resource.B ↑

field.C + alta exposición
   ↓
sensor health ↓

resource.D intake
   ↓
metabolic reserve ↑

resource.E intake
   ↓
integrity ↓
```

Ninguna de estas relaciones se revela.

Un Symbiont debería poder descubrir:

```text
A predice B

D suele preceder recuperación

E parece perjudicarme
```

sin conocer:

```text
temperatura
alimento
toxina
```

Aquí es donde empieza realmente el grounding.

---

# 8. Recursos

El actual `SharedHabitat` ya tiene:

```text
resources
renewal_rate
acquisition_cost
physiological_usefulness
information_content
```

Yo conservaría ese modelo conceptual, pero lo espacializaría.

Pasaríamos de:

```text
SharedHabitat
     │
resource pool
```

a:

```text
World
 │
 ├── region A
 │     ├ resource.01
 │     └ resource.02
 │
 ├── region B
 │     └ resource.03
 │
 └── region C
       ├ resource.01
       └ resource.04
```

Cada recurso tendría propiedades reales:

```text
quantity
renewal
diffusion
decay
mobility
acquisition cost
physiological effect
information signature
```

Y, muy importante:

### no existiría `food`

Existiría:

```text
resource.72ac
```

que casualmente provoca:

```text
+reserve
```

al ser metabolizado.

---

# 9. No todo recurso debería ser bueno

Esto es necesario para que pueda aparecer aprendizaje significativo.

Por ejemplo:

```text
R1 → +reserva, barato
R2 → +reserva, muy caro
R3 → +reserva ahora, daño lento después
R4 → neutro
R5 → ligeramente tóxico
R6 → útil sólo combinado con R2
```

Así aparecen problemas reales de inferencia.

Especialmente interesante:

```text
R3
 ↓
beneficio inmediato
 ↓
daño retardado
```

Un organismo puramente reactivo preferirá R3.

Uno capaz de aprender dependencias temporales quizá deje de hacerlo.

Eso sería una prueba maravillosa para el sistema predictivo actual.

---

# 10. Ciclos

Necesitamos temporalidad ambiental:

```text
día / noche
estaciones
ciclos lentos
pulsos
eventos irregulares
```

Pero nunca llamarlos así en el organismo.

Algo podría seguir:

$$
F(t)=a+b\sin(\omega t+\phi)
$$

Otro proceso:

```text
resource spawning
  condicionada por field.3
```

Otro:

```text
hazard burst
p ≈ .001 por tick
```

Y otro podría ser casi estable.

Entonces podemos descubrir si un Symbiont distingue:

```text
ruido
periodicidad
tendencia
causalidad
evento
```

---

# 11. Movimiento

El primer repertorio motor debería ser extremadamente pequeño.

Por ejemplo seis canales direccionales + reposo:

```text
actuator.01
actuator.02
actuator.03
actuator.04
actuator.05
actuator.06
actuator.07
```

Observatory sabe:

```text
01 = forward-left
02 = forward
...
07 = stay
```

pero esa semántica **no entra en cognition**.

Moverse cuesta recursos.

Y diferentes superficies pueden alterar ese coste.

Así los organismos podrían terminar desarrollando comportamientos parecidos a:

```text
rutas
territorialidad
migración
forrajeo
refugio
```

sin que esos conceptos estén codificados.

---

# 12. Percepción

Aquí el nuevo trabajo sensorial encaja como un guante.

El mundo ofrecería `ObservableSource`s locales.

Ejemplo:

```text
field local
resource density local
gradient
contact
nearby organism emissions
internal state
```

Pero un organismo no recibe todos necesariamente.

El pipeline sigue siendo:

```text
world field
   ↓
ObservableSource
   ↓
signal.x
   ↓
Sensor
   ↓
Percept
   ↓
Cognition
```

Y gracias a la arquitectura sensorial nueva dos Symbionts podrían mirar **exactamente el mismo mundo** con aparatos perceptivos distintos.

Esto abre una pregunta científica preciosa:

> ¿Dos organismos que habitan exactamente el mismo universo terminan construyendo mundos subjetivos distintos?

---

# 13. Importante: no implementaría «visión»

Todavía no.

La arquitectura actual sigue trabajando fundamentalmente con señales escalares y modalidades bounded. `research/STATUS.md` lo reconoce explícitamente: la geometría vectorial y las modalidades sensoriales verdaderamente emergentes siguen abiertas.

Por eso no cometería el error de meter inmediatamente:

```text
camera image → pixels → vision
```

Primero:

```text
local scalar fields
gradients
contact
short temporal patterns
multi-source relationships
```

Cuando emerjan `ReceptorProgram` y geometría vectorial, entonces podremos incorporar modalidades espacialmente mucho más ricas.

---

# 14. Acción e intervención

Tampoco daría acciones como:

```text
eat()
attack()
mate()
trade()
```

Polyworld sí puede hacer esto porque investiga otra cosa. ([PubMed Central (PMC)][2])

Para Symbiont intentaría utilizar **operaciones físicas más primitivas**.

Por ejemplo:

```text
move
sample
acquire
release
emit
contact
rest
```

El significado emergente de estas combinaciones podría acabar siendo:

```text
forrajear
huir
seguir
proteger
intercambiar
señalizar
cooperar
```

pero esas son etiquetas nuestras.

---

# 15. Interacción entre Symbionts

Los individuos son también parte del mundo.

Un organismo cercano produce:

```text
presence field
motion perturbation
resource competition
opaque emissions
contact effects
```

No debería aparecer mágicamente:

```text
entity.type = symbiont
```

en cognition.

El organismo tendría que descubrir que ciertas fuentes ambientales:

* se desplazan,
* responden,
* consumen,
* producen mensajes,
* tienen regularidades distintas a los objetos pasivos.

Con suficiente desarrollo podríamos probar:

> **¿descubre la categoría «otro agente»?**

Eso sería mucho más interesante que proporcionársela.

---

# 16. Comunicación

Aquí ya tenemos una ventaja enorme.

El repo actual tiene comunicación estructurada opaca:

```text
opaque symbols
variable-length sequences
silence
cost
grounding
```

En Symbiont World la comunicación debería volverse **espacial**.

Una emisión podría tener:

```text
range
attenuation
duration
cost
channel
```

Ejemplo:

```text
Symbiont A
   ↓ sequence.912
   ))))))))

B recibe 0.82
C recibe 0.31
D no recibe
```

Eso cambia radicalmente la ecología de la comunicación.

Puede aparecer:

```text
proximidad
agrupamiento
territorialidad
señalización local
dialectos
```

sin introducir una red social global.

---

# 17. Nada de broadcast global

Esto me parece esencial.

Si todos pueden hablar instantáneamente con todos:

```text
population → global chat
```

destruimos casi toda la importancia del espacio.

Debe ser:

```text
locality
+
range
+
cost
+
noise
```

La topología social debe emerger en buena parte de **quién puede encontrarse físicamente con quién**.

---

# 18. Fisiología

El mundo tiene que alimentar directamente la fisiología existente.

Actualmente Symbiont ya modela:

```text
intake
assimilation
maintenance
activity
learning
memory
degradation
dormancy
death
```

Por tanto World no debería crear otro sistema de HP o energía.

Debería suministrar **entradas al metabolismo existente**.

Ejemplo:

```text
World resource
      ↓
acquisition
      ↓
existing MetabolicLedger
      ↓
reserve
      ↓
learning / maintenance / movement
```

Esto evita duplicar conceptos.

---

# 19. Muerte

La muerte debe convertirse en un evento ecológico real.

Actualmente ya es irreversible.

En World:

```text
Symbiont dies
   ↓
position becomes free
   ↓
resources allocated to it released
   ↓
possibly local environmental residue
   ↓
lineage remains in history
```

Yo incluso añadiría más adelante una opción:

```text
dead biomass → reusable resources
```

pero **no en v1**, porque añade otra capa causal innecesaria.

---

# 20. Reproducción

La arquitectura actual usa `habitat-authorized birth`.

La conservaría.

El Symbiont puede estar:

```text
READY
```

pero World decide si físicamente hay:

```text
space
resources
capacity
```

para materializar la cría.

Eso no significa selección artificial.

El mundo únicamente aplica sus leyes.

La descendencia aparece cerca del progenitor:

```text
parent cell
   ↓
available neighboring cell
   ↓
offspring
```

No la teletransportaría aleatoriamente.

Así la genealogía adquiere también **estructura geográfica**.

---

# 21. Herencia

Mantendría exactamente la distinción que ya existe:

```text
GENÉTICA
    ↓
capacity / parameters

EPIGENÉTICA
    ↓
bounded priors

CULTURA
    ↓
post-birth social transmission

FENOTIPO APRENDIDO
    ✕ no germinal
```

Esto es científicamente muy limpio.

Y abre experimentos fantásticos:

```text
genética solamente
vs
genética + epigenética
vs
genética + cultura
```

---

# 22. Mundo permanente

Aquí aparece tu idea original.

El mundo tendría un:

```text
world_id
```

que sobrevive a los individuos.

Por ejemplo:

```text
world.0001
created: 2026-10-01

tick 0
...
tick 18,726,291
...
```

Los individuos nacen y mueren dentro.

```text
World 1
│
├─ Generation 0
│   ├ A
│   ├ B
│   └ C
│
├─ Generation 1
│   ├ A.1
│   ├ B.1
│   └ B.2
│
├─ ...
│
└─ Generation 184
```

El mundo no se reinicia porque un organismo muera.

---

# 23. Tiempo

Separaría tres conceptos:

```text
wall time
simulation time
biological ticks
```

El mundo puede ejecutarse:

```text
1×
10×
100×
máxima velocidad
```

sin cambiar su causalidad.

Esto es fundamental para investigación.

Un experimento de «un año» no debería necesitar necesariamente un año humano.

---

# 24. Determinismo

Cada run tendría:

```text
world seed
world config fingerprint
kernel version
initial founders
```

Por tanto:

```text
same state
+ same events
+ same RNG state
=
same future
```

Esto es imprescindible para poder repetir historias interesantes.

Si vemos:

> «En generación 47 aparece una conducta extraña».

debemos poder regresar al tick anterior y reproducirla exactamente.

---

# 25. Event sourcing

Yo haría que **World fuera event-sourced desde el primer día**.

No depender sólo de snapshots.

Ejemplo:

```text
tick 8712991

WORLD_FIELD_CHANGED
RESOURCE_RENEWED
ORGANISM_MOVED
RESOURCE_ACQUIRED
ORGANISM_EMITTED
ORGANISM_CONTACT
BIRTH
DEATH
GENOME_MUTATION
CULTURAL_TRANSMISSION
```

Cada evento incluiría:

```text
event_id
world_id
tick
actor
position
payload
causal_parent_ids
```

Los snapshots sirven para rendimiento.

El event log constituye la historia.

---

# 26. Esto es importantísimo: causal provenance

Añadiría explícitamente:

```text
causal_parent_ids
```

cuando sea posible.

Por ejemplo:

```text
RESOURCE_ACQUIRED #7812
        ↓
METABOLIC_RESERVE_CHANGED #7813
        ↓
REPRODUCTION_READY #7820
        ↓
BIRTH #7901
```

Así Observatory podría reconstruir cadenas causales sin «explicárselas» al organismo.

---

# 27. Observatory tendría seis escalas

Yo evolucionaría el Observatory actual hacia:

```text
WORLD
REGION
POPULATION
LINEAGE
INDIVIDUAL
MIND
```

### World

Veríamos:

```text
fields
resources
organism density
birth/death
migration
events
```

### Region

```text
resource history
population turnover
local lineages
communications
```

### Population

La vista que ya existe se ampliaría:

```text
ecology
knowledge
activity
dissent
genealogy
culture
```

### Lineage

```text
genome mutations
births
extinctions
phenotypic divergence
```

### Individual

La anatomía funcional que ya existe.

### Mind

```text
signals
sensors
concepts
predictions
beliefs
self-model
private model
```

---

# 28. Y mantendría cuatro capas epistemológicas

En lugar de sólo Reality / Phenotype / Self, formalizaría:

```text
1. WORLD TRUTH
   lo que existe

2. PHENOTYPE
   lo que el organismo hace/es

3. PERCEPT
   lo que recibe

4. SELF / MODEL
   lo que cree
```

Esto nos permite distinguir:

```text
resource realmente presente
        ↓
señal disponible
        ↓
sensor la detecta o no
        ↓
concepto aprendido
        ↓
predicción
        ↓
acción
```

La discrepancia entre esas capas es precisamente la información científica interesante.

---

# 29. World Truth nunca entra en el Symbiont

Esto debe ser un invariante probado automáticamente:

```text
observer.*
world.semantic.*
ground_truth.*
```

no pueden entrar en:

```text
Sensor
CognitiveGraph
Private SLM
Culture
Decision
```

Propongo incluso tests de integridad de taint/provenance.

Algo como:

```text
assert no_ground_truth_reaches_organism()
```

en cada pipeline de datos.

---

# 30. Regiones y nichos

El mapa no debería ser homogéneo.

Diseñaría unas pocas regiones causales emergentes a partir de campos, no etiquetas.

Por ejemplo:

```text
        North
    high field A
    low resource X

West             East
resource Y       resource X
high hazard      periodic field B

        South
    stable conditions
    scarce resources
```

Nosotros lo visualizamos como biomas.

Para ellos sólo existen distribuciones de señales.

Esto permite que aparezcan:

```text
nichos
migraciones
especialización
```

La investigación reciente en ALife respalda precisamente la importancia de estructura espacial + ecología para la dinámica evolutiva. ([MIT Press Direct][7])

---

# 31. Un pequeño número de leyes, mucha combinatoria

No crearía cien tipos de recurso.

Para World v1:

```text
4 campos ambientales
4 recursos
2 hazards
1 canal social
1 canal comunicativo
```

es suficiente.

Porque queremos estudiar:

> qué emerge de las relaciones,

no impresionar visualmente.

Por ejemplo:

```text
Field A
Field B
Field C
Field D

Resource 1
Resource 2
Resource 3
Resource 4

Hazard 1
Hazard 2
```

Con relaciones cruzadas ya aparecen cientos de estados ecológicos posibles.

---

# 32. Evitaría explícitamente las quests

Nada como:

```text
collect 10 resources
reach location X
survive 100 ticks
communicate with B
```

Eso convertiría el experimento en RL disfrazado.

Nuestro criterio debe ser:

```text
mundo produce consecuencias
organismo produce comportamiento
observador mide
```

No:

```text
evaluador define éxito
 ↓
organismo optimiza éxito
```

---

# 33. Tampoco daría fitness

Especialmente:

```text
fitness = lifespan
```

sería peligroso.

Porque inmediatamente convertiríamos toda la dinámica en optimización de un número.

El fitness real se observa retrospectivamente:

```text
descendencia
persistencia del linaje
supervivencia
acceso a recursos
```

pero jamás se proporciona como señal.

Esto está muy alineado con el principio de digital evolution basado en selección resultante de la reproducción y competencia, no necesariamente de una función evaluadora explícita. ([MIT Press Direct][9])

---

# 34. Una distinción crucial: persistencia ≠ open-endedness

Podemos ejecutar:

```text
1.000.000.000 ticks
```

y no obtener nada interesante.

Podría aparecer un equilibrio:

```text
todos hacen A
todos comen B
todos se reproducen igual
```

Eso no sería evolución abierta.

Por eso necesitamos medir externamente:

```text
phenotypic diversity
genotypic diversity
behavioral diversity
niche count
innovation rate
lineage turnover
phylogenetic depth
adaptive novelty
cultural novelty
complexity
```

Las métricas MODES y la literatura de open-ended evolution son muy pertinentes aquí. ([MIT Press Direct][10])

---

# 35. Qué sería una «innovación»

No basta con:

```text
nuevo genome_id
```

Una mutación irrelevante no es innovación.

Yo distinguiría:

```text
genotypic novelty
phenotypic novelty
behavioral novelty
ecological novelty
cognitive novelty
cultural novelty
```

Por ejemplo:

> un linaje comienza a explotar un recurso que ningún antepasado explotaba.

Eso sí es interesante.

Otro:

> aparece una estrategia de obtención basada en anticipar un ciclo.

Otro:

> un mensaje reduce el coste de búsqueda del receptor.

Otro:

> surge un comportamiento transmitido culturalmente que no está genéticamente fijado.

---

# 36. Nicho emergente

No asignaría:

```text
species = forager
species = hunter
```

Observatory puede inferir posteriormente clusters.

Por ejemplo:

```text
Lineage 37

82% intake resource.3
habitat preference region.7
low movement
high communication
```

Nosotros podríamos denominarlo:

> «especialista de resource.3»

pero jamás el organismo.

---

# 37. Selección natural auténtica dentro del sistema

Si:

```text
Genotype A
→ aprende rápido
→ consume muchos recursos

Genotype B
→ aprende lento
→ mantenimiento barato
```

entonces según el mundo:

```text
abundancia → A prospera
escasez → B prospera
```

El mundo no decide quién gana.

Simplemente aplica:

```text
resource availability
+
cost
+
reproduction
+
death
```

Eso sí sería una ecología digital convincente.

---

# 38. Cambios ambientales

Después de estabilizar v1, introduciría cambios raros.

Por ejemplo:

```text
Day 0–10000
regime A

Day 10001
gradual transition

Day 15000+
regime B
```

Y observamos:

```text
plasticidad
migración
extinción
adaptación genética
adaptación cultural
```

El trabajo reciente sobre poblaciones sometidas a cambios disruptivos del hábitat muestra precisamente lo fértil que resulta esta clase de experimento. ([MIT Press Direct][11])

---

# 39. Cultura

Symbiont tiene ya una base que muchos experimentos anteriores no poseen.

Eso permite estudiar una pregunta brutal:

```text
Gen 1 descubre X
        ↓
Gen 2 recibe X socialmente
        ↓
Gen 3 modifica X
        ↓
Gen 4 nunca ha observado el fenómeno original
pero conserva comportamiento útil
```

Podemos diferenciar:

```text
evolución genética
ontogenia
evolución cultural
```

Eso conecta directamente con una de las fronteras contemporáneas de open-ended evolution. ([MIT Press Direct][8])

---

# 40. El mundo debe poder olvidar a sus habitantes, pero no su historia

Estado operativo:

```text
living population
```

puede estar bounded.

Historia:

```text
append-only archive
```

puede crecer externamente.

Así los Symbionts no cargan con toda la genealogía mundial.

Pero nosotros sí podemos reconstruirla.

---

# 41. Arquitectura software concreta

No crearía otro repo inmediatamente.

Dado que ahora mismo `symbiont`, `symbiont_lab` y Observatory están integrados dentro de `symbiont-lab`, empezaría como un nuevo paquete:

```text
src/
  symbiont/
      ...
  symbiont_world/
      __init__.py
      kernel.py
      clock.py
      topology.py
      fields.py
      resources.py
      hazards.py
      occupancy.py
      actions.py
      perception.py
      ecology.py
      lifecycle.py
      events.py
      checkpoint.py

  symbiont_lab/
      ...
      world/
          runner.py
          experiments.py
          metrics.py
          replay.py
```

Cuando madure, ya decidiríamos si merece convertirse en repositorio propio.

Eso evita crear fronteras prematuras.

---

# 42. La frontera sería ésta

```text
symbiont_world
     │
     │ WorldObservation
     ▼
symbiont
     │
     │ WorldAction
     ▼
symbiont_world
```

Dos contratos.

Nada más.

Por ejemplo:

```python
WorldObservation
```

contiene únicamente lo físicamente observable.

Y:

```python
WorldAction
```

contiene únicamente acciones permitidas.

Sin acceso del organismo a:

```text
World
Cell
Resource
Hazard
GroundTruth
```

---

# 43. Tick mundial

Definiría un orden determinista estricto:

```text
1  world scheduled processes
2  field propagation
3  resource renewal/decay
4  organism local observation surfaces
5  sensor sampling
6  organism cognition
7  organism decisions
8  resolve movements
9  resolve resource competition
10 resolve contacts
11 resolve communications
12 physiological consequences
13 births
14 deaths
15 cultural deliveries
16 telemetry
17 journal commit
18 checkpoint if due
```

El orden es crítico.

No puede depender del orden del diccionario o de scheduling de threads.

---

# 44. Acciones simultáneas

Si A y B quieren el mismo recurso:

mal diseño:

```text
A ejecuta primero
A gana
```

porque aparecería una ventaja accidental por orden de ejecución.

Correcto:

```text
intent A
intent B

     ↓

resolver simultáneamente

     ↓

allocation rule
```

La regla puede ser:

```text
proportional
lottery deterministic with RNG
cost-dependent
```

pero debe estar declarada y reproducible.

---

# 45. Paralelismo sin perder determinismo

Más adelante podemos dividir el mapa:

```text
region workers
```

pero los ticks deberían funcionar como barreras:

```text
compute intents
      ↓
synchronize
      ↓
resolve
      ↓
commit world
```

Así podemos escalar miles de Symbionts sin introducir nondeterminism.

---

# 46. Primer tamaño

No empezaría con 10.000 organismos.

World Alpha:

```text
64 × 64 cells
4.096 locations

8 founders

capacity: 64 organisms

4 fields
4 resource types
2 hazards

1 world tick / simulation tick
```

Es suficiente para comprobar casi toda la arquitectura.

---

# 47. Después World Beta

```text
256 × 256
65.536 cells

32 founders
capacity 512

regional ecology
reproduction
mutation
culture
communication
```

Y sólo después escalaría más.

---

# 48. Mundo «Genesis»

El primer mundo canónico podría llamarse:

```text
Genesis
```

No porque vayamos a afirmar que hay vida, sino porque sería el entorno cero de la población.

Yo congelaría su configuración:

```text
worlds/genesis/world.toml
```

Algo conceptualmente así:

```toml
[world]
schema = 1
width = 64
height = 64
topology = "hex"
seed = 101

[population]
founders = 8
capacity = 64

[time]
checkpoint_interval = 1024

[fields]
count = 4

[resources]
count = 4

[hazards]
count = 2

[communication]
local = true
attenuation = true
```

Los significados reales de cada field/resource se guardarían sólo en **apparatus metadata**.

No en el contrato organismo.

---

# 49. Genesis debería tener una ecología resoluble, pero no trivial

Algo así:

```text
R1
abundante
poco nutritivo
regeneración rápida

R2
escaso
muy nutritivo
regeneración lenta

R3
beneficioso a corto plazo
daño diferido

R4
beneficioso sólo bajo determinado estado fisiológico
```

Campos:

```text
F1
ciclo periódico

F2
gradiente espacial

F3
ruido autocorrelacionado

F4
evento raro
```

Hazards:

```text
H1
dependiente de F1

H2
dependiente de densidad poblacional
```

Ya con eso aparecen problemas realmente complejos.

---

# 50. El hazard dependiente de población me interesa especialmente

Por ejemplo:

```text
más población
      ↓
más contaminación / presión
      ↓
menor disponibilidad
```

Sin llamarlo contaminación.

Esto introduce **retroalimentación organismo → mundo**.

Ahí aparece verdadera ecología:

```text
organismos cambian entorno
      ↓
entorno cambia selección
      ↓
selección cambia organismos
```

Sin esa realimentación el mundo sería principalmente un escenario pasivo.

---

# 51. Ingeniería de nicho

Posteriormente permitiría acciones que modifiquen ligeramente el mundo:

```text
resource depletion
waste production
local field alteration
persistent emissions
```

Esto puede crear **niche construction**.

Un linaje podría modificar un territorio de forma que favorezca a sus descendientes.

No necesitamos llamarlo «construir un nido».

Simplemente emerge de la dinámica.

---

# 52. Lo que no haría en World v1

Dejaría expresamente fuera:

```text
3D
visión por píxeles
LLMs externos
física rígida
objetos manufacturables
herramientas
construcción compleja
depredación explícita
combate
sexualidad compleja
evolución de las leyes físicas
ecosistemas generados proceduralmente sin límite
```

Todo eso puede llegar.

Pero ahora taparía la pregunta científica principal.

---

# 53. La pregunta científica de World v1

La escribiría literalmente así:

> **¿Puede un Symbiont situado en un entorno espacial persistente y no semantizado aprender regularidades ambientales y modificar autónomamente su percepción y comportamiento de forma que produzca mejores consecuencias fisiológicas, sin recibir objetivos, etiquetas ni señales de recompensa del evaluador?**

Eso es testable.

---

# 54. Y World v2

Después:

> **¿Puede una población desarrollar nichos ecológicos diferentes bajo un mismo mundo?**

---

# 55. World v3

> **¿Puede la selección entre generaciones producir adaptación heredable a nichos sin fitness explícito?**

---

# 56. World v4

> **¿Puede información aprendida socialmente persistir y mejorar resultados después de desaparecer sus descubridores?**

---

# 57. World v5

> **¿Puede aparecer innovación cultural acumulativa que exceda lo descubierto individualmente?**

Eso sí nos lleva a la visión grande.

---

# 58. Qué mediría desde el primer día

El aparato científico debería registrar, sin suministrar estas métricas al organismo:

| Escala         | Variables                                                |
| -------------- | -------------------------------------------------------- |
| Mundo          | entropía espacial, recursos, estabilidad, perturbaciones |
| Ecología       | abundancia, nichos, competencia, ocupación               |
| Individuo      | edad, reservas, movimiento, intake                       |
| Cognición      | error predictivo, conceptos, utilidad causal             |
| Sensores       | especialización, lineage, selección                      |
| Genética       | mutaciones, diversidad, distancia                        |
| Filogenia      | profundidad, branching, extinciones                      |
| Social         | encuentros, reciprocidad, aislamiento                    |
| Comunicación   | información, grounding, estructura                       |
| Cultura        | persistencia, derivación, acumulación                    |
| Open-endedness | innovación, diversidad, complejidad                      |

No utilizaría ninguna métrica individual como «puntuación final».

---

# 59. Necesitamos controles muy duros

Cada experimento debería poder ejecutarse contra variantes:

```text
learning ON / OFF
sensor plasticity ON / OFF
culture ON / OFF
mutation ON / OFF
communication ON / OFF
spatiality ON / shuffled
resource scarcity ON / OFF
```

Entonces podremos responder:

> ¿apareció esto gracias al aprendizaje?

en vez de simplemente:

> «mira qué comportamiento tan curioso».

Esto es especialmente importante porque vuestro propio programa de investigación ya encontró ejemplos donde una capacidad existente podía parecer adaptación sin haber sido seleccionada autónomamente. Esa disciplina que aplicasteis a Sensory Plasticity debería mantenerse aquí también.

---

# 60. El Observatory debería permitir replay contrafactual

No cambiar el experimento original.

Pero desde un snapshot histórico crear:

```text
Branch A — replay original

Branch B — mismo estado,
           pero resource R3 desaparece

Branch C — misma población,
           comunicación desactivada
```

Estas ramas pertenecen a `symbiont_lab`.

Nunca al mundo original.

Eso sería potentísimo para inferir causalidad.

---

# 61. Muy importante: mundo vivo y experimento no son exactamente lo mismo

Tendríamos:

```text
WORLD
una entidad persistente
```

y:

```text
EXPERIMENT
una observación/control científico
sobre un mundo o réplica
```

El mundo puede vivir durante meses.

Los experimentos pueden tomar clones reproducibles de momentos de ese mundo.

Eso evita sacrificar la «historia viva» cada vez que queremos hacer ciencia.

---

# 62. Dos clases de mundos

Yo acabaría teniendo:

### Canonical worlds

Permanentes:

```text
Genesis
Gaia-1
...
```

No se manipulan arbitrariamente.

### Experimental worlds

Clonados:

```text
Genesis@tick-481720
 + perturbation X
```

para pruebas.

Así mantenemos tanto:

**natural history**

como:

**experimental science**.

Avida precisamente destacó por evolucionar desde la mera observación de evolución digital hacia experimentación rigurosamente controlada. ([Frontiers][12])

---

# 63. World y mundo real

Hay otro punto interesante.

El Symbiont original vive sobre un host real.

No creo que debamos abandonarlo.

Tendríamos dos ecologías:

```text
HOST ECOLOGY
mundo físico/computacional real

SYMBIONT WORLD
mundo digital controlado
```

Eso nos permite algo científicamente magnífico:

> probar la misma arquitectura cognitiva en un mundo perfectamente conocido y en un entorno real parcialmente desconocido.

World sería nuestro laboratorio controlado.

Host sería nuestro mundo externo.

---

# 64. No reemplazaría al `SharedHabitat`

Lo convertiría en un nivel inferior.

Ahora tenemos aproximadamente:

```text
SharedHabitat
```

Yo evolucionaría hacia:

```text
World
 └ Region
    └ Habitat/Resource Surface
```

`SharedHabitat` puede continuar siendo la unidad bounded de un recurso o una zona.

No necesitamos tirarlo.

---

# 65. Tampoco reemplazaría `IntegratedHabitatRuntime`

Lo ampliaría hacia:

```text
IntegratedWorldRuntime
```

conceptualmente:

```text
IntegratedHabitatRuntime
        ↓
one habitat/population runtime

IntegratedWorldRuntime
        ↓
many spatial habitats
+ topology
+ movement
+ fields
+ environment dynamics
```

Es una evolución natural de lo que ya tenéis.

---

# 66. Arquitectura final que propondría

```text
                      WORLD KERNEL
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
      Topology           Fields           Resources
         │                 │                  │
         └──────────────┬──┴───────┬──────────┘
                        │          Hazards
                        ▼
                 Interaction Layer
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
     Symbiont A                  Symbiont B
     sensors                     sensors
     cognition                   cognition
     physiology                  physiology
     culture                     culture
           │                         │
           └────────────┬────────────┘
                        ▼
                   World Commit
                        │
                append-only events
                        ▼
                  World Journal
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
         Observatory          Symbiont Lab
          passive             experiments
```

---

# 67. Mi decisión sobre la visualización

Para humanos haría que el mundo parezca mucho más rico de lo que realmente es.

Un campo podría representarse como:

```text
temperatura → color
resource density → vegetación
hazard → niebla
communication → ondas
```

aunque internamente sólo sean números.

Así Observatory puede ofrecer algo casi parecido a observar un terrario:

```text
             ◌ ◌
      ●→              ◉
           ≋≋≋
  ▲                     ●
          ◉ ◉
```

Los dibujos son nuestros.

La física sigue siendo abstracta.

Eso es perfecto.

---

# 68. Incluso podríamos tener «modo naturalista»

Sin métricas.

Sólo:

```text
mapa
organismos
nacimientos
muertes
movimientos
señales
```

Como mirar un hormiguero.

Y luego activar:

```text
Scientific overlay
```

y ver toda la verdad.

Creo que eso haría el proyecto muchísimo más tangible.

---

# 69. Cómo sabremos que empieza a ponerse interesante

Yo marcaría cinco niveles.

```text
LEVEL 0 — SURVIVAL

el organismo simplemente persiste
```

```text
LEVEL 1 — ADAPTATION

cambia conducta según experiencia
```

```text
LEVEL 2 — ECOLOGY

diferentes organismos ocupan nichos distintos
```

```text
LEVEL 3 — EVOLUTION

aparecen diferencias heredables seleccionadas
```

```text
LEVEL 4 — CULTURE

conocimiento persiste entre individuos
```

```text
LEVEL 5 — OPEN-ENDEDNESS

continúan apareciendo novedades adaptativas
que nosotros no habíamos enumerado
```

No afirmaría LEVEL 5 rápidamente.

La literatura actual es bastante clara en que ésa sigue siendo una de las dificultades fundamentales de Artificial Life. ([MIT Press Direct][13])

---

# 70. Cómo lo construiría realmente

Lo dividiría en **siete hitos**, pero sin desarrollar todo a la vez.

### W0 — contratos

Crear:

```text
symbiont_world
WorldState
WorldObservation
WorldAction
WorldEvent
WorldCheckpoint
```

sin ecología todavía.

### W1 — espacio

```text
hex topology
occupancy
movement
local observations
deterministic resolution
```

Un solo Symbiont.

### W2 — mundo causal

```text
fields
resources
hazards
cycles
spatial gradients
```

Un Symbiont viviendo permanentemente.

### W3 — metabolismo

Acoplar:

```text
resource acquisition
→ existing physiology
→ dormancy/death
```

Aquí ya existe verdaderamente «vivir en el mundo».

### W4 — población

```text
multiple organisms
local competition
birth
death
genealogy
```

### W5 — sociedad

```text
local encounter
communication range
culture
social consequences
```

### W6 — evolución longitudinal

```text
mutation
selection
lineages
niches
extinction
```

### W7 — open-ended research

No añadir features por añadir.

Medir:

```text
innovation
complexity
niche creation
cultural evolution
```

---

# 71. Primer experimento que ejecutaría

No 20 bichitos.

**Uno.**

```text
WORLD-0001
       │
       ▼
Symbiont A
```

Lo dejamos varios cientos de miles de ticks.

El mundo tiene:

```text
2 recursos beneficiosos
1 perjudicial retardado
2 ciclos ambientales
1 gradiente espacial
```

Y preguntamos solamente:

> ¿aprende A algo verdadero del mundo que mejore causalmente su trayectoria fisiológica?

Necesitamos demostrar eso antes de llenar el mapa.

---

# 72. Segundo experimento

Dos Symbionts idénticos:

```text
same genome
same starting cell
```

pero:

```text
different stochastic history
```

Queremos comprobar:

> ¿divergen realmente sus sensores, conceptos y conducta?

Esto es particularmente importante porque vuestra investigación sensorial reciente encontró convergencia completa bajo varias condiciones. `research/STATUS.md` registra, por ejemplo, `unique_phenotypes = 1` en el protocolo previo y 18/18 organismos convergiendo sobre la misma preferencia en otro protocolo.

World debería proporcionarnos entornos donde **la historia importe de verdad**.

---

# 73. Tercer experimento

8 fundadores.

Sin mutación.

Objetivo:

```text
ecological differentiation
without genetic variation
```

Si aparecen nichos, son ontogenéticos/sociales.

---

# 74. Cuarto

Activamos mutación.

Entonces podemos separar:

```text
plasticidad
vs
evolución
```

---

# 75. Quinto

Activamos cultura.

Entonces ya tenemos las tres temporalidades:

```text
APRENDIZAJE
durante una vida

EVOLUCIÓN
entre generaciones

CULTURA
entre individuos y generaciones
```

Ese es, para mí, **el verdadero gran experimento Symbiont**.

---

# Conclusión

Después de revisar tanto los antecedentes como el código actual, **sí construiría Symbiont World**.

Pero no como un proyecto lateral.

Lo considero el paso lógico posterior al organismo v1.

Hasta ahora hemos estado construyendo:

> **el bicho.**

World nos permitiría dejar de preguntarnos únicamente:

> «¿funciona este mecanismo cognitivo?»

y empezar a preguntar:

> **«¿qué hace este organismo cuando tiene una vida que vivir?»**

La arquitectura actual está sorprendentemente bien preparada para ello: la frontera `source → sensor → percept`, la fisiología, la muerte irreversible, la reproducción bounded, la herencia separada del fenotipo, la cultura con provenance y el Observatory pasivo son justamente los elementos que hacen viable hacerlo sin convertirlo en un videojuego de RL.

Mi diseño base, por tanto, sería:

> **Un universo 2D hexagonal, espacial y persistente; causal pero semánticamente opaco; con campos, recursos, riesgos y ciclos; interacción local, recursos finitos, coste físico de acción y percepción, reproducción y muerte reales dentro de la fisiología existente, comunicación espacial, herencia y cultura; completamente event-sourced, determinista y reproducible; observado desde fuera por Observatory sin ningún canal de retorno.**

Y haría algo más antes de implementar una sola línea: **escribiría `docs/design/symbiont-world.md` como especificación normativa**, junto con los invariantes epistemológicos, modelo de tick, contratos `WorldObservation/WorldAction`, esquema de eventos, Genesis v1 y los primeros experimentos preregistrados. Ahí sí tendríamos una base suficientemente rigurosa para empezar a construir el mundo de los bichitos.

[1]: https://direct.mit.edu/artl/article/10/2/191/2455/Avida-A-Software-Platform-for-Research-in?utm_source=chatgpt.com "Avida: A Software Platform for Research in Computational Evolutionary Biology | Artificial Life | MIT Press"
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC2801533/?utm_source=chatgpt.com "How evolution guides complexity - PMC"
[3]: https://openai.com/index/neural-mmo/?trk=public_profile_project-title&utm_source=chatgpt.com "Neural MMO: A massively multiagent game environment | OpenAI"
[4]: https://deepmind.google/blog/melting-pot-an-evaluation-suite-for-multi-agent-reinforcement-learning/?utm_source=chatgpt.com "Melting Pot: an evaluation suite for multi-agent reinforcement learning — Google DeepMind"
[5]: https://arxiv.org/abs/1901.01753?utm_source=chatgpt.com "Paired Open-Ended Trailblazer (POET): Endlessly Generating Increasingly Complex and Diverse Learning Environments and Their Solutions"
[6]: https://direct.mit.edu/artl/article/25/2/198/2923/Open-Endedness-for-the-Sake-of-Open-Endedness?utm_source=chatgpt.com "Open-Endedness for the Sake of Open-Endedness | Artificial Life | MIT Press"
[7]: https://direct.mit.edu/artl/article/31/2/129/130570/Ecology-Spatial-Structure-and-Selection-Pressure?utm_source=chatgpt.com "Ecology, Spatial Structure, and Selection Pressure Induce Strong Signatures in Phylogenetic Structure | Artificial Life | MIT Press"
[8]: https://direct.mit.edu/artl/article/30/3/417/116175/Evolved-Open-Endedness-in-Cultural-Evolution-A-New?utm_source=chatgpt.com "Evolved Open-Endedness in Cultural Evolution: A New Dimension in Open-Ended Evolution Research | Artificial Life | MIT Press"
[9]: https://direct.mit.edu/artl/article/26/2/274/93255/The-Surprising-Creativity-of-Digital-Evolution-A?utm_source=chatgpt.com "The Surprising Creativity of Digital Evolution: A Collection of Anecdotes from the Evolutionary Computation and Artificial Life Research Communities | Artificial Life | MIT Press"
[10]: https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox-Measurements-of-Open-Ended?utm_source=chatgpt.com "The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems | Artificial Life | MIT Press"
[11]: https://direct.mit.edu/artl/article/31/1/106/124849/Survival-and-Evolutionary-Adaptation-of?utm_source=chatgpt.com "Survival and Evolutionary Adaptation of Populations Under Disruptive Habitat Change: A Study With Darwinian Cellular Automata | Artificial Life | MIT Press"
[12]: https://www.frontiersin.org/journals/ecology-and-evolution/articles/10.3389/fevo.2021.739047/full?utm_source=chatgpt.com "Frontiers | Symbiosis in Digital Evolution: Past, Present, and Future"
[13]: https://direct.mit.edu/artl/article/30/1/1/120293/What-Is-Artificial-Life-Today-and-Where-Should-It?utm_source=chatgpt.com "What Is Artificial Life Today, and Where Should It Go? | Artificial Life | MIT Press"
