# Selección Causal en Streaming, Treaps y Métricas de Evaluación Estadística

## 1. El Rol del Aparato Científico (`symbiont_lab`)

En la arquitectura de Symbiont Lab, el aparato experimental se encuentra estrictamente desacoplado del organismo:

- **El Organismo (`symbiont`):** Opera a ciegas respecto a las etiquetas del mundo; solo observa señales locales, mantiene creencias y toma decisiones causales.
- **El Aparato Científico (`symbiont_lab`):** Posee omnisciencia sobre la simulación (accede al *Ground Truth* $y^* \in \{0, 1\}$), ejecuta estudios de replicación, aplica intervenciones contrafactuales pareadas y evalúa rigurosamente el desempeño estadístico del organismo sin contaminar su proceso de inferencia.

Este documento formaliza los dos núcleos matemáticos de este aparato:

1. El algoritmo de **selección causal en streaming** basado en árboles cartesianos balanceados aleatoriamente (*Treaps*) ([`symbiont_lab.studies.common.causal_selection`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont_lab/studies/common/causal_selection.py)).
2. La batería de métricas de calibración probabilística, Brier Score y descomposición de matrices de confusión desacopladas ([`symbiont.simulation.metrics`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/metrics.py) y [`evaluation.py`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/evaluation.py)).

---

## 2. Selección Causal en Streaming: El Problema de la Mochila en Línea

En estudios de presupuesto de atención comparativos (v0.24, v0.27), el evaluador debe comparar diferentes heurísticas de priorización (basadas en riesgo, novedad, combinadas o aleatorias) asignando a cada una exactamente el mismo presupuesto de selección $K$ sobre una secuencia temporal de $M$ eventos elegibles.

Una selección retrospectiva ingenua (ordenar todos los $M$ eventos al final de la ejecución y tomar los $K$ mejores) comete **violación causal de lookahead**:

- Utiliza información del futuro para fijar el umbral óptimo del pasado.
- Un organismo real en streaming no conoce cuáles serán las puntuaciones máximas de los eventos futuros.

El problema formal consiste en:
> *Dada una corriente de eventos en línea $e_1, e_2, \dots, e_M$ con puntuaciones $s(e_i)$, seleccionar de forma irrevocable en el instante $t$ si $e_t$ se incluye en la muestra, garantizando que al finalizar se hayan seleccionado exactamente $K$ eventos y que la probabilidad marginal de selección coincida con el cuantil empírico de la historia observada.*

---

## 3. El Treap de Estadísticos de Orden Dinámicos con SplitMix64

