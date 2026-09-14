# Cognición de Agentes, Curiosidad Contrafactual y Metacognición

> **Estado:** IMPLEMENTADO  
> **Tipo:** REGLAS DE DECISIÓN HEURÍSTICA Y METASCORE MULTIVARIANTE  
> **Módulos relacionados:** [`symbiont.core.model`](../../src/symbiont/core/model.py), [`symbiont.core.agent`](../../src/symbiont/core/agent.py), [`symbiont.core.curiosity`](../../src/symbiont/core/curiosity.py), [`symbiont.core.metacognition`](../../src/symbiont/core/metacognition.py)

---

## 1. Introducción al Ciclo Cognitivo del Agente

En Symbiont, cada agente autónomo sintetiza observaciones continuas, construye modelos locales de normalidad, formula hipótesis causales, explora preguntas contrafactuales mediante curiosidad intrínseca y emite evaluaciones sobre el estado de sus creencias.

El diseño está estructurado en tres niveles:

1. **Nivel Sensoriomotor y Representacional:** Discretización en firmas de Hamming ternarias y detección multivariante de novedad ([`symbiont.core.model`](../../src/symbiont/core/model.py)).
2. **Nivel de Inferencia y Decisión:** Cálculo de riesgo aparente, sospecha combinada, curiosidad y adaptación a la deriva mediante histéresis ([`symbiont.core.agent`](../../src/symbiont/core/agent.py)).
3. **Nivel Metacognitivo:** Agregación de presiones epistémicas en la población y clasificación de regímenes cualitativos de certidumbre ([`symbiont.core.metacognition`](../../src/symbiont/core/metacognition.py)).

> **Nota Epistemológica:**  
> Las ecuaciones de este capítulo constituyen **modelos de puntuación heurística multilineales** calibrados empíricamente para balancear exploración y estabilidad en el entorno de simulación, no deducciones analíticas de la teoría de la decisión estadística formal.

---

## 2. Álgebra de Firmas Ternarias y Novedad Multivariante

> **Clasificación:** IDENTIDAD DEL CÓDIGO / COMPRESIÓN DE INFORMACIÓN

