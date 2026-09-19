# Symbiont World v4 — Living World & Scientific Observatory

**Estado:** diseño y especificación técnica para v4.
**Ámbito:** `symbiont_world` + `symbiont_lab.world` + World Scientific Observatory.
**Principio rector:** el mundo evoluciona de una cuadrícula tabular a un territorio ecológico dinámico y continuo con organismos visualmente vivos e interactivos, sin perder el rigor científico, la atomicidad del tick ni la disciplina de lectura exclusiva (read-only) del observador.

---

# 1. Objetivo: De "rejilla técnica" a "microscopio del ecosistema"

Symbiont World v3 consolidó la atomicidad (`failed_tick(s) == s`), la persistencia atómica con verificación SHA-256 (`future(continuous) == future(restore_from_disk)`), el journal causal y el render sin flicker.

En v4, la ambición sube un orden de magnitud:

1. **El mundo adquiere relieve y geografía viva**: el territorio no es un array uniforme de celdas; posee relieve lógico (elevación), permeabilidad (corredores y barreras), gradientes de humedad y temperatura, fertilidad, perturbaciones locales y rastros dejados por los organismos (huellas que decaen).
2. **Movimiento espacial explícito**: los organismos pueden desplazarse endógenamente entre celdas transitables según permeabilidad y ocupación, dejando estelas ecológicas.
3. **Organismos con morfología derivada del fenotipo**: el aspecto visual de cada individuo no es un skin artificial, sino una expresión directa de su edad, generación, sensores desarrollados, vigor fisiológico y conexiones cognitivas.
4. **Interpolación de movimiento y Ghost Mode**: el desplazamiento entre ticks se anima suavemente; podemos activar el modo fantasma (*ghost mode*) para rastrear la trayectoria histórica completa de un individuo.
5. **Eventos espaciales sobre el terreno**: los hechos confirmados del journal (`RESOURCE_ACQUIRED`, `PHYSIOLOGICAL_DAMAGE`, `REPAIR`, `DEATH`, `MOVE`) generan efectos visuales temporales directamente en las coordenadas donde ocurrieron.
6. **Exploración epistemológica comparada**:
   - *World Reality*: ground truth del aparato científico.
   - *Organism Perception*: lo que el individuo realmente captó a través de sus transductores (con niebla de percepción).
   - *Organism Self & Mind*: hipótesis internas y grafo cognitivo (sensores → conceptos → predictores).
7. **Vista Poblacional y Escala Virtualizada**: pantalla dedicada con clustering fenotípico, grafo de linajes y motor de renderizado basado en Canvas capaz de escalar fluidamente a mundos grandes con pan/zoom semántico.

---

# 2. Geografía Dinámica: CellPhenotype

Cada celda en el aparato evaluador posee propiedades topográficas y dinámicas completas. Estas propiedades son **ground truth del aparato científico**, nunca semántica entregada al organismo.

```text
CellPhenotype
├── q, r
├── region_id
├── elevation              # [0.0, 1.0] relieve: valles (0.1), mesetas (0.5), picos (0.9)
├── permeability           # [0.0, 1.0] transitabilidad: corredores abiertos (1.0) vs barreras rocosas (0.2)
├── moisture               # [0.0, 1.0] gradiente de humedad: árido (0.1) vs humedal (0.9)
├── temperature            # [0.0, 1.0] gradiente térmico: frío boreal (0.1) vs cálido (0.9)
├── fertility              # [0.0, 1.0] modula la velocidad de renovación de recursos
├── disturbance            # [0.0, 1.0] perturbación ambiental reciente (decae temporalmente)
├── traces                 # [0.0, 1.0] intensidad acumulada de paso de organismos (decae temporalmente)
├── resource_reservoirs    # cantidades actuales y capacidades
├── hazard_exposures       # exposición real ponderada por densidad local
└── field_values           # gradientes y oscilaciones globales
```

### Emergencia ecológica resultante

- **Valles y corredores**: celdas con alta permeabilidad y humedad donde el tránsito y la recolección son más eficientes.
- **Barreras y cumbres**: celdas con alta elevación y baja permeabilidad que actúan como fronteras ecológicas naturales.
- **Zonas refugio**: áreas con bajo nivel de peligro (`hazard`) y fertilidad moderada.
- **Huellas y rutas**: las celdas por donde transitan los organismos acumulan un rastro (`traces`) que decae con el tiempo, permitiendo visualizar rutas migratorias y áreas sobreexplotadas.

---

# 3. Resolución de Movimiento y Acciones Espaciales

El movimiento utiliza la infraestructura determinista de `symbiont_world.movement.resolve_movement`:

1. Los organismos pueden manifestar una intención de movimiento (dirección 0..5 o reposo).
2. Se evalúa la permeabilidad de la celda destino: celdas con permeabilidad extremadamente baja actúan como barreras infranqueables.
3. Las intenciones simultáneas sobre la misma celda se resuelven con tie-break determinista con RNG con namespace.
4. Cuando un organismo se desplaza con éxito:
   - Se emite y confirma un evento causal `MOVE` con la posición previa y la nueva.
   - La celda previa incrementa su nivel de `traces` (rastro).
   - El cuerpo en `WorldState.bodies` actualiza `occupied_cell`.

---

# 4. Motor de Renderizado: Canvas Virtualizado y Multicapa

Para permitir tanto mundos de prueba (8×8) como mundos medianos (64×64) y grandes (128×128+), el observador implementa una arquitectura multicapa:

```text
┌──────────────────────────────────────────────────────────┐
│                 OBSERVATORY RENDER ENGINE                │
├──────────────────────────────────────────────────────────┤
│ Layer 0: Terrain Canvas (biomas, relieve, niebla)        │
│ Layer 1: Trails & Heatmap Canvas (huellas, ocupación)    │
│ Layer 2: Entity & Movement Layer (glifos interpolados)   │
│ Layer 3: Spatial Events Layer (partículas de eventos)    │
│ Layer 4: Interactive Selection & Tooltip Overlay         │
└──────────────────────────────────────────────────────────┘
```