Para evaluar cuantiles exactos en tiempo $O(\log n)$ por cada nuevo evento sin reordenar arrays de memoria ($O(n \log n)$ por evento, o $O(n^2)$ total), Symbiont Lab implementa un **Treap** ([`OrderStatisticHistory`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont_lab/studies/common/causal_selection.py#L83-L106)).

Un Treap es un árbol binario de búsqueda donde cada nodo posee:

- Una clave de búsqueda primaria: $\text{key} = (\text{score}, \text{serial}) \in \mathbb{R} \times \mathbb{N}_0$ (orden total estricto).
- Una prioridad de montículo (*heap priority*) generada pseudoaleatoriamente: $p \in [0, 2^{64}-1]$.
- El tamaño del subárbol $S_{\text{node}} = 1 + S_{\text{left}} + S_{\text{right}}$.

### 3.1 Prioridades Deterministas mediante SplitMix64

Para evitar llamadas a números aleatorios de Python que distorsionen los experimentos, las prioridades se derivan deterministamente a partir del número de serie ordinal mediante el generador de congruencia y mezcla de 64 bits SplitMix64 ([`_priority`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont_lab/studies/common/causal_selection.py#L29-L35)):

$$\begin{aligned}
v_0 &= (s + \text{0x9E3779B97F4A7C15}) \pmod{2^{64}} \\
v_1 &= \big( v_0 \oplus (v_0 \gg 30) \big) \times \text{0xBF58476D1CE4E5B9} \pmod{2^{64}} \\
v_2 &= \big( v_1 \oplus (v_1 \gg 27) \big) \times \text{0x94D049BB133111EB} \pmod{2^{64}} \\
p &= \big( v_2 \oplus (v_2 \gg 31) \big) \pmod{2^{64}}
\end{aligned}$$

La constante $\gamma = \text{0x9E3779B97F4A7C15} = \lfloor 2^{64} / \phi \rfloor$ es la razón áurea entera en 64 bits, garantizando una dispersión cuasi-uniforme de prioridades independientemente de la distribución de las puntuaciones $s$.

```text
         Treap Node: (key, priority, size)
                      ┌──────────────────────┐
                      │ (0.78, s=12), p=8921 │ size=5
                      └──────────┬───────────┘
                    left         │         right
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
┌──────────────────────┐                   ┌──────────────────────┐
│ (0.42, s=3), p=6401  │ size=2            │ (0.85, s=7), p=7210  │ size=2
└──────────┬───────────┘                   └──────────┬───────────┘
           │ left                                     │ right
           ▼                                          ▼
┌──────────────────────┐                   ┌──────────────────────┐
│ (0.15, s=1), p=2103  │ size=1            │ (0.94, s=15), p=4109 │ size=1
└──────────────────────┘                   └──────────────────────┘
```

### 3.2 Búsqueda del $k$-ésimo Cuantil en $O(\log n)$
Dado el tamaño de subárbol almacenado en cada nodo, la consulta del elemento en la posición ordinal $k \in \{0, \dots, n-1\}$ se resuelve de forma puramente descendente ([`_kth`](file:///home/alessbarb/workspace/repos/incubating/symbiont_lab/studies/common/causal_selection.py#L72-L81)):

$$\operatorname{kth}(\text{node}, k) = \begin{cases}
\operatorname{kth}(\text{node.left}, k) & \text{si } k < S_{\text{left}} \\
\text{node.key} & \text{si } k = S_{\text{left}} \\
\operatorname{kth}(\text{node.right}, k - S_{\text{left}} - 1) & \text{si } k > S_{\text{left}}
\end{cases}$$

El umbral dinámico para una tasa objetivo $\tau = \frac{K_{\text{rem}}}{E_{\text{rem}}}$ sobre una historia de longitud $n \ge 32$ se calcula evaluando el cuantil $q = 1.0 - \tau$:

$$\text{index} = \min\Big( n - 1, \; \max\big(0, \; \lfloor (1.0 - \tau)(n - 1) \rfloor\big) \Big)$$

$$\theta_{\text{causal}} = \operatorname{kth}(\text{root}, \text{index})_{\text{score}}$$

---

## 4. Algoritmo de Decisión de Selección en Streaming

En cada paso $t$ sobre el conjunto de eventos elegibles ([`online_indices`](file:///home/alessbarb/workspace/repos/incubating/symbiont_lab/studies/common/causal_selection.py#L118-L180)):

Sean:
- $B_{\text{rem}}$: Presupuesto de eventos restantes por seleccionar.
- $E_{\text{rem}}$: Número de eventos elegibles restantes en el stream.
- $s_t$: Puntuación del evento actual.

```python
must_take = B_rem >= E_rem

if must_take:
    take = True
    forced += 1
elif random_mode:
    take = random_score < (B_rem / E_rem)
else:
    target_rate = B_rem / E_rem
    threshold = history.threshold(target_rate, fallback)
    if s_t > threshold:
        take = True
    elif abs(s_t - threshold) <= 1e-12:
        take = tie_break_score < target_rate
    else:
        take = False

if take:
    selected.append(t)
history.add(s_t)
```

### 4.1 Invariantes del Algoritmo
1. **Cumplimiento Exacto del Presupuesto:**
   Si en algún punto $B_{\text{rem}} = E_{\text{rem}}$, la condición `must_take` fuerza la selección de todos los eventos restantes, asegurando invariablemente que $|\text{selected}| = K$. El contador `forced` mide cuántos eventos se seleccionaron por agotamiento de tiempo en lugar de por mérito informacional.
2. **Ausencia Estricta de Lookahead:**
   El umbral $\theta$ se extrae exclusivamente del historial $[s_1, \dots, s_{t-1}]$. El evento $s_t$ se añade al Treap *después* de tomar la decisión.

---

## 5. Métricas de Evaluación Probabilística del Simulador

El aparato de evaluación ([`symbiont.simulation.evaluation.Evaluator`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/evaluation.py)) procesa las decisiones del organismo comparándolas con la verdad fundamental $y^* \in \{0, 1\}$.

### 5.1 Puntuación de Brier (*Brier Score*)
El Brier Score ([`brier_score`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/metrics.py#L13-L14)) es una regla de puntuación estrictamente adecuada (*strictly proper scoring rule*) que mide el error cuadrático medio de las probabilidades predichas:

$$BS = \frac{1}{N} \sum_{i=1}^N \big( p_i - y_i^* \big)^2 \in [0, 1]$$

donde $p_i = \mathbb{P}(\text{Threat} \mid \mathcal{F}_{\text{org}})$ es la probabilidad estimada por el organismo y $y_i^* \in \{0, 1\}$ es la verdad fundamental.
- $BS = 0$: Predicción perfecta con certeza absoluta.
- $BS = 0.25$: Predictor trivial no informativo ($p_i = 0.5 \quad \forall i$).

### 5.2 Error Esperado de Calibración (*Expected Calibration Error - ECE*)
Para evaluar si las probabilidades declaradas por el organismo corresponden a frecuencias reales en el mundo ([`expected_calibration_error`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/metrics.py#L17-L27)), se particiona el espacio de probabilidad $[0, 1]$ en $M = 10$ intervalos uniformes:

$$B_m = \left( \frac{m-1}{10}, \; \frac{m}{10} \right], \quad m \in \{1, 2, \dots, 10\}$$

Para cada caja $B_m$ no vacía:
- **Confianza Media:** $\operatorname{conf}(B_m) = \frac{1}{|B_m|} \sum_{i \in B_m} p_i$.
- **Tasa Real de Amenazas:** $\operatorname{acc}(B_m) = \frac{1}{|B_m|} \sum_{i \in B_m} y_i^*$.

El ECE es la discrepancia absoluta media ponderada por el tamaño de la caja:

$$ECE = \sum_{m=1}^{10} \frac{|B_m|}{N} \Big| \operatorname{conf}(B_m) - \operatorname{acc}(B_m) \Big| \in [0, 1]$$

---

## 6. Desacoplamiento de Matrices de Confusión (Atención vs. Clasificación)

Uno de los principios de diseño fundamentales de Symbiont (ADR-0003) establece que **la atención no equivale a la clasificación de amenaza**.
- Un organismo puede atender a una señal simplemente porque es novedosa o incierta, concluyendo tras investigarla que es perfectamente benigna.
- Un organismo puede clasificar una señal como amenaza basándose en memoria previa sin requerir una segunda mirada.

Por ello, [`EvaluationCounts`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/simulation/evaluation.py#L13-L95) mantiene dos matrices de confusión completamente desacopladas:

```text
                    MATRIZ DE ATENCIÓN                      MATRIZ DE CLASIFICACIÓN
               (¿Se gastó presupuesto?)                     (¿Se creyó amenaza?)
               Investigó     No Investigó                  Creyó Threat   Creyó Benign
             ┌─────────────┬─────────────┐               ┌─────────────┬─────────────┐
Amenaza Real │   TP_att    │   FN_att    │  Amenaza Real │   TP_class  │   FN_class  │
             ├─────────────┼─────────────┤               ├─────────────┼─────────────┤
Benigno Real │   FP_att    │   TN_att    │  Benigno Real │   FP_class  │   TN_class  │
             └─────────────┴─────────────┘               └─────────────┴─────────────┘
```

### 6.1 Métricas de Atención
- **Exhaustividad de Atención (*Attention Recall / Detection Rate*):**
  $$\text{Recall}_{\text{att}} = \frac{TP_{\text{att}}}{TP_{\text{att}} + FN_{\text{att}}} = \frac{\text{Amenazas Investigadas}}{\text{Amenazas Totales}}$$
- **Precisión de Atención:**
  $$\text{Precision}_{\text{att}} = \frac{TP_{\text{att}}}{TP_{\text{att}} + FP_{\text{att}}}$$
- **Tasa de Falsos Positivos de Atención (Sobrecarga de Investigación):**
  $$\text{FPR}_{\text{att}} = \frac{FP_{\text{att}}}{\text{Eventos Benignos}}$$

### 6.2 Métricas de Clasificación
- **Exhaustividad de Clasificación (*Classification Recall*):**
  $$\text{Recall}_{\text{class}} = \frac{TP_{\text{class}}}{TP_{\text{class}} + FN_{\text{class}}}$$
- **Precisión de Clasificación:**
  $$\text{Precision}_{\text{class}} = \frac{TP_{\text{class}}}{TP_{\text{class}} + FP_{\text{class}}}$$
- **Tasa de Fallo de Clasificación (*Miss Rate*):**
  $$\text{Miss Rate} = \frac{FN_{\text{class}}}{\text{Amenazas Totales}} = 1 - \text{Recall}_{\text{class}}$$

### 6.3 Métricas de Seguridad Epistémica: Sobreconfianza y Puntos Ciegos
Para detectar si el organismo sufre de arrogancia predictiva o puntos ciegos críticos:

1. **Tasa de Sobreconfianza (*Overconfidence Rate*):**
   Fracción de predicciones emitidas con alta confianza ($\max(p, 1-p) \ge 0.75$) que resultaron ser erróneas:
   $$\text{Overconfidence} = \frac{\sum_{i: \text{conf}_i \ge 0.75} \mathbb{I}(\hat{y}_i \neq y_i^*)}{\sum_{i} \mathbb{I}(\text{conf}_i \ge 0.75)}$$

2. **Tasa de Omisión de Alta Confianza (*High-Confidence Threat Miss Rate / Blind Spot Rate*):**
   Fracción de amenazas reales donde el organismo estaba altamente confiado de que la entidad era benigna ($p < 0.25$):
   $$\text{BlindSpotRate} = \frac{\sum_{i: y_i^*=1 \land p_i < 0.25} 1}{\text{Amenazas Totales}}$$

Esta métrica constituye el indicador crítico de seguridad: un punto ciego de alta confianza es órdenes de magnitud más peligroso para un anfitrión que una duda con baja certeza.
