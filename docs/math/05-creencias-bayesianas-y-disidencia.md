# Dinámica de Creencias, Sorpresa Epistémica y Registro de Disidencia

> **Estado:** IMPLEMENTADO  
> **Tipo:** FILTRO ADAPTATIVO CON MOTIVACIÓN BAYESIANA  
> **Módulos relacionados:** [`symbiont.core.beliefs`](../../src/symbiont/core/beliefs.py), [`symbiont.core.evidence`](../../src/symbiont/core/evidence.py)

---

## 1. La Naturaleza de las Creencias en Symbiont

En Symbiont, una creencia no es una etiqueta determinista, sino una distribución subjetiva que evoluciona ante percepciones locales ruidosas ([`symbiont.core.beliefs`](../../src/symbiont/core/beliefs.py)).

El modelo persigue cuatro propiedades operativas:

1. **Acumulación Suave:** A medida que se observan evidencias consistentes, la certeza subjetiva se incrementa.
2. **Reversibilidad:** Si el comportamiento del anfitrión cambia, la creencia puede cruzar la frontera de decisión ($p \ge 0.5 \leftrightarrow p < 0.5$).
3. **Sensibilidad al Conflicto:** Si observaciones sucesivas discrepan entre sí, la certeza decae.
4. **Preservación de la Disidencia:** Si un lote de evidencia discrepa fuertemente de la línea base establecida, el desacuerdo se registra de forma inmutable como un evento histórico explícito ([`symbiont.core.evidence`](../../src/symbiont/core/evidence.py)).

---

## 2. El Modelo de Actualización con Pseudo-Observaciones

Cada patrón o firma abstracta $\text{fp}$ mapea a un estado [`BeliefState`](../../src/symbiont/core/beliefs.py):

$$\mathbf{b} = (p, E, C) \in [0, 1] \times [0, E_{\max}] \times [0, 1]$$

donde $p$ es la probabilidad a posteriori estimada, $E$ es la masa de evidencia acumulada ($E_{\max} = 32.0$), y $C$ es la memoria exponencial de conflicto acumulado.

### 2.1 Ecuación de Actualización

Al observar una probabilidad $P_{\text{obs}} \in [0, 1]$ con confianza $c_{\text{obs}} \in [0, 1]$:

$$w = \max(0.05, c_{\text{obs}})$$

$$P_{\text{posterior}} = \frac{P_{\text{prior}} \cdot E + P_{\text{obs}} \cdot w}{E + w}$$

### 2.2 Interpretación Bayesiana y Límite de Saturación

Durante la fase **no saturada** ($E + w \le E_{\max}$), esta regla es matemáticamente isomórfica a la actualización de la media de una distribución Beta conjugada $\text{Beta}(\alpha, \beta)$ con $E = \alpha + \beta$.

> **Matiz de Inferencia Bayesiana:**  
> Cuando la evidencia acumulada alcanza el tope configurado $E_{\max} = 32.0$, la actualización aplica:
>
> $$E_{t} = \min(32.0, \; E_{t-1} + w) = 32.0$$
>
> La probabilidad $P_{\text{posterior}}$ se computa temporalmente con denominador $E + w$, pero en el paso siguiente el estado se almacena con masa 32.0. Por tanto, tras la saturación, el sistema **deja de ser un estimador bayesiano conjugado exacto** y opera como un **filtro adaptativo de masa finita**, diseñado para prevenir la parálisis epistémica y permitir la reversión de creencias ante nueva evidencia sostenida.

---

## 3. Dinámica del Conflicto y Sorpresa

La sorpresa mide la discrepancia absoluta instantánea:

$$S_t = |P_{\text{obs}} - P_{\text{prior}}| \in [0, 1]$$

### 3.1 Filtro de Conflicto Acumulado

El conflicto $C_t$ integra la sorpresa en el tiempo como un filtro paso bajo:

$$C_t = \min\Big( 1.0, \; 0.75 \cdot C_{t-1} + 0.25 \cdot S_t \Big)$$

- Si las observaciones confirman la expectativa ($S_t \approx 0$), el conflicto decae hacia cero con vida media de $\approx 2.4$ pasos.
- Si las observaciones oscilan continuamente entre extremos ($S_t \approx 1$), $C_t$ satura en $1.0$.

### 3.2 Reversiones de Creencia (*Belief Reversals*)

Una reversión se registra cuando la probabilidad cruza la frontera de decisión ($0.5$) respecto al paso anterior, habiendo existido revisiones previas:

$$\text{Reversal}_t = \mathbb{I}\Big( (P_{\text{prior}} \ge 0.5) \neq (P_{\text{posterior}} \ge 0.5) \land \text{revisions} > 0 \Big)$$

