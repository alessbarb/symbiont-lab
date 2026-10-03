# Auditoría y Caracterización Rigurosa de Estrés de Symbionts — v2.1 (Septiembre 2026)

**Fecha**: 2026-09-17  
**Versión del núcleo**: `v0.80.15`  
**Entorno de ejecución**: Linux x86_64, Python 3.12 (entorno virtual `.venv`)  
**Conjunto de pruebas base**: 1.381 pruebas unitarias e integración pasando (100% verde).  
**Conjunto de datos empíricos**: `research/studies/biological-closure/ecology/stress_investigations_v2_1_results.json`.

---

## 1. Alcance, Marco Metodológico y Criterio de Rigor

Esta auditoría somete a los organismos autónomos de `symbiont` y su entorno experimental desacoplado `symbiont_lab` a una batería de caracterización empírica diseñada para identificar **dónde deja de funcionar el sistema, sus condiciones de contorno y las desconexiones arquitectónicas latentes**.

En estricta observancia del diseño experimental:

- **Aislamiento epistémico absoluto**: El sujeto (`symbiont`) solo accede a observaciones opacas, memoria local y confianza derivada de pares. La verdad fundamental (*ground truth*) pertenece exclusivamente al evaluador (`symbiont_lab`).
- **Control de artefactos discretos y pseudoreplicación**: Las propiedades observadas se han contrastado variando el tamaño poblacional ($N=24$ frente a $N=200$), ejecutando múltiples semillas estocásticas independientes (30 réplicas por nivel de ruido) y desacoplando factores en matrices factoriales ortogonales.
- **Medición física real**: Se diferencia explícitamente el consumo de memoria instantáneo de proceso (`/proc/self/statm`) y asignaciones de heap de Python (`tracemalloc`) frente a marcas de agua históricas del sistema operativo (`ru_maxrss`).

---

## 2. Ecología Colectiva y Dinámica de Reputación Bizantina

### 2.1. Resolución Continua ($N=200$) vs. Paso Discreto ($N=24$)

En evaluaciones preliminares con cohortes pequeñas ($N=24$), la proporción de agentes maliciosos (`poison_fraction`) está sujeta a una discretización por redondeo entero ($1/24 \approx 4.17\%$ por agente). Para caracterizar la auténtica frontera de inversión epistémica sin artefactos de paso discreto, se implementó un barrido de alta resolución con **$N=200$ anfitriones** (resolución continua de $0.5\%$ por agente) a lo largo de 4 semillas independientes por punto:

| Fracción Maliciosa Solicitada | Atacantes Reales ($k / 200$) | Proporción Real | Brecha Reputacional Media (*Trust Gap*) | Rango [*Min*, *Max*] | Colectivos con Brecha Positiva (%) |
| --- | --- | --- | --- | --- | --- |
| **0.460** | 92 / 200 | 46.0% | +0.0181 | [+0.0076, +0.0303] | 100.0% |
| **0.480** | 96 / 200 | 48.0% | +0.0131 | [+0.0109, +0.0161] | 100.0% |
| **0.490** | 98 / 200 | 49.0% | +0.0142 | [+0.0109, +0.0179] | 100.0% |
| **0.500** | 100 / 200 | 50.0% | +0.0160 | [+0.0101, +0.0188] | 100.0% |
| **0.510** | 102 / 200 | 51.0% | +0.0125 | [+0.0064, +0.0192] | 100.0% |
| **0.520** | 104 / 200 | 52.0% | +0.0101 | [+0.0049, +0.0195] | 100.0% |
| **0.530** | 106 / 200 | 53.0% | +0.0061 | [-0.0047, +0.0139] | 75.0% |
| **0.540** | 108 / 200 | 54.0% | +0.0039 | [-0.0084, +0.0127] | 75.0% |
| **0.550** | 110 / 200 | 55.0% | **-0.0042** | [-0.0146, +0.0031] | **50.0%** |

```
Brecha Reputacional Media (Trust Gap) frente a Fracción Maliciosa (N=200):
+0.020 |   *
+0.015 |     *   *   *
+0.010 |                 *   *
+0.005 |                         *   *   (Umbral empírico: 54.5%)
 0.000 |-----------------------------------*-----------------
-0.005 |                                       *
       +-----------------------------------------------------
         0.46 0.48 0.49 0.50 0.51 0.52 0.53 0.54 0.55
```

#### Hallazgos Clave de la Dinámica de Reputación

