# Automodelo del Organismo, Costos y Cuantización No-Lineal

## 1. Justificación y Objetivos del Automodelo

Un organismo adaptativo que interactúa con un anfitrión real no puede asumir que todos sus sensores son eternamente funcionales, ni que todas las observaciones tienen el mismo costo en tiempo de cómputo.

- Sensores en hardware defectuoso o interfaces de red caídas pueden devolver periódicamente errores, datos corruptos o latencias exorbitantes.
- Si el organismo no posee un modelo de sus propias limitaciones perceptuales, continuará invirtiendo su presupuesto de atención en sensores muertos o inestables.

[`SelfModel`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py) formaliza un **automodelo acotado y no-semántico** que evalúa continuamente tres variables endógenas por cada sensor:

1. **Costo Computacional Atribuido:** Tiempo de ejecución medido en segundos.
2. **Salud Operativa:** Tasa de éxito y calidad de las lecturas.
3. **Confianza Epistémica del Sensor:** Función compuesta de salud, calidad y madurez histórica.

---

## 2. Dinámica Temporal: EWMA y Decaimiento con Zona de Gracia

Las métricas del automodelo se suavizan mediante un filtro EWMA con constante $\alpha = 0.06$ ([`SELF_MODEL_EWMA_ALPHA`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py#L10)):

$$\mu_t = \alpha \cdot x_t + (1 - \alpha) \cdot \mu_{t-1}$$

### 2.1 Ecuación de Relajación Inactiva (*Idle Decay*)

Cuando un sensor deja de ser muestreado durante $\Delta t = t_{\text{actual}} - t_{\text{último}}$ ticks:

- Si la ausencia es breve, el organismo debe preservar el conocimiento adquirido.
- Si la ausencia es prolongada, el estado debe relajarse exponencialmente hacia un valor neutro $x_{\text{neutral}}$ (por ejemplo, salud hacia $0.5$ o confianza hacia $0.0$).

Para lograr este comportamiento, se define una **zona de gracia** de $\tau_{\text{grace}} = 20$ ticks ([`IDLE_GRACE_TICKS`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py#L13)):

$$\text{steps} = \max\Big(0, \; \Delta t - \tau_{\text{grace}}\Big)$$

El valor relajado en el tick actual es:

$$x_{\text{decayed}}(\Delta t) = x_{\text{neutral}} + \big( x_{\text{last}} - x_{\text{neutral}} \big) \cdot (1 - \alpha)^{\text{steps}}$$

```text
Valor del Estado
   ▲
1.0│  x_last
   │  ─────────────┐ (Zona de gracia: primeros 20 ticks sin cambio)
   │               ╲
   │                ╲  Decaimiento: (1 - α)^steps
0.5│─────────────────●───────────────────────────  x_neutral (Salud = 0.5)
   │                  `─.
   │                     `───.
0.0└────────┬──────────────┬──────────────► Ticks Inactivos Δt
   0        20 (τ_grace)   50             100
```

---

## 3. Función de Madurez Logarítmica Normalizada

Para determinar cuándo un sensor está suficientemente consolidado para influir en las decisiones de atención, se define la madurez en función del número acumulado de éxitos $s \in \mathbb{N}_0$ ([`_maturity`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py#L61-L65)):

$$\operatorname{Maturity}(s) = \begin{cases}
0.0 & \text{si } s \le 0 \\
\min\left( 1.0, \; \frac{\ln(1 + s)}{\ln(1 + N_{\min})} \right) & \text{si } s > 0 \quad (\text{con } N_{\min} = 5)
\end{cases}$$

### 3.1 Ventajas Matemáticas del Perfil Logarítmico
En comparación con una rampa lineal $\frac{s}{N_{\min}}$:
1. **Crecimiento Rápido Inicial:** La derivada $\frac{d}{ds} \operatorname{Maturity} = \frac{1}{(1+s)\ln(1 + N_{\min})}$ es máxima en $s=0$, permitiendo que los primeros éxitos incrementen rápidamente la madurez.
2. **Concavidad y Rendimientos Decrecientes:** Refleja el principio bayesiano de que las primeras muestras aportan la mayor reducción de entropía.
3. **Cota Exacta:** En $s = N_{\min} = 5$, $\operatorname{Maturity}(5) = \frac{\ln(6)}{\ln(6)} = 1.0$.

### 3.2 Confianza Compuesta del Sensor
El objetivo de confianza instantáneo integra la salud operativa ($H$), la calidad intrínseca ($Q$) y la madurez:

$$\operatorname{Target}_{\text{conf}} = \operatorname{clip}\Big( 0.70 \cdot H + 0.30 \cdot Q, \; 0.0, \; 1.0 \Big) \cdot \operatorname{Maturity}(s)$$

Un sensor que reporte calidad nominal pero solo haya tenido 1 éxito poseerá una madurez de $\frac{\ln(2)}{\ln(6)} \approx 0.387$, restringiendo su confianza a $\le 0.387$ hasta acumular $5$ éxitos.

---

## 4. Normalización de Costo Relativo respecto a la Mediana Poblacional

Para informar al planificador de atención sin imponer umbrales fijos de hardware (un tick en una Raspberry Pi puede tomar 100 ms mientras que en un servidor Xeon toma 2 ms), el automodelo computa el costo relativo en [`relative_cost`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py#L129-L142).

Dado un subconjunto de capacidades de referencia consolidadas $\mathcal{R}_{\text{est}} = \{c_j \mid \text{established}_j\}$:

Se obtiene la mediana poblacional de los costos EWMA observados:

$$C_{\text{ref}} = \operatorname{median}\Big( \big\{ \text{cost\_ewma}_j \;\big|\; j \in \mathcal{R}_{\text{est}} \big\} \Big)$$

El costo relativo del sensor $i$ se define como:

$$r_{\text{cost}}(i) = \operatorname{clip}\left( \frac{\text{cost\_ewma}_i}{C_{\text{ref}}}, \; 0.25, \; 4.0 \right)$$

### 4.1 Justificación Teórica de la Mediana y el Truncamiento
1. **Robustez ante Outliers:** La media aritmética $\frac{1}{N}\sum c_j$ tiene punto de ruptura $\epsilon^* = 0$, lo que significa que un único sensor bloqueado en una llamada sincrónica durante 10 segundos distorsionaría el costo de referencia de todos los demás. La mediana tiene punto de ruptura óptimo $\epsilon^* = 0.50$.
2. **Cotas de Variación Relativa $[0.25, 4.0]$:** Limitar la relación a un rango dinámico de un factor $16\times$ (desde un cuarto hasta cuatro veces la mediana) previene que un sensor ultra-rápido gane prioridad infinita o que un sensor moderadamente pesado quede perpetuamente hambriento de atención.

---

## 5. Álgebra de Cuantización y Dequantización en Checkpoints

Para cumplir con las normas de privacidad del anfitrión y los límites estrictos de almacenamiento (el payload del automodelo no debe contener micro-timestamps ni números flotantes de precisión arbitraria que permitan la reconstrucción espectral de lecturas pasadas), el estado se somete a **cuantización discreta en clases cerradas**.

### 5.1 Cuantización Uniforme de Salud, Calidad y Madurez
Para cualquier variable normalizada $v \in [0, 1]$ con $K$ clases discretas ($K \in \{8, 16\}$):

$$\operatorname{Quantize}(v, K) = \operatorname{round}\Big( \operatorname{clip}(v, 0.0, 1.0) \cdot (K - 1) \Big) \in \{0, 1, \dots, K-1\}$$

La reconstrucción en el arranque (dequantización) es:

$$v_{\text{rec}} = \frac{\operatorname{Quantize}(v, K)}{K - 1}$$

El error de cuantización máximo está estrictamente acotado por:

$$\epsilon_{\max} = \frac{1}{2(K - 1)}$$

Para $K = 16$ clases, $\epsilon_{\max} = \frac{1}{30} \approx 0.0333$.

### 5.2 Cuantización Logarítmica de Costos
El tiempo de CPU varía en varias órdenes de magnitud (desde microsegundos hasta segundos). Una cuantización lineal perdería toda resolución en las latencias bajas.

Symbiont define una escala logarítmica con tiempo de referencia $S_{\text{ref}} = 1.0 \text{ s}$ y $K_{\text{cost}} = 16$ clases ([`_quantize_cost`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/selfmodel.py#L221-L229)):

$$\rho(c) = \min\left( 1.0, \; \frac{\ln\big(1 + \max(0, c)\big)}{\ln(1 + S_{\text{ref}})} \right) = \min\left( 1.0, \; \frac{\ln(1 + c)}{\ln(2)} \right)$$

$$\operatorname{Class}_{\text{cost}}(c) = \operatorname{round}\Big( \rho(c) \cdot (K_{\text{cost}} - 1) \Big) \in \{0, 1, \dots, 15\}$$

### 5.3 Dequantización Exacta Mediante Exponencial Inversa
Para recuperar el valor continuo estimado a partir de la clase discreta $q \in \{0, \dots, 15\}$:

$$\hat{\rho} = \frac{q}{K_{\text{cost}} - 1} = \frac{q}{15}$$

Despejando $c$ de la ecuación $\hat{\rho} = \frac{\ln(1 + c)}{\ln(2)}$:

$$\ln(1 + c) = \hat{\rho} \cdot \ln(2) \implies 1 + c = e^{\hat{\rho} \ln(2)} = 2^{\hat{\rho}}$$

$$c_{\text{rec}} = e^{\hat{\rho} \ln(2)} - 1 = \operatorname{expm1}\big( \hat{\rho} \cdot \ln(2) \big)$$

### 5.4 Distribución de Resolución de la Cuantización Logarítmica
La resolución efectiva $dc / dq$ se obtiene derivando:

$$\frac{dc}{dq} = \frac{\ln(2)}{15} \cdot 2^{q / 15}$$

- Para latencias pequeñas ($q=0, c \approx 0\,\text{ms}$): $\frac{dc}{dq} \approx \frac{0.693}{15} \approx 0.046 \text{ s} = 46 \text{ ms}$.
- Para latencias altas ($q=15, c \approx 1000\,\text{ms}$): $\frac{dc}{dq} \approx 2 \cdot 0.046 \approx 92 \text{ ms}$.

Esta transformación asigna naturalmente el doble de densidad de clases a las variaciones en micro-latencias que a las perturbaciones en latencias de segundo orden, optimizando la conservación de información bajo una cuota de apenas 4 bits por parámetro.
