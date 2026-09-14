# Plasticidad Endógena, Grafos Cognitivos Recurrentes y Dinámica de Activación

> **Estado:** PARCIALMENTE IMPLEMENTADO (v0.55/v0.56) / ESPECIFICADO (v0.57/v0.58)  
> **Tipo:** ARQUITECTURA DE RED RECURRENTE Y ESPECIFICACIÓN DE APRENDIZAJE  
> **Módulos relacionados:** [`symbiont.cognition.activation`](../../src/symbiont/cognition/activation.py), [`symbiont.cognition.graph`](../../src/symbiont/cognition/graph.py), [`symbiont.cognition.genome`](../../src/symbiont/cognition/genome.py)

---

## 1. El Paradigma de Plasticidad de Datos bajo Kernel Inmutable

El subsistema de cognición plástica de Symbiont implementa una red recurrente dispersa e interpretable sin requerir metaprogramación ni modificación del código fuente Python residente.

El modelo se organiza en cuatro capas de abstracción:

```text
  ┌──────────────────────────────────────────────────────────┐
  │                 KERNEL INMUTABLE [IMPLEMENTADO]          │
  │  Límites duros: N_max=128, C_max=32, E_max=1024, etc.    │
  │  Catálogo cerrado de tipos de nodo y aristas             │
  │  Modo seguro y cuotas de ejecución no aprendibles        │
  └────────────────────────────┬─────────────────────────────┘
                               │ Define rangos y límites
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 GENOMA DECLARATIVO [IMPLEMENTADO]        │
  │  Configuración heredable JSON validada contra esquema    │
  │  Presupuestos blandos, tasas base, ventanas de latencia  │
  └────────────────────────────┬─────────────────────────────┘
                               │ Configura el nacimiento
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 FENOTIPO PLÁSTICO [EN PROGRESO]          │
  │  Grafo recurrente activo: nodos, aristas, pesos w_ij     │
  │  Trazas de elegibilidad, conceptos latentes              │
  └────────────────────────────┬─────────────────────────────┘
                               │ Procesa cada tick
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 ESTADO DINÁMICO (EFÍMERO) [IMPLEMENTADO] │
  │  Activaciones a(t), entradas netas u(t), readouts        │
  └──────────────────────────────────────────────────────────┘
```

---

## 2. Normalización Sensorial No Lineal [IMPLEMENTADO]

> **Clasificación:** IDENTIDAD DEL CÓDIGO

Antes de ingresar al grafo cognitivo, las lecturas del sistema pasan por el normalizador [`SensoryNormalizer`](../../src/symbiont/cognition/activation.py).

Para una lectura continua $x_t \in \mathbb{R}$, se evalúa la desviación respecto a la media móvil local $\mu_{t-1}$ y su varianza $\sigma_{t-1}^2$:

$$\sigma_t = \sqrt{\max\big(\sigma_{t-1}^2, \; 10^{-6}\big)}$$

$$z_t = \frac{x_t - \mu_{t-1}}{\sigma_t}$$

Se aplica un recorte simétrico en $[-z_{\max}, z_{\max}]$ (por defecto $z_{\max} = 4.0$):

$$z_{\text{clip}} = \operatorname{clip}(z_t, -z_{\max}, z_{\max})$$

La activación sensorial $a_i(t) \in (-1, 1)$ se obtiene mediante compresión hiperbólica tangencial con factor de suavidad $s = 2.0$:

$$a_i(t) = \tanh\left( \frac{z_{\text{clip}}}{s} \right)$$

---

## 3. Dinámica de Activación del Grafo Recurrente [IMPLEMENTADO]

> **Clasificación:** IDENTIDAD DEL CÓDIGO / DETERMINISMO DE PROPAGACIÓN

El grafo [`CognitiveGraph`](../../src/symbiont/cognition/graph.py) opera sobre un catálogo cerrado de tipos:

- **Nodos:** `SENSE`, `CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT`.
- **Aristas:** `EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`.

### 3.1 Teorema de Causalidad Estricta y Doble Buffer

Sea $d_{ij} \in \{0, 1\}$ el retardo discreto de la arista que conecta el nodo $i$ con el nodo $j$.

**Invariante de Retardo Causal:**
$$d_{ij} = 0 \iff \operatorname{Kind}(i) = \text{SENSE}$$

Si la fuente $i$ es un nodo interno (`CONCEPT`, `STATE`, etc.), **obligatoriamente** $d_{ij} = 1$.

*Consecuencia Algorítmica:*
La activación de cualquier nodo interno en el instante $t$ depende únicamente de las entradas sensoriales en $t$ y del vector de activaciones del paso previo $t-1$:

$$\mathbf{a}_{\text{internal}}(t) = \mathbf{f}\Big( \mathbf{a}_{\text{sense}}(t), \; \mathbf{a}_{\text{internal}}(t-1) \Big)$$

Esto elimina dependencias circulares instantáneas (ciclos algebraicos de retardo 0) y hace que la activación sea invariante respecto al orden de recorrido de los nodos en memoria.

### 3.2 Compuertas Multiplicativas (*Gating Factor*)

Para un nodo $j$, sea $\mathcal{E}_{\text{gate}}(j)$ el conjunto de aristas entrantes de tipo `GATING`.
El factor de compuerta $G_j(t) \in [0, 1]$ modula multiplicativamente la entrada:

