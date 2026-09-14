# Dinámica de Creencias Bayesianas, Sorpresa y Registro de Disidencia

## 1. La Naturaleza de las Creencias en Symbiont

En Symbiont, una creencia no es una etiqueta determinista ("esto es un troyano" o "esto es normal"), sino una distribución de probabilidad subjetiva que evoluciona en el tiempo bajo la influencia de percepciones locales ruidosas y parciales ([`symbiont.core.beliefs`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/beliefs.py)).

Un modelo de creencias riguroso debe poseer cuatro propiedades formales:

1. **Convergencia Asintótica:** A medida que se acumulan observaciones consistentes, la certeza debe aproximarse a 1.
2. **Capacidad de Rectificación (Reversibilidad):** Si la naturaleza de una señal cambia, la creencia debe poder cruzar la frontera de decisión en cualquier dirección ($p \ge 0.5 \leftrightarrow p < 0.5$).
3. **Sensibilidad al Conflicto:** Si observaciones sucesivas se contradicen mutuamente, la certeza epistémica debe decaer aunque la masa total de evidencia sea elevada.
4. **Preservación Inmutable de la Contradicción:** Cuando nueva evidencia choca frontalmente con la creencia establecida, el hecho de la disidencia debe quedar registrado como un evento histórico inmutable ([`symbiont.core.evidence`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/evidence.py)), en lugar de promediarse silenciosamente como si nunca hubiera existido conflicto.

---

## 2. El Modelo de Actualización Bayesiana con Pseudo-Observaciones

