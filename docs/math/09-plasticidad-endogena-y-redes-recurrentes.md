# Plasticidad Endógena, Grafos Cognitivos Recurrentes y Dinámica de Activación

## 1. El Paradigma de Plasticidad de Datos bajo Kernel Inmutable

El sistema de cognición plástica de Symbiont ([`symbiont.cognition`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/cognition)) implementa un modelo formal de red recurrente dispersa e interpretable sin requerir compilación dinámica, metaprogramación ni modificación del código Python residente.

El modelo opera bajo una jerarquía estratificada no modificable:

```text
  ┌──────────────────────────────────────────────────────────┐
  │                 KERNEL INMUTABLE                         │
  │  Límites duros: N_max=128, C_max=32, E_max=1024, etc.    │
  │  Catálogo cerrado de tipos de nodo y aristas             │
  │  Modo seguro y cuotas de memoria/tiempo no aprendibles   │
  └────────────────────────────┬─────────────────────────────┘
                               │ Define rangos y límites
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 GENOMA DECLARATIVO                       │
  │  Configuración heredable JSON sin código ejecutable      │
  │  Presupuestos blandos, tasas base, ventanas de latencia  │
  └────────────────────────────┬─────────────────────────────┘
                               │ Configura el nacimiento
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 FENOTIPO PLÁSTICO                        │
  │  Grafo recurrente activo: nodos, aristas, pesos w_ij     │
  │  Trazas de elegibilidad, conceptos latentes, metaparám.  │
  └────────────────────────────┬─────────────────────────────┘
                               │ Procesa cada tick
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 ESTADO DINÁMICO (EFÍMERO)                │
  │  Activaciones a(t), entradas netas u(t), errores e(t)    │
  └──────────────────────────────────────────────────────────┘
```

El principio matemático rector es:
> *Symbiont puede cambiar **qué aprende, cuánto aprende y cómo organiza su grafo**, pero no puede cambiar **qué operaciones tiene permitidas ni violar los límites de Lyapunov del kernel**.*

---

## 2. Normalización Sensorial Robusta

Antes de ingresar al grafo cognitivo, las lecturas crudas de cualquier sensor pasan por el normalizador no lineal [`SensoryNormalizer`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/cognition/activation.py).

Para una lectura cruda $x_t \in \mathbb{R}$:
Se calcula la puntuación $Z$ estandarizada contra la media móvil y varianza móvil locales:

$$\sigma_t = \sqrt{\max\big(\sigma_{t-1}^2, \; 10^{-6}\big)}$$

$$z_t = \frac{x_t - \mu_{t-1}}{\sigma_t}$$

Para eliminar el impacto de valores atípicos patológicos, se aplica un truncamiento rígido en $[-z_{\max}, z_{\max}]$ (por defecto $z_{\max} = 4.0$):

$$z_{\text{clip}} = \operatorname{clip}(z_t, -z_{\max}, z_{\max})$$

La activación sensorial $a_i(t) \in (-1, 1)$ se produce mediante una compresión sigmoidal tangencial con factor de suavizado $s = 2.0$:

$$a_i(t) = \tanh\left( \frac{z_{\text{clip}}}{s} \right)$$

```text
Activación a_i(t)
   ▲
1.0│                                    .──────── tanh(z_clip / 2)
   │                             .─'
0.5│                       .─'
   │                 .─'
0.0│───────────────●────────────────────► Puntuación Z
   │          .─'
-0.5│      .─'
   │ .─'
-1.0│'──────── Truncamiento en z_max = ±4.0
   └───────────┬───────────┬───────────►
              -4.0         0.0        +4.0
```

### 2.1 Actualización de Estadísticas Sensoriales

Tras calcular la activación del paso actual, las estadísticas se actualizan mediante EWMA con $\alpha = 0.06$:

$$\begin{aligned}
\delta_t &= x_t - \mu_{t-1} \\
\mu_t &= \mu_{t-1} + \alpha \cdot \delta_t \\
\sigma_t^2 &= (1 - \alpha) \cdot \sigma_{t-1}^2 + \alpha \cdot \delta_t^2
\end{aligned}$$

---

## 3. Dinámica de Activación del Grafo Recurrente

El grafo cognitivo [`CognitiveGraph`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/cognition/graph.py) opera sobre un catálogo cerrado de tipos:
- **Tipos de Nodo:** `SENSE`, `CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT`.
- **Tipos de Arista:** `EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`.

### 3.1 Teorema de Causalidad Estricta y Doble Buffer
Sea $d_{ij} \in \{0, 1\}$ el retardo discreto de la arista que conecta el nodo $i$ con el nodo $j$.

**Axioma de Retardo Causal:**
$$d_{ij} = 0 \iff \operatorname{Kind}(i) = \text{SENSE}$$

Si la fuente $i$ es un nodo interno (`CONCEPT`, `STATE`, etc.), **obligatoriamente** $d_{ij} = 1$.

*Consecuencia Matemática:*
La activación de cualquier nodo interno en el instante $t$ depende exclusivamente del vector de entradas externas en $t$ y del vector de activaciones internas del instante previo $t-1$:

$$\mathbf{a}_{\text{internal}}(t) = \mathbf{f}\Big( \mathbf{a}_{\text{sense}}(t), \; \mathbf{a}_{\text{internal}}(t-1) \Big)$$

Esto garantiza que:
1. No existen dependencias circulares sincrónicas (ciclos algebraicos de retardo 0).
2. El resultado del ciclo es invariante respecto al orden de iteración de los diccionarios en memoria.
3. El cálculo es determinista y paralelizable en un paso de avance.

