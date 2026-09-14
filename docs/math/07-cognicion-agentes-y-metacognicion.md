# Cognición de Agentes, Curiosidad Contrafactual y Metacognición

## 1. Introducción al Ciclo Cognitivo del Agente

En Symbiont, cada agente autónomo sintetiza observaciones continuas, construye modelos locales de normalidad, formula hipótesis causales, explora preguntas contrafactuales mediante curiosidad intrínseca y emite evaluaciones epistémicas sobre la calidad de sus propias creencias.

El diseño matemático de esta cognición está estructurado en tres niveles jerárquicos:

1. **Nivel Sensoriomotor y Representacional:** Discretización en firmas de Hamming ternarias y detección multivariante de novedad ([`symbiont.core.model`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/model.py)).
2. **Nivel de Inferencia y Decisión:** Cálculo de riesgo, sospecha combinada, curiosidad y adaptación a la deriva con histéresis ([`symbiont.core.agent`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/agent.py)).
3. **Nivel Reflexivo / Metacognitivo:** Evaluación de la presión epistémica global de la población y estado cualitativo de certidumbre colectiva ([`symbiont.core.metacognition`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/metacognition.py)).

---

## 2. Álgebra de Firmas Ternarias y Novedad Multivariante

Dado el vector de observación sintético $\mathbf{x} = (x_1, x_2, x_3, x_4, x_5) \in [0, 1]^5$, el sistema extrae una firma abstracta mediante cuantización no lineal:

$$\phi_{\text{bin}}(v) = \begin{cases}
\text{"L"} & \text{si } v < 0.25 \quad (\text{Bajo / Low}) \\
\text{"M"} & \text{si } 0.25 \le v < 0.60 \quad (\text{Medio / Medium}) \\
\text{"H"} & \text{si } v \ge 0.60 \quad (\text{Alto / High})
\end{cases}$$

La firma $\text{fp} = \phi_{\text{bin}}(x_1) \parallel \text{"-"} \parallel \dots \parallel \phi_{\text{bin}}(x_5)$ pertenece a un espacio discreto de cardinalidad:

$$|\Sigma_{\text{patterns}}| = 3^5 = 243 \text{ estados}$$

Esta compresión drástica actúa como un *cuello de botella informacional* (*information bottleneck*) que previene el sobreajuste a micro-fluctuaciones y permite la agregación colectiva de observaciones entre múltiples hosts.

