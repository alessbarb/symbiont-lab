# Asignación Causal de Atención y Optimización de Presupuestos Finitos

> **Estado:** IMPLEMENTADO  
> **Tipo:** POLÍTICA HEURÍSTICA Y ASIGNACIÓN DE RECURSOS  
> **Módulos relacionados:** [`symbiont.core.attention`](../../src/symbiont/core/attention.py)

---

## 1. El Problema de la Atención Acotada

En cualquier sistema biológico o computacional que interactúa con un entorno de alta dimensionalidad, el ancho de banda perceptual es un recurso estrictamente limitado. Un organismo no puede muestrear todas las superficies de observación en cada tick con alta resolución.

El subsistema de atención de Symbiont ([`symbiont.core.attention`](../../src/symbiont/core/attention.py)) formaliza la selección de capacidades bajo cuatro principios rectores:

1. **Causalidad Estricta:** La selección de atención en el tick $t$ se realiza utilizando exclusivamente la información conocida antes de realizar cualquier nueva observación en $t$. No existe lookahead, etiquetas de amenaza ni recompensas futuras.
2. **Presupuesto Duro e Inviolable:** Existe un presupuesto escalar $B > 0$ por tick. La suma de los costos de las observaciones seleccionadas no puede exceder $B$.
3. **No-Clasificación (ADR-0003):** La atención es un mecanismo de optimización informacional, no un juicio de amenaza. Una capacidad que recibe atención no es declarada "anómala"; es simplemente una capacidad sobre la que existe mayor dispersión relativa o falta de aclimatación.
4. **Determinismo y Complejidad Acotada:** El algoritmo de selección opera en tiempo $O(n \log n)$ y memoria $O(n)$, con desempates deterministas por orden lexicográfico.

---

## 2. Formulación Matemática: De la Mochila 0/1 a la Heurística Voraz Desacoplada

Sea un conjunto de $N$ capacidades candidatas $\mathcal{C} = \{c_1, c_2, \dots, c_N\}$.
Para cada candidata $c_i$, se definen:

- $u_i \in [0, +\infty]$: La dispersión o incertidumbre de la línea base.
- $k_i \in (0, +\infty)$: El costo físico intrínseco de consumo de presupuesto.
- $r_i \in (0, +\infty)$: El costo o sesgo de ranking asignado por el automodelo.

El problema idealizado de optimización combinatoria corresponde al problema de la mochila 0/1:

$$\max_{\mathbf{z} \in \{0, 1\}^N} \sum_{i=1}^N z_i u_i \quad \text{sujeto a} \quad \sum_{i=1}^N z_i k_i \le B$$

### 2.1 Heurística Voraz vs. Mochila 0/1 Exacta

El problema de la mochila 0/1 es NP-duro. Los algoritmos de programación dinámica estándar requieren tiempo pseudo-polinomial y memoria dependiente de la discretización del presupuesto $B$. Si el presupuesto es continuo o cambia entre ticks, la programación dinámica introduce latencias variables (*computational jitter*), inadmisibles para el ciclo residente.

Por ello, Symbiont adopta una **política heurística voraz de una sola pasada** en tiempo $O(N \log N)$.

> **Matiz Teórico sobre Dantzig (1957):**  
> Ordenar por densidad de valor es óptimo para la **relajación continua (mochila fraccionaria)**. Para la mochila 0/1 entera implementada, la heurística voraz simple no posee garantías de optimalidad general y puede, en casos extremos construidos ad-hoc, desviarse significativamente del óptimo si no se añaden fases de ramificación. Symbiont asume conscientemente este compromiso para garantizar determinismo, ejecución estricta en una pasada y predictibilidad temporal.

---

## 3. Cuantificación de Dispersión Relativa: Coeficiente de Variación

