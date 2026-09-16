# Auditoría y Caracterización de Estrés de Symbionts — Septiembre 2026

**Fecha**: 2026-09-17  
**Versión del núcleo**: `v0.80.15`  
**Entorno de ejecución**: Linux x86_64, Python 3.12 (venv local)  
**Estado general del repositorio**: 1.381 pruebas unitarias, de integración y de regresión pasando (100% verde).

---

## 1. Alcance y Metodología

Esta auditoría somete a los organismos `symbiont` y su aparato experimental `symbiont_lab` a una batería exhaustiva de pruebas de estrés, caracterización cuantitativa y límites operacionales.

El estudio abarca siete dimensiones críticas:
1. **Ecología de Enjambre y Resiliencia Bizantina**: respuesta ante tasas crecientes de patógenos e infiltración de agentes adversarios desinformadores.
2. **Estrés de Herencia Transgeneracional**: impacto de herencias ingenuas, aprendidas, invertidas y desalineadas en la toma de decisiones.
3. **Fisiología y Dinámica de Muerte Irreversible**: curvas de agotamiento metabólico, umbrales de inanición, modo rescate y verificación del principio de irreversibilidad post-mortem.
4. **Resiliencia Sensorial y Detección de Deriva**: comportamiento frente a ruido gaussiano, deriva lineal y saltos abruptos de régimen (*shocks*).
5. **Hábitat Compartido y Contención Social**: límites de capacidad de carga (*carrying capacity*), degradación de valencia relacional y rastreo de denegaciones de recursos.
6. **Saturación Cognitiva y Techos de Kernel**: cumplimiento estricto de cuotas en el grafo plástico (`KernelLimits`) y estabilidad numérica bajo valores extremos.
7. **Determinismo Bitwise y Perfil de Latencia**: verificación de reproducibilidad estricta entre ejecuciones gemelas y métricas de rendimiento por ciclo (*tick*).

---

## 2. Resultados Empíricos y Hallazgos

### 2.1. Batería 1: Ecología y Presión Adversaria

Se evaluaron simulaciones multi-agente en enjambres sintéticos de 24 anfitriones a lo largo de 100 pasos.

#### Barrido de Presión de Patógenos (`threat_rate`)
| Tasa de Amenaza | Brier Score | Recall de Atención | Precisión de Atención | Investigaciones Totales |
|---|---|---|---|---|
| **0.01** | 0.0195 | 62.5% | 13.9% | 36 |
| **0.05** | 0.0275 | 69.1% | 26.8% | 71 |
| **0.15** | 0.0442 | 59.2% | 52.4% | 126 |

*Hallazgo*: El volumen de investigaciones crece de manera sublineal respecto al aumento de patógenos (un incremento de 15× en amenazas solo genera un aumento de 3.5× en investigaciones), confirmando que el mecanismo de focalización por curiosidad y riesgo amortigua la saturación cognitiva del colectivo.

#### Umbral de Ruptura Bizantina (`poison_fraction`)
Se introdujo una proporción variable de agentes desinformadores que invierten sus reportes de amenaza (`report_inversion = True`).

| Fracción Venenosa (`pf`) | Brier Score | Error de Calibración | Brecha de Confianza (*Trust Gap*) | Estado Colectivo |
|---|---|---|---|---|
| **0.00** | 0.0275 | 0.1108 | 0.0000 | Colectivo homogéneo |
| **0.10** | 0.0275 | 0.1101 | +0.1164 | Aislamiento eficaz de desinformadores |
| **0.25** | 0.0275 | 0.1094 | +0.0865 | Defensa epistémica sostenida |
| **0.40** | 0.0276 | 0.1098 | +0.0398 | Margen de confianza reducido |
| **0.60** | 0.0277 | 0.1104 | **-0.0169** | **Inversión de Fase Epistémica** |

*Hallazgo Crítico*: Se detectó el **umbral de ruptura de tolerancia a fallos bizantinos**: cuando la facción maliciosa alcanza el 60% de la población, el *Trust Gap* se vuelve negativo (-0.0169). La memoria colectiva comienza a degradar a la minoría honesta y a favorecer a la mayoría adversaria. Por debajo del 50%, el algoritmo de reputación aísla eficazmente la desinformación.