### 2.1 Métrica de Novedad Multidimensional
Cada agente mantiene un modelo local de anfitrión [`HostModel`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/model.py#L62-L89) con estadísticas EWMA para cada dimensión $(\mu_i, \sigma_i)$.

La madurez del modelo local satura a las 24 observaciones:

$$\operatorname{Maturity}(n) = \min\left( \frac{\min_i n_i}{24.0}, \; 1.0 \right)$$

Si $\operatorname{Maturity} < 0.25$, la novedad es idénticamente 0 (inhibición de juicio prematuro).
En caso contrario, se computa la discrepancia $Z$ multivariante acotada:

$$z_i = \frac{|x_i - \mu_i|}{\max(\sigma_i, 0.12)}$$

$$\bar{z} = \frac{1}{5} \sum_{i=1}^5 \min(z_i, 8.0)$$

$$\operatorname{Novelty}(\mathbf{x}) = \min\left( \frac{\bar{z}}{4.0}, \; 1.0 \right) \in [0, 1]$$

El umbral de saturación $z_{\max} = 8.0$ impide que un solo sensor anómalo sature la puntuación completa, requiriendo coherencia entre múltiples variables para alcanzar máxima novedad.

---

## 3. Curiosidad Intrínseca y Prospección Contrafactual

El organismo genera preguntas contrafactuales en un espacio sombra (*shadow world*) sin actuar sobre el sistema real ([`symbiont.core.curiosity.CuriosityPlanner`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/curiosity.py)).

Para una hipótesis activa con firma $\text{fp} = (b_1, \dots, b_5)$, el planificador genera vecinos adyacentes en el grafo de Hamming:

$$\operatorname{Adj}(b_i) = \begin{cases} \{\text{"M"}\} & \text{si } b_i \in \{\text{"L"}, \text{"H"}\} \\ \{\text{"L"}, \text{"H"}\} & \text{si } b_i = \text{"M"} \end{cases}$$

Para cada firma vecina $\text{fp}'$, se consultan las creencias colectivas previas $(P_{\text{base}}, c_{\text{base}})$ y $(P_{\text{neighbor}}, c_{\text{neighbor}})$.

### 3.1 Ganancia de Información Esperada ($IG$)
Se calculan tres factores:
1. **Discriminación Contrafactual:**
   $$d = \begin{cases} |P_{\text{base}} - P_{\text{neighbor}}| & \text{si el vecino es conocido} \\ 0.25 & \text{si el vecino es nuevo} \end{cases}$$
2. **Brecha de Evidencia (*Evidence Gap*):**
   $$g = \begin{cases} 1.0 - c_{\text{neighbor}} & \text{si el vecino es conocido} \\ 1.0 & \text{si el vecino es nuevo} \end{cases}$$
3. **Incertidumbre de Base:**
   $$u = 1.0 - c_{\text{base}}$$

La Ganancia de Información Esperada se formaliza como:

$$IG = \min\Big( 1.0, \; u \cdot \big( 0.45 + 0.35 \cdot d + 0.20 \cdot g \big) \cdot \big( 0.65 + 0.35 \cdot \text{priority} \big) \Big)$$

### 3.2 Costo y Utilidad de Exploración
Dado que ciertas características sensoriales conllevan un mayor overhead de medición (modelado por la posición del índice $i \in \{0, \dots, 4\}$):

$$\operatorname{Cost}(i) = 0.10 + 0.04 \cdot \frac{i}{4} \in [0.10, 0.14]$$

La utilidad final de la sonda de curiosidad es el cociente regularizado:

$$\operatorname{Utility} = \min\left( 1.0, \; \frac{IG}{0.55 + \operatorname{Cost}} \right)$$

Las sondas se ordenan por utilidad decreciente y alimentan las investigaciones del ciclo cognitivo.

---

## 4. El Motor de Decisión del Agente

En cada tick, el agente integra señales de múltiples fuentes para decidir si investiga y si clasifica el evento como amenaza ([`symbiont.core.agent.Agent.assess`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/agent.py#L25-L101)).

### 4.1 Función de Riesgo Aparente
$$R_{\text{raw}} = \min\Big( 1.0, \; 0.12\,x_{\text{cpu}} + 0.18\,x_{\text{net}} + 0.28\,x_{\text{file}} + 0.16\,x_{\text{proc}} + 0.26\,x_{\text{persist}} \Big)$$

$$R = \min\big( 1.0, \; R_{\text{raw}} \cdot \text{risk\_scale} \big)$$

### 4.2 Incertidumbre Compuesta del Agente
La incertidumbre subjetiva integra la madurez del modelo local, la certeza del colectivo y la ambigüedad del riesgo:

$$U_{\text{agent}} = \min\Big( 1.0, \; 0.38(1 - \operatorname{Maturity}) + 0.42(1 - c_{\text{coll}}) + 0.20\big(1 - 2|R - 0.5|\big) \Big)$$

### 4.3 Sospecha Combinada
La probabilidad subjetiva de amenaza fusiona riesgo aparente, novedad, consenso colectivo y memoria local:

$$w_{\text{local}} = 0.12 \cdot c_{\text{local}}$$

$$S_{\text{comb}} = \operatorname{clip}\left( \frac{0.72 \cdot R + 0.18 \cdot \operatorname{Novelty} + 0.10 \cdot P_{\text{coll}} c_{\text{coll}} + w_{\text{local}} \cdot P_{\text{local}}}{1.0 + w_{\text{local}}}, \; 0.0, \; 1.0 \right)$$

### 4.4 Lógica de Decisión con Doble Umbral e Histéresis
Sea $b$ el sesgo individual del agente ($\text{investigation\_bias}$).
El agente toma dos decisiones separadas:

1. **Decisión de Atención / Investigación Activa (`should_investigate`):**
   Requiere madurez mínima ($\operatorname{Maturity} \ge 0.5$) y se activa por sospecha elevada o por curiosidad epistémica:
   $$\text{Investigate} \iff \operatorname{Maturity} \ge 0.5 \land \Big( S_{\text{comb}} \ge 0.43 + b \;\lor\; \operatorname{Curiosity} \ge \max(0.012, \; 0.025 - 0.25 b) \Big)$$

2. **Decisión de Clasificación de Amenaza (`believes_threat`):**
   Tiene un umbral más estricto que la mera investigación:
   $$\text{Threat} \iff S_{\text{comb}} \ge 0.48 + 0.5 b$$

### 4.5 Adaptación a la Deriva por Histéresis de Racha
Para no re-adaptar el modelo ante un ataque o anomalía hostil, se implementa una máquina de estados con racha (*streak*):

$$\text{DriftCandidate} \iff \Big( \operatorname{Maturity} \ge 0.5 \land \operatorname{Novelty} \ge 0.45 \land R < 0.45 \land P_{\text{coll}} < 0.65 \Big)$$

$$\text{Streak}_t = \begin{cases} \text{Streak}_{t-1} + 1 & \text{si DriftCandidate es Verdadero} \\ \max(0, \text{Streak}_{t-1} - 1) & \text{en otro caso} \end{cases}$$

- Si $\text{Streak} \ge 5$: Se confirma que la novedad no es hostil (bajo riesgo y bajo consenso de amenaza). El agente actualiza su línea base con la observación anómala y resetea $\text{Streak} \leftarrow 2$.
- Si la racha no alcanza 5, la línea base permanece intacta.

---

## 5. Metacognición Poblacional

[`MetacognitionEngine`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/metacognition.py) estima la autoconciencia epistémica de la población sin acceder a ground truth:

### 5.1 Ecuación de Presión Epistémica ($P_{\text{epistemic}}$)
Dada una colección de evaluaciones de los agentes en el tick $t$:

$$\begin{aligned}
\bar{u} &= \frac{1}{N} \sum_i U_i \quad (\text{Incertidumbre media}) \\
\bar{\nu} &= \frac{1}{N} \sum_i \operatorname{Novelty}_i \quad (\text{Novedad media}) \\
\bar{c} &= \frac{1}{N} \sum_i \operatorname{Curiosity}_i \quad (\text{Curiosidad media}) \\
P_{\text{disagreement}} &= \frac{1}{N} \sum_i \Big( 1.0 - 2|P_{\text{coll}, i} - 0.5| \Big) \quad (\text{Presión de desacuerdo}) \\
P_{\text{questions}} &= \min\left( 1.0, \; \frac{|\text{OpenQuestions}|}{\max(|\text{Patterns}|, 1)} \right) \quad (\text{Presión de preguntas abiertas})
\end{aligned}$$

La presión epistémica total es la combinación lineal convexa truncada:

$$P_{\text{epistemic}} = \min\Big( 1.0, \; 0.42\,\bar{u} + 0.24\,\bar{\nu} + 0.20\,P_{\text{disagreement}} + 0.10\,P_{\text{questions}} + 0.04\,\min(8.0\,\bar{c}, 1.0) \Big)$$

La **Autoconfianza Metacognitiva** es su complemento:

$$C_{\text{self}} = 1.0 - P_{\text{epistemic}} \in [0, 1]$$

### 5.2 Estados de Fase Metacognitiva
A partir de estos continuos, el sistema clasifica su fase cualitativa:
- `uncertain`: $C_{\text{self}} < 0.40$.
- `novel`: $\bar{\nu} > 0.30$.
- `contested`: $P_{\text{disagreement}} > 0.62 \land P_{\text{questions}} > 0.08$.
- `stable`: $C_{\text{self}} > 0.72 \land P_{\text{questions}} < 0.10$.
- `watchful`: en cualquier otro caso intermedio.
