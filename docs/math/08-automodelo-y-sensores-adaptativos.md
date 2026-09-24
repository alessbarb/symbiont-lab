# Automodelo del Organismo, Costos y Cuantización Discreta

> **Estado:** IMPLEMENTADO  
> **Tipo:** ESTIMACIÓN ENDÓGENA Y ESPECIFICACIÓN DE PERSISTENCIA CUANTIZADA  
> **Módulos relacionados:** [`symbiont.core.selfmodel`](../../src/symbiont/core/cognition/self_model.py)

---

## 1. Justificación y Objetivos del Automodelo

Un organismo adaptativo que interactúa con un anfitrión real no puede asumir que todos sus sensores son permanentemente funcionales ni que todas las lecturas conllevan el mismo costo de CPU.

- Dispositivos con controladores lentos o interfaces con timeout pueden degradar el ciclo cognitivo completo.
- Si el organismo carece de un modelo endógeno de sus propios sensores, continuará asignando atención a canales muertos o excesivamente gravosos.

[`SelfModel`](../../src/symbiont/core/cognition/self_model.py) formaliza un **automodelo acotado y no-semántico** que evalúa continuamente:

1. **Costo Computacional Atribuido:** Latencia de muestreo medida en segundos.
2. **Salud y Calidad Operativa:** Éxito en la recolección de lecturas.
3. **Confianza del Sensor:** Función de madurez histórica y salud.

---

## 2. Dinámica Temporal: EWMA y Decaimiento con Zona de Gracia