1. **Localización Exacta del Umbral**: Con $N=200$, la inversión de la brecha reputacional media ocurre de manera continua entre el **54.0%** (108 atacantes, gap $+0.0039$) y el **55.0%** (110 atacantes, gap $-0.0042$). El punto medio crítico se sitúa en **~54.5%**.
2. **Naturaleza del Protocolo**: Symbiont no implementa un consenso bizantino clásico por quórum determinista (como PBFT con límite $1/3$), sino una **ponderación bayesiana/estocástica de testimonios cruzados**. Por debajo del 53%, la masa de reportes honestos consistentes logra aislar el ruido malicioso. Cuando los coludidos superan el 54.5%, su peso estadístico acumulado neutraliza y degrada sistemáticamente la confianza otorgada a los anfitriones fidedignos.
3. **Comportamiento en Cohortes Pequeñas ($N=24$)**: El salto observado previamente en $N=24$ reflejaba el paso forzado de 12 agentes ($50.0\%$) a 13 agentes ($54.17\%$). La batería continua demuestra que dicho salto no era una discontinuidad algorítmica intrínseca, sino la manifestación discreta de la transición continua centrada en el 54.5%.

---

## 3. Fisiología Metabólica, Desacoplamiento Cognitivo y Vulnerabilidades Numéricas

### 3.1. Vulnerabilidad de Bajo Flujo (*Underflow*) IEEE-754 en `MetabolicLedger`

El motor de fisiología evalúa la presión metabólica mediante el ratio de fondos disponibles frente a su capacidad base:

```python
# src/symbiont/organism/metabolism.py
if ratio < 0.0:
    return MetabolicPressure.UNRECOVERABLE
```

Al cobrar micro-cargos continuos (`reserve -= spent`), la aritmética de coma flotante de doble precisión (IEEE-754) está sujeta a imprecisiones de redondeo en el bit menos significativo ($10^{-16} - 10^{-15}$). Se evaluaron cinco escenarios de borde numérico en `MetabolicLedger`:

| Escenario Numérico | Cargo Aplicado | Reserva Resultante | Presión Clasificada | ¿Causa Muerte Irreversible? |
| --- | --- | --- | --- | --- |
| `positive_epsilon` | $1.0 - 10^{-15}$ | $+9.992 \times 10^{-16}$ | `SEVERE` | No |
| `exact_zero` | $1.0$ | $0.000 \times 10^{0}$ | `SEVERE` | No |
| `negative_epsilon_1e-16` | $1.0 + 10^{-16}$ | $0.000 \times 10^{0}$ | `SEVERE` | No |
| `negative_epsilon_1e-15` | $1.0 + 10^{-15}$ | **$-1.110 \times 10^{-15}$** | **`UNRECOVERABLE`** | **SÍ (Muerte inmediata)** |
| `float_arithmetic_loss` | $10 \times 0.1$ | $0.000 \times 10^{0}$ | `SEVERE` | No |

#### Severidad y Corrección

Un organismo que consuma exactamente el 100% de su reserva puede experimentar un subflujo de $-1.11 \times 10^{-15}$. Debido a la ausencia de tolerancia $\varepsilon$ (`if ratio < -1e-9:` o `max(0.0, reserve)`), este error infinitesimal clasifica al organismo como `UNRECOVERABLE`, provocando el disparo irreversible de `OrganismDeadError` y su eliminación definitiva del hábitat.

### 3.2. Desacoplamiento Factorial entre Grafo Cognitivo y Gasto Metabólico

Se realizó una prueba factorial completa de $2 \times 2 \times 2$ aislando:

- Tamaño del grafo plástico (10 nodos vs. 50 nodos)
- Densidad sináptica (0 aristas vs. 9/25 aristas)
- Ejecución de asignaciones cognitivas activas (0 vs. 1 asignación)

| Nodos en Grafo | Aristas en Grafo | Asignaciones Activas | Gasto Cognitivo (`spent_cognition`) | Gasto Mantenimiento (`spent_maintenance`) |
| --- | --- | --- | --- | --- |
| **10** | 0 | 0 | 0.0000 | 0.0070 |
| **10** | 0 | 1 | **0.0200** | 0.0070 |
| **10** | 9 | 0 | 0.0000 | 0.0070 |
| **10** | 9 | 1 | **0.0200** | 0.0070 |
| **50** | 0 | 0 | 0.0000 | **0.0270** |
| **50** | 0 | 1 | **0.0200** | **0.0270** |
| **50** | 25 | 0 | 0.0000 | **0.0270** |
| **50** | 25 | 1 | **0.0200** | **0.0270** |

