# Asignación Causal de Atención y Optimización de Presupuestos Finitos

## 1. El Problema de la Atención Acotada

En cualquier sistema biológico o computacional que interactúa con un entorno de alta dimensionalidad, el ancho de banda sensorial es un recurso estrictamente limitado. Un organismo no puede inspeccionar todas las superficies de observación simultáneamente en cada tick con alta resolución.

El subsistema de atención de Symbiont ([`symbiont.core.attention`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/attention.py)) formaliza la selección de qué capacidades merecen inversión de recursos bajo cuatro axiomas fundamentales:

1. **Causalidad Estricta:** La selección de atención en el tick $t$ debe realizarse utilizando únicamente la información conocida antes de realizar cualquier nueva observación en $t$. No existe ninguna señal futura, etiqueta de amenaza ni recompensa posterior.
2. **Presupuesto Duro e Inviolable:** Existe una cuota escalar máxima $B > 0$ por tick. El costo acumulado de las observaciones seleccionadas no puede superar $B$.
3. **No-Clasificación (ADR-0003):** La atención es un mecanismo de optimización de ganancia epistémica, no un juicio de amenaza. Una señal que recibe alta atención no es declarada "peligrosa" o "anómala"; es simplemente una señal sobre la cual el organismo posee mayor incertidumbre relativa o menor conocimiento previo.
4. **Determinismo y Complejidad Acotada:** El algoritmo de selección debe ser $O(n \log n)$ en tiempo, $O(n)$ en memoria y completamente determinista (empates resueltos por orden lexicográfico).

---

## 2. Formulación Matemática: La Heurística de la Mochila Voraz

Sea un conjunto de $N$ capacidades candidatas $\mathcal{C} = \{c_1, c_2, \dots, c_N\}$.
Para cada candidata $c_i$, se definen tres cantidades:

- $u_i \in [0, +\infty]$: La incertidumbre estadística del estado actual.
- $k_i \in (0, +\infty)$: El costo intrínseco de consumo de presupuesto (por defecto $k_i = 1.0$).
- $r_i \in (0, +\infty)$: El sesgo de costo de ranking relativo (por defecto $r_i = 1.0$).

El problema formal de optimización combinatoria equivale al problema de la mochila 0/1 (*0/1 Knapsack Problem*):

$$\max_{\mathbf{z} \in \{0, 1\}^N} \sum_{i=1}^N z_i u_i \quad \text{sujeto a} \quad \sum_{i=1}^N z_i k_i \le B$$

### 2.1 Justificación Teórica de la Heurística Voraz vs. Solución Exacta

El problema de la mochila 0/1 es NP-duro. Los algoritmos de programación dinámica estándar requieren tiempo pseudo-polinomial $O(N \cdot B)$ y espacio proporcional al presupuesto discretizado. Si el presupuesto es continuo o cambia dinámicamente, la programación dinámica introduce latencia variable e impredecible (*computational jitter*), violando los límites de tiempo real del ciclo cognitivo.

Por tanto, Symbiont adopta la **heurística voraz por densidad de valor de Dantzig (1957)**, que proporciona la solución óptima para la relajación continua del problema y garantiza una cota de aproximación en tiempo $O(N \log N)$ de una sola pasada.

---

## 3. Función de Incertidumbre de la Línea Base: Coeficiente de Variación