---

## 4. Función de Certeza Subjetiva y Análisis de Dimensiones

La certeza $\text{Certainty} \in [0, 1]$ en [`BeliefState.certainty`](../../src/symbiont/core/beliefs.py) se define como:

$$\text{Certainty}(E, C) = \operatorname{clip}\left( \Big( 1 - e^{-E / 4.0} \Big) \cdot \Big( 1 - 0.60 \cdot C \Big), \; 0.0, \; 1.0 \right)$$

```text
Certainty
   ▲
1.0│              C = 0.0 (Sin conflicto)
   │             .───────────────────────  1 - exp(-E/4)
0.8│          .─'
   │       .─'    C = 0.5 (Conflicto moderado)
   │     .─'─────────────────────────────  0.7 * [1 - exp(-E/4)]
0.4│ .─'          C = 1.0 (Máximo conflicto)
   │.────────────────────────────────────  0.4 * [1 - exp(-E/4)]
0.0└──────┬──────┬──────┬──────┬──────► Masa de Evidencia E
   0      4      8      16     32
```

### 4.1 Distinción Conceptual: Certeza, Polarización y Conflicto

Para evitar ambigüedades pedagógicas, el compendio formaliza tres dimensiones ortogonales:

1. **Fuerza o Madurez de la Creencia ($E$):** Masa acumulada de observaciones.
2. **Polarización de la Probabilidad ($|p - 0.5|$):** Proximidad a los extremos deterministas (0 o 1).
3. **Conflicto Histórico ($C$):** Nivel acumulado de sorpresa y contradicción reciente.

> **Aclaración sobre $p = 0.5$:**  
> Un estado con $p = 0.5, E = 32.0, C = 0.0$ genera una certeza de:
> $$\text{Certainty} = 1 - e^{-32/4} = 1 - e^{-8} \approx 0.999665$$
> Esto indica una **alta confianza en la estabilidad de la estimación**, no una demostración ontológica de que el fenómeno sea una moneda perfecta. Refleja que, bajo la evidencia observada, la probabilidad subjetiva se ha estabilizado de forma consistente en el centro sin oscilaciones.

---

## 5. Discrepancia Estandarizada del Lote y Registro de Disidencia

Cuando el organismo ejecuta una inspección de alta resolución (*second look*), recopila un lote de lecturas discretas $\mathcal{X}_{\text{batch}} = \{x_1, \dots, x_m\}$.

[`EvidenceRevisionLedger`](../../src/symbiont/core/evidence.py) evalúa si este lote choca con la línea base aclimatada $(\mu_{\text{prior}}, \sigma_{\text{prior}})$.

### 5.1 Discrepancia Estandarizada del Desplazamiento

Se calcula la media del lote $\bar{x}_{\text{batch}} = \frac{1}{m}\sum x_i$ y se evalúa el desplazamiento:

$$Z_{\text{batch}} = \frac{\bar{x}_{\text{batch}} - \mu_{\text{prior}}}{\sigma_{\text{prior}}}$$

> **Distinción con el Test Z Clásico:**  
> La formulación $Z_{\text{batch}}$ **no divide por $\sqrt{m}$**. Por tanto, no es una prueba de significación estadística para contrastar si la media muestral proviene de la población (cuyo estadístico sería $\frac{\bar{x} - \mu}{\sigma / \sqrt{m}}$). En Symbiont, $Z_{\text{batch}}$ representa una **medida heurística del tamaño del desplazamiento en desviaciones estándar de la línea base**.

### 5.2 Emisión y Preservación de la Disidencia

Si la línea base previa está aclimatada ($\sigma_{\text{prior}} > 0$) y la discrepancia supera el umbral:

$$|Z_{\text{batch}}| \ge z_{\text{conflict}} \quad (\text{por defecto } z_{\text{conflict}} = 2.0)$$

Se genera un registro inmutable [`DissentRecord`](../../src/symbiont/core/evidence.py):

$$\text{DissentRecord} = \big( \text{capability\_id}, \; \mu_{\text{prior}}, \; \sigma_{\text{prior}}, \; \bar{x}_{\text{batch}}, \; Z_{\text{batch}} \big)$$

El organismo aplica un doble movimiento deliberado:

1. **Adapta la línea base:** Las lecturas se transfieren a la aclimatación (`acclimation.observe`), permitiendo que el organismo asimile la realidad observada.
2. **Preserva la discordia:** El registro de desacuerdo se guarda en una cola circular de tamaño 256, permitiendo a la capa narrativa ([`symbiont.core.narrative`](../../src/symbiont/core/narrative.py)) reportar al operador humano que la creencia fue modificada bajo condiciones de contestación estadística.