### 3.2 Compuertas Multiplicativas (*Gating Factor*)
Para un nodo destino $j$, sea $\mathcal{E}_{\text{gate}}(j)$ el conjunto de aristas entrantes de tipo `GATING`.
El factor de compuerta $G_j(t) \in [0, 1]$ modula multiplicativamente la entrada total:

$$G_j(t) = \begin{cases}
1.0 & \text{si } \mathcal{E}_{\text{gate}}(j) = \emptyset \\
\prod_{e \in \mathcal{E}_{\text{gate}}(j)} \operatorname{clip}\Big( w_e \cdot a_{\text{source}(e)}(t - d_e), \; 0.0, \; 1.0 \Big) & \text{en otro caso}
\end{cases}$$

### 3.3 Entrada Neta y Activación Hiperbólica
Sea $\mathcal{E}_{\text{signal}}(j)$ el conjunto de aristas entrantes no-gating (`EXCITATORY`, `INHIBITORY`, `PREDICTIVE`).

La entrada neta $u_j(t)$ integra el sesgo propio $b_j$ y la suma ponderada modulada:

$$u_j(t) = b_j + G_j(t) \cdot \sum_{e \in \mathcal{E}_{\text{signal}}(j)} w_e \cdot a_{\text{source}(e)}(t - d_e)$$

La activación final del nodo se normaliza mediante la constante de escala temporal (temperatura) $\tau_j \in [0.1, 10.0]$:

$$a_j(t) = \tanh\left( \frac{u_j(t)}{\tau_j} \right) \in (-1, 1)$$

---

## 4. Estabilidad Asintótica y Teorema de Acotamiento de Lyapunov

**Teorema de Acotamiento Global:**
Para cualquier secuencia de entradas finitas $\{x(t)\}_{t=0}^\infty$ y cualquier topología admisible de aristas bajo los límites de kernel:

$$\|\mathbf{a}(t)\|_\infty < 1.0 \quad \forall t \ge 0$$

*Demostración:*
1. Para cada nodo sensorial, por definición de la función sigmoide:
   $$a_i(t) = \tanh\left(\frac{z_{\text{clip}}}{s}\right) \implies |a_i(t)| < 1.0$$
2. Para cada nodo interno $j$, dado que los pesos están acotados por kernel $w \in [-2.0, 2.0]$, el número máximo de aristas entrantes es $E_{\max} \le 1024$ y los retardos aseguran $|a_{\text{source}}(t-1)| < 1.0$:
   $$|G_j(t)| \le 1.0$$
   $$|u_j(t)| \le |b_j| + 1.0 \cdot \sum_{e} |w_e| \cdot 1.0 \le |b_{\max}| + E_{\max} \cdot w_{\max} < +\infty$$
3. Como $\tau_j \ge 0.1 > 0$, el argumento $\frac{u_j(t)}{\tau_j}$ es estrictamente finito y pertenece a $\mathbb{R}$.
4. Como la función $\tanh(y)$ cumple $|\tanh(y)| < 1 \quad \forall y \in \mathbb{R}$ y es estrictamente monótona, se deduce que:
   $$|a_j(t)| < 1.0 \quad \forall j, \forall t \quad \blacksquare$$

No existen puntos fijos divergentes ni explosión numérica de gradientes. Todo el espacio de fases dinámico está contenido en el hipercubo compacto $[-1, 1]^N$.

---

## 5. Reglas de Aprendizaje Local y Metaplasticidad

El aprendizaje del fenotipo ocurre sin etiquetas externas mediante dos mecanismos complementarios:

### 5.1 Regla de Oja Estabilizada para Plasticidad Hebbiana
Para aristas asociativas descriptivas entre el nodo pre-sináptico $i$ y el post-sináptico $j$, la regla estándar de Hebb ($\Delta w = \eta a_i a_j$) es inestable porque introduce retroalimentación positiva que hace divergir los pesos a $\pm \infty$.

Symbiont adopta la **regla de normalización de Oja (1982)**:

$$\Delta w_{ij}(t) = \eta_{ij} \cdot m(t) \cdot \Big[ a_i(t - d_{ij}) \cdot a_j(t) - a_j(t)^2 \cdot w_{ij}(t) \Big]$$

donde:
- $\eta_{ij} \in [0.001, 0.08]$ es la tasa de aprendizaje modulada por la plasticidad de la arista.
- $m(t) \in [0, 1]$ es el modulador neuromodulador local (atención, salud perceptual y estabilidad).
- El término de desvanecimiento autorregulado $-a_j^2 w_{ij}$ surge de la aproximación de Taylor de primer orden de la normalización por la norma euclidiana:

$$\mathbf{w}_{t+1} = \frac{\mathbf{w}_t + \eta a_j \mathbf{a}_i}{\|\mathbf{w}_t + \eta a_j \mathbf{a}_i\|_2} \approx \mathbf{w}_t + \eta a_j (\mathbf{a}_i - a_j \mathbf{w}_t)$$

Esto confina automáticamente el vector de pesos a la esfera unidad $\|\mathbf{w}\|_2 \le 1.0$, garantizando convergencia sin necesidad de normalizaciones explícitas globales.

### 5.2 Trazas de Elegibilidad Temporal
Para vincular eventos pasados con consecuencias demoradas en el ciclo cognitivo, cada arista mantiene una traza de elegibilidad $q_{ij} \in \mathbb{R}$:

$$q_{ij}(t) = \lambda_{\text{elig}} \cdot q_{ij}(t-1) + a_i(t - d_{ij}) \cdot a_j(t)$$

donde $\lambda_{\text{elig}} \in [0.80, 0.98]$ es el factor de decaimiento temporal. La actualización efectiva de los metaparámetros se aplica únicamente sobre las aristas con soporte en su traza causal dentro de la ventana de atención.
