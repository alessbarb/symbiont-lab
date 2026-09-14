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

### 3.1 Causalidad Estricta y Eliminación de Ciclos Instantáneos

Sea $d_{ij} \in \{0, 1\}$ el retardo discreto de la arista que conecta el nodo fuente $i$ con el nodo destino $j$.

En [`CognitiveGraph`](../../src/symbiont/cognition/graph.py#L115-L124), el kernel impone dos restricciones topológicas fundamentales:

1. **Restricción de Origen para Retardo Cero:**
   $$d_{ij} = 0 \implies \operatorname{Kind}(i) = \text{SENSE}$$
   El retardo cero está permitido únicamente si la fuente es un nodo sensorial. Para cualquier nodo interno, obligatoriamente $d_{ij} = 1$:
   $$\operatorname{Kind}(i) \neq \text{SENSE} \implies d_{ij} = 1$$

2. **Prohibición de Aristas Entrantes hacia Sensores:**
   Para cualquier nodo $j$ tal que $\operatorname{Kind}(j) = \text{SENSE}$, el kernel prohíbe explícitamente aristas entrantes ([`graph.py` L122-L123](../../src/symbiont/cognition/graph.py#L122-L123)):
   $$\operatorname{deg}^-(j) = 0 \quad \forall j \text{ con } \operatorname{Kind}(j) = \text{SENSE}$$
   Las activaciones de los sensores se fijan de forma estrictamente exógena a partir de las lecturas del entorno en cada tick y no dependen de ninguna arista de la red.

**Demostración de Aciclicidad Instantánea:**  
Puesto que toda arista con retardo $d = 0$ parte de un nodo sensorial ($\operatorname{Kind}(i) = \text{SENSE}$) y finaliza en un nodo no sensorial ($\operatorname{Kind}(j) \neq \text{SENSE}$), el subgrafo inducido por las aristas de retardo cero $\mathcal{G}_0 = (\mathcal{V}, \mathcal{E}_0)$ es estrictamente un **grafo bipartito dirigido** desde $\text{SENSE}$ hacia $\mathcal{V} \setminus \text{SENSE}$.  
Como ningún nodo sensorial admite aristas entrantes, no puede existir ningún camino dirigido de retardo cero de longitud $\ge 2$ (lo que excluye tanto conexiones entre sensores como ciclos entre nodos internos). Por tanto, **el grafo carece de dependencias algebraicas instantáneas o ciclos de retardo cero**.

*Consecuencia Algorítmica:*  
Dado que los nodos sensoriales pueden emitir tanto aristas directas ($d=0$) como aristas con retardo unitario ($d=1$), la activación de los nodos internos en el instante $t$ depende de las entradas sensoriales del tick actual y del vector completo de activaciones del paso previo $t-1$:

$$\mathbf{a}_{\text{internal}}(t) = \mathbf{f}\Big( \mathbf{a}_{\text{sense}}(t), \; \mathbf{a}(t-1) \Big)$$

donde $\mathbf{a}(t-1) = \big(\mathbf{a}_{\text{sense}}(t-1), \; \mathbf{a}_{\text{internal}}(t-1)\big)$.

Esto elimina dependencias circulares instantáneas y hace que la activación sea invariante respecto al orden de recorrido de los nodos en memoria.

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

La activación final utiliza el **parámetro de escala de activación** $\tau_j \in [0.1, 10.0]$:

$$a_j(t) = \tanh\left( \frac{u_j(t)}{\tau_j} \right)$$

> **Precisión Terminológica:**  
> $\tau_j$ opera aquí como un parámetro de escala o factor de suavizado/temperatura que modula la pendiente de saturación en el origen ($\left.\frac{da_j}{du_j}\right|_{0} = \frac{1}{\tau_j}$). No debe confundirse con una «constante de escala temporal», ya que la formulación estática $a = \tanh(u / \tau)$ no incluye derivadas continuas ni términos autorregresivos propios.

---

## 4. Análisis de Acotamiento: Modelo Matemático, Implementación Numérica y Dinámica [IMPLEMENTADO]

> **Clasificación:** PROPOSICIÓN / IDENTIDAD DEL ALGORITMO

Para evaluar la estabilidad del grafo recurrente, es imprescindible separar rigurosamente tres dimensiones: el modelo analítico continuo, la aritmética de coma flotante y la dinámica recurrente.

### 4.1 Modelo Matemático (Números Reales)
Bajo álgebra sobre $\mathbb{R}$:
1. Para cada nodo sensorial: $a_i(t) = \tanh(z_{\text{clip}} / s)$. Como $z_{\text{clip}}$ es finito y $s = 2.0 > 0$, la propiedad analítica de la tangente hiperbólica establece:
   $$\tanh(x) \in (-1, 1) \quad \forall x \in \mathbb{R}$$
2. Para cada nodo interno $j$, los pesos satisfacen $w \in [-2.0, 2.0]$ y el grado entrante cumple $\deg^-(j) \le E_{\max} = 1024$. Asumiendo $b_j \in \mathbb{R}$ finito:
   $$|u_j(t)| \le |b_j| + 1.0 \cdot \deg^-(j) \cdot 2.0 < +\infty$$
3. Como $\tau_j \ge 0.1 > 0$, el argumento $u_j(t) / \tau_j$ es estrictamente finito. En consecuencia, sobre los números reales:
   $$a_j(t) \in (-1, 1) \implies |a_j(t)| < 1.0 \quad \forall t \ge 0$$

### 4.2 Implementación Numérica (Coma Flotante IEEE 754)
En la práctica computacional de punto flotante de 64 bits (`float` de Python / doble precisión IEEE 754):
- Para argumentos con magnitud $|x| \gtrsim 20$, `math.tanh(x)` satura numéricamente en $\pm 1.0$ (por ejemplo, `math.tanh(100) == 1.0`). La cota observable en memoria es por tanto **el intervalo cerrado $[-1.0, 1.0]$**, es decir, $|a| \le 1.0$.
- **Sobre la Ausencia de Desbordamientos en Operaciones Intermedias:**  
  Las validaciones descritas (comprobar que los sesgos iniciales sean finitos con `math.isfinite` y que $\tau_j \ge 0.1$) **no garantizan por sí solas operaciones intermedias finitas**. Esa garantía requiere límites de magnitud suficientes o un tratamiento explícito de los desbordamientos.  
  *Contraejemplo demostrativo:* Un nodo sin aristas entrantes con sesgo $b_j = 10^{308}$ satisface `math.isfinite(1e308) == True` y $\tau_j = 0.1 \ge 0.1$, pero la división intermedia $10^{308} / 0.1$ desborda a `inf`. Aunque en Python `math.tanh(float("inf"))` devuelve `1.0`, la operación intermedia produjo un desbordamiento en punto flotante. Por consiguiente, la ausencia de desbordamientos intermedios en la implementación está condicionada a los órdenes de magnitud prácticos de las entradas y sesgos o al control explícito de excepciones aritméticas.

### 4.3 Matiz sobre Estabilidad Dinámica
El acotamiento de activaciones en $[-1, 1]^N$ demuestra **confinamiento de la trayectoria en un conjunto compacto**, pero:
> **No demuestra estabilidad de Lyapunov ni convergencia.**  
> Un sistema no lineal en tiempo discreto $\mathbf{a}(t) = \tanh\left(\frac{1}{\tau} \mathbf{W} \mathbf{a}(t-1)\right)$ con activaciones confinadas en $[-1, 1]^N$ puede presentar atractores periódicos (ciclos límite), bifurcaciones de periodo o comportamiento caótico dependiente de las condiciones iniciales si los autovalores de la matriz de pesos $\mathbf{W}$ poseen módulo significativamente superior a la escala $\tau$.

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