Cada patrón o firma sensorial abstracta $\text{fp} \in \Sigma^*$ mapea a un estado de creencia continuo [`BeliefState`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/beliefs.py#L8-L23):

$$\mathbf{b} = (p, E, C) \in [0, 1] \times [0, E_{\max}] \times [0, 1]$$

donde $p$ es la probabilidad a posteriori estimada, $E$ es la masa de evidencia acumulada ($E_{\max} = 32.0$), y $C$ es la memoria de conflicto acumulado.

### 2.1 Ecuación de Actualización de Probabilidad

Al presentarse una nueva observación con probabilidad estimada $P_{\text{obs}} \in [0, 1]$ y un nivel de confianza asociado $c_{\text{obs}} \in [0, 1]$ en el paso temporal $t$:

El peso de la nueva evidencia se acota inferiormente para evitar actualizaciones nulas:

$$w = \max(0.05, c_{\text{obs}})$$

La probabilidad a posteriori $P_{\text{posterior}}$ se calcula mediante la media ponderada exacta:

$$P_{\text{posterior}} = \frac{P_{\text{prior}} \cdot E + P_{\text{obs}} \cdot w}{E + w}$$

### 2.2 Derivación desde la Inferencia Conjugada Beta-Binomial

Esta regla de actualización es isomórfica a la media de una distribución Beta conjugada:

$$\text{Beta}(\alpha, \beta) \implies \mathbb{E}[P] = \frac{\alpha}{\alpha + \beta}$$

Sea $E = \alpha + \beta$ el tamaño muestral efectivo (número de pseudo-observaciones previas) y $P_{\text{prior}} = \frac{\alpha}{E}$.
Al observar un peso equivalente a $w$ pseudo-muestras con proporción de éxitos $P_{\text{obs}}$:

$$\alpha' = \alpha + w \cdot P_{\text{obs}} = P_{\text{prior}} \cdot E + P_{\text{obs}} \cdot w$$
$$\beta' = \beta + w \cdot (1 - P_{\text{obs}}) = (1 - P_{\text{prior}}) \cdot E + (1 - P_{\text{obs}}) \cdot w$$
$$E' = \alpha' + \beta' = E + w$$

Por consiguiente:
$$\mathbb{E}[P'] = \frac{\alpha'}{E'} = \frac{P_{\text{prior}} \cdot E + P_{\text{obs}} \cdot w}{E + w} \quad \blacksquare$$

### 2.3 Acumulación y Saturación de Evidencia

Para prevenir la *parálisis epistémica* (donde una creencia acumula tanta evidencia que se vuelve matemáticamente impermeable a nueva información en horizontes temporales infinitos), la masa de evidencia está acotada superiormente por $E_{\max} = 32.0$:

$$E_{t} = \min\big(E_{\max}, \; E_{t-1} + w\big)$$

Esto garantiza que una masa de evidencia fresca de magnitud $w$ siempre mantenga una influencia relativa mínima de al menos:

$$\frac{w}{E_{\max} + w} \ge \frac{0.05}{32.05} \approx 0.00156$$

permitiendo que una secuencia sostenida de evidencia contraria revierta cualquier creencia establecida.

---

## 3. Dinámica del Conflicto y Sorpresa Epistémica

La sorpresa mide la distancia absoluta entre la expectativa a priori del organismo y la nueva observación:

$$S_t = |P_{\text{obs}} - P_{\text{prior}}| \in [0, 1]$$

### 3.1 Filtro de Conflicto Acumulado

El conflicto $C_t$ actúa como un filtro paso bajo con memoria exponencial que integra la sorpresa en el tiempo:

$$C_t = \min\Big( 1.0, \; 0.75 \cdot C_{t-1} + 0.25 \cdot S_t \Big)$$

- Si las observaciones confirman consistentemente la expectativa ($P_{\text{obs}} \approx P_{\text{prior}}$), entonces $S_t \to 0$ y $C_t$ decae exponencialmente hacia 0 con constante de tiempo $\tau = \frac{1}{\ln(1/0.75)} \approx 3.47$ revisiones.
- Si las observaciones alternan violentamente entre extremos (ej. $0$ y $1$), $S_t \approx 1$ y $C_t$ satura rápidamente en $1.0$.

### 3.2 Reversiones de Creencia (*Belief Reversals*)

Una reversión ocurre cuando la probabilidad a posteriori cruza la frontera de decisión ($0.5$) respecto a la probabilidad a priori, habiendo existido revisiones previas:

$$\text{Reversal}_t = \mathbb{I}\Big( (P_{\text{prior}} \ge 0.5) \neq (P_{\text{posterior}} \ge 0.5) \land \text{revisions} > 0 \Big)$$

El contador acumulado de reversiones sirve como indicador de inestabilidad ecológica en el aparato experimental.

---

## 4. Función No-Lineal de Certeza Matemática

La certeza subjetiva $\text{Certainty} \in [0, 1]$ no depende únicamente de la probabilidad $p$. Una creencia de $p = 0.5$ construida con $E = 32.0$ y $C = 0.0$ refleja una certeza absoluta de que el fenómeno es perfectamente ambiguo (equidistribuido), mientras que $p = 0.5$ con $E = 0.0$ refleja ignorancia total.

La función de certeza en [`BeliefState.certainty`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/beliefs.py#L18-L22) se define como:

$$\text{Certainty}(E, C) = \operatorname{clip}\left( \underbrace{\Big( 1 - e^{-E / 4.0} \Big)}_{\text{Masa de Evidencia}} \cdot \underbrace{\Big( 1 - 0.60 \cdot C \Big)}_{\text{Penalización por Conflicto}}, \; 0.0, \; 1.0 \right)$$

```text
Certainty
   ▲
1.0│              C = 0.0 (Sin conflicto)
   │             .───────────────────────  1 - exp(-E/4)
0.8│          .─'
   │       .─'
0.6│     .─'      C = 0.5 (Conflicto moderado)
   │   .─'───────────────────────────────  0.7 * [1 - exp(-E/4)]
0.4│ .─'          C = 1.0 (Máximo conflicto)
   │.────────────────────────────────────  0.4 * [1 - exp(-E/4)]
0.0└──────┬──────┬──────┬──────┬──────► Masa de Evidencia E
   0      4      8      16     32
```

### 4.1 Análisis Asintótico y Derivadas Parciales

1. **Comportamiento en Cero Evidencia:**
   $$\lim_{E \to 0^+} \text{Certainty}(E, C) = (1 - 1) \cdot (1 - 0.60 C) = 0.0 \quad \forall C$$
   Sin evidencia empírica, la certeza es rigurosamente nula.

2. **Tasa de Crecimiento Marginal respecto a la Evidencia:**
   $$\frac{\partial \text{Certainty}}{\partial E} = \frac{1}{4.0} e^{-E / 4.0} (1 - 0.60 C) > 0$$
   El retorno epistémico marginal es decreciente. Para $E = 4.0$ (el punto característico), la masa alcanza $1 - e^{-1} \approx 63.2\%$ de su cota superior. Para $E = 16.0$, alcanza el $98.1\%$.

3. **Efecto Atenuador del Conflicto:**
   $$\frac{\partial \text{Certainty}}{\partial C} = -0.60 \Big( 1 - e^{-E / 4.0} \Big) \le 0$$
   Incluso con saturación máxima de evidencia ($E \to 32.0$), si el sistema se encuentra en contradicción permanente ($C = 1.0$), la certeza queda acotada superiormente a:
   $$\text{Certainty}_{\max}(C=1) \approx 1.0 \cdot (1 - 0.60) = 0.40$$
   El conflicto estructural destruye el $60\%$ de la confianza del organismo.

---

## 5. El Registro de Disidencia (*Evidence Revision Ledger*)

Cuando un organismo realiza un sondeo de alta resolución (*second look*, v0.39/v0.40) sobre una capacidad $c_k$, recibe un lote discreto de nuevas lecturas $\mathcal{X}_{\text{batch}} = \{x_1, x_2, \dots, x_m\}$.

[`EvidenceRevisionLedger`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/evidence.py) evalúa formalmente si el lote contradice la línea base acumulada $\mathcal{N}(\mu_{\text{prior}}, \sigma_{\text{prior}}^2)$.

### 5.1 Prueba Estadística de Disidencia ($Z$-Score de Lote)

Se calculan la media muestral del lote y la puntuación de discrepancia estandarizada:

$$\bar{x}_{\text{batch}} = \frac{1}{m} \sum_{i=1}^m x_i$$

$$Z_{\text{batch}} = \frac{\bar{x}_{\text{batch}} - \mu_{\text{prior}}}{\sigma_{\text{prior}}}$$

Si la línea base previa está aclimatada ($\sigma_{\text{prior}} > 0$) y la discrepancia supera el umbral crítico:

$$|Z_{\text{batch}}| \ge z_{\text{conflict}} \quad (\text{por defecto } z_{\text{conflict}} = 2.0)$$

Se emite un registro inmutable de disidencia [`DissentRecord`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/evidence.py#L12-L22):

$$\text{DissentRecord} = \big( \text{capability\_id}, \; \mu_{\text{prior}}, \; \sigma_{\text{prior}}, \; \bar{x}_{\text{batch}}, \; Z_{\text{batch}} \big)$$

### 5.2 El Doble Movimiento Epistemológico

Un diseño trivial podría descartar las observaciones discrepantes argumentando que son "ruido" o "valores atípicos". Otro diseño trivial podría simplemente promediarlas con el historial previo borrando el rastro del desacuerdo.

Symbiont ejecuta un **doble movimiento dialéctico**:

1. **Actualización Obligatoria:** El lote de lecturas se transfiere íntegramente al modelo de aclimatación para actualizar la línea base (`acclimation.observe(evidence)`). El organismo se adapta a la realidad de lo que observó.
2. **Preservación Inmutable de la Discordia:** El `DissentRecord` se almacena en una cola circular acotada ($\text{maxlen} = 256$). Cuando el generador narrativo (`symbiont.core.narrative`) construye explicaciones para el operador, declara explícitamente:
   > *"Esta creencia fue modificada hacia la nueva evidencia, pero al momento de la revisión existió una contradicción estadísticamente significativa ($Z = -3.42$)."*

Esto impide que el sistema proyecte una falsa certeza retrospectiva sobre su propio proceso de aprendizaje.