La incertidumbre $u(c_i)$ se calcula en [`uncertainty_from_baseline`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/attention.py#L86-L104) a partir de la estadística descriptiva acumulada $(\mu_i, \sigma_i, n_i)$:

$$u(c_i) = \begin{cases}
+\infty & \text{si la capacidad no está aclimatada } (n_i < N_{\text{min}}) \\
\sigma_i & \text{si } n_i \ge N_{\text{min}} \land \mu_i = 0.0 \\
\frac{\sigma_i}{|\mu_i|} & \text{si } n_i \ge N_{\text{min}} \land \mu_i \neq 0.0
\end{cases}$$

### 3.1 Propiedades Matemáticas del Coeficiente de Variación ($c_v$)
1. **Prioridad Epistémica de lo Inexplorado:**
   Si una señal nunca ha sido observada o no ha acumulado suficientes muestras para formar una distribución estable, su incertidumbre es infinitamente superior a cualquier señal ya conocida:
   $$u(\text{no aclimatado}) = +\infty > u(\text{aclimatado}) \quad \forall \text{ baseline existente}$$
   Esto garantiza que cada nueva capacidad descubierta en el sistema anfitrión gane automáticamente el presupuesto de atención frente a capacidades veteranas.

2. **Invariancia de Escala:**
   Sea una señal $X$ con media $\mu$ y desviación $\sigma$. Si se aplica un cambio de unidades lineales $Y = \alpha X$ con $\alpha > 0$:
   $$\mu_Y = \alpha \mu_X, \quad \sigma_Y = \alpha \sigma_X \implies c_v(Y) = \frac{\alpha \sigma_X}{\alpha |\mu_X|} = c_v(X)$$
   El coeficiente de variación es adimensional. Esto permite comparar directamente en la misma escala señales con órdenes de magnitud dispares (ej. uso de CPU en $[0, 1]$ frente a memoria en bytes en $[0, 10^{10}]$) sin requerir normalizaciones manuales arbitrarias.

3. **Interpretación Informacional:**
   Una señal cuya desviación típica es grande en proporción a su valor medio es aquella cuya dispersión relativa refleja un proceso estocástico menos concentrado, lo que maximiza la entropía diferencial de la distribución gaussiana asociada:
   $$h(X) = \frac{1}{2} \ln(2\pi e \sigma^2)$$

---

## 4. Desacoplamiento Causal entre Costo de Consumo y Costo de Ranking

Una vulnerabilidad clásica en sistemas adaptativos con presupuestos aprendidos es el *secuestro de presupuesto*: si un módulo interno aprende a estimar que una operación "cuesta muy poco", el planificador voraz podría empaquetar cientos de candidatos en un solo tick, saturando los recursos físicos del anfitrión.

Para blindar formalmente el sistema contra este riesgo, Symbiont introduce en la versión v0.53 una **separación estricta entre costo de ranking y costo de consumo**:

```text
Candidato c_i:
  ├── Incertidumbre: u_i
  ├── Costo de Ranking: r_i   ──► Determina la PRIORIDAD (orden de clasificación)
  └── Costo Físico:   k_i   ──► Determina el CONSUMO REAL del presupuesto duro B
```

### 4.1 La Función de Ordenación
Los candidatos se ordenan de acuerdo a la clave tupla determinista:

$$\operatorname{Key}(c_i) = \left( -\frac{u_i}{k_i \cdot r_i}, \;\; \operatorname{name}(c_i) \right)$$

El ratio voraz efectivo es:

$$\rho_i = \frac{u_i}{k_i \cdot r_i}$$

- A mayor incertidumbre $u_i$, mayor prioridad.
- A mayor costo de consumo $k_i$ o mayor penalización de ranking $r_i$, menor prioridad.
- El segundo término de la tupla (`name`) resuelve empates mediante orden lexicográfico estricto, garantizando determinismo bit a bit en cualquier arquitectura o plataforma.

### 4.2 Algoritmo de Asignación y Consumo Invariante
Sea $\mathcal{C}_{\text{ranked}} = (c_{(1)}, c_{(2)}, \dots, c_{(N)})$ la secuencia de candidatos ordenada según $\operatorname{Key}(\cdot)$.
El conjunto de asignaciones seleccionadas $\mathcal{A}$ se construye iterativamente:

```python
selected = []
remaining_budget = B

for candidate in ranked:
    if candidate.cost <= remaining_budget:
        selected.append(candidate)
        remaining_budget -= candidate.cost
```

### 4.3 Demostración de Seguridad contra Manipulación de Presupuesto
**Teorema:** Ningún sesgo introducido por un modelo de autoconocimiento en $r_i$ puede forzar al planificador a consumir un presupuesto superior a $B$.

*Demostración:*
Sea $r_i \to 0^+$ un sesgo extremo asignado a una capacidad $c_i$.
El ratio de ranking diverge:
$$\rho_i = \frac{u_i}{k_i \cdot r_i} \to +\infty$$
Esto sitúa a $c_i$ en la primera posición de la lista de ordenación ($c_{(1)} = c_i$).
Sin embargo, al evaluar la inclusión de $c_i$, la condición de aceptación verifica:
$$k_i \le B$$
Si $k_i \le B$, $c_i$ es seleccionado y el presupuesto remanente se actualiza exactamente a:
$$B' = B - k_i$$
La cantidad $k_i$ está gobernada de forma inmutable por la especificación de la plataforma o del host, independiente de $r_i$. Como la deducción se efectúa siempre sobre $k_i$, la suma total de las capacidades seleccionadas satisface idénticamente:
$$\sum_{c \in \mathcal{A}} k_c \le B \quad \blacksquare$$

Esto previene que una perturbación en los parámetros aprendidos del organismo degrade las garantías de consumo de CPU o tiempo de ejecución otorgadas al propietario del anfitrión.