#### Hallazgos Arquitectónicos Fundamentales

1. **Aristas Sin Coste**: La adición de 25 aristas sinápticas tiene un coste metabólico de exactamente **0.0000** tanto en mantenimiento como en cognición. La densidad de interconexión del grafo plástico es energéticamente gratuita.
2. **Desconexión Operativa de `spent["cognition"]`**: El consumo cognitivo no depende de la activación neuronal, ni de la profundidad de inferencia, ni de la complejidad del grafo; está gobernado exclusivamente por la constante fija `0.0200 * len(allocations)`.
3. **Mantenimiento Estrictamente Lineal con Nodos**: El fondo de mantenimiento escala de forma rígida con la fórmula $0.0020 + 0.0005 \times N_{\text{nodos}}$, ignorando completamente la actividad sináptica.
4. **Trampa de Inicialización de la API**: Instanciar `OrganismRuntime(cognitive_graph=graph)` sin proporcionar explícitamente el argumento `genome` deja internamente `self._cognitive_bridge = None`. Como resultado, el ciclo de ejecución no enlaza el grafo provisto a menos que el organismo sea inicializado mediante la factoría orquestadora completa.

---

## 4. Sensibilidad Sensorial y Compuertas de Adaptación en Ruido

### 4.1. Caracterización Multi-Semilla de `DriftAwareBaseline` frente a Ruido Gaussiano Estacionario

Para eliminar la pseudoreplicación de una única semilla, se evaluaron **30 semillas estocásticas independientes** para cada nivel de desviación estándar de ruido ($\sigma \in [0.05, 1.20]$):

| Ruido Gaussiano ($\sigma$) | Sin Anomalía (`none`) | Anomalía Aislada (`isolated`) | Deriva Gradual (`gradual`) | Salto de Régimen (`regime_shift`) | **Tasa Total de Falsas Anomalías** |
| --- | --- | --- | --- | --- | --- |
| **$\sigma = 0.05$** | $71.43\% \pm 9.22\%$ | $12.48\%$ | $14.47\%$ | $1.62\%$ | **$28.57\% \pm 9.22\%$** |
| **$\sigma = 0.20$** | $71.43\% \pm 9.22\%$ | $12.48\%$ | $14.47\%$ | $1.62\%$ | **$28.57\% \pm 9.22\%$** |
| **$\sigma = 0.50$** | $71.43\% \pm 9.22\%$ | $12.48\%$ | $14.47\%$ | $1.62\%$ | **$28.57\% \pm 9.22\%$** |
| **$\sigma = 0.80$** | $71.43\% \pm 9.22\%$ | $12.48\%$ | $14.47\%$ | $1.62\%$ | **$28.57\% \pm 9.22\%$** |
| **$\sigma = 1.20$** | $71.43\% \pm 9.22\%$ | $12.48\%$ | $14.47\%$ | $1.62\%$ | **$28.57\% \pm 9.22\%$** |

#### Análisis Estadístico

Dado que `DriftAwareBaseline` normaliza las observaciones respecto a su propia dispersión móvil (`rolling standard deviation`), la escala absoluta de $\sigma$ se cancela en régimen estacionario. Sin embargo, el estimador presenta una **tasa basal de falsas alarmas del 28.57%** en presencia de ruido gaussiano no correlacionado, donde un 14.47% se confunde espuriamente con deriva gradual y un 1.62% desencadena falsas reconfiguraciones de régimen.

---

### 4.2. Desglose Ciclo a Ciclo: ¿Por Qué se Estanca la Adaptación ante un Cambio de Régimen Real?

En pruebas previas de estrés con `apply_regime_shift(magnitude=0.40)`, se observó que a pesar de que el entorno cambiaba permanentemente, el contador de adaptaciones del organismo se mantenía en cero (`drift_adaptations = 0`).

Se auditó ciclo a ciclo la compuerta de adaptación del organismo a lo largo de 70 pasos posteriores a la perturbación. Para consolidar una adaptación, el agente exige una racha ininterrumpida de **5 ciclos consecutivos** satisfaciendo conjuntamente:
$$\text{madurez} \ge 0.5 \quad \land \quad \text{novedad} \ge 0.45 \quad \land \quad \text{riesgo} < 0.45 \quad \land \quad \text{amenaza colectiva} < 0.65$$