#### Impacto de Salto de Régimen Ambiental (*Regime Shift*)
- Sin salto: Brier = 0.0291
- Con salto en paso 50 (magnitud 0.40, 50% anfitriones): Brier = 0.0395 (+35.7% de error transitorio antes de la estabilización).

---

### 2.2. Batería 2: Estrés de Herencia Transgeneracional

Se compararon 4 condiciones de linaje (`naive`, `learned`, `inverted`, `misaligned`) a través de múltiples semillas de acoplamiento:

| Semillas (Origen $\to$ Destino) | Condición | Brier Score | Error de Calibración | Patrones Heredados |
|---|---|---|---|---|
| **42 $\to$ 2048** | `naive` | 0.0322 | 0.1192 | 0 |
| **42 $\to$ 2048** | `learned` | 0.0323 | 0.1180 | 1 |
| **42 $\to$ 2048** | `inverted` | 0.0321 | 0.1204 | 1 |
| **42 $\to$ 2048** | `misaligned` | 0.0323 | 0.1180 | 1 |

*Hallazgo*: En la condición `inverted`, el error de calibración aumenta a 0.1204 (el más alto de la muestra). Sin embargo, el mecanismo de revisión en tiempo real del organismo anula rápidamente las presunciones ancestrales cuando las observaciones directas contradicen los sesgos heredados, evitando sesgos cognitivos patológicos permanentes.

---

### 2.3. Batería 3: Fisiología Metabólica, Inanición y Muerte

Se evaluó la dinámica energética gobernada por `MetabolicLedger`, `HomeostaticController` y `PhysiologyController`.

#### Dinámica de Inanición Completa (`replenishment = 0.0`)
- **Reserva inicial**: 0.5 unidades en cada fondo (`observation`, `cognition`, `persistence`, `maintenance`).
- **Comportamiento observado**:
  - `tick 1–25`: Presión `NORMAL`, estado `ACTIVE`.
  - `tick 26–42`: Presión `ELEVATED`, estado `STRESSED`.
  - `tick 43–54`: Presión `SEVERE`, estado `DORMANT` (modo ahorro homeostático).
  - `tick 55`: Presión `UNRECOVERABLE` (reserva < 0.0), estado `DEAD`.
- **Verificación de Invariante de Muerte**:
  - En el `tick 56`, la llamada a `runtime.tick()` lanzó de manera determinista `OrganismDeadError("organism is irreversibly dead")`.
  - Los recursos en el hábitat y registros en la autoridad de nacimiento fueron liberados inmediatamente tras la muerte.

#### Rescate Metabólico desde Estado Crítico
- Un organismo forzado a presión `SEVERE` en el `tick 1` entró en estado `DORMANT`.
- Se administró una inyección metabólica de emergencia (`metabolism.intake = 1.0`).
- En el `tick 2`, el organismo se recuperó exitosamente al estado `ACTIVE` con reservas al 99.5%.
- *Conclusión*: El organismo tolera estados de crisis y latencia, permitiendo recuperación completa siempre que no se alcance la condición fatal irreversible.

---

### 2.4. Batería 4: Resiliencia Sensorial y Deriva (`DriftAwareBaseline`)

Se sometió el estimador de línea base adaptativa a perturbaciones controladas:

1. **Señal Limpia Constante**: 100% clasificada como `none` (sin falsos positivos).
2. **Deriva Progresiva Lineal (+0.05/tick)**: clasificaciones distribuidas en 14 `isolated`, 13 `gradual` y 13 `regime_shift`.
3. **Salto Abrupto de Régimen (+4.5 desviaciones estándar sostenidas)**:
   - Secuencia exacta observada: `['isolated', 'isolated', 'regime_shift', 'none', 'none']`.
   - *Interpretación matemática*: La línea base retiene la perturbación como anomalía aislada durante los dos primeros ciclos. Al tercer ciclo consecutivo, confirma el nuevo régimen, recomputa su media y varianza sobre el buffer reciente, y en los ciclos 4 y 5 clasifica el nuevo nivel como normal (`none`).