- **Soporte de Pan & Zoom**: navegación fluida mediante arrastre de ratón y rueda de zoom.
- **Virtualización**: en mundos grandes, sólo se rasterizan las celdas contenidas en el viewport activo.
- **Modos de Visualización**:
  - *Reality*: vista del mundo físico con relieve y biomas.
  - *Perception*: vista desde los sentidos del organismo seleccionado (las áreas no percibidas muestran niebla de exploración).
  - *Heatmap*: mapa de calor histórico acumulado de ocupación.

---

# 5. Organismos Vivos y Morfología Fenotípica

El glifo del organismo se construye a partir de su estado biológico real:

- **Cuerpo base**: radio proporcional a la edad/desarrollo madurativo.
- **Anillo de integridad**: circunferencia exterior con colorimetría continua (esmeralda → ámbar → carmesí) y patrón de trazo según estado vital (`active`, `stressed`, `dormant`, `agonizing`, `dead`).
- **Núcleo metabólico**: núcleo central cuyo brillo y diámetro indican el nivel de reserva energética.
- **Estructuras sensoriales**: apéndices/antenas radiales cuyo número y longitud corresponden a los sensores descubiertos o especializados.
- **Pulso de actividad**: ondas expansivas breves ante ingesta de recursos, daño o reparación.
- **Cadáver persistente**: al morir, permanece un marcador esquelético atenuado que se desvanece tras varios ticks.

---

# 6. Dimensión Temporal, Ghost Mode y Eventos Espaciales

1. **Timeline Navegable**: scrubber horizontal para retroceder en la memoria de ticks registrados.
2. **Ghost Mode**: al hacer clic en un organismo, se despliega su estela histórica (`t-k → ... → t-1 → t`) con degradado de opacidad, permitiendo comprender sus decisiones de exploración.
3. **Eventos Flotantes en el Mapa**:
   - `RESOURCE_ACQUIRED`: anillo cian expansivo con indicación de cantidad.
   - `PHYSIOLOGICAL_DAMAGE`: destello rojo angular en la posición del impacto.
   - `REPAIR`: pulso verde suave.
   - `MOVE`: vector de desplazamiento con flecha translúcida.
   - Al hacer clic en un evento espacial, se abre su detalle causal en el inspector.

---

# 7. Cuatro Perspectivas Epistemológicas + Mente + Linaje

El inspector lateral profundiza en la estructura epistemológica:

- **[ Reality ]**: Relieve, permeabilidad, humedad, temperatura, fertilidad, peligros locales reales y recursos de la celda.
- **[ Phenotype ]**: Morfología, estado fisiológico, reservas, presión, edad, generación y última acción.
- **[ Perception ]**: Señales filtradas que realmente llegaron a los receptores, con opción de activar la vista subjetiva del mundo.
- **[ Self ]**: Creencias internas y autopercepción sin trampas evaluator-side.
- **[ Mind ]**: Grafo de cognición activa mostrando la cadena `Sensación → Concepto → Predicción`.
- **[ Lineage & History ]**: Cronología de eventos en los que ha participado el organismo.

---

# 8. Pantalla de Población

Una vista alternativa al mapa geográfico que ofrece análisis ecológico agregado:

- **Clustering Fenotípico (Scatter 2D)**: distribución de individuos según dimensiones fisiológicas (integridad vs reserva vs plasticidad cognitiva).
- **Árbol de Linajes**: grafo genealógico de fundadores y descendientes.
- **Métricas Macroecológicas**: índices de diversidad, estrés global y longevidad promedio.

---

# 9. Plan de Implementación

- **Fase P0 — Relieve Lógico, Terreno Dinámico y Movimiento Espacial**:
  - Definición de `CellPhenotype` y `DynamicGeography` en `symbiont_lab.world.terrain`.
  - Integración de intenciones de movimiento y resolución espacial en `PopulationGenesisRuntime`.
  - Depósito y decaimiento de huellas (`traces`) y eventos espaciales `MOVE`.
  - Tests unitarios de movimiento, permeabilidad y conservación espacial.
- **Fase P1 — Motor de Renderizado Canvas con Pan & Zoom**:
  - Sustitución de la cuadrícula rígida por Canvas reactivo de alto rendimiento.
  - Implementación de control de cámara (zoom, pan, viewport virtualizado).
  - Capas de relieve (sombreado de colinas/valles), humedad, biomas y huellas.
- **Fase P2 — Glifos Vivos, Morfología Fenotípica e Interpolación**:
  - Glifos con antenas sensoriales, anillo de integridad y pulso de actividad.
  - Interpolación continua de posiciones entre ticks para animación fluida.
  - Marcadores de muerte persistente y estelas de desplazamiento.
- **Fase P3 — Navegación Temporal, Ghost Mode y Eventos en el Mapa**:
  - Scrubber de histórico temporal con playback.
  - Modo fantasma para visualizar la trayectoria pasada de un individuo.
  - Visualización espacial de eventos del journal directamente sobre el terreno.
- **Fase P4 — Perspectiva Subjetiva (Perception Overlay) y Vista Poblacional**:
  - Toggle de niebla de percepción (mundo visto a través del organismo).
  - Pantalla de análisis poblacional (clusters 2D de fenotipo, distribución de estados).
  - Grafo cognitivo en el inspector (`Mind`).
- **Verificación Completa y Push**:
  - Ejecución de la suite completa de pruebas (`pytest`).
  - Verificación de determinismo y lectura estricta.
  - `git push origin main`.