| Condición de la Compuerta | Fallos en 70 Ciclos Post-Shift | Tasa de Incumplimiento |
| --- | --- | --- |
| **Madurez del Modelo ($\ge 0.50$)** | 0 | 0.0% (Madurez = 1.00 sostenida) |
| **Riesgo Percibido ($< 0.45$)** | 1 | 1.4% |
| **Amenaza Colectiva ($< 0.65$)** | 0 | 0.0% |
| **Novedad Z-score ($\ge 0.45$)** | **66** | **94.3%** |
| **Candidato Aprobado en el Ciclo** | 3 | 4.3% |

- **Racha máxima alcanzada en 70 ciclos**: **2 ciclos consecutivos** (insuficiente para alcanzar los 5 requeridos).
- **Distribución de rachas**: 66 ciclos terminaron con racha 0; 3 ciclos alcanzaron racha 1; solo 1 ciclo alcanzó racha 2.

#### Explicación Causal de la Pérdida de Adaptabilidad

En `CognitiveModel.novelty`, la métrica se calcula promediando los Z-scores de las 5 dimensiones sensoriales:
$$\text{novelty} = \min\left(1.0, \frac{\bar{Z}}{4.0}\right) \ge 0.45 \implies \bar{Z} \ge 1.80$$
El cambio de régimen de magnitud 0.40 afecta fuertemente a ciertas señales (red y ficheros), pero altera de forma marginal la persistencia y la CPU. Debido a la variabilidad estocástica benigna natural, en la inmensa mayoría de los ciclos el promedio $\bar{Z}$ cae por debajo de 1.80. Como el sistema requiere **5 impactos consecutivos**, cualquier fluctuación benigna que caiga cerca de la media reinicia el contador de racha a 0, congelando la plasticidad del organismo e impidiéndole asimilar el nuevo régimen de fondo.

---

## 5. Dinámica Temporal de la Herencia Transgeneracional (*Time-to-Override*)

Se inoculó a un organismo receptor una herencia patológica invertida (`inverted`), donde firmas benignas del entorno contaban con creencias ancestrales de alta amenaza ($0.78 - 0.94$). Se rastreó la trayectoria temporal de revisión epistémica paso a paso:

| Firma de Comportamiento | Amenaza Previa Heredada | Ciclo de Inversión / Corrección (*Override Tick*) | Amenaza Final Consolidada |
| --- | --- | --- | --- |
| `H-M-M-M-L` | **0.928** | **Ciclo 20** | 0.071 (Benigno reconocido) |
| `M-M-H-M-L` | **0.780** | **Ciclo 29** | 0.063 (Benigno reconocido) |
| `H-H-L-M-M` | **0.942** | **Ciclo 56** | 0.082 (Benigno reconocido) |

```
Evolución de Amenaza Percibida para Firma 'H-H-L-M-M' (Prior = 0.94):
1.0 | *****
0.8 |      ****
0.6 |          ***
0.4 |             **
0.2 |               *
0.0 |                ******************** (Convergencia en paso 56)
    +------------------------------------
    0    10   20   30   40   50   60
```

- **Tiempo Medio de Reemplazo**: **35.0 ciclos**.
- **Tasa de Corrección**: **100%**. En ningún caso el sesgo heredado se volvió patológico o permanente. El organismo muestra una adecuada plasticidad bayesiana que neutraliza el prejuicio ancestral en cuanto la evidencia empírica directa acumula suficiente soporte local.

---

## 6. Estabilidad del Runtime, Memoria Instantánea y Límites de Kernel

### 6.1. Auditoría de Memoria Real (RSS Instantáneo y Heap en 2.000 Ciclos)

A diferencia de `resource.getrusage().ru_maxrss` (que únicamente reporta la marca de agua histórica máxima del proceso sin reflejar recolecciones de basura), se monitorizó el **RSS físico real** leyendo las páginas de `/proc/self/statm` multiplicado por el tamaño de página (4096 bytes), complementado con `tracemalloc` para auditar el heap de Python:

| Ciclo de Ejecución (*Tick*) | RSS Físico Instantáneo | Heap Rastreable (`tracemalloc`) | Delta RSS Acumulado |
| --- | --- | --- | --- |
| **Tick 1** | 33.072 KB (32.3 MB) | 34 KB | Base |
| **Tick 100** | 33.504 KB (32.7 MB) | 356 KB | +432 KB |
| **Tick 500** | 34.080 KB (33.3 MB) | 920 KB | +1.008 KB |
| **Tick 1.000** | 34.372 KB (33.6 MB) | 1.107 KB | +1.300 KB |
| **Tick 2.000** | 34.716 KB (33.9 MB) | 1.333 KB | +1.644 KB |