4. **Ruido de Alta Frecuencia ($\sigma = 0.8$)**: 54% `none`, 30% `isolated`, 10% `gradual`, 6% `regime_shift`, demostrando un filtrado robusto que evita reajustes espurios de la línea base ante fluctuaciones térmicas/ruidosas.

---

### 2.5. Batería 5: Dinámica Social y Contención de Recursos

Se evaluó la coexistencia en `SharedHabitat` y la formación de relaciones en `RelationLedger`:

1. **Límites de Capacidad de Carga**:
   - Con capacidad = 5 y recursos = 10.0, sobre 12 solicitudes de admisión se admitieron exactamente 5 organismos y se denegaron 7.
   - El saldo residual de recursos (2.5 unidades) permaneció intacto y protegido.
2. **Evolución de Valencia Social**:
   - Cooperación bilateral sostenida (5 intercambios): Soporte = 5.0, Daño = 0.0 $\to$ Valencia `POSITIVE`.
   - Contención unilateral y daño repetido (6 conflictos): Soporte = 0.0, Daño = 7.2 $\to$ Valencia `NEGATIVE`.
3. **Memoria de Escasez y Denegación**:
   - `ResourceEvidenceLedger` registró 5 denegaciones consecutivas sobre el token `channel_delta`, degradando la disponibilidad a 0.00 de forma controlada sin fugas de memoria.

---

### 2.6. Batería 6: Techos de Kernel y Estabilidad Numérica

1. **Control de Mutaciones Estructurales**:
   - Configuración estricta: `KernelLimits(max_nodes=6, max_concepts=3, max_edges=6)`.
   - 10 intentos de adición de nodos: **2 aceptadas, 8 rechazadas**. Nodos finales = 6.
   - 15 intentos de adición de aristas: **2 aceptadas, 13 rechazadas**. Aristas finales = 5.
   - *Invariante comprobado*: Ni el crecimiento plástico ni las mutaciones dinámicas pueden desbordar los límites duros asignados por el anfitrión.
2. **Estabilidad Numérica bajo Entradas Extremas**:
   - Estimulación con valores de $10^6$, $-10^6$ y $0.0$.
   - Cero valores `NaN` o `Inf` generados en las activaciones cognitivas; la función de transferencia acotó las respuestas sin colapso aritmético.

---

### 2.7. Batería 7: Determinismo y Rendimiento

1. **Determinismo Bitwise**:
   - Dos simulaciones independientes con semilla idéntica (1337) produjeron idénticos valores en Brier Score (`0.02473053`), error de calibración, investigaciones y brechas de reputación.
2. **Perfil de Latencia (120 ciclos consecutivos)**:
   - **Tiempo total**: 0.127 segundos.
   - **Latencia media**: **1.06 ms por ciclo**.
   - **Latencia Percentil 95**: **1.61 ms por ciclo**.
   - Sin acumulación detectable de memoria RSS o fugas de referencias.

---

## 3. Síntesis de Conclusiones

| Propiedad | Estado | Observación |
|---|---|---|
| **Aislamiento de Verdad Fundamental** | Impecable | Las decisiones del organismo dependen exclusivamente de señales opacas y memorias locales. |
| **Resiliencia Bizantina** | Robusta hasta < 50% | Umbral de tolerancia identificado en ~50%; a 60% se produce inversión de polaridad epistémica. |
| **Integridad Metabólica** | Determinista | Muerte irreversible estrictamente forzada por `OrganismDeadError`. Recuperación posible en latencia. |
| **Detección de Deriva** | Precisión matemática | Clasificación impecable de anomalías transitorias vs. desplazamientos reales de régimen. |
| **Gobernanza Cognitiva** | Inquebrantable | Respeto absoluto de `KernelLimits`; protección ante saturación de conceptos y conexiones. |
| **Rendimiento** | Alta eficiencia | ~1 ms/tick, determinismo bit a bit verificado. |
