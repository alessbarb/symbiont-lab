# Percepción, Aclimatación Sensorial y Álgebra de Relaciones

## 1. Motivación y Principios de Diseño

En Symbiont, el sistema perceptor no asume un conjunto fijo de sensores preconfigurados ni conoce a priori la escala, media o varianza de las señales del anfitrión. Para interactuar con un sistema real o sintético sin violar la privacidad y sin almacenar telemetría cruda (lo que violaría los requisitos de seguridad y memoria acotada), se diseñan operadores en línea capaces de:

1. Aprender estadísticas descriptivas de orden 1 (media) y orden 2 (varianza) con complejidad espacial $O(1)$.
2. Medir la correlación lineal y la precedencia temporal entre pares de señales desconocidas.
3. Asignar valor dinámico de utilidad a cada señal basándose en su contenido de información (variabilidad y movimiento) ponderado por su fiabilidad (disponibilidad).
4. Podar redundancias collinear sin requerir inversión matricial ni descomposición en componentes principales completa ($O(N^3)$).

---

## 2. El Algoritmo de Welford Univariado

Para estimar la media muestral $\bar{x}_n$ y la varianza muestral insesgada $s_n^2$ de una secuencia infinita de observaciones $x_1, x_2, \dots, x_n \in \mathbb{R}$, la formulación ingenua de libro de texto:

$$\bar{x}_n = \frac{1}{n} \sum_{i=1}^n x_i, \quad s_n^2 = \frac{1}{n-1} \left( \sum_{i=1}^n x_i^2 - n \bar{x}_n^2 \right)$$

sufre de **cancelación catastrófica** en aritmética de punto flotante de precisión simple o doble (IEEE 754). Cuando la varianza es pequeña en comparación con el cuadrado de la media ($\sigma^2 \ll \mu^2$), los términos $\sum x_i^2$ y $n \bar{x}_n^2$ tienen magnitudes casi idénticas, provocando la pérdida total de dígitos significativos y arrojando con frecuencia valores negativos de varianza ($\sigma^2 < 0$), lo que produce errores de ejecución (`math domain error` al calcular $\sqrt{\sigma^2}$).

### 2.1 Ecuaciones de Recurrencia