La dispersión estadística $u(c_i)$ se calcula en [`uncertainty_from_baseline`](../../src/symbiont/core/attention.py#L86-L104) a partir de $(\mu_i, \sigma_i, n_i)$:

$$u(c_i) = \begin{cases}
+\infty & \text{si la capacidad no está aclimatada } (n_i < N_{\text{min}}) \\
\sigma_i & \text{si } n_i \ge N_{\text{min}} \land \mu_i = 0.0 \\
\frac{\sigma_i}{|\mu_i|} & \text{si } n_i \ge N_{\text{min}} \land \mu_i \neq 0.0
\end{cases}$$

### 3.1 Propiedades y Limitaciones del Coeficiente de Variación ($c_v$)
1. **Prioridad Epistémica de lo Desconocido:**
   Una señal sin muestras suficientes recibe $u = +\infty$, superando a cualquier señal ya establecida y garantizando la exploración inicial de nuevas capacidades.
2. **Invariancia de Escala:**
   Para señales positivas con escala de razón, si $Y = \alpha X$ con $\alpha > 0$, entonces $c_v(Y) = c_v(X)$, lo que permite comparar magnitudes dispares sin reescalado manual.

> **Advertencia sobre Entropía y Escala:**  
> El coeficiente de variación $c_v = \frac{\sigma}{|\mu|}$ es una medida de **dispersión relativa**, no de entropía. La entropía diferencial gaussiana depende únicamente de la varianza: $h(X) = \frac{1}{2}\ln(2\pi e \sigma^2)$, no de $\mu$.  
> Presenta además dos limitaciones teóricas:
> - Si $\mu \approx 0$, $c_v$ diverge independientemente de cuán pequeña y concentrada sea la varianza $\sigma^2$.
> - Cuando $\mu = 0$, el código conmuta al desvío típico $\sigma_i$, que deja de ser adimensional.  
> Su uso en Symbiont se justifica como una regla heurística de ingeniería para priorizar señales ruidosas en relación con su media de operación.

---

## 4. Desacoplamiento Formal entre Costo de Consumo y Costo de Ranking

> **Clasificación:** PROPOSICIÓN / INVARIANTE DE SEGURIDAD

Una debilidad habitual en sistemas con presupuestos aprendidos es que un componente interno aprenda que una acción "cuesta cero" para engañar al planificador y consumir recursos desmedidos.

Symbiont resuelve esto desacoplando el criterio de ordenación del consumo físico:

```text
Candidato c_i:
  ├── Incertidumbre: u_i
  ├── Costo de Ranking: r_i   ──► Modula la PRIORIDAD (orden voraz)
  └── Costo Físico:   k_i   ──► Descuenta el PRESUPUESTO DURO B
```

### 4.1 Función de Ordenación Determinista
Los candidatos se ordenan lexicográficamente por la tupla:

$$\operatorname{Key}(c_i) = \left( -\frac{u_i}{k_i \cdot r_i}, \;\; \operatorname{name}(c_i) \right)$$

El ratio de prioridad es:

$$\rho_i = \frac{u_i}{k_i \cdot r_i}$$

El término `name` resuelve cualquier empate de forma estrictamente determinista, eliminando la dependencia del orden interno de las tablas hash.

### 4.2 Invarianza de Presupuesto Duro
**Proposición (Inviolabilidad del Presupuesto):**  
Ningún sesgo aprendido en $r_i$ puede provocar que la suma de los costos de las capacidades seleccionadas supere el presupuesto configurado $B$.

*Demostración:*  
Sea $\mathcal{A} \subseteq \mathcal{C}$ el subconjunto de candidatos elegidos por el bucle voraz:
```python
selected = []
remaining = B
for candidate in ranked:
    if candidate.cost <= remaining:
        selected.append(candidate)
        remaining -= candidate.cost
```
Cada elemento $c \in \mathcal{A}$ se incorpora si y solo si $k_c \le \text{remaining}$. La actualización decrementa estrictamente $\text{remaining} \leftarrow \text{remaining} - k_c$, donde $k_c$ es el costo físico gobernado e inmutable. Por inducción sobre los elementos agregados:

$$\sum_{c \in \mathcal{A}} k_c \le B \quad \blacksquare$$

El parámetro aprendido $r_i$ altera exclusivamente qué capacidades compiten primero por el presupuesto, pero jamás altera la cantidad física de cuota que consumen.