Dado el vector de observación sintético $\mathbf{x} = (x_1, x_2, x_3, x_4, x_5) \in [0, 1]^5$, se extrae una firma discreta mediante partición ternaria ([`fingerprint`](../../src/symbiont/core/model.py#L108-L119)):

$$\phi_{\text{bin}}(v) = \begin{cases}
\text{"L"} & \text{si } v < 0.25 \quad (\text{Bajo / Low}) \\
\text{"M"} & \text{si } 0.25 \le v < 0.60 \quad (\text{Medio / Medium}) \\
\text{"H"} & \text{si } v \ge 0.60 \quad (\text{Alto / High})
\end{cases}$$

El espacio de patrones resultantes tiene cardinalidad finita:

$$|\Sigma_{\text{patterns}}| = 3^5 = 243 \text{ estados}$$

Esta discretización tosca actúa como un *cuello de botella de información* (*information bottleneck*) deliberado, facilitando el consenso y la concordancia de memorias entre múltiples anfitriones con perfiles de ruido dispares.

### 2.1 Métrica Heurística de Novedad Multidimensional
Cada agente mantiene un modelo local [`HostModel`](../../src/symbiont/core/model.py) con estadísticas EWMA para cada una de las 5 dimensiones $(\mu_i, \sigma_i)$.

La madurez del modelo satura en 24 observaciones:

$$\operatorname{Maturity}(n) = \min\left( \frac{\min_i n_i}{24.0}, \; 1.0 \right)$$

Si $\operatorname{Maturity} < 0.25$, la novedad es idénticamente 0.0 (inhibición de juicio durante el calentamiento inicial).
En caso contrario:

$$z_i = \frac{|x_i - \mu_i|}{\max(\sigma_i, 0.12)}$$

$$\bar{z} = \frac{1}{5} \sum_{i=1}^5 \min(z_i, 8.0)$$

$$\operatorname{Novelty}(\mathbf{x}) = \min\left( \frac{\bar{z}}{4.0}, \; 1.0 \right) \in [0, 1]$$

El recorte en $z_{\max} = 8.0$ previene que una perturbación unidimensional extrema domine la puntuación completa, requiriendo desplazamiento consistente en varias características para aproximar la novedad a $1.0$.

---

## 3. Curiosidad Intrínseca y Contrafactuales en el Espacio Sombra

> **Clasificación:** HEURÍSTICA DE RANKING INFORMACIONAL

El organismo genera preguntas contrafactuales en un espacio sombra (*shadow world*) sin actuar sobre el anfitrión real ([`CuriosityPlanner`](../../src/symbiont/core/curiosity.py)).

Para una hipótesis activa con firma $\text{fp} = (b_1, \dots, b_5)$, el planificador explora vecinos adyacentes en el hipercubo ternario:

$$\operatorname{Adj}(b_i) = \begin{cases} \{\text{"M"}\} & \text{si } b_i \in \{\text{"L"}, \text{"H"}\} \\ \{\text{"L"}, \text{"H"}\} & \text{si } b_i = \text{"M"} \end{cases}$$

Para cada vecino $\text{fp}'$, se consultan las creencias colectivas previas $(P_{\text{base}}, c_{\text{base}})$ y $(P_{\text{neighbor}}, c_{\text{neighbor}})$.

### 3.1 Ganancia de Información Esperada Heurística ($IG$)
Se calculan:
1. **Discriminación Contrafactual:**
   $$d = \begin{cases} |P_{\text{base}} - P_{\text{neighbor}}| & \text{si el vecino es conocido} \\ 0.25 & \text{si el vecino es nuevo} \end{cases}$$
2. **Brecha de Evidencia (*Evidence Gap*):**
   $$g = \begin{cases} 1.0 - c_{\text{neighbor}} & \text{si el vecino es conocido} \\ 1.0 & \text{si el vecino es nuevo} \end{cases}$$
3. **Incertidumbre de Base:**
   $$u = 1.0 - c_{\text{base}}$$

La ganancia de información esperada se formaliza como:

$$IG = \min\Big( 1.0, \; u \cdot \big( 0.45 + 0.35 \cdot d + 0.20 \cdot g \big) \cdot \big( 0.65 + 0.35 \cdot \text{priority} \big) \Big)$$

### 3.2 Costo y Utilidad de Exploración
Asumiendo un costo sintético ordinal según la posición de la característica $i \in \{0, \dots, 4\}$:

$$\operatorname{Cost}(i) = 0.10 + 0.04 \cdot \frac{i}{4} \in [0.10, 0.14]$$

La utilidad de la sonda es el cociente regularizado:

$$\operatorname{Utility} = \min\left( 1.0, \; \frac{IG}{0.55 + \operatorname{Cost}} \right)$$

---

## 4. El Motor de Decisión del Agente

> **Clasificación:** REGLA DE DECISIÓN MULTILINEAL CON HISTÉRESIS

En cada tick, el agente integra señales de múltiples fuentes para decidir si investiga y si clasifica el evento como amenaza ([`Agent.assess`](../../src/symbiont/core/agent.py#L25-L101)).

### 4.1 Función de Riesgo Aparente
$$R_{\text{raw}} = \min\Big( 1.0, \; 0.12\,x_{\text{cpu}} + 0.18\,x_{\text{net}} + 0.28\,x_{\text{file}} + 0.16\,x_{\text{proc}} + 0.26\,x_{\text{persist}} \Big)$$

$$R = \min\big( 1.0, \; R_{\text{raw}} \cdot \text{risk\_scale} \big)$$

### 4.2 Incertidumbre Compuesta del Agente
$$U_{\text{agent}} = \min\Big( 1.0, \; 0.38(1 - \operatorname{Maturity}) + 0.42(1 - c_{\text{coll}}) + 0.20\big(1 - 2|R - 0.5|\big) \Big)$$

### 4.3 Sospecha Combinada
$$w_{\text{local}} = 0.12 \cdot c_{\text{local}}$$

$$S_{\text{comb}} = \operatorname{clip}\left( \frac{0.72 \cdot R + 0.18 \cdot \operatorname{Novelty} + 0.10 \cdot P_{\text{coll}} c_{\text{coll}} + w_{\text{local}} \cdot P_{\text{local}}}{1.0 + w_{\text{local}}}, \; 0.0, \; 1.0 \right)$$

### 4.4 Lógica de Decisión con Doble Umbral e Histéresis
Sea $b$ el sesgo individual del agente ($\text{investigation\_bias}$).
El agente toma dos decisiones separadas:

1. **Atención / Investigación Activa (`should_investigate`):**
   $$\text{Investigate} \iff \operatorname{Maturity} \ge 0.5 \land \Big( S_{\text{comb}} \ge 0.43 + b \;\lor\; \operatorname{Curiosity} \ge \max(0.012, \; 0.025 - 0.25 b) \Big)$$

2. **Clasificación de Amenaza (`believes_threat`):**
   $$\text{Threat} \iff S_{\text{comb}} \ge 0.48 + 0.5 b$$

### 4.5 Adaptación a la Deriva por Histéresis de Racha
Para evitar que una anomalía hostil fuerce la re-adaptación del modelo de normalidad, se implementa una máquina de estados con racha (*streak*):

$$\text{DriftCandidate} \iff \Big( \operatorname{Maturity} \ge 0.5 \land \operatorname{Novelty} \ge 0.45 \land R < 0.45 \land P_{\text{coll}} < 0.65 \Big)$$

$$\text{Streak}_t = \begin{cases} \text{Streak}_{t-1} + 1 & \text{si DriftCandidate es Verdadero} \\ \max(0, \text{Streak}_{t-1} - 1) & \text{en otro caso} \end{cases}$$

- Si $\text{Streak} \ge 5$: Se asume que la novedad sostenida no es un ataque agudo (riesgo aparente bajo y consenso no hostil). El agente incorpora la observación a su línea base y resetea $\text{Streak} \leftarrow 2$.
- Si la racha no alcanza 5, la línea base del anfitrión permanece intacta.

---

## 5. Metacognición Poblacional

> **Clasificación:** AGREGACIÓN EPITÉMICA GLOBAL

[`MetacognitionEngine`](../../src/symbiont/core/metacognition.py) sintetiza un indicador global del estado epistémico de la población:

$$\begin{aligned}
\bar{u} &= \frac{1}{N} \sum_i U_i, \qquad \bar{\nu} = \frac{1}{N} \sum_i \operatorname{Novelty}_i, \qquad \bar{c} = \frac{1}{N} \sum_i \operatorname{Curiosity}_i \\
P_{\text{disagreement}} &= \frac{1}{N} \sum_i \Big( 1.0 - 2|P_{\text{coll}, i} - 0.5| \Big) \\
P_{\text{questions}} &= \min\left( 1.0, \; \frac{|\text{OpenQuestions}|}{\max(|\text{Patterns}|, 1)} \right)
\end{aligned}$$

La **Presión Epistémica** total es:

$$P_{\text{epistemic}} = \min\Big( 1.0, \; 0.42\,\bar{u} + 0.24\,\bar{\nu} + 0.20\,P_{\text{disagreement}} + 0.10\,P_{\text{questions}} + 0.04\,\min(8.0\,\bar{c}, 1.0) \Big)$$

La **Autoconfianza Metacognitiva** es:

$$C_{\text{self}} = 1.0 - P_{\text{epistemic}} \in [0, 1]$$

### 5.1 Clasificación Cualitativa de Régimen
- `uncertain`: $C_{\text{self}} < 0.40$.
- `novel`: $\bar{\nu} > 0.30$.
- `contested`: $P_{\text{disagreement}} > 0.62 \land P_{\text{questions}} > 0.08$.
- `stable`: $C_{\text{self}} > 0.72 \land P_{\text{questions}} < 0.10$.
- `watchful`: régimen por defecto en transiciones intermedias.