Symbiont implementa el algoritmo en línea de Welford (1962) en [`RunningStats`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/acclimation.py#L51-L76) y [`SenseState`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/adaptive.py#L28-L74):

Sea $M_{2, n} = \sum_{i=1}^n (x_i - \bar{x}_n)^2$ la suma de desviaciones cuadráticas respecto a la media acumulada hasta el paso $n$.

Al recibir la observación $x_n$:

$$\begin{aligned}
n &\leftarrow n + 1 \\
\delta_n &= x_n - \mu_{n-1} \\
\mu_n &= \mu_{n-1} + \frac{\delta_n}{n} \\
M_{2, n} &= M_{2, n-1} + \delta_n \cdot (x_n - \mu_n)
\end{aligned}$$

### 2.2 Demostración de Consistencia
Demostraremos algebraicamente la actualización de $M_2$:

**Lema:** $x_n - \mu_n = \delta_n \left( 1 - \frac{1}{n} \right) = \delta_n \frac{n-1}{n}$.

*Demostración:*
$$x_n - \mu_n = x_n - \left( \mu_{n-1} + \frac{x_n - \mu_{n-1}}{n} \right) = (x_n - \mu_{n-1}) - \frac{x_n - \mu_{n-1}}{n} = \delta_n \left( 1 - \frac{1}{n} \right)$$

Ahora expandimos $M_{2, n}$:
$$M_{2, n} = \sum_{i=1}^n (x_i - \mu_n)^2 = \sum_{i=1}^{n-1} (x_i - \mu_n)^2 + (x_n - \mu_n)^2$$

Dado que $x_i - \mu_n = (x_i - \mu_{n-1}) + (\mu_{n-1} - \mu_n) = (x_i - \mu_{n-1}) - \frac{\delta_n}{n}$:

$$\begin{aligned}
\sum_{i=1}^{n-1} (x_i - \mu_n)^2 &= \sum_{i=1}^{n-1} \left( (x_i - \mu_{n-1}) - \frac{\delta_n}{n} \right)^2 \\
&= \sum_{i=1}^{n-1} (x_i - \mu_{n-1})^2 - \frac{2\delta_n}{n} \underbrace{\sum_{i=1}^{n-1} (x_i - \mu_{n-1})}_{= 0} + (n-1) \frac{\delta_n^2}{n^2} \\
&= M_{2, n-1} + \frac{n-1}{n^2} \delta_n^2
\end{aligned}$$

Sumando el término del paso $n$:
$$(x_n - \mu_n)^2 = \left( \frac{n-1}{n} \delta_n \right)^2 = \frac{(n-1)^2}{n^2} \delta_n^2$$

Por tanto:
$$M_{2, n} = M_{2, n-1} + \frac{n-1}{n^2} \delta_n^2 + \frac{(n-1)^2}{n^2} \delta_n^2 = M_{2, n-1} + \frac{n(n-1)}{n^2} \delta_n^2 = M_{2, n-1} + \frac{n-1}{n} \delta_n^2$$

Dado que $\delta_n (x_n - \mu_n) = \delta_n \left( \frac{n-1}{n} \delta_n \right) = \frac{n-1}{n} \delta_n^2$, la igualdad queda demostrada:
$$M_{2, n} = M_{2, n-1} + \delta_n (x_n - \mu_n) \quad \blacksquare$$

### 2.3 Cálculo de Varianza y Desviación Típica
La varianza muestral se calcula como:

$$\sigma_n^2 = \begin{cases}
\frac{M_{2, n}}{n} & \text{en } \texttt{RunningStats} \text{ (máxima verosimilitud)} \\
\frac{M_{2, n}}{n-1} & \text{en } \texttt{SenseState} \text{ (estimador insesgado de Bessel)}
\end{cases}$$

$$\sigma_n = \sqrt{\max(0.0, \sigma_n^2)}$$

### 2.4 Propiedad de Reconstrucción Exacta sin Retención Cruda
Un requisito no negociable de seguridad es que el checkpoint no contenga muestras crudas pasadas. Al serializar [`CapabilityBaseline`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/acclimation.py#L12-L49), se guardan únicamente $(n, \mu, \sigma^2)$. Al restaurar, el acumulador $M_2$ se regenera de forma exacta mediante:

$$M_2 = \sigma^2 \cdot n$$

lo que permite reanudar las actualizaciones de Welford sin discontinuidades ni distorsión numérica.

---

## 3. Algoritmo de Welford Bivariado para Correlación en Línea

Para descubrir relaciones funcionales entre capacidades del sistema (por ejemplo, entre uso de CPU y temperatura o tráfico de red), el sistema utiliza [`PairAccumulator`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/adaptive.py#L113-L200).

Tradicionalmente, la covarianza se computa acumulando sumas crudas: $\sum x_i, \sum y_i, \sum x_i y_i$. Sin embargo, cuando las señales son contadores monótonos crecientes del kernel Linux (con valores como $10^{14}$ bytes transferidos), $\sum x_i y_i$ desborda la mantisa de 53 bits de coma flotante, anulando la correlación.

### 3.1 Momento Conjunto Centrado (Co-momento)
Symbiont mantiene el co-momento centrado $C_{xy, n} = \sum_{i=1}^n (x_i - \bar{x}_n)(y_i - \bar{y}_n)$.

Al recibir el par ordenado $(x_n, y_n)$:

$$\begin{aligned}
n &\leftarrow n + 1 \\
dx_n &= x_n - \mu_{x, n-1} \\
\mu_{x, n} &= \mu_{x, n-1} + \frac{dx_n}{n} \\
dy_n &= y_n - \mu_{y, n-1} \\
\mu_{y, n} &= \mu_{y, n-1} + \frac{dy_n}{n} \\
C_{xy, n} &= C_{xy, n-1} + dx_n \cdot (y_n - \mu_{y, n}) \\
M_{2, x, n} &= M_{2, x, n-1} + dx_n \cdot (x_n - \mu_{x, n}) \\
M_{2, y, n} &= M_{2, y, n-1} + dy_n \cdot (y_n - \mu_{y, n})
\end{aligned}$$

### 3.2 Coeficiente de Correlación de Pearson
El coeficiente de correlación lineal $r \in [-1, 1]$ se obtiene en $O(1)$:

$$r(X, Y) = \begin{cases}
\text{indefinido (None)} & \text{si } n < 3 \lor M_{2, x} \le 10^{-18} \lor M_{2, y} \le 10^{-18} \\
\operatorname{clip}\left( \frac{C_{xy}}{\sqrt{M_{2, x} \cdot M_{2, y}}}, -1.0, 1.0 \right) & \text{en otro caso}
\end{cases}$$

---

## 4. Dinámica Temporal: Correlación Síncrona vs. Desfasada

Para inferir estructura causal sin imponer modelos semánticos externos, cada relación [`SensoryRelation`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/adaptive.py#L203-L252) mantiene tres acumuladores bivariados independientes:

```text
Tick t-1:       x(t-1)                     y(t-1)
                   │  ╲                   ╱  │
                   │   ╲   Lagged a→b    ╱   │
                   │    ╲               ╱    │
                   │     ▼             ▼     │
Tick t:         x(t) ◄─── Synchronous ───► y(t)
                         Lagged b→a
```

1. **Correlación Síncrona ($r_{\text{sync}}$):**
   Mide la co-activación instantánea en el mismo tick:
   $$r_{\text{sync}} = r\big(x(t), y(t)\big)$$

2. **Precedencia Temporal de $A$ hacia $B$ ($r_{a \to b}$):**
   Mide la capacidad de la señal $A$ en el paso previo para anticipar a la señal $B$:
   $$r_{a \to b} = r\big(x(t-1), y(t)\big)$$

3. **Precedencia Temporal de $B$ hacia $A$ ($r_{b \to a}$):**
   $$r_{b \to a} = r\big(y(t-1), x(t)\big)$$

**Fuerza de la Relación:**
Para priorizar qué pares merecen atención en el modelo adaptativo, se define:

$$\text{Strength}(A, B) = \max\Big( |r_{\text{sync}}|, |r_{a \to b}|, |r_{b \to a}| \Big)$$

---

## 5. Función de Utilidad Dinámica Sensorial

El organismo debe resolver de manera autónoma un problema de asignación sensorial: entre cientos de superficies del sistema operativo disponibles (sensores de disco, memoria, interfaces virtuales, etc.), ¿cuáles merecen muestreo rutinario?

En [`SenseState.utility`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/adaptive.py#L49-L56), la utilidad $U \in [0, 1]$ se calcula mediante tres variables no-semánticas:

### 5.1 Componentes de la Utilidad

1. **Disponibilidad ($A$):**
   Fracción de intentos en los que el sensor produjo un valor numérico válido y no nulo:
   $$A = \frac{N_{\text{available}}}{N_{\text{samples}}} \in [0, 1]$$

2. **Escala Invariante ($S$):**
   Factor de normalización que combina magnitud absoluta y dispersión:
   $$S = |\mu| + \sigma + \epsilon, \quad \text{donde } \epsilon = 10^{-12}$$

3. **Variabilidad Relativa Normalizada ($V$):**
   Una señal que permanece constante (varianza cero) no transporta información sobre el estado del anfitrión:
   $$V = \min\left( 1.0, \frac{\sigma}{S} \right) \in [0, 1]$$

4. **Cinemática del Cambio / Movimiento ($M$):**
   Se rastrea la media móvil exponencial (EWMA) de los incrementos absolutos sucesivos entre ticks contiguos con lectura:
   $$\Delta_{\text{raw}}(t) = |x(t) - x(t_{\text{prev}})|$$
   $$\Delta_{\text{ewma}}(t) = 0.20 \cdot \Delta_{\text{raw}}(t) + 0.80 \cdot \Delta_{\text{ewma}}(t-1)$$
   $$M = \min\left( 1.0, \frac{\Delta_{\text{ewma}}}{S} \right) \in [0, 1]$$

### 5.2 Formulación Cerrada de la Utilidad
Si $N_{\text{available}} < 2$, $U = 0.0$. En caso contrario:

$$U(s) = A \cdot \Big( 0.65 \cdot V + 0.35 \cdot M \Big)$$

Esta fórmula pondera con un $65\%$ la amplitud de la distribución de la señal y con un $35\%$ la vivacidad de su dinamismo temporal, escalado todo por la probabilidad de que la lectura esté disponible.

---

## 6. Selección y Poda de Redundancia Collineal

Dado un conjunto de sentidos candidatos ordenados por utilidad decreciente $U_1 \ge U_2 \ge \dots \ge U_k$:

Un sentido candidato $s_j$ se declara **redundante** respecto al conjunto ya seleccionado $\mathcal{S}_{\text{sel}}$ si existe algún $s_i \in \mathcal{S}_{\text{sel}}$ con suficiente soporte histórico ($N_{\text{samples}} \ge 6$) tal que:

$$|r_{\text{sync}}(s_i, s_j)| \ge \theta_{\text{redundancy}} \quad (\text{por defecto } \theta_{\text{redundancy}} = 0.97)$$

Si se declara redundante, $s_j$ se excluye de la cuota principal (límite activo $K_{\text{active}} = 24$) y se relega a la lista de reserva, garantizando que el espacio sensorial abarque dimensiones informacionales no collineales.

---

## 7. Planificación de Muestreo: Sondas Rotativas y Cursor Circular

Para evitar que una mala estimación inicial descarte permanentemente una señal útil (*ceguera temprana irreversible*), el organismo divide los sentidos en tres estratos:

1. **Activos:** Rutinariamente muestreados cada tick.
2. **Desconocidos / Latentes:** Aún no observados o por debajo de $N_{\text{min}}$.
3. **Dormidos (*Dormant*):** Conocidos pero actualmente no seleccionados por el filtro de utilidad/redundancia.

Sea $\mathcal{P} = \text{Unknown} \cup \text{Dormant}$ el grupo de exploración, con tamaño $P = |\mathcal{P}|$.
Sea $B_{\text{probe}}$ el presupuesto de sondeo ($B_{\text{probe}} = 4$ en régimen regular, $B_{\text{probe}} = 32$ en régimen de arranque).

El cursor circular $c \in \mathbb{N}_0$ selecciona los índices:

$$\text{Indices} = \left\{ (c + i) \pmod P \;\middle|\; i = 0, 1, \dots, \min(B_{\text{probe}}, P) - 1 \right\}$$

$$c \leftarrow c + \min(B_{\text{probe}}, P)$$

Para garantizar reproducibilidad e invariancia respecto al orden de los diccionarios de Python, los candidatos se ordenan lexicográficamente por su clave criptográfica:

$$\text{order\_key}(c_k) = \operatorname{SHA-256}(\text{"symbiont-sampling:"} \parallel c_k)$$

Esto produce una cobertura ergódica determinista donde cada señal latente vuelve a ser sondeada periódicamente sin intervención de números pseudoaleatorios ni llamadas al sistema operativo.