$$G_j(t) = \begin{cases}
1.0 & \text{si } \mathcal{E}_{\text{gate}}(j) = \emptyset \\
\prod_{e \in \mathcal{E}_{\text{gate}}(j)} \operatorname{clip}\Big( w_e \cdot a_{\text{source}(e)}(t - d_e), \; 0.0, \; 1.0 \Big) & \text{en otro caso}
\end{cases}$$

### 3.3 Entrada Neta y Activación
Sea $\mathcal{E}_{\text{signal}}(j)$ el conjunto de aristas entrantes no-gating.
La entrada neta $u_j(t)$ integra el sesgo propio $b_j \in \mathbb{R}$ (validado como finito en la inicialización) y la suma ponderada modulada:

$$u_j(t) = b_j + G_j(t) \cdot \sum_{e \in \mathcal{E}_{\text{signal}}(j)} w_e \cdot a_{\text{source}(e)}(t - d_e)$$

La activación final utiliza la constante de escala temporal $\tau_j \in [0.1, 10.0]$:

$$a_j(t) = \tanh\left( \frac{u_j(t)}{\tau_j} \right) \in (-1, 1)$$

---

## 4. Invariante de Acotamiento Global de Activaciones [IMPLEMENTADO]

> **Clasificación:** PROPOSICIÓN / IDENTIDAD DEL ALGORITMO

**Proposición (Acotamiento Estricto de Activaciones):**  
Para cualquier secuencia de entradas finitas y cualquier grafo admisible bajo los límites del kernel:

$$\|\mathbf{a}(t)\|_\infty < 1.0 \quad \forall t \ge 0$$

*Demostración:*
1. Para cada nodo sensorial: $a_i(t) = \tanh(z_{\text{clip}} / s)$. Como $\tanh(x) \in (-1, 1)$ para todo $x \in \mathbb{R}$, se cumple $|a_i(t)| < 1.0$.
2. Para cada nodo interno $j$, los pesos están acotados por kernel en $w \in [-2.0, 2.0]$. El grado de entrada entrante cumple $\deg^-(j) \le E_{\max} = 1024$.
3. Asumiendo que el sesgo $b_j$ es finito:
   $$|u_j(t)| \le |b_j| + 1.0 \cdot \sum_{e \in \mathcal{E}_{\text{signal}}(j)} |w_e| \cdot 1.0 \le |b_j| + \deg^-(j) \cdot 2.0 < +\infty$$
4. Dado que $\tau_j \ge 0.1 > 0$, el argumento $u_j(t) / \tau_j$ es estrictamente finito. Por las propiedades asintóticas de la tangente hiperbólica:
   $$|a_j(t)| = \left| \tanh\left(\frac{u_j(t)}{\tau_j}\right) \right| < 1.0 \quad \blacksquare$$

> **Matiz de Estabilidad Dinámica:**  
> Esta proposición demuestra **acotamiento de activaciones y ausencia de explosión numérica (`NaN` o `inf`)**.  
> **No demuestra estabilidad asintótica de Lyapunov**, contracción, unicidad de puntos fijos ni convergencia a estados estacionarios. Una red recurrente de este tipo, incluso con activaciones acotadas en $(-1, 1)$, puede exhibir oscilaciones persistentes, ciclos límite o dinámicas caóticas si la matriz de pesos tiene autovalores de módulo superior a 1.

---

## 5. Reglas de Aprendizaje Local y Plasticidad [ESPECIFICADO]

> **Clasificación:** ESPECIFICACIÓN DE APRENDIZAJE (ROADMAP v0.57)

### 5.1 Regla de Oja Estabilizada
Para aristas asociativas entre nodos plásticos, la especificación incorpora la regla normalizadora de Oja (1982):

$$\Delta w_{ij}(t) = \eta_{ij} \cdot m(t) \cdot \Big[ a_i(t - d_{ij}) \cdot a_j(t) - a_j(t)^2 \cdot w_{ij}(t) \Big]$$

donde:
- $\eta_{ij}$ es la tasa de aprendizaje modulada por la plasticidad de la arista.
- $m(t) \in [0, 1]$ es el modulador local (atención, salud perceptual y estabilidad).

> **Matiz de Rigor sobre la Regla de Oja:**  
> La regla discreta de Oja introduce una **presión de decaimiento cuadrático** que, bajo condiciones continuas estacionarias e iteraciones infinitesimales, limita el crecimiento y orienta los pesos hacia los autovectores principales.  
> Sin embargo, en una red recurrente con pasos discretos finitos, compuertas multiplicativas y clipping, no garantiza matemáticamente que $\|\mathbf{w}\|_2 \le 1$ en cada tick. El acotamiento duro de los pesos en Symbiont proviene de la guarda del kernel:
> $$w_{ij} \in [-2.0, 2.0]$$

### 5.2 Trazas de Elegibilidad Temporal [ESPECIFICADO]
Para asociar activaciones previas con consecuencias diferidas:

$$q_{ij}(t) = \lambda_{\text{elig}} \cdot q_{ij}(t-1) + a_i(t - d_{ij}) \cdot a_j(t)$$

con $\lambda_{\text{elig}} \in [0.80, 0.98]$ gobernado por el genoma declarativo ([`symbiont.cognition.genome`](../../src/symbiont/cognition/genome.py)).