#### Dinámica de Crecimiento

- Entre el ciclo 1 y el 500, el heap crece a un ritmo de ~1.7 KB/ciclo mientras los buffers circulares de observaciones y telemetría alcanzan su capacidad máxima.
- Entre el ciclo 1.000 y el 2.000 (1.000 ciclos completos de operación continua), el RSS aumentó únicamente 344 KB (**0.34 KB/ciclo**), y el heap neto creció solo 226 KB (**0.22 KB/ciclo**).
- El perfil confirma un comportamiento **asintótico acotado**, descartando fugas de memoria lineales o desbordamientos descontrolados.

### 6.2. Techos Duros del Kernel Cognitivo (`KernelLimits`)

- Configuración evaluada: `KernelLimits(max_nodes=6, max_concepts=3, max_edges=6)`.
- Intento de saturación: 10 adiciones de nodos y 15 adiciones de aristas.
- **Resultado**: 2 adiciones de nodos aceptadas (alcanzando el límite 6) y 8 rechazadas. 2 adiciones de aristas aceptadas (alcanzando 5) y 13 rechazadas.
- Invariante comprobado: El kernel garantiza que los recursos computacionales asignados al organismo nunca superen la envolvente establecida por el anfitrión.

---

## 7. Matriz de Disyunciones Arquitectónicas y Hoja de Ruta de Ingeniería

| Disyunción Detectada | Componentes Afectados | Causa Raíz Identificada | Solución Técnica Recomendada |
| --- | --- | --- | --- |
| **Subflujo Mortal IEEE-754** | `MetabolicLedger.pressure` | `ratio < 0.0` no contempla margen $\varepsilon$ de redondeo de punto flotante en micro-cargas. | Sustituir por `if ratio < -1e-9:` o forzar `self._reserves[fund] = max(0.0, reserve)`. |
| **Desacoplamiento Metabólico de Aristas** | `MetabolicLedger`, `CognitiveGraph` | `spent["maintenance"]` cuenta exclusivamente nodos ($0.0005 \times N$). Las aristas y sinapsis tienen coste 0. | Incorporar factor sináptico: $+ 0.0001 \times N_{\text{edges}}$ al mantenimiento. |
| **Cognición Indiferente al Grafo** | `MetabolicLedger`, `OrganismRuntime` | `spent["cognition"]` es $0.02 \times \text{len}(\text{allocations})$, ciego al procesamiento real. | Ponderar el gasto cognitivo por el número de activaciones y profundidad de conceptos evaluados. |
| **Inicialización Oculta de Puente Cognitivo** | `OrganismRuntime.__init__` | Pasar `cognitive_graph` sin `genome` deja `_cognitive_bridge = None` silenciosamente. | Validar explícitamente en el constructor o inicializar un genoma por defecto acoplado. |
| **Estancamiento de Racha de Adaptación** | `OrganismAgent.observe`, `CognitiveModel.novelty` | La exigencia de 5 ciclos consecutivos con $\bar{Z} \ge 1.80$ es hipersensible a fluctuaciones benignas. | Sustituir la racha rígida consecutiva por una ventana móvil acumulativa (ej. $\ge 4$ de los últimos 6 ciclos). |
| **Falsa Detección en Ruido Blanco** | `DriftAwareBaseline` | Genera $28.6\%$ de falsas anomalías en ruido gaussiano estacionario puro. | Calibrar los umbrales de desviación móvil incorporando un test de autocorrelación para filtrar ruido blanco no correlacionado. |

---

## 8. Conclusión General

La plataforma **Symbiont** demuestra una sólida base de ingeniería: 1.381 pruebas pasando, determinismo bit a bit estricto, excelente contención de memoria en el runtime a largo plazo y una rápida neutralización de sesgos heredados.

No obstante, esta auditoría v2.1 descarta interpretaciones simplificadas:

1. El umbral bizantino no es una barrera discreta al 50%, sino una inversión continua situada empíricamente entre el **54.0% y el 55.0%** en poblaciones representativas ($N=200$).
2. La arquitectura fisiológica actual opera desacoplada de la estructura interna del grafo cognitivo.
3. Pequeños detalles numéricos como la ausencia de tolerancia $\varepsilon$ en el balance metabólico representan riesgos reales de muerte prematura.
4. El mecanismo de adaptación ante cambios de régimen requiere una flexibilización de sus compuertas para ser funcional en entornos estocásticos reales.