Las métricas del automodelo se suavizan mediante un filtro EWMA con constante $\alpha = 0.06$ ([`SELF_MODEL_EWMA_ALPHA`](../../src/symbiont/core/cognition/self_model.py#L10)):

$$\mu_t = \alpha \cdot x_t + (1 - \alpha) \cdot \mu_{t-1}$$

### 2.1 Ecuación de Relajación Inactiva (*Idle Decay*)

Cuando un sensor deja de ser muestreado durante $\Delta t = t_{\text{actual}} - t_{\text{último}}$ ticks:

- En pausas breves, el estado aprendido debe persistir intacto.
- En ausencias prolongadas, el estado debe relajarse hacia un valor neutro $x_{\text{neutral}}$ (salud hacia $0.5$, confianza hacia $0.0$).

Se define una **zona de gracia** de $\tau_{\text{grace}} = 20$ ticks ([`IDLE_GRACE_TICKS`](../../src/symbiont/core/cognition/self_model.py#L13)):

$$\text{steps} = \max\Big(0, \; \Delta t - \tau_{\text{grace}}\Big)$$

$$x_{\text{decayed}}(\Delta t) = x_{\text{neutral}} + \big( x_{\text{last}} - x_{\text{neutral}} \big) \cdot (1 - \alpha)^{\text{steps}}$$

```text
Valor del Estado
   ▲
1.0│  x_last
   │  ─────────────┐ (Zona de gracia: primeros 20 ticks sin cambio)
   │               ╲
   │                ╲  Decaimiento suave: (1 - α)^steps
0.5│─────────────────●───────────────────────────  x_neutral (Salud = 0.5)
   │                  `─.
   │                     `───.
0.0└────────┬──────────────┬──────────────► Ticks Inactivos Δt
   0        20 (τ_grace)   50             100
```

---

## 3. Función de Madurez Logarítmica Normalizada

Para determinar cuándo un sensor dispone de soporte muestral suficiente ([`_maturity`](../../src/symbiont/core/cognition/self_model.py#L61-L65)):

$$\operatorname{Maturity}(s) = \begin{cases}
0.0 & \text{si } s \le 0 \\
\min\left( 1.0, \; \frac{\ln(1 + s)}{\ln(1 + N_{\min})} \right) & \text{si } s > 0 \quad (\text{con } N_{\min} = 5)
\end{cases}$$

### 3.1 Propiedades del Perfil Logarítmico
1. **Derivada decreciente:** El primer éxito eleva la madurez a $\frac{\ln(2)}{\ln(6)} \approx 0.387$, mientras que los éxitos posteriores aportan rendimientos marginales decrecientes hasta alcanzar $1.0$ en $s = 5$.
2. **Inhibición Temprana:** Modula la confianza del sensor impidiendo que un solo muestreo afortunado otorgue credibilidad plena.

### 3.2 El Eje de Salud y Calidad en la Implementación Actual
La confianza compuesta se calcula formalmente como:

$$\operatorname{Target}_{\text{conf}} = \operatorname{clip}\Big( 0.70 \cdot H + 0.30 \cdot Q, \; 0.0, \; 1.0 \Big) \cdot \operatorname{Maturity}(s)$$

> **Nota de Implementación (Colapso Efectivo de Ejes):**  
> En la base de código actual (`v0.53`), tanto $H$ (`health_ewma`) como $Q$ (`quality_ewma`) se actualizan a partir del mismo valor de salud `health_obs`, y en la deserialización del checkpoint `quality_ewma` se restaura directamente desde `health_class`. Por consiguiente, en la práctica actual:
> $$H_t = Q_t \implies 0.70 \cdot H_t + 0.30 \cdot Q_t \equiv H_t$$
> Ambas variables representan hoy un único eje operativo efectivo. La separación matemática anticipa la especialización planificada:
> - *Salud:* Disponibilidad y éxito de invocación de la sonda.
> - *Calidad:* Precisión y fidelidad del payload entregado.

---

## 4. Normalización de Costo Relativo respecto a la Mediana

Para que la ponderación de costos sea agnóstica a la velocidad absoluta de la máquina anfitriona ([`relative_cost`](../../src/symbiont/core/cognition/self_model.py#L129-L142)):

Dado un conjunto de sensores de referencia ya consolidados $\mathcal{R}_{\text{est}}$:

$$C_{\text{ref}} = \operatorname{median}\Big( \big\{ \text{cost\_ewma}_j \;\big|\; j \in \mathcal{R}_{\text{est}} \big\} \Big)$$

$$r_{\text{cost}}(i) = \operatorname{clip}\left( \frac{\text{cost\_ewma}_i}{C_{\text{ref}}}, \; 0.25, \; 4.0 \right)$$

El uso de la mediana ofrece un punto de ruptura del $50\%$ frente a llamadas bloqueadas atípicas. El rango acotado $[0.25, 4.0]$ limita la influencia del costo en la prioridad a un factor máximo de $16\times$.

---

## 5. Cuantización y Reducción de Reconstructibilidad en Checkpoints

Para mitigar la reconstrucción de telemetría y acotar el payload a 4 bits por métrica, el automodelo proyecta los estados continuos en clases cerradas.

### 5.1 Cuantización Uniforme de Salud y Confianza
Para variables en $[0, 1]$ con $K$ clases ($K=16$ para salud y confianza; $K=8$ para madurez):

$$\operatorname{Quantize}(v, K) = \operatorname{round}\Big( \operatorname{clip}(v, 0.0, 1.0) \cdot (K - 1) \Big) \in \{0, \dots, K-1\}$$

El **valor representativo reconstruido** al restaurar es:

$$\hat{v} = \frac{\operatorname{Quantize}(v, K)}{K - 1}$$

### 5.2 Cuantización Logarítmica de Costos
Para el costo de ejecución en segundos con referencia $S_{\text{ref}} = 1.0 \text{ s}$ y $K_{\text{cost}} = 16$ clases ([`_quantize_cost`](../../src/symbiont/core/cognition/self_model.py#L221-L229)):

$$\rho(c) = \min\left( 1.0, \; \frac{\ln\big(1 + \max(0, c)\big)}{\ln(2)} \right) = \min\big( 1.0, \; \log_2(1 + \max(0, c)) \big)$$

$$\operatorname{Class}_{\text{cost}}(c) = \operatorname{round}\Big( 15 \cdot \rho(c) \Big) \in \{0, 1, \dots, 15\}$$

El valor representativo reconstruido al deserializar el checkpoint se obtiene mediante la inversa exponencial:

$$\hat{c}(q) = \operatorname{expm1}\left( \frac{q}{15} \cdot \ln(2) \right) = 2^{q / 15} - 1$$

### 5.3 Análisis Analítico de las Celdas de Cuantización
Calculando explícitamente los intervalos de partición y valores representativos:

1. **Límite Superior de la Celda Cero ($q=0$):**  
   Debido a que Python implementa la regla de redondeo al par más cercano (*round-half-to-even* / IEEE 754), el punto medio exacto $0.5$ se redondea a $0$ (`round(0.5) == 0`). Por consiguiente, la condición de asignación a la clase 0 incluye el extremo:
   $$15 \cdot \log_2(1 + c) \le 0.5 \iff \log_2(1 + c) \le \frac{1}{30} \iff c \le 2^{1/30} - 1$$
   $$c_{\text{boundary}, 0} = 2^{1/30} - 1 \approx \mathbf{23.374 \text{ ms}}$$
   La frontera matemática exacta es $2^{1/30} - 1$ ($\approx 23.374\text{ ms}$ como aproximación decimal). Cualquier latencia continua en el intervalo cerrado $[0.0, \; 2^{1/30} - 1]$ se asigna a la clase $q = 0$, cuyo valor representativo reconstruido es $\hat{c}(0) = 0.0 \text{ ms}$.

2. **Primera Reconstrucción Positiva ($q=1$):**  
   Para la clase $q=1$, el valor representativo reconstruido es:
   $$\hat{c}(1) = 2^{1/15} - 1 \approx \mathbf{47.294 \text{ ms}}$$
   Esta clase cubre el intervalo $(2^{1/30} - 1, \; 2^{1.5/15} - 1) \approx (23.374 \text{ ms}, \; 71.773 \text{ ms})$.

> **Implicaciones Prácticas de Ingeniería:**  
> - **Colapso de Micro-Latencias:** Las latencias de ejecución típicas en sondeos de memoria o lectura de `/proc` (50 µs, 1 ms, 10 ms, 20 ms) caen todas dentro de $[0.0, \; 2^{1/30} - 1]$, colapsando idénticamente en la clase 0 y reconstruyéndose como 0.0 ms al restaurar un checkpoint.
> - **Rango Efectivo de Discriminación:** La función logarítmica comienza a resolver diferencias a partir de la frontera $2^{1/30} - 1 \approx 23.374$ ms, permitiendo discriminar operaciones pesadas de E/S o inspección periódica de disco frente a comprobaciones ligeras.
> - **Irreversibilidad y Pérdida de Escala en Bajos Costos:** La función de cuantización $c \mapsto q$ (y por ende la composición $c \mapsto \hat{c}$) es una transformación no inyectiva que comprime infinitos valores en 16 clases discretas, aun cuando la función de reconstrucción $\hat{c}: \{0, \dots, 15\} \to \mathbb{R}^+$ es estrictamente inyectiva sobre las clases. Por encima de $2^{1/30} - 1 \approx 23.374$ ms se retiene una progresión geométrica aproximada entre clases sucesivas; sin embargo, para toda latencia $c \le 2^{1/30} - 1$, la escala colapsa a cero, eliminando cualquier diferenciación interna entre operaciones ligeras.
